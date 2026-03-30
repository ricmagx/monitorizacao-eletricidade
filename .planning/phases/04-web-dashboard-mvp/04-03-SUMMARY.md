---
phase: 04-web-dashboard-mvp
plan: 03
subsystem: ui
tags: [fastapi, htmx, jinja2, ranking, recommendation, launchd, uvicorn]

# Dependency graph
requires:
  - phase: 04-01
    provides: data_loader service, conftest fixtures, FastAPI app skeleton
  - phase: 04-02
    provides: consumo/custo charts, custo_form, dashboard_content.html structure

provides:
  - calculate_annual_ranking: ranking de fornecedores por custo anual estimado (top-5 + atual)
  - build_recommendation: banner de recomendacao com limiar 50 EUR/ano
  - ranking_table.html: tabela com highlight no fornecedor atual
  - recomendacao_banner.html: banner-success com mensagem de poupanca
  - LaunchAgent plist para auto-start uvicorn no login

affects: [fase 04 verifier, utilizador final — instalar plist manualmente]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rankings calculados sobre history[].top_3 + current_supplier_result, extrapolados para 12 meses"
    - "Banner de recomendacao gated por SAVING_THRESHOLD_EUR = 50 (limiar anual)"
    - "Fornecedor atual adicionado apos top-5 se nao estiver incluido (nao duplica)"

key-files:
  created:
    - src/web/services/rankings.py
    - src/web/templates/partials/ranking_table.html
    - src/web/templates/partials/recomendacao_banner.html
    - tests/test_web_rankings.py
    - launchd/com.ricmag.monitorizacao-eletricidade.dashboard.plist
  modified:
    - src/web/templates/partials/dashboard_content.html
    - src/web/routes/dashboard.py

key-decisions:
  - "SAVING_THRESHOLD_EUR = 50 como limiar anual (poupanca mensal * 12) — banner so aparece quando compensador"
  - "Fornecedor atual destacado com class=highlight na tabela, sempre presente (mesmo fora do top-5)"
  - "LaunchAgent nao instalado automaticamente — deixado para o utilizador instalar manualmente (cp + launchctl load)"
  - "KeepAlive=true no plist — launchd reinicia uvicorn automaticamente se crashar"

patterns-established:
  - "rankings.py como servico puro (sem I/O) — recebe analysis dict ja carregado, calcula e retorna"
  - "build_recommendation usa history_summary.latest_saving_vs_current_eur * 12 para poupanca anual"

requirements-completed:
  - DASH-05
  - DASH-06

# Metrics
duration: 25min
completed: 2026-03-30
---

# Phase 04 Plan 03: Ranking de Fornecedores + LaunchAgent Summary

**Servico de ranking anual (top-5 + atual destacado) e banner de poupanca (>50 EUR/ano) com LaunchAgent uvicorn para auto-start no login**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-30T01:00:00Z
- **Completed:** 2026-03-30T01:25:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Servico `rankings.py` com `calculate_annual_ranking` (extrapola historico para ranking anual, top-5 + atual) e `build_recommendation` (banner gated por 50 EUR/ano)
- Templates Jinja2 para tabela de ranking com `class="highlight"` no fornecedor atual e banner de recomendacao `banner-success`
- `dashboard_content.html` actualizado para incluir ranking e banner reais (substituidos placeholders)
- `dashboard.py` integrado com imports e passagem de `ranking` + `recommendation` para contexto do template
- LaunchAgent plist criado e validado com `plistlib` — pronto para instalacao manual

## Task Commits

1. **Task 1: Servico de ranking + templates** - `4b29f3b` (feat — TDD, 7 testes verdes)
2. **Task 2: LaunchAgent plist** - `c556ac3` (feat)

## Files Created/Modified

- `src/web/services/rankings.py` — `calculate_annual_ranking` e `build_recommendation`
- `src/web/templates/partials/ranking_table.html` — tabela top-5 + atual com highlight
- `src/web/templates/partials/recomendacao_banner.html` — banner banner-success condicional
- `src/web/templates/partials/dashboard_content.html` — substituir placeholders por includes reais
- `src/web/routes/dashboard.py` — importar rankings, calcular e passar ao contexto
- `tests/test_web_rankings.py` — 7 testes (ranking basic, top5, current_in_top5, empty, recommendation significant/insignificant/no_data)
- `launchd/com.ricmag.monitorizacao-eletricidade.dashboard.plist` — LaunchAgent uvicorn 127.0.0.1:8000

## Decisions Made

- Limiar de poupanca anual 50 EUR/ano (poupanca mensal * 12): valor razoavel para evitar ruido em poupancas marginais
- Fornecedor atual sempre presente na tabela (mesmo fora do top-5) — requisito DASH-05
- LaunchAgent nao instalado automaticamente para evitar iniciar servico sem validacao do utilizador

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — implementacao directa conforme especificacao do plano.

## User Setup Required

Para activar o LaunchAgent (auto-start da dashboard no login):

```bash
cp launchd/com.ricmag.monitorizacao-eletricidade.dashboard.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.dashboard.plist
```

Verificar que esta activo:

```bash
launchctl list | grep monitorizacao-eletricidade.dashboard
```

Dashboard disponivel em: http://127.0.0.1:8000

## Next Phase Readiness

- Dashboard completo: consumo, custo, ranking e recomendacao todos funcionais
- Fase 04 concluida — pipeline web-dashboard-mvp entregue
- Pendente: sessao E-REDES requer re-bootstrap manual (FIX-03) para alimentar dados reais

---
*Phase: 04-web-dashboard-mvp*
*Completed: 2026-03-30*

## Self-Check: PASSED

- FOUND: src/web/services/rankings.py
- FOUND: src/web/templates/partials/ranking_table.html
- FOUND: src/web/templates/partials/recomendacao_banner.html
- FOUND: launchd/com.ricmag.monitorizacao-eletricidade.dashboard.plist
- FOUND: tests/test_web_rankings.py
- FOUND commit: 4b29f3b
- FOUND commit: c556ac3
