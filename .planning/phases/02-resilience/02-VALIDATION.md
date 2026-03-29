---
phase: 2
slug: resilience
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.3 |
| **Config file** | none — Wave 0 installs `pytest.ini` |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| W0-01 | 01 | 0 | RES-01 | unit (mock) | `python -m pytest tests/test_tiagofelicia_fallback.py -x` | ❌ W0 | ⬜ pending |
| W0-02 | 01 | 0 | RES-02 | unit | `python -m pytest tests/test_xlsx_validation.py -x` | ❌ W0 | ⬜ pending |
| W0-03 | 01 | 0 | RES-03 | unit | `python -m pytest tests/test_supplier_missing.py -x` | ❌ W0 | ⬜ pending |
| 2-01-01 | 01 | 1 | RES-01 | unit (mock) | `python -m pytest tests/test_tiagofelicia_fallback.py -x` | ✅ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | RES-03 | unit | `python -m pytest tests/test_supplier_missing.py -x` | ✅ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | RES-02 | unit | `python -m pytest tests/test_xlsx_validation.py -x` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — torna `tests/` um package Python
- [ ] `tests/conftest.py` — fixtures partilhadas (sample XLSX, sample CSV, config de teste com catálogo local, mock da page Playwright)
- [ ] `tests/test_tiagofelicia_fallback.py` — stubs para RES-01 (mock de falha de rede + verificação de relatório)
- [ ] `tests/test_xlsx_validation.py` — stubs para RES-02 (bounds check: 0 kWh, >5000 kWh, valores normais)
- [ ] `tests/test_supplier_missing.py` — stubs para RES-03 (None result + warning no relatório)
- [ ] `pytest.ini` — define `testpaths = ["tests"]` e `pythonpath = ["src/backend"]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Relatório indica "catálogo local" quando fallback activo | RES-01 | Verificação visual do ficheiro .md gerado | Bloquear `tiagofelicia.pt` via mock, correr pipeline, abrir relatório e confirmar texto de fallback |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
