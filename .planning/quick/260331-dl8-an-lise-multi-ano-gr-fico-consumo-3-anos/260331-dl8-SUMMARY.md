---
phase: 11-analise-multi-ano
plan: dl8
subsystem: web-dashboard
tags: [multi-ano, chart, htmx, analysis]
dependency_graph:
  requires: [consumo_mensal SQLite, comparacoes SQLite]
  provides: [build_consumo_multi_ano, build_resumo_anual, build_comparacao_meses, /local/{id}/multi-ano]
  affects: [dashboard_content.html, consumo_chart.html]
tech_stack:
  added: []
  patterns: [Chart.js grouped bars, HTMX fragment swap, Jinja2 conditional include]
key_files:
  created:
    - src/web/templates/partials/resumo_anual.html
    - src/web/templates/partials/multi_ano.html
  modified:
    - src/web/services/data_loader.py
    - src/web/routes/dashboard.py
    - src/web/templates/partials/consumo_chart.html
    - src/web/templates/partials/dashboard_content.html
    - tests/test_web_data_loader.py
    - tests/test_web_dashboard.py
decisions:
  - "Gráfico multi-ano usa total_kwh (vazio+fora_vazio) por barra — simplifica leitura vs barras empilhadas por tipo"
  - "Paleta fixa 5 cores Chart.js: azul, laranja, verde, roxo, vermelho — máximo 5 anos simultâneos"
  - "consumo_chart.html retrocompatível: modo multi-ano activado apenas se consumo_multi_ano presente no contexto"
  - "Form HTMX em resumo_anual.html usa hx-trigger='change' — actualiza automaticamente ao seleccionar"
  - "selected_ano1/ano2 com default para últimos 2 anos disponíveis quando params ausentes"
metrics:
  duration_seconds: 558
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_modified: 8
---

# Phase 11 Plan dl8: Análise Multi-ano — Gráfico Consumo 3 Anos Summary

**One-liner:** Análise multi-ano com barras Chart.js agrupadas por ano (paleta fixa), endpoint HTMX `/multi-ano`, resumo anual de totais e comparação mensal lado a lado.

## Objective

Fechar os requisitos ANAL-01/02/03: gráfico de consumo com anos distinguíveis por cor, comparação mês-a-mês entre dois anos, e painel de resumo anual.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Funções de análise multi-ano em data_loader.py | d3c492a | data_loader.py, test_web_data_loader.py |
| 2 | Endpoint HTMX + templates multi-ano | a61917c | dashboard.py, consumo_chart.html, resumo_anual.html, multi_ano.html, dashboard_content.html, test_web_dashboard.py |

## Funções Adicionadas a data_loader.py

### `build_consumo_multi_ano(consumo_data: list) -> dict`
- Agrupa consumo por ano; cada dataset tem 12 entradas (None para meses sem dados)
- Output: `{"anos": [...], "meses": ["Jan",...], "datasets": [{"ano": str, "vazio": [...], "fora_vazio": [...]}]}`

### `build_resumo_anual(consumo_data: list, comparacoes_history: list | None) -> list`
- Totais anuais de consumo kWh e custo EUR
- `custo_total_eur=None` quando `comparacoes_history=None`

### `build_comparacao_meses(consumo_data, comparacoes_history, ano1, ano2, mes) -> dict`
- Compara mesmo mês entre dois anos: consumo kWh + custo EUR
- Retorna `None` nos campos quando dados inexistentes

## Endpoint e Templates

- **GET /local/{local_id}/multi-ano**: aceita `?ano1=&ano2=&mes=`, SQLite-first com fallback CSV/JSON
- **consumo_chart.html**: modo multi-ano activado quando `consumo_multi_ano` presente (retrocompatível)
- **resumo_anual.html**: tabela totais + form HTMX com selects + comparação mensal lado a lado
- **multi_ano.html**: container `#multi-ano-container` que inclui os dois partials
- **dashboard_content.html**: botão "Analise Multi-ano" com `hx-get` + div vazia receptora

## Decisões de Implementação

1. **Barras agrupadas vs empilhadas**: gráfico multi-ano usa total_kwh por ano numa barra — mais legível do que barras empilhadas vazio/fora_vazio por ano
2. **Paleta fixa 5 cores**: `['#3b82f6','#f97316','#22c55e','#a855f7','#ef4444']` — máximo 5 anos simultâneos, consistente entre re-renders
3. **Retrocompatibilidade consumo_chart.html**: bloco `{% if consumo_multi_ano is defined and consumo_multi_ano %}` — contexto normal não passa esta variável, comportamento original preservado
4. **hx-trigger='change'**: form actualiza automaticamente ao mudar selects, sem botão Submit
5. **Default anos_disponiveis**: `selected_ano1` = penúltimo ano, `selected_ano2` = último ano quando params ausentes

## Testes Adicionados

- **4 testes TDD** em `tests/test_web_data_loader.py::TestMultiAno`
- **6 testes** em `tests/test_web_dashboard.py` (endpoint multi-ano)
- **Total suite**: 126 passed, 14 skipped (116 existentes + 10 novos)

## Deviations from Plan

None — plano executado exactamente como escrito.

## Self-Check: PASSED

All files verified:
- src/web/services/data_loader.py: FOUND
- src/web/routes/dashboard.py: FOUND
- src/web/templates/partials/consumo_chart.html: FOUND
- src/web/templates/partials/resumo_anual.html: FOUND
- src/web/templates/partials/multi_ano.html: FOUND
- commit d3c492a: FOUND
- commit a61917c: FOUND
