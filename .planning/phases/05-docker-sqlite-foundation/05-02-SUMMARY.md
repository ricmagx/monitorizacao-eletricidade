---
phase: 05-docker-sqlite-foundation
plan: "02"
subsystem: db
tags: [sqlite, sqlalchemy, alembic, schema, migrations, wal]
dependency_graph:
  requires: []
  provides: [db-layer, schema, alembic-migrations]
  affects: [05-03-fastapi-docker]
tech_stack:
  added: [alembic==1.12.1]
  patterns: [SQLAlchemy Core, Alembic migrations, WAL mode, upsert on_conflict_do_update]
key_files:
  created:
    - src/db/__init__.py
    - src/db/engine.py
    - src/db/schema.py
    - src/db/migrations/__init__.py
    - src/db/migrations/env.py
    - src/db/migrations/script.py.mako
    - src/db/migrations/versions/__init__.py
    - src/db/migrations/versions/001_initial_schema.py
    - alembic.ini
    - tests/test_db_schema.py
    - tests/test_db_migrations.py
  modified: []
decisions:
  - "SQLAlchemy Core (not ORM) para manter queries explícitas e compatibilidade com o padrão do projecto"
  - "WAL mode activado via event listener em cada conexão para garantir consistência independentemente do caller"
  - "UNIQUE constraint nomeada (uq_consumo_loc_month, uq_custos_loc_month) para Alembic downgrade correcto"
  - "DB_PATH configurável via env var para suporte Docker com bind mount"
metrics:
  duration_seconds: 144
  completed_date: "2026-03-30"
  tasks_completed: 2
  files_created: 11
---

# Phase 05 Plan 02: SQLite Schema + Alembic Migrations Summary

SQLAlchemy Core schema com 3 tabelas, WAL mode via event listener, UNIQUE constraints, e Alembic 001 migration que cria tudo do zero.

## What Was Built

SQLite database layer completa para o sistema de monitorização de electricidade v2.0:

- **Engine SQLAlchemy** com WAL mode (PRAGMA journal_mode=WAL) e foreign_keys=ON activados via event listener em cada conexão. DB_PATH configurável via variável de ambiente para suporte Docker.
- **3 tabelas definidas** via SQLAlchemy Core:
  - `consumo_mensal`: histórico de consumo E-REDES por local e mês, com UNIQUE constraint em (location_id, year_month) e suporte a upsert
  - `comparacoes`: cache de resultados tiagofelicia.pt com campo cached_at para gestão de TTL
  - `custos_reais`: custos reais de faturas por local/mês, com UNIQUE constraint para idempotência
- **Alembic migrations**: ficheiro `001_initial_schema.py` cria as 3 tabelas a partir de uma DB vazia; idempotente (upgrade head duas vezes sem erros)
- **10 testes**: 8 em test_db_schema.py (colunas, constraints, upsert, WAL, foreign_keys) + 2 em test_db_migrations.py (criação de tabelas, idempotência)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 8af0f9a | test | Failing tests for SQLAlchemy schema and WAL engine (RED) |
| ad0665c | feat | SQLAlchemy schema + WAL engine implementation (GREEN) |
| 78b895a | feat | Alembic migrations infrastructure |

## Test Results

```
10 passed in 0.17s
```

All acceptance criteria met:
- src/db/engine.py contains `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`, `check_same_thread`
- src/db/schema.py defines all 3 tables with UniqueConstraints named `uq_consumo_loc_month` and `uq_custos_loc_month`, and `cached_at` in comparacoes
- alembic.ini has `script_location = src/db/migrations`
- migrations/env.py imports metadata from src.db.schema and respects DB_PATH env var
- 001_initial_schema.py has `revision = '001'` and `down_revision = None`

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functionality is wired and operational.

## Self-Check: PASSED

Files exist:
- src/db/__init__.py: FOUND
- src/db/engine.py: FOUND
- src/db/schema.py: FOUND
- src/db/migrations/env.py: FOUND
- src/db/migrations/versions/001_initial_schema.py: FOUND
- alembic.ini: FOUND
- tests/test_db_schema.py: FOUND
- tests/test_db_migrations.py: FOUND

Commits exist: 8af0f9a, ad0665c, 78b895a — all FOUND in git log.
