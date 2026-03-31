---
phase: 9
slug: dashboard-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_web_dashboard.py tests/test_web_rankings.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_web_dashboard.py tests/test_web_rankings.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | UI-02 | integration | `pytest tests/test_web_dashboard.py -x -k "selector"` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | UI-02 | integration | `pytest tests/test_web_dashboard.py::test_local_dashboard_swap -x` | ✅ | ⬜ pending |
| 09-01-03 | 01 | 1 | UI-04 | integration | `pytest tests/test_web_dashboard.py::test_consumo_chart_sqlite -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | UI-03 | unit | `pytest tests/test_web_rankings.py::test_annual_ranking_poupanca -x` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | UI-03 | integration | `pytest tests/test_web_rankings.py -x` | ✅ | ⬜ pending |
| 09-02-03 | 02 | 2 | UI-05 | integration | `pytest tests/test_web_dashboard.py::test_custo_chart_two_bars -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_web_dashboard.py` — adicionar `test_local_dashboard_swap` (locais SQLite-only), `test_consumo_chart_sqlite`, `test_custo_chart_two_bars`
- [ ] `tests/test_web_rankings.py` — adicionar `test_annual_ranking_poupanca` com campo `poupanca_potencial`
- [ ] `tests/conftest.py` — verificar fixture `web_client` com locais SQLite (seed em `comparacoes` + `consumo_mensal`)

*Wave 0 deve ser o primeiro task do primeiro plano.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Layout segue UI-SPEC (cores, tipografia, espaçamento) | UI-05 | Visual — não automatizável | Abrir browser em localhost:8000, comparar com 06-UI-SPEC.md side-by-side |
| Selector muda dados sem reload de página (comportamento HTMX) | UI-02 | Requer browser real | Abrir DevTools Network tab, seleccionar local diferente, confirmar que não há full-page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
