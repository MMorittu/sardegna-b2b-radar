# Sardegna B2B Procurement & CME Intelligence Radar (`v1.1.0`)

A production-grade, **100% live (zero-demo)** asynchronous B2B procurement, Bill of Quantities (*Computo Metrico Estimativo*), and regional grant intelligence engine for the Sardinian precast concrete (*C.A.V. / Vibrocompresso*, `ATECO 23.61.0`) and civil construction supply sector.

---

## Project Documentation

| Document | Description |
| :--- | :--- |
| [**`ARCHITECTURE.md`**](./ARCHITECTURE.md) | End-to-end funnel architecture (Mermaid), module map, and road-freight logistics tiering. |
| [**`CHANGELOG.md`**](./CHANGELOG.md) | Chronological release log with ISO timestamps (`[YYYY-MM-DD HH:MM]`). |
| [**`docs/ROADMAP.md`**](./docs/ROADMAP.md) | Project milestones (M1 Backend Core, M2 Next.js Web Dashboard, M3 Scheduled Automation). |
| [**`docs/DECISIONS.md`**](./docs/DECISIONS.md) | Architecture Decision Records (`ADR-001` .. `ADR-004`). |
| [**`CONTRIBUTING.md`**](./CONTRIBUTING.md) | TDD workflow, Conventional Commits standard, and pre-release checklist. |

---

## Funnel Architecture (Milestone 1)

1. **Live Connectors & Real `HTTP 200` Validator (`scrapers/`):**
   - **ANAC BDNCP (`appalto v2.3` + OpenData CKAN 2026 JSONL):** extracts Sardinian public works, awarded contractor (`FLAG_AGGIUDICATARIO`), VAT/Tax ID, road distance from the configured logistics hub, rebate %, RUP, and pre-construction window (`avvioContratto == []` and `subappalti == []`).
   - **SardegnaCAT (`XMLBANDI` + `DownloadAttach.asp`):** parses open tenders and award notices with automatic `/portalegare/` URL normalization and ZIP attachment discovery.
   - **Local CUC Portals (PA Digitale / Municipium):** municipal union procurement portals across Sardinia.
   - **Regional Grants — RAS (Apollo GraphQL) & Chamber of Commerce:** non-repayable SME and artisan manufacturing grants (`ATECO 23.61.0`).
   - **`HttpUrlValidator`:** follows redirects, enforces real `HTTP 200` responses, and blocks soft-404 error pages before persistence.
2. **Streaming Bill of Quantities Parser (`cme/`):**
   - Streams `.pdf`, `.pdf.p7m`, and multi-document `.zip` archives in memory to isolate the *Computo Metrico Estimativo* (supporting multi-page ACCA PriMus layouts and `´` thousand separators like `2´981,89`).
   - **Gate 1 (Strict Exclusions):** filters out earthworks/demolitions, **natural stone** (basalt, Orosei marble, granite, porphyry), and **ready-mix concrete truck pours (`> 1 t` / exposure classes S4-S5)**.
   - **Gate 2 (Catalog Classification):** classifies **Line A** (Precast Reinforced Concrete C.A.V. & vibro-compressed items `ATECO 23.61.0`, island-wide delivery via crane trucks) and **Line B** (rebar `B450C`, aggregates, PVC `SN4`, multilayer pipes, hollow bricks, technical mortars, waterproofing `ATECO 47.52`, competitive within `<= 40 km` of the logistics hub).
3. **Idempotent Storage & Mini-CRM (`storage/`):**
   - Persists `tenders`, `cme_items`, and `crm_status` (`da_chiamare | preventivo_inviato | vinto | scartato`) in **SQLite WAL** (`data/radar.db`) with optional cloud sync.
4. **Zero-Fluff Dispatchers (`notifiers/`):**
   - Generates high-density B2B cards for **Telegram HTML**, **WhatsApp**, and `data/leads_digest.md`.

---

## Quickstart & CLI Reference

```powershell
# Run live scan across all Sardinian procurement & grant portals
.\.venv\Scripts\sardegna-radar.exe scan

# Parse a Computo Metrico Estimativo (PDF / ZIP / URL)
.\.venv\Scripts\sardegna-radar.exe parse-cme <computo.pdf|project.zip|url> --anac-json <cig_v23.json> --save

# List qualified B2B leads
.\.venv\Scripts\sardegna-radar.exe leads --min-score 45

# Update CRM status for a tender CIG
.\.venv\Scripts\sardegna-radar.exe set-status BCB16FC2F3 preventivo_inviato

# Execute the full unit & integration test suite (104 tests)
.\.venv\Scripts\python.exe -m pytest -v
```
