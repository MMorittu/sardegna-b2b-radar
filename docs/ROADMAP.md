# Project Roadmap — Sardegna B2B Procurement Radar

Last updated: **`2026-11-11 17:00`**

---

## Milestone 1: Backend Core, Live Connectors & Streaming CME Parser — COMPLETED (100%)
- [x] Strictly typed Python 3.11+ architecture with Pydantic v2 and Typer/Rich CLI.
- [x] Live **ANAC BDNCP (`appalto v2.3` + CKAN 2026 JSONL)** connector extracting awarded contractor, Tax ID, RUP, rebate %, and pre-construction status (`avvioContratto == []`).
- [x] Live **SardegnaCAT (`XMLBANDI`)**, local CUC portals, and **RAS / Chamber of Commerce Grants** connectors.
- [x] Async **`HttpUrlValidator`** enforcing real `HTTP 200` checks and blocking soft-404 pages.
- [x] **Streaming Bill of Quantities Parser (`cme/`)** for PriMus PDFs/ZIPs with Gate 1 (Exclusions) and Gate 2 (Line A Precast C.A.V. island-wide + Line B Construction Supplies `<= 40 km`).
- [x] Idempotent **SQLite WAL** storage (`data/radar.db`) + cloud PostgreSQL adapter.
- [x] Compact Telegram HTML, WhatsApp card, and Markdown digest dispatchers.
- [x] Full unit and integration test suite (`104 passed, 0 failed`).

---

## Milestone 2: Next.js Web & Mobile CRM Dashboard — NEXT
- [ ] **Frontend Application (`Next.js 14+` App Router, TypeScript, Tailwind CSS):**
  - Responsive B2B interface optimized for mobile and desktop use.
- [ ] **Live Cloud Database Sync:**
  - Real-time synchronization of tenders, extracted CME items, and CRM states.
- [ ] **Awarded Site & Contractor View (Lead Card):**
  - Instant overview of Winning Contractor, VAT/Tax ID, Municipality, road distance tier, and estimated Line A / Line B supply value.
  - Expandable Bill of Quantities table displaying matched items, quantities, unit prices, and totals.
- [ ] **One-Click Commercial Actions:**
  - Instant CRM status transitions (`da_chiamare` $\to$ `preventivo_inviato` $\to$ `vinto` / `scartato`).
  - **"Generate WhatsApp / Email Quote Draft"** button pre-filled with the extracted precast/material items.

---

## Milestone 3: Scheduled Automation & Contractor Enrichment — FUTURE
- [ ] **Automated Morning Digest (Cron / GitHub Actions):**
  - Scheduled `07:30` daily scan dispatching newly qualified B2B leads to Telegram/WhatsApp.
- [ ] **Contractor Directory Enrichment:**
  - Automated lookup of certified email (PEC) and contact details from the awarded contractor's Tax ID.
- [ ] **Contract Start & Subcontract Monitoring:**
  - Automated alert when a tracked tender publishes its site handover date or subcontract notice.
