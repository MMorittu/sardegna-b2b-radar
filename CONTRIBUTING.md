# Contributing Guide & Engineering Workflow — Sardegna B2B Radar

This document defines the engineering workflow, coding conventions, and quality checklist for **Sardegna B2B Radar**.

---

## 1. Test-Driven Development (TDD) Workflow

1. **Red -> Green -> Refactor:**
   - Write or update the unit/integration test in `tests/`.
   - Verify the test fails before implementation and passes immediately after.
2. **Full Test Suite Verification:**
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -v
   ```
3. **Documentation & Context Sync:**
   - Record notable changes with an ISO timestamp `[YYYY-MM-DD HH:MM]` in [`CHANGELOG.md`](./CHANGELOG.md).
   - Document major architectural trade-offs in [`docs/DECISIONS.md`](./docs/DECISIONS.md).

---

## 2. Commit Conventions (Conventional Commits)

All commits must follow the **Conventional Commits** specification:

- `feat(module): concise description of the new capability`
- `fix(module): description of the bug fix`
- `refactor(module): internal code cleanup without behavior change`
- `test(module): new or updated unit/integration tests`
- `docs(context): documentation, ADR, or changelog updates`

---

## 3. Python Engineering Standards

- **Runtime:** Python `>= 3.11` with `from __future__ import annotations` in every module.
- **Type Safety:** Strict type annotations across parameters and return types; domain boundaries validated via `Pydantic v2`.
- **Network Resilience:** All HTTP clients must use `httpx.AsyncClient` with `AsyncHTTPTransport(retries=3)` and explicit timeouts.
- **Error Handling:** Raise typed exceptions from `src/sardegna_radar/exceptions.py` rather than swallowing broad `Exception` blocks.

---

## 4. Pre-Release Checklist

- [ ] `.\.venv\Scripts\python.exe -m pytest -q` passes **100% (`0 failed`)**.
- [ ] Zero hardcoded tokens, API keys, or private credentials in `git diff`.
- [ ] `CHANGELOG.md` updated with `[YYYY-MM-DD HH:MM]`.
- [ ] All candidate notice URLs pass `HttpUrlValidator`.
