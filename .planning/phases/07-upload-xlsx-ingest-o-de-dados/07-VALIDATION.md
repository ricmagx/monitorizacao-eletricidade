---
phase: 7
slug: upload-xlsx-ingest-o-de-dados
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `tests/conftest.py` (existing) |
| **Quick run command** | `pytest tests/ -x -q --tb=short` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

### Plan 01 — Data layer + services (Wave 1)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-00 | 01 | 1 | ALL (stubs) | stub | `pytest tests/test_web_upload.py tests/test_ingestao_xlsx.py tests/test_web_locais.py tests/test_comparacao.py -x -q` | Wave 0 creates | ⬜ pending |
| 7-01-01 | 01 | 1 | CONF-01, CONF-02 | unit | `python -c "from src.db.schema import locais; print(locais.c.keys())"` | n/a (schema) | ⬜ pending |
| 7-01-02 | 01 | 1 | UPLD-02 | unit | `python -c "from src.backend.eredes_to_monthly_csv import parse_xlsx_to_dict; print('ok')"` | n/a (refactor) | ⬜ pending |
| 7-01-03 | 01 | 1 | UPLD-02, UPLD-05, CONF-01, CONF-02 | unit | `python -c "from src.web.services.ingestao_xlsx import ingerir_xlsx; from src.web.services.locais_service import get_all_locais; print('ok')"` | n/a (services) | ⬜ pending |

### Plan 02 — HTTP endpoints + templates + wiring (Wave 2)

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-02-01 | 02 | 2 | UPLD-01, COMP-01 | integration | `python -c "from src.web.routes.upload import router; print('ok')"` + `pytest tests/test_web_upload.py -x -q` | tests/test_web_upload.py | ⬜ pending |
| 7-02-02 | 02 | 2 | CONF-01, CONF-02 | integration | `python -c "from src.web.app import app; routes = [r.path for r in app.routes]; assert '/locais' in routes"` + `pytest tests/test_web_locais.py -x -q` | tests/test_web_locais.py | ⬜ pending |
| 7-02-03 | 02 | 2 | UPLD-01, CONF-01 | smoke | `python -c "content = open('src/web/templates/dashboard.html').read(); assert 'upload_xlsx.html' in content; assert 'Gerir locais' in content"` | n/a (template) | ⬜ pending |
| 7-02-04 | 02 | 2 | COMP-01 | smoke | `grep -q 'playwright' requirements-docker.txt && grep -q 'playwright install chromium' Dockerfile` | n/a (config) | ⬜ pending |
| 7-02-05 | 02 | 2 | CONF-01 | integration | `python -c "from src.web.services.data_loader import load_locations; import inspect; assert 'engine' in inspect.signature(load_locations).parameters"` | n/a (data_loader) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_web_upload.py` — stubs for UPLD-01, COMP-01, graceful degradation (playwright unavailable)
- [x] `tests/test_ingestao_xlsx.py` — stubs for UPLD-02, UPLD-05 (store monthly, idempotency, CPE routing)
- [x] `tests/test_web_locais.py` — stubs for CONF-01, CONF-02 (create local, edit fornecedor, list)
- [x] `tests/test_comparacao.py` — stubs for COMP-02 (store tiagofelicia.pt result, idempotency)
- [x] `tests/conftest.py` — fixture `db_engine_test` for in-memory SQLite with Phase 7 tables

*(Wave 0 is Task 0 of Plan 01 — creates all stubs before any implementation begins.)*

---

## Automated Stubs Summary

| Test File | Stubs | Covers |
|-----------|-------|--------|
| `tests/test_web_upload.py` | `test_upload_xlsx_ok`, `test_upload_xlsx_cpe_nao_detectado`, `test_background_task_registada`, `test_upload_sem_playwright_retorna_200` | UPLD-01, UPLD-05, COMP-01, COMP-01 graceful degradation |
| `tests/test_ingestao_xlsx.py` | `test_ingestao_escreve_sqlite`, `test_cpe_routing`, `test_idempotencia`, `test_cpe_nao_detectado` | UPLD-02, UPLD-05, idempotency |
| `tests/test_web_locais.py` | `test_criar_local`, `test_editar_fornecedor`, `test_listar_locais` | CONF-01, CONF-02 |
| `tests/test_comparacao.py` | `test_comparacao_guardada`, `test_comparacao_idempotente` | COMP-02 |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Upload XLSX via browser form, receive confirmation | UPLD-01 | UI interaction required | Upload real E-REDES XLSX, verify period + CPE shown in response |

*(COMP-01 has automated stub `test_background_task_registada` + `test_upload_sem_playwright_retorna_200`. Full browser verification is manual but automated coverage ensures the code path works.)*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
