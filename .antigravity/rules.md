# Antigravity Workspace Rules — Sardegna B2B Radar

Segui rigorosamente le regole definite in [`AGENTS.md`](../AGENTS.md):

1. **Plan-Before-Execute:** Chiedi sempre l'approvazione del piano prima di eseguire modifiche multi-file, migrazioni/schemi DB, modifiche allo scoring del catalogo EDILMORITTU S.R.L., modifiche a `pyproject.toml` o comandi Git esterni (`push`, `reset`, `rebase`).
2. **Test-First & 100% Green:** Ogni modifica al codice richiede che `.\.venv\Scripts\python.exe -m pytest -q` passi al 100% prima di concludere il task.
3. **Changelog Timestamp:** Aggiorna sempre `CHANGELOG.md` con timestamp `[YYYY-MM-DD HH:MM]` dopo ogni feature o fix significativo.
4. **Zero Hardcoded Secrets & $0 OPEX Core:** Nessuna credenziale nel codice; nessuna dipendenza da API LLM a pagamento nel ciclo di scansione e matching.
