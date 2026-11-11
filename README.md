# Sardegna B2B Radar — EDILMORITTU S.R.L. (`v1.1.0`)

Motore B2B **100% live (zero demo)** di intelligence su gare pubbliche aggiudicate, gare lavori aperte e bandi PMI/Artigiani in Sardegna, calibrato esclusivamente sul catalogo produttivo e commerciale di **EDILMORITTU S.R.L.** (`P.IVA 00799740915` — `REA NU-49501` — `Albo Artigiani NU-23034` — SS 129 km 82,200, Silanus NU).

---

## Documentazione & Contesto del Progetto

| File | Descrizione |
| :--- | :--- |
| [**`AGENTS.md`**](./AGENTS.md) | Regole del progetto, vincolo **Plan-Before-Execute** e regole di dominio EDILMORITTU S.R.L. |
| [**`ARCHITECTURE.md`**](./ARCHITECTURE.md) | Diagramma Mermaid della pipeline a imbuto, mappa dei moduli e logica dei Tier logistici da Silanus. |
| [**`CHANGELOG.md`**](./CHANGELOG.md) | Storico cronologico delle modifiche con data e ora ISO (`[YYYY-MM-DD HH:MM]`). |
| [**`docs/ROADMAP.md`**](./docs/ROADMAP.md) | Stato di avanzamento (Milestone 1 completata, Milestone 2 Next.js Dashboard, Milestone 3 Cron). |
| [**`docs/DECISIONS.md`**](./docs/DECISIONS.md) | Registro delle decisioni architetturali (`ADR-001` .. `ADR-004`). |
| [**`CONTRIBUTING.md`**](./CONTRIBUTING.md) | Standard TDD, Conventional Commits e checklist pre-rilascio. |

---

## Architettura a Imbuto (Milestone 1)

1. **Connettori Live + Validatore `HTTP 200` (`scrapers/`):**
   - **ANAC BDNCP (`appalto v2.3` + OpenData CKAN 2026 JSONL):** estrazione lavori Sardegna, vincitore reale (`FLAG_AGGIUDICATARIO`), P.IVA/CF + stima distanza sede da Silanus, ribasso %, RUP, stato cantiere (`avvioContratto == []` e `subappalti == []`).
   - **SardegnaCAT (`XMLBANDI` + `DownloadAttach.asp`):** gare lavori/forniture aperte ed esiti con riscrittura automatica `/portalegare/` e URL ZIP allegati.
   - **CUC Locali (PA Digitale / Municipium):** es. Comunità Montana Nuorese.
   - **Bandi RAS (Apollo GraphQL) & CCIAA Nuoro (`nu.camcom.it`):** contributi a fondo perduto per `ATECO 23.61.0` e imprese artigiane.
   - **`HttpUrlValidator`:** ogni singolo URL salvato segue i redirect, verifica `HTTP 200` reale e blocca i soft-404.
2. **Parser Streaming Computi Metrici (`cme/`):**
   - Estrae in memoria da `.pdf`, `.pdf.p7m` o `.zip` multi-elaborato **solo il Computo Metrico Estimativo**, gestendo formati ACCA PriMus multi-pagina e separatori migliaia `´` (`2´981,89`).
   - **Gate 1 (Esclusioni Rigide):** scarta demolizioni/scavi/discariche, **pietra naturale** (basalto, marmo di Orosei, granito, travertino, porfido) e **getti di calcestruzzo preconfezionato da autobetoniera (`> 1 t` / classe S4-S5)**.
   - **Gate 2 (Catalogo Reale):** classifica **Linea A** (C.A.V. & vibrocompresso `ATECO 23.61.0`, consegna in tutta la Sardegna con 2 camion autogru) e **Linea B** (ferro `B450C`, inerti, PVC `SN4`, multistrato, forati, malte ripristino cls, guaine, pitture `ATECO 47.52`, vantaggio logistico `<= 40 km` da Silanus).
3. **Storage Dual-Ready (`storage/` + `supabase/migrations/`):**
   - Tabelle `tenders` + `cme_items` + `crm_status` (`da_chiamare | preventivo_inviato | vinto | scartato`) su **SQLite WAL** (`data/radar.db`) e **Supabase Postgres** (RLS + partial indexes per la Dashboard Next.js Milestone 2).
4. **Output Ultra-Sintetico (`notifiers/`):**
   - Card zero-fluff per **Telegram HTML**, **WhatsApp** e `data/leads_digest.md`.

---

## Comandi Principali

```powershell
# Eseguire la scansione live su tutti i portali
.\.venv\Scripts\sardegna-radar.exe scan

# Analizzare un Computo Metrico Estimativo (PDF / ZIP / URL)
.\.venv\Scripts\sardegna-radar.exe parse-cme <computo.pdf|progetto.zip|url> --anac-json <cig_v23.json> --save

# Visualizzare i lead qualificati
.\.venv\Scripts\sardegna-radar.exe leads --min-score 45

# Aggiornare lo stato CRM di un lead
.\.venv\Scripts\sardegna-radar.exe set-status BCB16FC2F3 preventivo_inviato

# Eseguire l'intera suite di test (104 test)
.\.venv\Scripts\python.exe -m pytest -v
```
