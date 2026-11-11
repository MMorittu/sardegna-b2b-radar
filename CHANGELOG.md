# Changelog — Sardegna B2B Radar (EDILMORITTU S.R.L.)

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.
Il formato si basa su [Keep a Changelog](https://keepachangelog.com/it/1.1.0/) esteso con **data e ora ISO (`[YYYY-MM-DD HH:MM]`)**, autore e Milestone di riferimento.

---

## [Unreleased] — Milestone 2 (Next.js Web Dashboard & Cloud Sync)
- **[Planned]** Dashboard web Next.js 14+ (App Router, TypeScript, Tailwind) collegata a Supabase Postgres.
- **[Planned]** Azioni rapide mobile/desktop per contattare l'impresa aggiudicataria (pulsante chiamata, template preventivo WhatsApp precompilato con voci CME).
- **[Planned]** Filtro visuale per raggio chilometrico da Silanus (`<= 40 km`, `40-100 km`, `> 100 km`) e stato CRM.

---

## [1.1.0] — 2026-11-11 16:58 — Governance, Contesto, Pulizia Repo & Regole Agenti
*Autore: Massimiliano Morittu & Antigravity*

### Added
- `[2026-11-11 16:30]` Creato [`AGENTS.md`](./AGENTS.md) e [`.antigravity/rules.md`](./.antigravity/rules.md) con regola **Plan-Before-Execute** per operazioni sensibili, vincoli TDD, sicurezza credenziali e regole di dominio EDILMORITTU S.R.L.
- `[2026-11-11 16:30]` Creato [`CHANGELOG.md`](./CHANGELOG.md) con tracciamento cronologico data/ora.
- `[2026-11-11 16:30]` Creato [`ARCHITECTURE.md`](./ARCHITECTURE.md) con diagrammi Mermaid del flusso a imbuto e mappa dei moduli.
- `[2026-11-11 16:30]` Creato [`CONTRIBUTING.md`](./CONTRIBUTING.md), [`docs/DECISIONS.md`](./docs/DECISIONS.md) (ADR-001..004) e [`docs/ROADMAP.md`](./docs/ROADMAP.md).
- `[2026-11-11 16:30]` Creata nota MOC nel Second Brain Obsidian (`03_PROJECTS/Sardegna_B2B_Radar.md`).

### Changed & Cleaned
- `[2026-11-11 16:58]` Allineata versione pacchetto a `1.1.0` in `pyproject.toml`, `src/sardegna_radar/__init__.py` e `tests/test_version.py`; esportati `CMEStreamParser` ed eccezioni nel namespace pubblico.
- `[2026-11-11 16:58]` Rimossi artefatti obsoleti (`docs/verification-notes.md`, bytecode orfani `demo_feed.*.pyc`) e aggiornato `data/.gitignore` per ignorare `adaptive_selectors/`.
- `[2026-11-11 16:58]` Aggiornato `README.md` con indice navigabile verso tutti i documenti di governance e architettura.

---

## [1.0.0] — 2026-11-11 15:31 — Milestone 1 (Motore Live, Parser CME & Storage Duale)
*Autore: Massimiliano Morittu & Antigravity*

### Added
- `[2026-11-11 11:30]` **Parser Streaming Computi Metrici (`src/sardegna_radar/cme/`):** estrazione automatica in memoria da `.pdf`, `.pdf.p7m` e `.zip` multi-elaborato (formato ACCA PriMus, gestione separatore migliaia `´`), con Gate 1 (esclusioni pietra naturale, scavi, getti autobetoniera `> 1t`) e Gate 2 (classificazione Linea A C.A.V. e Linea B rivendita entro `40 km` da Silanus).
- `[2026-11-11 13:10]` **Connettore ANAC BDNCP v2.3 & OpenData CKAN (`scrapers/anac_api.py`):** estrazione gare lavori in Sardegna, identificazione aggiudicatario reale (`FLAG_AGGIUDICATARIO`), P.IVA/CF, ribasso %, RUP, distanza da Silanus e verifica cantiere non ancora avviato (`avvioContratto == []`, `subappalti == []`).
- `[2026-11-11 13:45]` **Connettori SardegnaCAT & Bandi PMI (`scrapers/sardegna_cat.py`, `scrapers/grants_ras_cciaa.py`):** integrazione feed `XMLBANDI`, riscrittura URL allegati `/portalegare/`, bandi Regione Sardegna (Apollo GraphQL) e bandi artigiani CCIAA Nuoro (`nu.camcom.it`).
- `[2026-11-11 14:15]` **Validatore HTTP Reale (`scrapers/url_validator.py`):** verifica `HTTP 200` con follow-redirect e rilevamento anti-soft-404 su ogni URL salvato.
- `[2026-11-11 14:40]` **Storage Dual-Ready (`storage/repository.py`, `storage/supabase_repo.py`, `supabase/migrations/`):** persistenza idempotente su SQLite WAL (`data/radar.db`) e migrazione SQL per Supabase Postgres con tabelle `tenders`, `cme_items` e gestione stati CRM (`da_chiamare | preventivo_inviato | vinto | scartato`).
- `[2026-11-11 15:00]` **Notificatori Zero-Fluff (`notifiers/telegram.py`):** generazione card sintetiche per Telegram HTML, WhatsApp e report `data/leads_digest.md`.

### Changed & Fixed
- `[2026-11-11 15:10]` Rimossa dipendenza da feed demo statici (`demo_feed.py` eliminato) per garantire operatività 100% live.
- `[2026-11-11 15:20]` Applicati fix da code review (`ponytail-review`) su gestione eccezioni (`exceptions.py`), portabilità fixture CI (`tests/fixtures/`) e resilienza scraper CCIAA Nuoro.

### Verified
- `[2026-11-11 15:31]` **Suite di test 100% verde:** `104 passed, 0 failed` (`pytest`).
- `[2026-11-11 15:31]` **Scansione Live eseguita su `data/radar.db`:** 164 gare/bandi indicizzati, 13 voci CME estratte sul caso reale di Bolotana (`CIG BCB16FC2F3`, aggiudicatario `FL. COSTRUZIONI & SERVIZI S.R.L.`, score `100/100`).

---

## [0.1.0] — 2026-11-10 21:00 — Inizializzazione Repository & Architettura Base
*Autore: Massimiliano Morittu & Antigravity*

### Added
- `[2026-11-10 19:00]` Specifica tecnica (`docs/specs/2026-11-10-sardegna-b2b-radar-spec.md`) e piano implementativo (`docs/plans/2026-11-10-sardegna-b2b-radar-plan.md`).
- `[2026-11-10 19:45]` Modelli Pydantic (`models.py`), configurazione (`config.py`) e motore deterministico di scoring C.A.V. (`matcher/cav_engine.py`).
- `[2026-11-10 20:30]` Repository SQLite WAL iniziale, CLI Typer/Rich (`cli.py`) e workflow GitHub Actions CI (`.github/workflows/ci.yml`).
