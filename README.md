# Sardegna B2B Procurement & CME Intelligence Radar (`v2.0.0`)

A production-grade, **fullstack asynchronous B2B procurement, Bill of Quantities (*Computo Metrico Estimativo*), and regional grant intelligence platform** tailored for the Sardinian precast concrete (*C.A.V. / Vibrocompresso*, `ATECO 23.61.0`) and civil construction supply sector.

Features an ultra-low latency Python 3.11+ async core, deterministic regex/PDF streaming engines ($0.00 OPEX / zero LLM reliance), and an industrial **Next.js 14 App Router** web dashboard with out-of-the-box offline demo mode.

---

## Portfolio Showcase & Architecture

```
               ┌────────────────────────────────────────────────────────┐
               │              SARDEGNA PUBLIC DATA SOURCES              │
               │  ANAC BDNCP (v2.3) • SardegnaCAT • Regional Grants RAS │
               └──────────────────────────┬─────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             PYTHON CORE RADAR ENGINE                             │
│  • HttpUrlValidator (SSRF protection & anti-soft-404)                            │
│  • Streaming CME Parser (PDF/ZIP/P7M, PriMus layout, Gate 1 exclusions)          │
│  • Catalog Scoring Engine (Line A C.A.V. & Line B Building Resale)              │
│  • Local SQLite WAL (`data/radar.db`) + Supabase Cloud Auto-Sync                │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS 14 APP ROUTER DASHBOARD                           │
│  • Server Components (SSR) + Zero-Friction Offline Demo Mode                    │
│  • Industrial UI ("Concrete Dark" theme, Hallmark stamp, zero-rounded borders)   │
│  • Interactive Mini-CRM (Status Pipeline, PEC & WhatsApp Quotation Generator)   │
│  • Hardened Security (Timing-safe Basic Auth, Sliding-Window Rate Limiter)       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Documentation

| Document | Description |
| :--- | :--- |
| [**`ARCHITECTURE.md`**](./ARCHITECTURE.md) | End-to-end funnel architecture (Mermaid), module map, and road-freight logistics tiering. |
| [**`CHANGELOG.md`**](./CHANGELOG.md) | Chronological release log with ISO timestamps (`[YYYY-MM-DD HH:MM]`). |
| [**`docs/ROADMAP.md`**](./docs/ROADMAP.md) | Project milestones (M1 Backend Core, M2 Next.js Web Dashboard, M3 Cloud Scheduled Automation). |
| [**`docs/DECISIONS.md`**](./docs/DECISIONS.md) | Architecture Decision Records (`ADR-001` .. `ADR-004`). |
| [**`CONTRIBUTING.md`**](./CONTRIBUTING.md) | TDD workflow, Conventional Commits standard, and pre-release checklist. |

---

## Key Modules & Features

### 1. Python Core Engine (`src/sardegna_radar/`)
- **Live Scrapers & Real `HTTP 200` Validator:**
  - **ANAC BDNCP (`appalto v2.3` + OpenData CKAN 2026 JSONL):** extracts Sardinian public works, awarded contractor (`FLAG_AGGIUDICATARIO`), VAT/Tax ID, road distance from the configured logistics hub, rebate %, RUP, and pre-construction window (`avvioContratto == []` and `subappalti == []`).
  - **SardegnaCAT (`XMLBANDI` + `DownloadAttach.asp`):** parses open tenders and award notices with automatic `/portalegare/` URL normalization and ZIP attachment discovery.
  - **Regional Grants (RAS GraphQL):** non-repayable SME and artisan manufacturing grants (`ATECO 23.61.0`).
  - **`HttpUrlValidator`:** anti-SSRF IP verification, redirect follow, enforces real `HTTP 200` responses, and blocks soft-404 error pages before persistence.
- **Streaming Bill of Quantities Parser (`cme/`):**
  - Streams `.pdf`, `.pdf.p7m`, and multi-document `.zip` archives in memory to isolate the *Computo Metrico Estimativo* (supporting multi-page ACCA PriMus layouts and `´` thousand separators like `2´981,89`).
  - **Gate 1 (Strict Exclusions):** filters out earthworks/demolitions, **natural stone** (basalt, Orosei marble, granite, porphyry), and **ready-mix concrete truck pours (`> 1 t` / exposure classes S4-S5)**.
  - **Gate 2 (Catalog Classification):** classifies **Line A** (Precast Reinforced Concrete C.A.V. & vibro-compressed items `ATECO 23.61.0`, island-wide delivery via crane trucks) and **Line B** (rebar `B450C`, aggregates, PVC `SN4`, multilayer pipes, hollow bricks, technical mortars, waterproofing `ATECO 47.52`, competitive within `<= 40 km` of the logistics hub).
- **Idempotent Storage & Mini-CRM (`storage/`):**
  - Persists `tenders`, `cme_items`, and `crm_status` (`da_chiamare | preventivo_inviato | vinto | scartato`) in **SQLite WAL** (`data/radar.db`) with automatic Supabase Cloud synchronization.

### 2. Modern Web Dashboard (`web/`)
- **Framework:** Next.js 14 App Router, TypeScript, Tailwind CSS, Lucide Icons.
- **Ready-to-Run Demo Mode:** Seamlessly falls back to an embedded verified dataset (`web/lib/demo-data.ts`) with realistic tenders and parsed CME lines when external database keys are not supplied.
- **Sub-Supply Quotation Generator (`web/lib/quick-actions.ts`):** Produces pre-compiled, professional B2B sub-supply offers for PEC (ready to paste into Aruba PEC or Legalmail) and WhatsApp outreach messages.
- **Perimeter Security:** Edge middleware with timing-safe Basic Auth (`web/lib/auth.ts`) and sliding-window in-memory rate limiting (`web/lib/rate-limiter.ts`).

---

## Quickstart Guide

### Option A: Next.js Web Dashboard (Instant Showcase)

Clone the repository and run the web application directly in demo mode:

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.  
*(Default demo credentials: User: `radar_demo` | Password: `RADAR_DEMO_2026`)*.

To run the web test suite:
```bash
npm test
```

### Option B: Python Core CLI

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

# Run test suite
python -m pytest -q

# Run live scan across all Sardinian procurement & grant portals
sardegna-radar scan

# Parse a Computo Metrico Estimativo (PDF / ZIP / URL)
sardegna-radar parse-cme <computo.pdf|project.zip|url> --anac-json <cig_v23.json> --save

# List qualified B2B leads
sardegna-radar leads --min-score 45

# Update CRM status for a tender CIG
sardegna-radar set-status <CIG> preventivo_inviato
```

---

## License

MIT License — Copyright (c) 2026 MMorittu.
