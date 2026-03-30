---
phase: 04-web-dashboard-mvp
plan: 01
subsystem: ui
tags: [fastapi, htmx, jinja2, chart.js, python, pytest]

# Dependency graph
requires:
  - phase: 03-multi-location-refactor
    provides: config/system.json multi-location schema com locations[].id, locations[].pipeline
provides:
  - FastAPI app (src.web.app:app) com StaticFiles e Jinja2Templates
  - data_loader service com load_locations, load_consumo_csv, load_analysis_json, load_monthly_status, get_freshness_info
  - GET / e GET /local/{id}/dashboard routes
  - HTMX 2.0.8 e Chart.js 4.5.1 como ficheiros estaticos locais
  - Templates Jinja2: base.html, dashboard.html, partials/dashboard_content.html, partials/frescura_badge.html
  - Infraestrutura de testes: 15 testes passando (data loader + routes)
affects:
  - 04-02 (charts — constroi sobre canvas ids consumo-chart e custo-chart)
  - 04-03 (ranking e recomendacao — usa partials/dashboard_content.html)

# Tech tracking
tech-stack:
  added: [fastapi 0.135.2, uvicorn, jinja2, python-multipart, httpx, htmx 2.0.8, chart.js 4.5.1]
  patterns: [app.state para config/templates injectados nos routes, TemplateResponse com request= kwarg (Starlette 1.0), data_loader sem estado]

key-files:
  created:
    - src/web/app.py
    - src/web/routes/dashboard.py
    - src/web/services/data_loader.py
    - src/web/static/vendor/htmx.min.js
    - src/web/static/vendor/chart.umd.min.js
    - src/web/static/style.css
    - src/web/templates/base.html
    - src/web/templates/dashboard.html
    - src/web/templates/partials/dashboard_content.html
    - src/web/templates/partials/frescura_badge.html
    - tests/test_web_data_loader.py
    - tests/test_web_dashboard.py
  modified:
    - tests/conftest.py
    - requirements.txt
    - pytest.ini
    - src/__init__.py

key-decisions:
  - "app.state guarda config_path e templates — permite override nos testes sem monkeypatch complexo"
  - "TemplateResponse usa request= kwarg (API Starlette 1.0) — nao context dict posicional"
  - "pytest.ini pythonpath inclui . (project root) para src.web ser importavel nos testes"
  - "FastAPI upgradeado de 0.104.1 para 0.135.2 para compatibilidade com Starlette 1.0.0"

patterns-established:
  - "Pattern: data_loader funcoes sao puras (sem estado, sem side effects) — facilitam testes unitarios"
  - "Pattern: _load_location_data helper no router — evita duplicacao entre / e /local/{id}/dashboard"
  - "Pattern: HTMX swap para fragmentos — GET /local/{id}/dashboard retorna partial sem DOCTYPE"

requirements-completed: [DASH-01]

# Metrics
duration: 6min
completed: 2026-03-30
---

# Phase 4 Plan 01: Web Dashboard Foundation Summary

**FastAPI app com selector de local HTMX, data_loader service testado para CSV/JSON/frescura, e HTMX 2.0.8 + Chart.js 4.5.1 servidos como ficheiros estaticos locais**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-30T00:39:40Z
- **Completed:** 2026-03-30T00:45:46Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments

- App FastAPI funcional com GET / (homepage com selector) e GET /local/{id}/dashboard (fragmento HTMX)
- Data loader service com 5 funcoes testadas: load_locations, load_consumo_csv, load_analysis_json, load_monthly_status, get_freshness_info (limiar 40 dias)
- HTMX 2.0.8 (51KB) e Chart.js 4.5.1 (208KB) descarregados e servidos localmente — zero pedidos CDN
- 15 testes passando: 10 data loader + 5 routes (homepage, swap, 404)
- Templates Jinja2 completos com selector de local e indicador de frescura

## Task Commits

1. **Task 1: FastAPI app, data_loader service, TDD testes** - `0abe7b8` (feat)
2. **Task 2: Ficheiros estaticos e CSS completo** - `7247ba6` (feat)

## Files Created/Modified

- `src/__init__.py` - Package marker para resolver src.web.app
- `src/web/app.py` - FastAPI app com StaticFiles, Jinja2Templates, app.state
- `src/web/routes/dashboard.py` - GET / e GET /local/{id}/dashboard com 404 para local invalido
- `src/web/services/data_loader.py` - Servico de leitura CSV, JSON, status, frescura
- `src/web/static/vendor/htmx.min.js` - HTMX 2.0.8 (51KB, local)
- `src/web/static/vendor/chart.umd.min.js` - Chart.js 4.5.1 (208KB, local)
- `src/web/static/style.css` - CSS minimalista com custom properties
- `src/web/templates/base.html` - Template base com Jinja2, sem CDN externo
- `src/web/templates/dashboard.html` - Pagina completa com selector e dashboard-content div
- `src/web/templates/partials/dashboard_content.html` - Fragmento HTMX com canvas ids consumo-chart e custo-chart
- `src/web/templates/partials/frescura_badge.html` - Badge com badge-ok/badge-stale
- `tests/test_web_data_loader.py` - 10 testes unitarios data loader
- `tests/test_web_dashboard.py` - 5 testes de routes
- `tests/conftest.py` - Fixtures sample_analysis_json, sample_status_json, sample_config_json, web_client
- `requirements.txt` - Adiciona fastapi, uvicorn, jinja2, python-multipart, httpx
- `pytest.ini` - Adiciona . ao pythonpath para importar src.web

## Decisions Made

- Upgradeado FastAPI 0.104.1 para 0.135.2: versao instalada era incompativel com Starlette 1.0.0 (TypeError em Router.__init__)
- API `TemplateResponse` mudou no Starlette 1.0: passou de posicional `(name, context)` para keyword-only `(request=, name=, context=)` — ajustado no routes/dashboard.py
- `app.state.config_path` permite override nos testes sem alterar app global — solucao limpa para TestClient

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FastAPI incompativel com Starlette 1.0.0**
- **Found during:** Task 1 (testes dashboard)
- **Issue:** FastAPI 0.104.1 instalado mas Starlette 1.0.0 instalada — TypeError em Router.__init__ ao importar app
- **Fix:** Upgradeado FastAPI para 0.135.2 via pip
- **Files modified:** requirements.txt (versao actualizada)
- **Verification:** 15 testes passam com exit code 0
- **Committed in:** 0abe7b8 (Task 1 commit)

**2. [Rule 1 - Bug] TemplateResponse API mudou no Starlette 1.0**
- **Found during:** Task 1 (teste test_homepage_ok)
- **Issue:** TypeError unhashable type 'dict' ao chamar TemplateResponse(name, context) — API posicional removida
- **Fix:** Mudado para TemplateResponse(request=request, name=..., context=...) em ambas as routes
- **Files modified:** src/web/routes/dashboard.py
- **Verification:** 15 testes passam
- **Committed in:** 0abe7b8 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Ambas as correccoes necessarias para funcionalidade. Sem scope creep.

## Issues Encountered

- FastAPI version mismatch com Starlette no ambiente — resolvido com upgrade rapido

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Canvas ids `consumo-chart` e `custo-chart` presentes no partial — Plan 04-02 pode injectar dados Chart.js
- Ids `ranking-section` e `recomendacao-section` presentes no partial — Plan 04-03 pode preencher
- `uvicorn src.web.app:app` funcional para teste manual em localhost:8000
- Selector de local HTMX funcional — troca /local/{id}/dashboard com hx-swap="innerHTML"

## Known Stubs

- `src/web/templates/partials/dashboard_content.html`: canvas `consumo-chart` e `custo-chart` sem dados (placeholder para Plan 04-02)
- `src/web/templates/partials/dashboard_content.html`: `ranking-section` e `recomendacao-section` com texto placeholder (para Plan 04-03)

Estes stubs sao intencionais — estao documentados no PLAN.md como "dados injectados pelo Plan 02/03". Nao impedem o objectivo deste plano (fundacao da app).

---
*Phase: 04-web-dashboard-mvp*
*Completed: 2026-03-30*

## Self-Check: PASSED

- All 14 created/modified files exist on disk
- Commits 0abe7b8 and 7247ba6 verified in git log
- 15 tests passing (pytest exit code 0)
- All acceptance criteria met
