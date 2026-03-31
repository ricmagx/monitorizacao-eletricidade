---
phase: 10-cache-tiagofelicia-pt-integra-o-compara-o
plan: 02
subsystem: ui
tags: [jinja2, htmx, fastapi, css, tdd]

requires:
  - phase: 10-01
    provides: source field in freshness dict from get_freshness_from_sqlite

provides:
  - Badge ternario de frescura (fresh/cache/none) em frescura_badge.html
  - Badge relocado para dashboard_content.html (dentro do HTMX swap zone)
  - CSS badge-warn para estado cache (amarelo)
  - Campo source em get_freshness_from_sqlite e get_freshness_info
  - FRESH_THRESHOLD_HOURS=48 como constante em data_loader.py

affects:
  - qualquer fase que use o badge de frescura
  - phase 10-01 (complementa o campo source que esta fase tambem adiciona)

tech-stack:
  added: []
  patterns:
    - Badge ternario Jinja2 via freshness.source (fresh/cache/none)
    - Badge dentro do HTMX swap zone para actualizacao automatica ao mudar de local
    - FRESH_THRESHOLD_HOURS como constante modulo-level em data_loader.py

key-files:
  created: []
  modified:
    - src/web/templates/partials/frescura_badge.html
    - src/web/templates/partials/dashboard_content.html
    - src/web/templates/dashboard.html
    - src/web/static/style.css
    - src/web/services/data_loader.py
    - tests/test_web_dashboard.py

key-decisions:
  - "badge-warn usa mesmas cores que badge-stale (amarelo #fff3cd) — distincao semantica, nao visual. Diferenciacao visual pode ser feita no futuro editando badge-warn"
  - "source field adicionado em get_freshness_info (CSV fallback) e get_freshness_from_sqlite (SQLite) na mesma fase para garantir compatibilidade total do template"
  - "FRESH_THRESHOLD_HOURS=48 como constante modulo-level — partilhada entre as duas funcoes de frescura"

patterns-established:
  - "Badge de frescura: sempre dentro do HTMX swap zone (dashboard_content.html), nunca no header fixo"
  - "Freshness dict: sempre inclui campo source (fresh/cache/none) para logica ternaria no template"

requirements-completed:
  - COMP-04

duration: 12min
completed: 2026-03-31
---

# Phase 10 Plan 02: Badge Ternario de Frescura Summary

**Badge de frescura ternario (fresh verde / cache amarelo / sem dados amarelo) relocado para dentro do HTMX swap zone, actualizando automaticamente ao mudar de local no selector**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-31T00:00:00Z
- **Completed:** 2026-03-31T00:12:00Z
- **Tasks:** 1 (TDD: test + feat)
- **Files modified:** 6

## Accomplishments

- frescura_badge.html reescrito com logica ternaria: source=fresh → badge-ok verde, source=cache → badge-warn amarelo, source=none → badge-stale "Sem dados de comparacao"
- Badge relocado de dashboard.html (header, fora do HTMX swap zone) para dashboard_content.html (primeiro elemento, dentro do swap zone) — activa ao mudar de local via selector
- get_freshness_from_sqlite e get_freshness_info actualizado com campo source e constante FRESH_THRESHOLD_HOURS=48
- 5 testes de integracao adicionados para os 3 estados do badge e presenca no fragmento HTMX
- Suite completa: 112 tests passam, 14 skipped

## Task Commits

1. **TDD RED - Failing tests** - `6583b3a` (test)
2. **TDD GREEN - Badge implementation** - `5e354cb` (feat)

## Files Created/Modified

- `src/web/templates/partials/frescura_badge.html` - Reescrito com logica ternaria freshness.source
- `src/web/templates/partials/dashboard_content.html` - Badge adicionado como primeira linha (inclui frescura_badge.html)
- `src/web/templates/dashboard.html` - Badge removido do header (div.form-inline removido)
- `src/web/static/style.css` - Classe badge-warn adicionada (amarelo, identico a badge-stale semanticamente)
- `src/web/services/data_loader.py` - FRESH_THRESHOLD_HOURS=48, source field em get_freshness_info e get_freshness_from_sqlite
- `tests/test_web_dashboard.py` - 5 novos testes para badge ternario

## Decisions Made

- badge-warn e badge-stale usam as mesmas cores (amarelo #fff3cd) — a distincao e semantica: warn indica dados de cache disponiveis, stale indica ausencia total de dados. Diferenciacao visual futura e possivel editando apenas badge-warn em style.css.
- Campo source adicionado em ambas as funcoes (get_freshness_info para CSV fallback e get_freshness_from_sqlite para SQLite) na mesma fase para garantir que o template funciona em todos os caminhos de dados.
- FRESH_THRESHOLD_HOURS=48 definido como constante a nivel de modulo, partilhada entre as duas funcoes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Campo source adicionado a get_freshness_info (CSV fallback) alem de get_freshness_from_sqlite**

- **Found during:** Task 1 (implementacao do badge)
- **Issue:** O plan especificava adicionar source a get_freshness_info como passo 6, mas sem isso o template frescura_badge.html quebra em locais com pipeline CSV (source seria undefined no Jinja2)
- **Fix:** Adicionado campo source e constante FRESH_THRESHOLD_HOURS em ambas as funcoes em simultaneo — comportamento consistente em todos os caminhos
- **Files modified:** src/web/services/data_loader.py
- **Verification:** 112 testes passam incluindo testes com locais CSV e SQLite
- **Committed in:** 5e354cb (task feat commit)

**2. [Rule 3 - Blocking] Campo source adicionado na propria fase 10-02 (dependencia de 10-01)**

- **Found during:** Task 1 — 10-01 nao tinha sido executado no worktree
- **Issue:** depends_on: ["10-01"] mas 10-01 ainda nao tinha produzido o campo source em get_freshness_from_sqlite
- **Fix:** Implementado o campo source nesta fase (o que a tarefa 10-02 Action Step 6 ja previa como passo de compatibilidade). Quando 10-01 for executado, a adicao sera idempotente (mesma constante FRESH_THRESHOLD_HOURS e mesma logica).
- **Files modified:** src/web/services/data_loader.py
- **Verification:** Todos os testes passam
- **Committed in:** 5e354cb

---

**Total deviations:** 2 auto-fixed (ambos Rule 3 - blocking)
**Impact on plan:** Ambas as correcoes necessarias para completar a tarefa. Sem scope creep — o plano ja antecipava o step 6 de compatibilidade.

## Issues Encountered

Nenhum problema adicional alem dos desvios documentados acima.

## Known Stubs

Nenhum — todos os 3 estados do badge estao completamente implementados e wired ao freshness dict.

## Next Phase Readiness

- Badge ternario funcional em producao para os 3 estados (fresh/cache/none)
- Badge actualiza automaticamente ao mudar de local via HTMX selector
- Phase 10-01 (upsert cached_at + source em SQLite) pode ser executada de forma independente — data_loader.py ja tem a constante e a logica source

## Self-Check: PASSED

- FOUND: src/web/templates/partials/frescura_badge.html
- FOUND: src/web/templates/partials/dashboard_content.html
- FOUND: src/web/templates/dashboard.html
- FOUND: src/web/static/style.css
- FOUND: src/web/services/data_loader.py
- FOUND: tests/test_web_dashboard.py
- FOUND: .planning/phases/10-cache-tiagofelicia-pt-integra-o-compara-o/10-02-SUMMARY.md
- COMMIT 6583b3a: test(10-02) — FOUND
- COMMIT 5e354cb: feat(10-02) — FOUND
- pytest: 112 passed, 14 skipped

---
*Phase: 10-cache-tiagofelicia-pt-integra-o-compara-o*
*Completed: 2026-03-31*
