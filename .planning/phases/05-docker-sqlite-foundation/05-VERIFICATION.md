---
phase: 05-docker-sqlite-foundation
verified: 2026-03-30T12:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 5: Docker + SQLite Foundation — Verification Report

**Phase Goal:** Transformar o sistema num servico Docker com SQLite persistente — container arranca, aplica migracoes automaticamente, FastAPI responde em /health, e dados persistem entre restarts.
**Verified:** 2026-03-30
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Container arranca e uvicorn inicia na porta 8000 | VERIFIED | entrypoint.sh calls `exec uvicorn src.web.app:app --host 0.0.0.0 --port 8000`; docker smoke test confirmed on Unraid |
| 2 | Codigo nao contem referencias a osascript, launchd ou open -a Firefox (em ficheiros activos) | VERIFIED | grep on monthly_workflow.py, reminder_job.py, eredes_download.py, process_latest_download.py returns clean; install_launch_agent.py preserved per plan spec but not imported |
| 3 | config/system.json nao contem paths macOS hardcoded | VERIFIED | download_mode=disabled, watcher.enabled=False, watch_paths=[], local_download_watch_dir=/app/data/uploads |
| 4 | Tabela consumo_mensal existe com UNIQUE constraint em (location_id, year_month) | VERIFIED | schema.py defines uq_consumo_loc_month; test_consumo_unique passes |
| 5 | Tabela comparacoes existe com coluna cached_at | VERIFIED | schema.py defines cached_at as DateTime; test_comparacoes_columns passes |
| 6 | Tabela custos_reais existe com UNIQUE constraint em (location_id, year_month) | VERIFIED | schema.py defines uq_custos_loc_month; test_custos_unique passes |
| 7 | Alembic upgrade head cria todas as tabelas a partir de uma DB vazia | VERIFIED | test_upgrade_creates_tables passes; env.py has sys.path fix for Docker |
| 8 | Health endpoint /health responde 200 | VERIFIED | In-process call returns {"status":"ok","db":"connected"}; docker smoke test confirmed |
| 9 | Dados persistem entre restarts (named Docker volume) | VERIFIED | docker-compose.yml mounts energia_data:/app/data; docker smoke test confirmed persistence on Unraid |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Dockerfile` | Container image definition | VERIFIED | FROM python:3.11-slim, HEALTHCHECK present, CMD ./entrypoint.sh |
| `docker-compose.yml` | Service orchestration with named volume | VERIFIED | energia_data:/app/data, DB_PATH=/app/data/energia.db, build: . |
| `entrypoint.sh` | Container startup script | VERIFIED | alembic upgrade head + uvicorn src.web.app:app |
| `requirements-docker.txt` | Docker deps without Playwright | VERIFIED | 10 packages, no playwright, includes sqlalchemy>=2.0.0 and alembic>=1.18.0 |
| `src/db/engine.py` | SQLAlchemy engine with WAL mode | VERIFIED | PRAGMA journal_mode=WAL, PRAGMA foreign_keys=ON, check_same_thread=False |
| `src/db/schema.py` | Table definitions for 3 tables | VERIFIED | consumo_mensal, comparacoes, custos_reais with correct columns and constraints |
| `src/db/migrations/versions/001_initial_schema.py` | Initial Alembic migration | VERIFIED | op.create_table for all 3 tables, revision='001', down_revision=None |
| `src/db/migrations/env.py` | Alembic env with Docker sys.path fix | VERIFIED | sys.path fix present, DB_PATH env override, target_metadata=metadata |
| `alembic.ini` | Alembic config | VERIFIED | script_location=src/db/migrations |
| `src/web/app.py` | FastAPI app with lifespan and /health | VERIFIED | lifespan defined, metadata.create_all(engine), @app.get("/health"), app.state.db_engine |
| `tests/test_db_schema.py` | 8 unit tests for schema | VERIFIED | 8 tests: columns, unique, upsert, WAL, foreign_keys — all pass |
| `tests/test_db_migrations.py` | Migration tests | VERIFIED | test_upgrade_creates_tables, test_upgrade_idempotent — both pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `docker-compose.yml` | `Dockerfile` | build context | WIRED | `build: .` present on line 3 |
| `entrypoint.sh` | `src/web/app.py` | uvicorn command | WIRED | `exec uvicorn src.web.app:app` on line 5 |
| `entrypoint.sh` | `alembic.ini` | alembic upgrade head | WIRED | `alembic upgrade head` on line 4 |
| `docker-compose.yml` | named volume | energia_data:/app/data | WIRED | Volume mount confirmed |
| `src/db/migrations/env.py` | `src/db/schema.py` | target_metadata | WIRED | `from src.db.schema import metadata` on line 13 |
| `alembic.ini` | `src/db/migrations/` | script_location | WIRED | `script_location = src/db/migrations` on line 2 |
| `src/web/app.py` | `src/db/engine.py` | lifespan import | WIRED | `from src.db.engine import engine` on line 15 |
| `src/web/app.py` | `src/db/schema.py` | metadata.create_all | WIRED | `from src.db.schema import metadata` on line 16; `metadata.create_all(engine)` in lifespan |

**Note on Plan 02 key_link deviation:** Plan 02 specified `engine.py` should import `metadata` from `schema.py`. The implementation correctly does NOT do this — engine.py has no dependency on schema (separation of concerns). Instead, `app.py` imports both independently and wires them in `lifespan`. This is architecturally correct and not a gap.

### Data-Flow Trace (Level 4)

The Phase 5 goal is infrastructure (Docker + DB layer), not data rendering. The `/health` endpoint queries the DB and returns real connectivity status — verified in-process. The dashboard route exists but data-flow for dashboard rendering belongs to subsequent phases. Level 4 trace is N/A for this infrastructure phase.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| App module importable | `python3 -c "from src.web.app import app"` | APP_IMPORTABLE: OK | PASS |
| /health returns {"status":"ok","db":"connected"} | In-process call to `health()` | status=ok, db=connected | PASS |
| Schema exports all 3 tables | `from src.db.schema import metadata, consumo_mensal, comparacoes, custos_reais` | SCHEMA_EXPORTS: OK | PASS |
| Engine importable | `from src.db.engine import get_engine, engine` | ENGINE_IMPORTABLE: OK | PASS |
| 10/10 unit tests pass | `pytest tests/test_db_schema.py tests/test_db_migrations.py -v` | 10 passed in 0.23s | PASS |
| Docker smoke test on Unraid | `curl http://192.168.122.110:8000/health` | All 6 success criteria verified by human | PASS (human-verified) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INFRA-01 | 05-01, 05-03 | Sistema corre como container Docker no Unraid | SATISFIED | Dockerfile, docker-compose.yml, entrypoint.sh exist and work; human smoke test on Unraid confirmed |
| INFRA-03 | 05-03 | Dados persistem em volume Docker (SQLite) | SATISFIED | Named volume energia_data:/app/data; persistence verified in Docker smoke test |
| DADOS-01 | 05-02 | Historico de consumo mensal por local em SQLite (vazio/fora_vazio kWh) | SATISFIED | consumo_mensal table with vazio_kwh, fora_vazio_kwh, UNIQUE constraint; 3 tests pass |
| DADOS-02 | 05-02 | Historico de comparacoes tiagofelicia.pt em SQLite (por mes, por local) | SATISFIED | comparacoes table with location_id, year_month, top_3_json; test_comparacoes_columns passes |
| DADOS-03 | 05-02 | Custos reais de faturas em SQLite (por mes, por local) | SATISFIED | custos_reais table with custo_eur, source, UNIQUE constraint; test_custos_unique passes |
| DADOS-04 | 05-02 | Cache de resultados tiagofelicia.pt com timestamp | SATISFIED | comparacoes.cached_at (DateTime, default=utcnow); test_comparacoes_columns asserts cached_at |

All 6 requirements satisfied. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/backend/install_launch_agent.py` | 4, 8, 12, 37, 38 | launchd references | INFO | Not imported in Docker code path; plan explicitly preserved this file for archival |
| `src/backend/install_process_watch_agent.py` | 4, 8, 12, 37, 38 | launchd references | INFO | Not imported in Docker code path; plan explicitly preserved this file for archival |
| `src/backend/reminder_job.py` | 26, 31 | TODO Phase 7 comments | INFO | Expected stubs — plan specified logger.info replacement with Phase 7 TODO markers |
| `src/backend/monthly_workflow.py` | 173 | TODO Phase 7 comment | INFO | Expected stub — osascript replaced with logger.info per plan spec |
| `src/backend/eredes_download.py` | 49, 109 | TODO Phase 7 comments | INFO | Expected stubs — plan specified these as deferred to Phase 7 |

All anti-patterns are INFO severity. The `install_*.py` files are preserved as per plan spec (plan task 6 explicitly says "Do NOT delete... they can be archived in a later phase") and are not imported anywhere in the Docker execution path. The TODO Phase 7 stubs are intentional per the cleanup strategy. No blockers.

### Human Verification Required

The Docker smoke test was performed by the user on Unraid (192.168.122.110:8000). The following items were verified by human:

1. **Container builds and starts** — `docker compose up --build -d` completed without errors
2. **Health endpoint** — `curl http://192.168.122.110:8000/health` returned `{"status":"ok","db":"connected"}`
3. **Dashboard loads** — HTTP 200 on root path
4. **Data persistence** — Record written before `docker compose down` existed after `docker compose up`
5. **No macOS references** — grep confirmed clean
6. **Test suite inside container** — `pytest tests/ -x` passed (10/10)

All 6 success criteria from Plan 03 checkpoint task were confirmed by human.

### Gaps Summary

No gaps found. All must-haves verified at all levels:
- All 12 artifacts exist, are substantive, and are wired
- All 8 key links are present and connected
- 10/10 unit tests pass locally
- Health endpoint returns correct JSON in-process
- All 6 requirements (INFRA-01, INFRA-03, DADOS-01, DADOS-02, DADOS-03, DADOS-04) are satisfied
- Docker smoke test on Unraid confirmed by human

The phase goal is fully achieved: the system runs as a Docker container on Unraid, SQLite tables are created via Alembic on startup, FastAPI responds on /health with DB connectivity confirmed, and data persists across restarts via named volume.

---

_Verified: 2026-03-30T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
