---
phase: 04-web-dashboard-mvp
plan: 02
subsystem: ui
tags: [fastapi, chartjs, htmx, jinja2, charts, stacked-bar, mixed-chart]

# Dependency graph
requires:
  - phase: 04-01
    provides: dashboard route skeleton, data_loader with load_consumo_csv/load_analysis_json, FastAPI app.state patterns
provides:
  - Chart.js stacked bar para consumo mensal (vazio + fora_vazio)
  - Chart.js mixed bar+line para custo (estimativa vs custo real, spanGaps:false)
  - Formulario HTMX inline para entrada de custo real por mes
  - POST /local/{local_id}/custo-real com persistencia em custos_reais.json
  - load_custos_reais, save_custo_real, build_custo_chart_data em data_loader.py
affects:
  - 04-03 (ranking/recomendacao podem reutilizar padroes custo_chart)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "custos_reais.json como persistencia de dados de entrada do utilizador (ficheiro plano JSON)"
    - "HTMX hx-post + hx-target para swap parcial sem reload de pagina"
    - "spanGaps: false no Chart.js para omitir meses sem custo real (gap na linha)"
    - "custo_section.html como wrapper para swap atomico de grafico + formulario"

key-files:
  created:
    - src/web/routes/custos_reais.py
    - src/web/templates/partials/consumo_chart.html
    - src/web/templates/partials/custo_chart.html
    - src/web/templates/partials/custo_form.html
    - src/web/templates/partials/custo_section.html
    - tests/test_web_custos_reais.py
  modified:
    - src/web/services/data_loader.py
    - src/web/routes/dashboard.py
    - src/web/app.py
    - src/web/templates/partials/dashboard_content.html
    - tests/test_web_data_loader.py

key-decisions:
  - "custo_section.html como wrapper unico para swap HTMX — permite actualizar grafico + formulario num unico hx-swap"
  - "spanGaps: false no dataset de custo real — meses sem dado sao gaps na linha, nao zeros"
  - "None em custo_real_data (Python) serializa para null em JSON/tojson — compativel com Chart.js gap handling"
  - "custos_reais.json em data/{local_id}/ (nao em state/) — e dado de entrada do utilizador, nao estado do pipeline"

patterns-established:
  - "TDD RED-GREEN: testes escritos e falhados antes de qualquer implementacao"
  - "build_*_chart_data como funcao de servico separada da route — testavel de forma independente"

requirements-completed: [DASH-02, DASH-03, DASH-04]

# Metrics
duration: 4min
completed: 2026-03-30
---

# Phase 04 Plan 02: Graficos e Formulario de Custo Real Summary

**Chart.js stacked bar (consumo vazio/fora_vazio) + mixed bar+line (estimativa vs custo real) + formulario HTMX com persistencia em custos_reais.json**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-30T00:48:39Z
- **Completed:** 2026-03-30T00:51:58Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 11

## Accomplishments

- Dois graficos Chart.js funcionais: barras empilhadas de consumo e misto (bar+line) de custo
- Formulario HTMX por mes que persiste custos reais em `data/{local}/custos_reais.json`
- `build_custo_chart_data` com `None` para meses sem custo real (gap na linha, nao zero)
- 62 testes passam (suite completa incluindo planos anteriores)

## Task Commits

1. **TDD RED - test_web_custos_reais.py** - `1229a4e` (test)
2. **GREEN - implementacao completa** - `4a848c5` (feat)

## Files Created/Modified

- `src/web/services/data_loader.py` - Adicionado load_custos_reais, save_custo_real, build_custo_chart_data
- `src/web/routes/custos_reais.py` - POST /local/{local_id}/custo-real endpoint
- `src/web/routes/dashboard.py` - Contexto expandido com custos_reais, consumo_chart, custo_chart
- `src/web/app.py` - Registo de custos_router (app.state.templates ja existia do plan 01)
- `src/web/templates/partials/consumo_chart.html` - Chart.js stacked bar
- `src/web/templates/partials/custo_chart.html` - Chart.js mixed bar+line com spanGaps:false
- `src/web/templates/partials/custo_form.html` - Formulario HTMX com hx-post
- `src/web/templates/partials/custo_section.html` - Wrapper para swap atomico (grafico + form)
- `src/web/templates/partials/dashboard_content.html` - Substituidos placeholders por includes
- `tests/test_web_custos_reais.py` - 11 testes novos (load/save/endpoint)
- `tests/test_web_data_loader.py` - 2 testes novos (build_custo_chart_data)

## Decisions Made

- `custo_section.html` como wrapper unico para HTMX swap — permite que o POST actualize grafico E formulario num unico `innerHTML` swap sem recarregar a pagina
- `None` em Python para meses sem custo real serializa automaticamente para `null` via Jinja2 `tojson`, que Chart.js interpreta como gap com `spanGaps: false`
- `custos_reais.json` em `data/{local_id}/` e nao em `state/` — semanticamente e input do utilizador, nao estado do pipeline

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

- `dashboard_content.html`: `#ranking-section` e `#recomendacao-section` com texto "A implementar..." — intencionais, a ser preenchidos pelo Plan 03.

## Next Phase Readiness

- Graficos e formulario funcionais — dashboard tem os dois elementos visuais centrais
- Plan 03 pode implementar ranking e recomendacao nos divs `#ranking-section` e `#recomendacao-section` ja presentes no `dashboard_content.html`
- Padrao `custo_section.html` wrapper pode ser reutilizado pelo Plan 03 se necessitar de swap parcial similar

---
*Phase: 04-web-dashboard-mvp*
*Completed: 2026-03-30*
