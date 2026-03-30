---
phase: 4
slug: web-dashboard-mvp
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (já instalado) |
| **Config file** | `pytest.ini` ou `pyproject.toml [tool.pytest]` — Wave 0 instala se ausente |
| **Quick run command** | `pytest tests/web/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 segundos |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/web/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | DASH-01 | integration | `pytest tests/web/test_app.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | DASH-02 | integration | `pytest tests/web/test_routes.py::test_local_selector -x -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | DASH-03 | unit | `pytest tests/web/test_routes.py::test_chart_data -x -q` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | DASH-04 | manual | verificar no browser — DevTools Network tab | N/A | ⬜ pending |
| 4-03-01 | 03 | 2 | DASH-05 | unit | `pytest tests/web/test_rankings.py -x -q` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 2 | DASH-06 | unit | `pytest tests/web/test_yoy.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/web/__init__.py` — pacote de testes web
- [ ] `tests/web/test_app.py` — stubs para DASH-01 (startup + homepage)
- [ ] `tests/web/test_routes.py` — stubs para DASH-02 e DASH-03 (selector HTMX + chart data)
- [ ] `tests/web/test_rankings.py` — stubs para DASH-05 (ranking de fornecedores)
- [ ] `tests/web/test_yoy.py` — stubs para DASH-06 (delta ano-a-ano, graceful sem dados)
- [ ] `tests/conftest.py` — fixtures partilhadas (JSON de análise mock, paths de config)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTMX sem recarga de página | DASH-02 | DOM event, não observável por pytest | Browser DevTools → Network tab → verificar que apenas o fragmento HTML é devolvido, não a página completa |
| Ficheiros estáticos locais | DASH-07 | Requer inspeção de Network tab | Abrir DevTools → Network → confirmar que Chart.js e HTMX carregam de `localhost:8000/static/vendor/`, nenhum CDN externo |
| Indicador de frescura em aviso | DASH-05 | Requer manipulação de data | Alterar timestamp do último JSON para >40 dias → verificar indicador laranja/vermelho no browser |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
