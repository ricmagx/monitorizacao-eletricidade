---
phase: 10-cache-tiagofelicia-pt-integra-o-compara-o
plan: 01
subsystem: database
tags: [sqlalchemy, sqlite, upsert, freshness, tiagofelicia]

# Dependency graph
requires:
  - phase: 09-dashboard-ui
    provides: get_freshness_from_sqlite e tabela comparacoes com cached_at
provides:
  - on_conflict_do_update em upload.py — cached_at actualiza em cada consulta bem-sucedida
  - campo source em get_freshness_from_sqlite — distingue "fresh" (< 48h), "cache" (>= 48h), "none" (sem dados)
  - FRESH_THRESHOLD_HOURS = 48 como constante de controlo
affects: [10-02-badge-frescura, dashboard-freshness-badge]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "on_conflict_do_update com excluded — upsert SQLite que actualiza cached_at em cada insert conflituante"
    - "source ternario fresh/cache/none — baseado em horas desde cached_at vs FRESH_THRESHOLD_HOURS"

key-files:
  created:
    - tests/test_web_data_loader.py (4 novos testes adicionados)
  modified:
    - src/web/routes/upload.py
    - src/web/services/data_loader.py
    - tests/test_web_data_loader.py

key-decisions:
  - "on_conflict_do_update substitui on_conflict_do_nothing — cached_at deve ser renovado em cada consulta bem-sucedida para reflectir frescura real"
  - "FRESH_THRESHOLD_HOURS = 48 — threshold em horas (nao dias) para precisao no badge ternario"
  - "source none retornado quando max_cached_at is None ou exception — fallback seguro para ausencia total de dados"

patterns-established:
  - "Freshness source: fresh=<48h, cache=>=48h, none=sem dados — contrato para badge Plan 02"
  - "hours_ago = total_seconds()/3600 para calculo preciso de threshold em horas"

requirements-completed: [COMP-03]

# Metrics
duration: 8min
completed: 2026-03-31
---

# Phase 10 Plan 01: Upsert + Freshness Source Field Summary

**Upsert comparacoes com on_conflict_do_update (cached_at sempre renovado) e campo source ternario fresh/cache/none em get_freshness_from_sqlite com FRESH_THRESHOLD_HOURS=48**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-31T01:59:32Z
- **Completed:** 2026-03-31T02:07:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments

- `upload.py` actualiza `cached_at` em cada consulta bem-sucedida a tiagofelicia.pt via `on_conflict_do_update`
- `get_freshness_from_sqlite` retorna campo `source` com valores "fresh" (< 48h), "cache" (>= 48h), "none" (sem dados)
- 4 novos testes passam; suite completa verde (111 passed, 14 skipped)

## Task Commits

1. **Task 1: Upsert on_conflict_do_update + freshness source field** - `81b6e3e` (feat)

## Files Created/Modified

- `src/web/routes/upload.py` - on_conflict_do_update com set_ para top_3_json, current_supplier_result_json, generated_at, cached_at
- `src/web/services/data_loader.py` - FRESH_THRESHOLD_HOURS=48, campo source no dict de retorno, hours_ago para calculo preciso
- `tests/test_web_data_loader.py` - 4 novos testes: test_freshness_source_fresh, test_freshness_source_cache, test_freshness_source_none, test_freshness_source_stale_is_cache

## Decisions Made

- `on_conflict_do_update` com `excluded` (valores do INSERT conflituante) — padrao SQLAlchemy SQLite para renovar todos os campos em conflito
- Threshold em horas (`FRESH_THRESHOLD_HOURS = 48`) em vez de dias — necessario para badge ternario ter granularidade suficiente
- Calculo via `total_seconds() / 3600` em vez de `.days` — `.days` trunca para dias inteiros, perderia precisao sub-dia

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `source` field disponivel no dict de `get_freshness_from_sqlite` — base para o badge ternario da Phase 10 Plan 02
- `cached_at` actualiza em cada consulta tiagofelicia.pt — badge mostrara dados como "fresh" imediatamente apos upload bem-sucedido
- Sem bloqueadores para Plan 02

---
*Phase: 10-cache-tiagofelicia-pt-integra-o-compara-o*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FOUND: src/web/routes/upload.py
- FOUND: src/web/services/data_loader.py
- FOUND: tests/test_web_data_loader.py
- FOUND: SUMMARY.md
- FOUND: commit 81b6e3e
- PASS: on_conflict_do_update found in upload.py
- PASS: on_conflict_do_nothing removed from upload.py
- PASS: FRESH_THRESHOLD_HOURS in data_loader.py
- PASS: source field in return dict
- PASS: source none fallback returns
- PASS: test_freshness_source_fresh defined
