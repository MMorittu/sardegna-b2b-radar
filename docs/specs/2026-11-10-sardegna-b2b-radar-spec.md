# Sardegna B2B Tender & Procurement Radar — Design Spec

**Date:** 2026-11-10  
**Author:** `@MMorittu`  
**Target Domain:** Sardinian B2B Civil Infrastructure & Precast Concrete (**C.A.V.**) SMEs  

---

## 1. Problem & Vision (Architecture Synthesis)

Public infrastructure contractors winning tenders across Sardinia (water/sewage mains, road works, cemetery expansions, urban sub-services) immediately need certified vibro-compressed concrete products (**C.A.V.** — pipes, manholes, road kerbs, blocks, burial niches) with **CE / DoP** compliance. Similarly, Sardinian SMEs frequently miss regional non-repayable grants (RAS / SIPES / CCIAA Nuoro PID 68% digital transition grants).

### Why Existing Approaches Fail
1. **Manual Portal Checking:** Checking `SardegnaCAT`, `ANAC BDNCP`, and `Regione Sardegna (RAS)` manually every morning takes hours and misses newly awarded sub-contracts.
2. **LLM-First Scraping (`ScrapeGraphAI` on every page):** Feeding raw HTML DOMs of 100 daily notices into an LLM burns API tokens, is slow, and risks hallucinating CIG/CUP identifiers.
3. **Brittle DOM Scrapers:** Traditional BeautifulSoup scrapers break whenever regional portals alter CSS classes.

### Chosen Approach: Hybrid Reverse-API + Adaptive Scrapling + Deterministic Zero-Token Scoring
- **Layer 1 — Reverse-API First (`httpx` HTTP/2):** Query structured JSON/XML/RSS endpoints exposed by ANAC OCDS, RAS feeds, and Jaggaer/SardegnaCAT AJAX endpoints directly.
- **Layer 2 — Adaptive DOM Parsing (`Scrapling v0.4+`):** Use `scrapling.Selector(..., adaptive=True)` with `auto_save=True` for HTML notices so selectors self-heal across portal layout changes, plus optional `ScraplingMCPServer` integration for interactive agent inspection.
- **Layer 3 — Deterministic C.A.V. Matcher (`cav_engine.py`):** Pre-compiled, `@lru_cache`-optimized weighted regex engine that scores notices (`0–100`), maps specific C.A.V. precast concrete product lines, and calculates road-logistics tiers from Central Sardinia (`Silanus / Macomer Hub, NU`) at **$0.00 token cost**.
- **Layer 4 — Idempotent SQLite WAL Storage & Telegram Alerting:** Deduplicate on `(source, cig/external_id)` and dispatch instant rich alerts to Telegram or CLI tables.
