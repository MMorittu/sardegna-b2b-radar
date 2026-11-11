# Changelog — Sardegna B2B Procurement Radar

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) extended with **ISO timestamps (`[YYYY-MM-DD HH:MM]`)**, author, and Milestone reference.

---

## [Unreleased] — Milestone 2 (Next.js Web Dashboard & Cloud Sync)
- **[Planned]** Next.js 14+ Web Dashboard (App Router, TypeScript, Tailwind CSS) backed by PostgreSQL.
- **[Planned]** One-click mobile/desktop B2B quote generation (WhatsApp/Email templates pre-populated with extracted CME items).
- **[Planned]** Interactive filtering by road-freight radius (`<= 40 km`, `40-100 km`, `> 100 km`) and CRM status.

---

## [1.1.0] — 2026-11-11 17:00 — Architecture Documentation, ADR & Package Release
*Author: Massimiliano Morittu*

### Added
- `[2026-11-11 16:30]` Added [`CHANGELOG.md`](./CHANGELOG.md) with timestamped release history.
- `[2026-11-11 16:30]` Added [`ARCHITECTURE.md`](./ARCHITECTURE.md) with Mermaid data-funnel diagrams and module responsibilities.
- `[2026-11-11 16:30]` Added [`CONTRIBUTING.md`](./CONTRIBUTING.md), [`docs/DECISIONS.md`](./docs/DECISIONS.md) (`ADR-001`..`ADR-004`), and [`docs/ROADMAP.md`](./docs/ROADMAP.md).

### Changed & Cleaned
- `[2026-11-11 16:58]` Bumped package version to `1.1.0` in `pyproject.toml`, `src/sardegna_radar/__init__.py`, and `tests/test_version.py`; exported `CMEParser`, `CMEParseResult`, and typed exceptions in the root namespace.
- `[2026-11-11 17:00]` Generalized company configuration in `config.py` and `.env.example` for open-source portfolio release.

---

## [1.0.0] — 2026-11-11 15:31 — Milestone 1 (Live Connectors, Streaming CME Parser & Dual Storage)
*Author: Massimiliano Morittu*

### Added
- `[2026-11-11 11:30]` **Streaming Bill of Quantities Parser (`src/sardegna_radar/cme/`):** in-memory extraction from `.pdf`, `.pdf.p7m`, and multi-document `.zip` archives (ACCA PriMus format), featuring Gate 1 strict exclusions (natural stone, earthworks, ready-mix truck pours `> 1t`) and Gate 2 catalog matching (Line A Precast C.A.V. and Line B construction supplies).
- `[2026-11-11 13:10]` **ANAC BDNCP v2.3 & OpenData CKAN Connector (`scrapers/anac_api.py`):** extracts Sardinian public works, awarded contractor (`FLAG_AGGIUDICATARIO`), Tax ID, rebate %, RUP, logistics distance, and pre-construction status (`avvioContratto == []`, `subappalti == []`).
- `[2026-11-11 13:45]` **SardegnaCAT & Regional Grant Connectors (`scrapers/sardegna_cat.py`, `scrapers/grants_ras_cciaa.py`):** integrates `XMLBANDI` feeds, `/portalegare/` attachment URL rewriting, RAS Apollo GraphQL grants, and Chamber of Commerce notices.
- `[2026-11-11 14:15]` **Real HTTP Validator (`scrapers/url_validator.py`):** enforces `HTTP 200` verification with redirect following and anti-soft-404 checks.
- `[2026-11-11 14:40]` **Idempotent Storage (`storage/repository.py`):** SQLite WAL persistence (`data/radar.db`) for `tenders`, `cme_items`, and CRM lifecycle states (`da_chiamare | preventivo_inviato | vinto | scartato`).
- `[2026-11-11 15:00]` **Zero-Fluff Dispatchers (`notifiers/telegram.py`):** compact B2B lead cards for Telegram HTML, WhatsApp, and `data/leads_digest.md`.

### Verified
- `[2026-11-11 15:31]` **100% Test Suite Pass Rate:** `104 passed, 0 failed` (`pytest`).

---

## [0.1.0] — 2026-11-10 21:00 — Initial Repository & Core Engine
*Author: Massimiliano Morittu*

### Added
- `[2026-11-10 19:00]` Technical specification (`docs/specs/`) and implementation plan (`docs/plans/`).
- `[2026-11-10 19:45]` Pydantic v2 domain models (`models.py`), settings (`config.py`), and deterministic C.A.V. scoring engine (`matcher/cav_engine.py`).
- `[2026-11-10 20:30]` Initial SQLite WAL repository, Typer/Rich CLI (`cli.py`), and GitHub Actions CI workflow (`.github/workflows/ci.yml`).
