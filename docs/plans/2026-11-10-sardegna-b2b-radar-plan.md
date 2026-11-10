# Sardegna B2B Tender & Procurement Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade, asynchronous Python B2B procurement & regional grant intelligence engine (`sardegna-b2b-radar`) combining Reverse-API JSON connectors, adaptive `Scrapling` HTML parsers, a deterministic C.A.V. product scoring engine for Sardinian precast concrete manufacturers, SQLite WAL deduplication, and Telegram/CLI reporting.

**Architecture:** Modular `src/sardegna_radar` layout adhering to strict YAGNI discipline (zero dead abstractions, every module earns its keep). Network ingestion separates structured Reverse-API clients (`httpx.AsyncClient` with `AsyncHTTPTransport(retries=3)`) from adaptive HTML parsers (`scrapling.Selector(adaptive=True)`). Scoring and logistics tiering run deterministically in memory before persisting to an idempotent SQLite WAL database.

**Tech Stack:** Python 3.11+, `scrapling>=0.4.15`, `httpx>=0.28.1`, `pydantic>=2.0`, `pydantic-settings`, `typer`, `rich`, `sqlite3` (WAL mode), `pytest`, `pytest-asyncio`, `pytest-httpx>=0.36.0`.

**Spec:** `docs/specs/2026-11-10-sardegna-b2b-radar-spec.md`

## Global Constraints

- Python `>=3.11` with strict type annotations (`from __future__ import annotations`).
- Zero paid LLM API calls required in the core daily scan/match loop ($0.00 operating cost).
- All HTTP clients must use `httpx.AsyncHTTPTransport(retries=3)` and `httpx.Timeout(15.0, connect=30.0)`.
- CIG codes must normalize to uppercase 10-character alphanumeric strings when present; invalid/malformed monetary amounts in Italian format (`1.250.000,50 €`) must parse cleanly to `float`.
- SQLite storage must enable `PRAGMA journal_mode=WAL;` and guarantee idempotency on `(source, external_id)`.

## Review Focus

1. **Italian Currency & Date Formats:** Notices containing `"€ 145.200,00 oltre IVA"` or `"25/11/2026"` must parse into clean floats (`145200.0`) and ISO dates without raising `ValueError`.
2. **False-Positive Tender Filtering:** Tenders containing words like *"tubi"* in non-construction contexts (e.g., *"fornitura tubi endotracheali ospedalieri"*) must be penalized by negative medical/IT keywords so they score `< 20`.
3. **DOM Drift Resilience:** When a portal changes wrapper tags around tender rows, `scrapling.Selector(adaptive=True)` fallback selectors must still extract title, link, and CIG.
4. **Duplicate Scan Idempotency:** Running `sardegna-radar scan` twice on the same feed must insert `0` duplicate rows and emit `0` duplicate Telegram notifications.
5. **Graceful Offline/No-Token Execution:** When `TELEGRAM_BOT_TOKEN` is unset, the notifier must degrade cleanly to console/Markdown output without crashing.

---

### Task 1: Project Scaffolding, Configuration & Domain Models (`models.py`, `config.py`)

**Files:**
- `pyproject.toml`
- `.gitignore`
- `.env.example`
- `src/sardegna_radar/__init__.py`
- `src/sardegna_radar/config.py`
- `src/sardegna_radar/models.py`
- `tests/conftest.py`
- `tests/test_models.py`

- [x] Write failing unit tests in `tests/test_models.py` testing CIG normalization, Italian Euro currency parsing (`"€ 1.240.500,75"` -> `1240500.75`), province extraction (`NU, SS, OR, CA, SU`), and Pydantic validation.
- [x] Run `pytest tests/test_models.py` and verify it fails (RED).
- [x] Implement `pyproject.toml`, `config.py`, and `models.py` (`TenderNotice`, `CAVProductCategory`, `LogisticsTier`, `MatchAssessment`, `ScoredLead`).
- [x] Run `pytest tests/test_models.py` and verify all tests pass (GREEN).
- [x] Commit Task 1.

---

### Task 2: Deterministic C.A.V. Scoring & Silanus Logistics Engine (`matcher/cav_engine.py`)

**Files:**
- `src/sardegna_radar/matcher/__init__.py`
- `src/sardegna_radar/matcher/cav_engine.py`
- `tests/test_cav_engine.py`

- [x] Write parameterized tests in `tests/test_cav_engine.py` covering high-score civil works (sewage/aqueducts, road kerbs, cemetery burial niches), negative exclusions (hospital/medical tubes, school laptops), and logistics tiering from Silanus (`Tier 1 <40km`, `Tier 2 40-100km`, `Tier 3 >100km`).
- [x] Run `pytest tests/test_cav_engine.py` and verify failure (RED).
- [x] Implement `cav_engine.py` with `@lru_cache` pre-compiled regex patterns, CPV code boosters (`45231300-8`, `45233140-2`, `45215400-1`, `44114200-4`), negative filters, and municipality-to-Silanus tier mapping.
- [x] Run `pytest tests/test_cav_engine.py` and verify 100% pass (GREEN).
- [x] Commit Task 2.

---

### Task 3: Idempotent SQLite WAL Storage Layer (`storage/repository.py`)

**Files:**
- `src/sardegna_radar/storage/__init__.py`
- `src/sardegna_radar/storage/repository.py`
- `tests/test_repository.py`

- [x] Write failing tests in `tests/test_repository.py` using `tmp_path` to verify schema creation, `upsert_lead` idempotency on duplicate `(source, external_id)`, unnotified lead querying, and `mark_notified`.
- [x] Run `pytest tests/test_repository.py` and verify failure (RED).
- [x] Implement `RadarRepository` in `src/sardegna_radar/storage/repository.py` using `sqlite3` with `PRAGMA journal_mode=WAL;`.
- [x] Run `pytest tests/test_repository.py` and verify 100% pass (GREEN).
- [x] Commit Task 3.

---

### Task 4: Hybrid Reverse-API & Adaptive Scrapling Connectors (`scrapers/`)

**Files:**
- `src/sardegna_radar/scrapers/__init__.py`
- `src/sardegna_radar/scrapers/base.py`
- `src/sardegna_radar/scrapers/anac_api.py`
- `src/sardegna_radar/scrapers/sardegna_portals.py`
- `src/sardegna_radar/scrapers/demo_feed.py`
- `tests/test_scrapers.py`

- [x] Write async tests in `tests/test_scrapers.py` using `httpx_mock: HTTPXMock` (`pytest-httpx`) for the Reverse-API ANAC OCDS JSON connector and adaptive `scrapling.Selector(adaptive=True)` HTML parsing for RAS / SardegnaCAT tender tables.
- [x] Run `pytest tests/test_scrapers.py` and verify failure (RED).
- [x] Implement `base.py` (`httpx.AsyncClient` with `AsyncHTTPTransport(retries=3)`), `anac_api.py` (Reverse-API JSON parser), `sardegna_portals.py` (`scrapling.Selector` adaptive parser + MCP helper), and `demo_feed.py` (realistic Sardinian tenders dataset).
- [x] Run `pytest tests/test_scrapers.py` and verify 100% pass (GREEN).
- [x] Commit Task 4.

---

### Task 5: Telegram Dispatcher, Rich CLI & Technical Documentation (`notifiers/`, `cli.py`, `README.md`)

**Files:**
- `src/sardegna_radar/notifiers/__init__.py`
- `src/sardegna_radar/notifiers/telegram.py`
- `src/sardegna_radar/cli.py`
- `tests/test_cli_and_notifier.py`
- `README.md`

- [x] Write tests in `tests/test_cli_and_notifier.py` verifying Telegram payload formatting, `httpx_mock` webhook dispatch, fallback when token is missing, and Typer CLI commands (`init-db`, `scan --demo`, `leads`, `stats`, `export`).
- [x] Run `pytest tests/test_cli_and_notifier.py` and verify failure (RED).
- [x] Implement `telegram.py`, `cli.py`, and comprehensive English `README.md` with Mermaid architecture diagram.
- [x] Run full test suite `pytest -v` and CLI verification `sardegna-radar scan --demo` & `sardegna-radar leads`.
- [x] Commit Task 5.
