# Roadmap di Progetto — Sardegna B2B Radar (EDILMORITTU S.R.L.)

Stato aggiornato al: **`2026-11-11 16:30`**

---

## Milestone 1: Backend Core, Connettori Live & Parser CME — COMPLETATA (100%)
- [x] Architettura Python 3.11+ tipizzata con Pydantic v2 e CLI Typer/Rich.
- [x] Connettore live **ANAC BDNCP (`appalto v2.3` + CKAN 2026 JSONL)** con estrazione vincitore, P.IVA, RUP, ribasso % e stato cantiere (`avvioContratto == []`).
- [x] Connettore live **SardegnaCAT (`XMLBANDI`)**, CUC locali e **Bandi RAS / CCIAA Nuoro**.
- [x] Validatore asincrono **`HttpUrlValidator`** (`HTTP 200` reale e blocco soft-404).
- [x] **Parser Streaming Computi Metrici (`cme/`)** per PDF/ZIP PriMus con Gate 1 (Esclusioni) e Gate 2 (Linea A C.A.V. Tutta Sardegna + Linea B Rivendita `<= 40 km` da Silanus).
- [x] Storage duale **SQLite WAL** (`data/radar.db`) + schema e client **Supabase Postgres** (`supabase/migrations/`).
- [x] Notifiche sintetiche Telegram HTML, WhatsApp card e digest Markdown.
- [x] Suite di test unitari e di integrazione al 100% (`104 passed, 0 failed`).
- [x] Governance, regole agenti (`AGENTS.md`, `.antigravity/rules.md`), `CHANGELOG.md` con data/ora e ADR.

---

## Milestone 2: Dashboard Web & Mobile Next.js + CRM Familiare — PROSSIMO STEP
- [ ] **Inizializzazione Progetto Frontend (`web/` o repo dedicato Next.js 14+ App Router, TypeScript, Tailwind CSS):**
  - Interfaccia pensata per uso rapido da smartphone e desktop in azienda a Silanus.
- [ ] **Integrazione Live con Supabase Postgres:**
  - Sincronizzazione automatica dal comando `sardegna-radar scan` verso Supabase.
- [ ] **Vista "Cantiere & Vincitore" (Lead Card):**
  - Visualizzazione immediata di: Impresa Aggiudicataria, P.IVA, Comune dei lavori, distanza km da Silanus, importo stimato forniture Linea A e Linea B.
  - Tabella espandibile con le singole voci estratte dal Computo Metrico Estimativo (quantità, prezzo unitario, totale).
- [ ] **Azioni One-Click (Mini-CRM Operativo):**
  - Cambio stato istantaneo (`da_chiamare` $\to$ `preventivo_inviato` $\to$ `vinto` / `scartato`).
  - Pulsante **"Genera Bozza Preventivo WhatsApp / Email"** con elenco delle voci C.A.V. / materiali già formattato per l'impresa vincitrice.

---

## Milestone 3: Automazione Schedulata & Arricchimento Contatti — FUTURA
- [ ] **Esecuzione Automatica Giornaliera (Cron / GitHub Actions):**
  - Scansione automatica ogni mattina alle `07:30` con invio diretto dei nuovi lead qualificati sul canale Telegram / WhatsApp aziendale.
- [ ] **Arricchimento Anagrafica Aggiudicatari:**
  - Associazione automatica di PEC, telefono o sede legale delle imprese sarde ricorrenti a partire dalla P.IVA estratta da ANAC.
- [ ] **Monitoraggio Subappalti e Avvio Lavori:**
  - Alert automatico quando un cantiere monitorato passa da `da_chiamare` alla pubblicazione della data di consegna lavori.
