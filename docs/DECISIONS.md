# Architecture Decision Records (ADR) — Sardegna B2B Radar

Questo documento raccoglie le decisioni architetturali e di business prese durante la progettazione di **Sardegna B2B Radar** per **EDILMORITTU S.R.L.**.

---

## ADR-001: Utilizzo di Reverse-API (`httpx`) + `Scrapling` anziché Browser Headless (Playwright/Selenium)
- **Data:** `2026-11-10`
- **Stato:** Accettato e Implementato (Milestone 1)
- **Contesto:** I portali di gare pubbliche (ANAC BDNCP, SardegnaCAT, portali CUC Municipium, RAS) espongono endpoint JSON/GraphQL/XML sottostanti o tabelle HTML statiche soggette a piccoli cambi di layout.
- **Decisione:** Usare `httpx.AsyncClient` con retry automatico per le API strutturate (ANAC v2.3, CKAN JSONL, RAS Apollo GraphQL, SardegnaCAT XML) e `scrapling.Selector(adaptive=True)` per l'HTML.
- **Conseguenze:**
  - Velocità di scansione superiore di 10x rispetto a un browser headless.
  - Consumo RAM minimo, eseguibile ovunque (PC locale, GitHub Actions gratuita).
  - Resilienza ai cambi del DOM grazie al matching adattivo di Scrapling.

---

## ADR-002: Motore di Scoring e CME Parser 100% Deterministici ($0.00 OPEX)
- **Data:** `2026-11-10`
- **Stato:** Accettato e Implementato (Milestone 1)
- **Contesto:** Analizzare centinaia di bandi e computi metrici al giorno tramite API LLM a pagamento genererebbe costi ricorrenti e possibili allucinazioni sui quantitativi o sui prezzi unitari.
- **Decisione:** Implementare un motore deterministico basato su espressioni regolari pre-compilate (`@lru_cache`), parser strutturato per i PDF ACCA PriMus e regole esplicite di catalogo (Gate 1 Esclusioni + Gate 2 Linea A / Linea B).
- **Conseguenze:**
  - Costo operativo giornaliero pari a **$0.00**.
  - Precisione matematica sui numeri del computo metrico (quantità, unità di misura, prezzi unitari e totali).
  - Esecuzione istantanea e completamente testabile offline.

---

## ADR-003: Storage Duale SQLite WAL + Supabase Postgres
- **Data:** `2026-11-11`
- **Stato:** Accettato e Implementato (Milestone 1)
- **Contesto:** Il radar deve poter funzionare immediatamente da terminale locale senza dipendenze cloud obbligatorie, ma deve anche alimentare la futura Dashboard Web/Mobile condivisa in famiglia (Milestone 2).
- **Decisione:** Adottare **SQLite in modalità WAL** (`data/radar.db`) come storage primario locale idempotente, affiancato da `SupabaseRepository` e migrazioni SQL pronte in `supabase/migrations/` con Row-Level Security (RLS) e indici parziali.
- **Conseguenze:**
  - Zero frizione in locale (nessun server DB da avviare).
  - Schema cloud già pronto per il frontend Next.js della Milestone 2.

---

## ADR-004: Filtri Rigidi di Esclusione sul Catalogo Reale EDILMORITTU S.R.L.
- **Data:** `2026-11-11`
- **Stato:** Accettato e Implementato (Milestone 1)
- **Contesto:** Nei computi metrici stradali e civili in Sardegna compaiono spesso voci ad alto importo che non rientrano nel core business di Edilmorittu (es. cordoli o pavimentazioni in basalto/granito, getti massivi in opera con autobetoniera, scavi e movimento terra).
- **Decisione:** Introdurre il **Gate 1 di Esclusione Rigida** in `cme/parser.py` prima del calcolo dello score:
  1. Scarto immediato di pietra naturale (basalto, granito, marmo di Orosei, porfido, trachite, pietra di Serrenti).
  2. Scarto di getti di calcestruzzo preconfezionato da autobetoniera (`> 1 t` / classi `S4-S5`).
  3. Scarto di demolizioni, scavi, trasporti a discarica e forniture ospedaliere/IT.
- **Conseguenze:**
  - Eliminazione dei falsi positivi: i lead che raggiungono punteggio alto contengono solo manufatti C.A.V./vibrocompressi (Linea A) o materiali da rivendita edile effettivamente a magazzino a Silanus (Linea B).
