# Guida di Contribuzione e Workflow — Sardegna B2B Radar

Questo documento definisce il flusso di lavoro, le convenzioni di codice e la checklist di qualità per sviluppare su **Sardegna B2B Radar**.

---

## 1. Workflow Operativo (Regola Plan-Before-Execute)

1. **Allineamento e Piano:** Prima di toccare schemi DB, regole di scoring, dipendenze o refactoring multi-file, definire il piano e ottenere l'approvazione (vedi [`AGENTS.md`](./AGENTS.md)).
2. **Sviluppo TDD (Red -> Green -> Refactor):**
   - Scrivere o aggiornare il test in `tests/`.
   - Verificare che il test fallisca prima dell'implementazione e passi subito dopo.
3. **Verifica Completa:**
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -v
   ```
4. **Aggiornamento Contesto:**
   - Aggiungere una voce con data e ora `[YYYY-MM-DD HH:MM]` in [`CHANGELOG.md`](./CHANGELOG.md).
   - Se è stata presa una scelta architetturale rilevante, documentarla in [`docs/DECISIONS.md`](./docs/DECISIONS.md).

---

## 2. Convenzioni per i Commit (Conventional Commits)

Tutti i commit devono seguire il formato **Conventional Commits**:

- `feat(modulo): descrizione sintetica della nuova funzionalità`
- `fix(modulo): descrizione del bug corretto`
- `refactor(modulo): pulizia codice senza cambio di comportamento`
- `test(modulo): aggiunta o aggiornamento test`
- `docs(contesto): aggiornamento documentazione, changelog o regole`

Esempio:
```text
feat(cme): add PriMus multi-page parser and Gate 1 stone exclusion
```

---

## 3. Standard di Codice Python

- **Versione:** Python `>= 3.11` con `from __future__ import annotations` in ogni modulo.
- **Tipizzazione:** Type hints completi su parametri e valori di ritorno; modelli validati con `Pydantic v2`.
- **Resilienza Rete:** Ogni client HTTP deve usare `httpx.AsyncClient` con `AsyncHTTPTransport(retries=3)` e timeout espliciti.
- **Gestione Errori:** Usare le eccezioni specifiche definite in `src/sardegna_radar/exceptions.py` evitando `except Exception:` silenziosi.

---

## 4. Checklist Pre-Commit / Pre-Release

- [ ] `.\.venv\Scripts\python.exe -m pytest -q` restituisce **100% passed (`0 failed`)**.
- [ ] Nessun token, API key o dato sensibile presente nel diff (`git diff`).
- [ ] `CHANGELOG.md` aggiornato con data e ora `[YYYY-MM-DD HH:MM]`.
- [ ] Tutti gli URL salvati nel DB passano la validazione `HttpUrlValidator`.
