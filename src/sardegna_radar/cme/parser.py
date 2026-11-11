"""Streaming PDF / ZIP / P7M Computo Metrico Estimativo (CME) parser."""

from __future__ import annotations

from dataclasses import dataclass, field
import io
import json
from pathlib import Path
import re
from typing import Any
import zipfile

import httpx
import pdfplumber

from sardegna_radar.cme.catalog_rules import check_cme_hard_exclusion, classify_cme_spec
from sardegna_radar.config import RadarSettings
from sardegna_radar.exceptions import CMEParseError
from sardegna_radar.models import CAVProductCategory, CMEItem, ProductLine, parse_italian_currency
from sardegna_radar.scrapers.base import build_async_http_client

_INT_RE = re.compile(r"^\d{1,4}$")
_NOISE_DESC_RE = re.compile(
    r"^(?:DESIGNAZIONE\s+DEI\s+LAVORI|R\s*I\s*P\s*O\s*R\s*T\s*O|A\s+R\s*I\s*P\s*O\s*R\s*T\s*A\s*R\s*E|"
    r"TOTALE\b|Parziale\b|COMMITTENTE:|PriMus\s+by\b|pag\.\s*\d+)",
    re.IGNORECASE,
)
_CAT_HEADER_RE = re.compile(r"\(Cat\s*\d+\)\s*$", re.IGNORECASE)

# Filename priority heuristics for selecting ONLY the Computo Metrico inside multi-file project ZIPs
_CME_POSITIVE_NAME_RE = re.compile(
    r"(?:computo[\s_\-]*metrico|\bcme\b|all[\.\s_\-]*b.*computo|metrico[\s_\-]*estimativo)",
    re.IGNORECASE,
)
_CME_NEGATIVE_NAME_RE = re.compile(
    r"(?:tavol[ae]|planimetri|relazion[ei]|capitolat[oi]|cronoprogramma|schema[\s_\-]*contratto|"
    r"piano[\s_\-]*sicurezza|\bpsc\b|analisi[\s_\-]*prezzi|incidenza[\s_\-]*manodopera)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class RawCMEItem:
    """Raw extracted row from a Computo Metrico PDF before catalog filtering."""

    item_number: int | None
    tariff_code: str
    spec_text: str
    full_description: str
    unit: str
    quantity: float
    unit_price_eur: float | None = None
    total_price_eur: float | None = None
    excluded_reason: str | None = None


@dataclass(slots=True)
class CMEParseResult:
    """Structured output of CMEParser suitable for CLI, Telegram, and Milestone 2 Dropzone API."""

    selected_filename: str
    total_raw_items: int
    matched_items: list[CMEItem] = field(default_factory=list)
    raw_items: list[RawCMEItem] = field(default_factory=list)


def strip_p7m_pdf_envelope(raw_bytes: bytes) -> bytes:
    """Extract embedded `%PDF-...%%EOF` payload from an unencrypted Italian `.pdf.p7m` CAdES file."""
    start = raw_bytes.find(b"%PDF-")
    if start == -1:
        raise CMEParseError("No '%PDF-' header found in binary stream.")
    eof_idx = raw_bytes.rfind(b"%%EOF")
    if eof_idx != -1 and eof_idx > start:
        end = eof_idx + len(b"%%EOF")
        # Keep trailing newline if present
        while end < len(raw_bytes) and raw_bytes[end : end + 1] in (b"\r", b"\n"):
            end += 1
        return raw_bytes[start:end]
    return raw_bytes[start:]


def select_cme_member_from_zip(zf: zipfile.ZipFile) -> str:
    """Pick the single Computo Metrico PDF/P7M entry inside a project ZIP without extracting drawings."""
    candidates: list[tuple[int, int, str]] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        lower = info.filename.lower()
        if not (lower.endswith(".pdf") or lower.endswith(".pdf.p7m")):
            continue
        score = 0
        if _CME_POSITIVE_NAME_RE.search(info.filename):
            score += 100
        elif "computo" in lower:
            score += 75
        elif "elenco" in lower and "prezzi" in lower:
            score += 25
        if _CME_NEGATIVE_NAME_RE.search(info.filename):
            score -= 80
        # Prefer smaller text PDFs over huge CAD vector sheets when scores tie
        candidates.append((score, -info.file_size, info.filename))

    if not candidates:
        raise CMEParseError("No PDF or PDF.P7M files found inside ZIP archive.")

    candidates.sort(reverse=True)
    best_score, _, best_name = candidates[0]
    if best_score < 0:
        raise CMEParseError(f"ZIP contains PDFs but none resemble a Computo Metrico: {best_name}")
    return best_name


def _reconstruct_tariff_code(tokens: list[str]) -> str:
    """Join wrapped ACCA PriMus left-column tariff fragments (`SAR26_PF.0` + `003.0015.000` + `2.A`)."""
    if not tokens:
        return ""
    primary: list[str] = []
    for idx, tok in enumerate(tokens):
        # PriMus often prints a secondary national sub-code `PF.0003...` below `SAR26_PF...`
        if idx > 0 and tok.startswith("PF.") and any("PF." in prev for prev in primary):
            break
        primary.append(tok)
    return "".join(primary).strip()


class CMEParser:
    """Deterministic streaming parser for Italian Computo Metrico Estimativo (`.pdf`, `.p7m`, `.zip`)."""

    def __init__(self, settings: RadarSettings | None = None) -> None:
        self.settings = settings or RadarSettings()

    def parse_path(self, path: Path | str) -> CMEParseResult:
        """Parse a local `.pdf`, `.pdf.p7m`, or `.zip` file."""
        file_path = Path(path)
        if not file_path.exists():
            raise CMEParseError(f"CME file does not exist: {file_path}")
        return self.parse_bytes(file_path.read_bytes(), filename=file_path.name)

    def parse_bytes(self, data: bytes, filename: str = "computo.pdf") -> CMEParseResult:
        """Parse in-memory bytes of a `.zip` archive, `.pdf.p7m` envelope, or plain `.pdf`."""
        if not data:
            raise CMEParseError("Empty CME byte stream.")

        selected_name = filename
        pdf_bytes = data

        if filename.lower().endswith(".zip") or data[:4] == b"PK\x03\x04":
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    selected_name = select_cme_member_from_zip(zf)
                    info = zf.getinfo(selected_name)
                    if info.file_size > 60 * 1024 * 1024:
                        raise CMEParseError(
                            f"Uncompressed CME entry '{selected_name}' exceeds 60 MB safety cap."
                        )
                    with zf.open(selected_name) as member_stream:
                        pdf_bytes = member_stream.read(60 * 1024 * 1024 + 1)
                    if len(pdf_bytes) > 60 * 1024 * 1024:
                        raise CMEParseError(
                            f"Decompressed CME stream '{selected_name}' exceeds 60 MB safety cap."
                        )
            except zipfile.BadZipFile as exc:
                raise CMEParseError(f"Invalid ZIP archive '{filename}': {exc}") from exc

        pdf_bytes = strip_p7m_pdf_envelope(pdf_bytes)
        raw_items = self._extract_raw_items_from_pdf(pdf_bytes)
        matched_items = self._classify_items(raw_items)
        return CMEParseResult(
            selected_filename=selected_name,
            total_raw_items=len(raw_items),
            matched_items=matched_items,
            raw_items=raw_items,
        )

    async def parse_url(
        self,
        url: str,
        client: httpx.AsyncClient | None = None,
        max_bytes: int = 45 * 1024 * 1024,
    ) -> CMEParseResult:
        """Stream a remote `.pdf` or `.zip` URL (e.g. SardegnaCAT `DownloadAttach.asp`) in memory."""
        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            chunks: list[bytes] = []
            downloaded = 0
            filename = url.rsplit("/", 1)[-1].split("?")[0] or "remote_cme.pdf"
            async with http_client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    raise CMEParseError(f"Remote CME download returned HTTP {resp.status_code}: {url}")
                cd = resp.headers.get("content-disposition", "")
                cd_match = re.search(r'filename="?([^";]+)"?', cd, re.IGNORECASE)
                if cd_match:
                    filename = cd_match.group(1).strip()
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise CMEParseError(f"Remote archive exceeds {max_bytes} bytes safety cap: {url}")
                    chunks.append(chunk)
            return self.parse_bytes(b"".join(chunks), filename=filename)
        finally:
            if owns_client:
                await http_client.aclose()

    def _extract_raw_items_from_pdf(self, pdf_bytes: bytes) -> list[RawCMEItem]:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                primus_items = self._extract_primus_layout(pdf)
                if primus_items:
                    return primus_items
                return self._extract_generic_fallback(pdf)
        except CMEParseError:
            raise
        except Exception as exc:
            raise CMEParseError(f"Failed to read CME PDF via pdfplumber: {exc}") from exc

    def _extract_primus_layout(self, pdf: pdfplumber.PDF) -> list[RawCMEItem]:
        """Coordinate-aware parser for ACCA PriMus / standard Italian multi-page CME tables."""
        items: list[RawCMEItem] = []
        active_num: int | None = None
        active_tariff_tokens: list[str] = []
        active_desc_lines: list[str] = []
        expected_next_num = 1

        for page in pdf.pages:
            words = page.extract_words(x_tolerance=2, y_tolerance=2)
            if not words:
                continue

            # Only process pages that have the CME table columns (`Num.Ord.` / `TARIFFA` / `SOMMANO`)
            page_header_texts = {w["text"] for w in words[:45]}
            if "Num.Ord." not in page_header_texts and "TARIFFA" not in page_header_texts:
                continue

            # Group words into visual horizontal lines (~3pt vertical tolerance)
            rows_by_bucket: dict[int, list[dict[str, Any]]] = {}
            for w in words:
                top = float(w["top"])
                if top < 62.0 or top > 805.0:
                    continue  # Skip page header (`Num.Ord. / DESIGNAZIONE`) and footer (`COMMITTENTE:`)
                bucket = round(top / 3.2)
                rows_by_bucket.setdefault(bucket, []).append(w)

            for bucket in sorted(rows_by_bucket):
                row_words = sorted(rows_by_bucket[bucket], key=lambda item: float(item["x0"]))
                left_tokens = [w["text"] for w in row_words if float(w["x0"]) < 78.0]
                desc_tokens = [w["text"] for w in row_words if 78.0 <= float(w["x0"]) < 302.0]
                right_tokens = [w["text"] for w in row_words if float(w["x0"]) >= 420.0]

                desc_line = " ".join(desc_tokens).strip()
                if desc_line and (_NOISE_DESC_RE.search(desc_line) or _CAT_HEADER_RE.search(desc_line)):
                    continue

                # Check if a new numbered CME item starts on this row (`1`, `2`, ..., `43`)
                if (
                    len(left_tokens) >= 1
                    and _INT_RE.match(left_tokens[0])
                    and desc_line
                    and "SOMMANO" not in desc_line
                ):
                    cand_num = int(left_tokens[0])
                    if cand_num == expected_next_num or (active_num is None and cand_num >= 1):
                        active_num = cand_num
                        expected_next_num = cand_num + 1
                        active_tariff_tokens = list(left_tokens[1:])
                        active_desc_lines = [desc_line]
                        continue

                if active_num is None:
                    continue

                # Accumulate wrapped tariff tokens from left column (`SAR26_PF.0`, `003.0015.000`, `2.A`)
                for lt in left_tokens:
                    if not _INT_RE.match(lt) or active_tariff_tokens:
                        active_tariff_tokens.append(lt)

                # Check if this row closes the item with `SOMMANO <unit>`
                if "SOMMANO" in desc_tokens:
                    som_idx = desc_tokens.index("SOMMANO")
                    unit = " ".join(desc_tokens[som_idx + 1 :]).strip()
                    nums = [
                        val
                        for tok in right_tokens
                        if (val := parse_italian_currency(tok)) is not None
                    ]
                    qty = nums[0] if len(nums) >= 1 else 0.0
                    unit_price = nums[1] if len(nums) >= 2 else None
                    total_price = nums[2] if len(nums) >= 3 else (nums[-1] if len(nums) == 2 else None)

                    full_desc = " ".join(active_desc_lines).strip()
                    # Isolate pure tariff specification before `Categoria di Opera` measurement lines
                    spec_text = re.split(r"\bCategoria\s+di\s+Opera\b", full_desc, maxsplit=1, flags=re.IGNORECASE)[0].strip()

                    items.append(
                        RawCMEItem(
                            item_number=active_num,
                            tariff_code=_reconstruct_tariff_code(active_tariff_tokens),
                            spec_text=spec_text or full_desc,
                            full_description=full_desc,
                            unit=unit,
                            quantity=qty,
                            unit_price_eur=unit_price,
                            total_price_eur=total_price,
                        )
                    )
                    active_num = None
                    active_tariff_tokens = []
                    active_desc_lines = []
                elif desc_line:
                    active_desc_lines.append(desc_line)

        return items

    def _extract_generic_fallback(self, pdf: pdfplumber.PDF) -> list[RawCMEItem]:
        """Fallback table extractor for non-PriMus tabular PDFs (e.g. Excel-exported CMEs)."""
        items: list[RawCMEItem] = []
        seq = 1
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    cells = [str(c or "").strip() for c in row if str(c or "").strip()]
                    if len(cells) < 3:
                        continue
                    joined = " ".join(cells)
                    if _NOISE_DESC_RE.search(joined):
                        continue
                    qty = parse_italian_currency(cells[-2]) if len(cells) >= 4 else parse_italian_currency(cells[-1])
                    if qty is None or qty <= 0:
                        continue
                    desc = max(cells, key=len)
                    if len(desc) < 12:
                        continue
                    items.append(
                        RawCMEItem(
                            item_number=seq,
                            tariff_code=cells[0] if len(cells[0]) < 32 else "",
                            spec_text=desc,
                            full_description=desc,
                            unit="",
                            quantity=qty,
                        )
                    )
                    seq += 1
        return items

    def _classify_items(self, raw_items: list[RawCMEItem]) -> list[CMEItem]:
        matched: list[CMEItem] = []
        for raw in raw_items:
            excl = check_cme_hard_exclusion(raw.spec_text, unit=raw.unit, quantity=raw.quantity)
            if excl is not None:
                raw.excluded_reason = excl
                continue
            rule = classify_cme_spec(raw.spec_text, unit=raw.unit, quantity=raw.quantity)
            if rule is None:
                continue
            matched.append(
                CMEItem(
                    item_number=raw.item_number,
                    tariff_code=raw.tariff_code,
                    description=raw.spec_text[:280],
                    unit=raw.unit,
                    quantity=raw.quantity,
                    unit_price_eur=raw.unit_price_eur,
                    total_price_eur=raw.total_price_eur,
                    product_line=rule.product_line,
                    category=rule.category,
                    matched_catalog_label=rule.label,
                )
            )
        return matched

    async def refine_ambiguous_with_llm(
        self,
        result: CMEParseResult,
        client: httpx.AsyncClient | None = None,
    ) -> CMEParseResult:
        """Optional lightweight LLM pass when `LLM_API_KEY` is configured; no-op offline."""
        if not self.settings.llm_enabled:
            return result
        ambiguous = [
            r
            for r in result.raw_items
            if r.excluded_reason is None
            and r.item_number not in {m.item_number for m in result.matched_items}
        ]
        if not ambiguous:
            return result

        owns_client = client is None
        http_client = client or build_async_http_client(self.settings)
        try:
            prompt_rows = [
                {"n": r.item_number, "code": r.tariff_code, "desc": r.spec_text[:200], "u": r.unit, "q": r.quantity}
                for r in ambiguous[:20]
            ]
            resp = await http_client.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
                json={
                    "model": self.settings.llm_model,
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Sei il tecnico preventivista di EDILMORITTU S.R.L. (Silanus, NU). "
                                "Escludi SEMPRE pietra naturale (basalto, marmo, granito, travertino) e "
                                "calcestruzzo liquido da autobetoniera (>1t). Restituisci JSON {\"matches\": []}."
                            ),
                        },
                        {"role": "user", "content": json.dumps(prompt_rows, ensure_ascii=False)},
                    ],
                },
            )
            if resp.status_code == 200:
                content = (
                    ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "{}"
                )
                parsed = json.loads(content)
                raw_by_num = {r.item_number: r for r in ambiguous if r.item_number is not None}
                for m in parsed.get("matches") or []:
                    num = m.get("n")
                    raw = raw_by_num.get(num)
                    if raw is None or check_cme_hard_exclusion(raw.spec_text, raw.unit, raw.quantity):
                        continue
                    try:
                        line = ProductLine(str(m["line"]))
                        cat = CAVProductCategory(str(m["category"]))
                    except (KeyError, ValueError):
                        continue
                    result.matched_items.append(
                        CMEItem(
                            item_number=raw.item_number,
                            tariff_code=raw.tariff_code,
                            description=raw.spec_text[:280],
                            unit=raw.unit,
                            quantity=raw.quantity,
                            unit_price_eur=raw.unit_price_eur,
                            total_price_eur=raw.total_price_eur,
                            product_line=line,
                            category=cat,
                            matched_catalog_label=str(m.get("label") or cat.value),
                        )
                    )
            return result
        finally:
            if owns_client:
                await http_client.aclose()
