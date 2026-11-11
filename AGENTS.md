# Sardegna B2B Radar — Project Rules & Agent Instructions

Queste regole vincolano qualsiasi agente AI (Antigravity, Gemini, sub-agenti) e sviluppatore che operi sul repository **sardegna-b2b-radar** per **EDILMORITTU S.R.L.** (`P.IVA 00799740915` — Silanus, NU).

---

## 1. Obbligo di Approvazione Preventiva del Piano (Plan-Before-Execute)

Non è necessario chiedere conferma per correzioni banali su singola riga o ispezioni in sola lettura, **MA è obbligatorio presentare un piano sintetico e attendere l'approvazione esplicita dell'utente prima di eseguire** in tutti i seguenti casi sensibili:

1. **Modifiche a Schemi DB o Migrazioni:** Qualsiasi alterazione a `storage/repository.py`, `storage/supabase_repo.py`, `supabase/migrations/` o cancellazione/reset di `data/radar.db`.
2. **Nuove Feature o Refactoring Multi-File:** Qualsiasi intervento che crei nuovi moduli o modifichi la struttura di più di un file contemporaneamente.
3. **Regole di Business e Scoring Catalogo EDILMORITTU S.R.L.:** Qualsiasi modifica a `matcher/cav_engine.py`, `cme/parser.py`, soglie di punteggio, raggi chilometrici da Silanus (`40 km` / `100 km`) o filtri di esclusione (pietra naturale, getti da autobetoniera `> 1t`, scavi).
4. **Dipendenze Esterne:** Qualsiasi aggiunta, rimozione o aggiornamento di pacchetti in `pyproject.toml`.
5. **Operazioni Git Sensibili o Esterne:** `git push`, `git reset`, `git rebase`, eliminazione di branch o sovrascrittura della cronologia.

---

## 2. Regole di Qualità, Test e Sicurezza

1. **TDD & 100% Test Pass Rate:**
   - Ogni nuova funzione, connettore o regola di parsing deve avere il corrispondente test unitario in `tests/`.
   - Nessun task può essere dichiarato concluso se `.\.venv\Scripts\python.exe -m pytest -q` presenta anche un solo fallimento (`0 failed`).
2. **Aggiornamento Obbligatorio del `CHANGELOG.md`:**
   - Al termine di ogni feature, bugfix o milestone, aggiornare sempre [`CHANGELOG.md`](./CHANGELOG.md) con data e ora nel formato `[YYYY-MM-DD HH:MM]` e autore.
3. **Sicurezza e Zero Segreti nel Codice:**
   - È severamente vietato inserire token o credenziali (`TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, ecc.) nei file sorgente o nei test. Usare esclusivamente `.env` (non tracciato) e variabili d'ambiente validate in `config.py`.
4. **Zero Costi LLM nel Core ($0.00 OPEX):**
   - Il ciclo giornaliero di scansione, parsing CME e scoring deve rimanere **100% deterministico** (regex precompilate, parser strutturati, API/Scrapling) senza dipendere da chiamate LLM a pagamento.
5. **Validazione Reale URL (`HTTP 200`):**
   - Nessun bando o gara può essere salvato con link ipotetici o rotti. Tutti i link devono passare attraverso `HttpUrlValidator` (verifica anti-soft-404).

---

## 3. Regole di Dominio Commerciale (EDILMORITTU S.R.L. — Silanus)

- **Linea A — Produzione Propria Manufatti C.A.V. & Vibrocompressi (`ATECO 23.61.0`):**
  - Pozzetti, prolunghe, chiusini, tubi, canalette, cordoli stradali, blocchi vibrocompressi, loculi cimiteriali prefabbricati.
  - **Raggio operativo:** Tutta la Sardegna (consegna con 2 camion autogru aziendali).
- **Linea B — Rivendita Edile & Ferramenta (`ATECO 47.52`):**
  - Ferro d'armatura `B450C`, inerti in big-bag, tubazioni PVC `SN4`/`SN8` e multistrato, laterizi/forati, malte tecniche, impermeabilizzanti e pitture.
  - **Raggio operativo:** Vantaggio logistico primario entro `<= 40 km` da Silanus (Marghine, Goceano, Barbagia/Nuorese, Alto Oristanese).
- **Esclusioni Rigide (Gate 1):**
  - Scartare sempre: pietra naturale (basalto, granito, marmo di Orosei, porfido, trachite), getti massivi in opera da autobetoniera (`> 1 t` / classi `S4-S5`), scavi, demolizioni, conferimenti a discarica e forniture mediche/IT.

---

## 4. Comandi Rapidi di Riferimento

```powershell
# Eseguire l'intera suite di test
.\.venv\Scripts\python.exe -m pytest -v

# Avviare scansione live
.\.venv\Scripts\sardegna-radar.exe scan

# Analizzare un Computo Metrico Estimativo (PDF / ZIP / URL)
.\.venv\Scripts\sardegna-radar.exe parse-cme <percorso_o_url> --save

# Visualizzare i lead qualificati
.\.venv\Scripts\sardegna-radar.exe leads --min-score 45

# Aggiornare lo stato CRM di un lead
.\.venv\Scripts\sardegna-radar.exe set-status <CIG> preventivo_inviato
```
