---
phase: 09-dashboard-ui
plan: 02
subsystem: web-dashboard
tags: [ui-spec, chart-js, ranking, templates, dashboard]
dependency_graph:
  requires: [09-01, 06-ui-spec]
  provides: [ui-spec-aligned-dashboard, poupanca-potencial-ranking, bar-bar-cost-chart]
  affects:
    - src/web/services/rankings.py
    - src/web/templates/partials/custo_chart.html
    - src/web/templates/partials/ranking_table.html
    - src/web/templates/partials/recomendacao_banner.html
    - src/web/templates/partials/dashboard_content.html
    - tests/test_web_dashboard.py
    - tests/test_web_rankings.py
tech_stack:
  added: []
  patterns:
    - Chart.js dual bar datasets (sem stack) para bar lado a lado
    - Jinja2 inline conditional para campos opcionais (plan no banner)
key_files:
  created: []
  modified:
    - src/web/services/rankings.py
    - src/web/templates/partials/custo_chart.html
    - src/web/templates/partials/ranking_table.html
    - src/web/templates/partials/recomendacao_banner.html
    - src/web/templates/partials/dashboard_content.html
    - tests/test_web_dashboard.py
    - tests/test_web_rankings.py
decisions:
  - Teste de poupanca_potencial usa web_client_sqlite (tem dados reais) em vez de web_client (sem dados = empty state sem thead)
metrics:
  duration_minutes: 4
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_modified: 7
  tests_added: 6
  tests_total: 107
---

# Phase 9 Plan 02: Dashboard UI Alignment Summary

**One-liner:** Alinhou componentes visuais com UI-SPEC — grafico de custo bar+bar, coluna poupanca potencial no ranking, banner com nome do plano, upload PDF integrado no layout.

## What Was Built

Tres divergencias entre o estado actual e a UI-SPEC corrigidas: (1) grafico de custo mudou de bar+line para bar+bar com cores UI-SPEC; (2) ranking ganhou coluna "Poupanca Potencial (EUR/ano)" calculada em `rankings.py`; (3) banner de recomendacao mostra plano alem do fornecedor. Layout do dashboard foi reorganizado: `custo_form.html` removido, `upload_xlsx.html` + `upload_pdf.html` integrados.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Poupanca potencial no ranking + plan no recommendation | 4e56a60 | src/web/services/rankings.py, tests/test_web_rankings.py |
| 2 | Alinhar templates com UI-SPEC | ee2c42c | 5 template files, tests/test_web_dashboard.py |

## Decisions Made

1. **Teste de poupanca usa web_client_sqlite:** O fixture `web_client` nao tem dados de ranking (BD vazia = empty state = sem thead). Para testar que a coluna "Poupanca Potencial" aparece no thead, e necessario um fixture com dados — `web_client_sqlite` tem seed data com comparacoes. Desvio do plano original que especificava `web_client`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Teste test_ranking_has_poupanca_column falhou com web_client (sem dados)**
- **Found during:** Task 2 (primeira execucao de testes)
- **Issue:** `web_client` usa BD vazia — ranking retorna lista vazia — template mostra empty state sem `<thead>` — "Poupanca Potencial" nao aparece no HTML.
- **Fix:** Alterado fixture do teste de `web_client` para `web_client_sqlite` (tem seed data com comparacoes que geram ranking).
- **Files modified:** tests/test_web_dashboard.py
- **Commit:** ee2c42c

## Verification Results

```
107 passed, 14 skipped in 0.87s
```

Todos os testes passam incluindo os 6 novos testes UI-SPEC.

## Known Stubs

None — todos os dados sao lidos de SQLite ou calculados em tempo real. Poupanca potencial calculada de dados reais.

## Self-Check: PASSED
