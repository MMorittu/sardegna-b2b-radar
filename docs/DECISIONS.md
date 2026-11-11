# Architecture Decision Records (ADR) — Sardegna B2B Radar

This document records the core architectural decisions made during the engineering of **Sardegna B2B Radar**.

---

## ADR-001: Hybrid Reverse-API (`httpx`) + `Scrapling` over Headless Browsers
- **Date:** `2026-11-10`
- **Status:** Accepted & Implemented (Milestone 1)
- **Context:** Italian public procurement portals (ANAC BDNCP, SardegnaCAT, Municipium CUC portals, RAS) expose structured JSON/GraphQL/XML endpoints alongside HTML tables prone to minor layout drift.
- **Decision:** Combine `httpx.AsyncClient` (with automatic transport retries) for structured APIs (ANAC v2.3, CKAN JSONL, RAS Apollo GraphQL, SardegnaCAT XML) with `scrapling.Selector(adaptive=True)` for resilient HTML extraction.
- **Consequences:**
  - 10x faster scan execution compared to Playwright/Selenium headless browsers.
  - Minimal memory footprint suitable for both local CLI runs and free CI runners.
  - Adaptive DOM matching survives upstream wrapper tag changes.

---

## ADR-002: 100% Deterministic Scoring & CME Parser ($0.00 OPEX Core)
- **Date:** `2026-11-10`
- **Status:** Accepted & Implemented (Milestone 1)
- **Context:** Parsing hundreds of daily tender notices and multi-page Bills of Quantities (*Computi Metrici Estimativi*) through paid LLM APIs introduces recurring operating costs and risks numerical hallucinations on quantities or unit prices.
- **Decision:** Build a deterministic pipeline backed by pre-compiled regular expressions (`@lru_cache`), a streaming ACCA PriMus PDF/ZIP table parser, and explicit two-stage catalog gates (Gate 1 Exclusions + Gate 2 Line A / Line B matching).
- **Consequences:**
  - **$0.00** daily operating cost.
  - Exact mathematical extraction of quantities, units of measure, unit prices, and line totals.
  - Fully offline-testable with deterministic fixtures.

---

## ADR-003: Dual-Ready SQLite WAL + Cloud PostgreSQL Adapter
- **Date:** `2026-11-11`
- **Status:** Accepted & Implemented (Milestone 1)
- **Context:** The engine must run zero-config on a local workstation while remaining ready to feed a collaborative Web/Mobile CRM Dashboard (Milestone 2).
- **Decision:** Use **SQLite in WAL mode** (`data/radar.db`) as the primary idempotent local store, paired with an optional cloud PostgreSQL repository adapter (`storage/supabase_repo.py`).
- **Consequences:**
  - Instant local CLI execution without external database containers.
  - Seamless state synchronization for the upcoming Next.js web frontend.

---

## ADR-004: Two-Stage Gate Filtering on Bills of Quantities (CME)
- **Date:** `2026-11-11`
- **Status:** Accepted & Implemented (Milestone 1)
- **Context:** Civil and road infrastructure Bills of Quantities frequently contain high-value line items outside the scope of a precast concrete manufacturer and building material distributor (e.g., natural stone kerbs/paving in basalt or granite, massive ready-mix concrete truck pours, bulk excavations).
- **Decision:** Enforce a strict **Gate 1 Exclusion Filter** in `cme/parser.py` prior to scoring:
  1. Reject natural stone items (basalt, granite, Orosei marble, porphyry, trachyte).
  2. Reject ready-mix concrete truck pours (`> 1 t` / classes `S4-S5`).
  3. Reject demolitions, excavations, landfill transport, and medical/IT supplies.
- **Consequences:**
  - Eliminates false positives: high-scoring leads correspond strictly to Precast Reinforced Concrete (Line A) or stocked construction materials within the local delivery radius (Line B).
