---
phase: 07-upload-xlsx-ingest-o-de-dados
plan: 03
subsystem: database
tags: [alembic, sqlite, migrations, batch-mode]

# Dependency graph
requires:
  - phase: 07-upload-xlsx-ingest-o-de-dados
    provides: Migration 002 que adiciona tabela locais e UniqueConstraint em comparacoes
provides:
  - env.py com render_as_batch=True para SQLite batch mode (online e offline)
  - Migration 002 com batch_alter_table para UniqueConstraint em comparacoes
  - alembic upgrade head funciona numa BD SQLite fresca (fresh install, CI/CD, Unraid)
affects: [08-comparacao-tarifarios, docker-deploy, ci-cd]

# Tech tracking
tech-stack:
  added: []
  patterns: [alembic-batch-mode, sqlite-alter-table-workaround]

key-files:
  created: []
  modified:
    - src/db/migrations/env.py
    - src/db/migrations/versions/002_add_locais.py

key-decisions:
  - "render_as_batch=True em AMBAS as funcoes de context.configure() (offline e online) — SQLite requer batch mode para ALTER TABLE operations"
  - "batch_alter_table como context manager para create/drop constraint — tabelas novas (op.create_table) nao precisam de batch"
  - "type_='unique' obrigatorio em batch_op.drop_constraint — batch mode precisa do tipo explicito para identificar a constraint"

patterns-established:
  - "Alembic batch mode: sempre render_as_batch=True em env.py para projectos SQLite"
  - "ALTER TABLE em SQLite: sempre via with op.batch_alter_table('tabela') as batch_op — nunca op directo"

requirements-completed: [COMP-02]

# Metrics
duration: 2min
completed: 2026-03-30
---

# Phase 07 Plan 03: SQLite Alembic Batch Mode Fix Summary

**Alembic env.py com render_as_batch=True e migration 002 com batch_alter_table — corrige NotImplementedError do SQLite em fresh installs e Unraid deploys**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-30T16:06:34Z
- **Completed:** 2026-03-30T16:08:26Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- env.py corrigido com render_as_batch=True em ambas as funcoes de configuracao (offline e online)
- Migration 002 refactorizada: UniqueConstraint em comparacoes via batch_alter_table (SQLite-safe)
- alembic upgrade head completa sem erros numa BD SQLite fresca — desbloqueia Docker fresh install, CI/CD e Unraid
- Suite completa de testes: 79 passed, 13 skipped — zero regressoes

## Task Commits

Cada task foi commitada atomicamente:

1. **Task 1: Adicionar render_as_batch=True ao env.py** - `5e4d482` (fix)
2. **Task 2: Refactorizar migration 002 para usar batch_alter_table** - `39b4722` (fix)

**Plan metadata:** a adicionar (docs commit)

## Files Created/Modified

- `src/db/migrations/env.py` — render_as_batch=True em run_migrations_offline() e run_migrations_online()
- `src/db/migrations/versions/002_add_locais.py` — UniqueConstraint via with op.batch_alter_table('comparacoes') as batch_op

## Decisions Made

- render_as_batch=True deve estar em AMBAS as funcoes de context.configure() — Alembic usa offline mode em alguns contextos CI, online mode em runtime normal
- op.create_table('locais') nao precisa de batch — e uma tabela nova, nao ALTER de existente; batch mode e so necessario para modificar tabelas ja existentes
- type_='unique' e obrigatorio em batch_op.drop_constraint() — sem o tipo, batch mode nao consegue identificar qual constraint remover (SQLite nao tem introspeccao nativa de constraints)

## Deviations from Plan

None - plan executado exactamente como escrito.

## Issues Encountered

None — o fix era cirurgico e preciso. O teste de verificacao (alembic upgrade head num tempfile SQLite) passou na primeira execucao apos as duas correcoes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Alembic upgrade head funciona em qualquer ambiente (fresh install, Unraid, CI/CD)
- COMP-02 fechado — bloqueador de deploy removido
- Phase 07 verification pode agora correr sem falhas relacionadas com migrations
- Pronto para Phase 08 (comparacao de tarifarios)

## Self-Check: PASSED

- FOUND: src/db/migrations/env.py
- FOUND: src/db/migrations/versions/002_add_locais.py
- FOUND: .planning/phases/07-upload-xlsx-ingest-o-de-dados/07-03-SUMMARY.md
- FOUND commit: 5e4d482 (Task 1)
- FOUND commit: 39b4722 (Task 2)

---
*Phase: 07-upload-xlsx-ingest-o-de-dados*
*Completed: 2026-03-30*
