---
phase: 05-docker-sqlite-foundation
plan: 03
subsystem: infra
tags: [fastapi, sqlalchemy, alembic, sqlite, docker, health-endpoint]

# Dependency graph
requires:
  - phase: 05-docker-sqlite-foundation
    provides: Dockerfile, docker-compose.yml, entrypoint.sh, SQLAlchemy schema, Alembic migrations
provides:
  - FastAPI app wired to SQLite engine via lifespan context manager
  - /health endpoint with DB connectivity check
  - Docker-compatible PROJECT_ROOT via APP_ROOT env var
  - Alembic env.py with sys.path fix for Docker
  - Full end-to-end smoke test verified on Unraid (192.168.122.110)
affects: [phase-6-ui-design, phase-7-upload-xlsx, phase-9-dashboard-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lifespan context manager for DB init (FastAPI + SQLAlchemy)"
    - "APP_ROOT env var for Docker-compatible path resolution"
    - "Health endpoint pattern: /health returns {status, db} with 503 on failure"

key-files:
  created: []
  modified:
    - src/web/app.py
    - src/db/migrations/env.py

key-decisions:
  - "metadata.create_all() in lifespan as safety net for local dev — Alembic is the primary path in Docker"
  - "APP_ROOT env var defaults to computed path — backward compatible, Docker can override"
  - "env.py sys.path fix committed as separate hotfix (b783b3f) after smoke test revealed import failure in Docker"

patterns-established:
  - "Health endpoint: always check DB with SELECT 1, return 503 on failure"
  - "Lifespan manager: import engine + metadata, create_all as dev safety net"
  - "Docker path resolution: use os.environ.get('APP_ROOT', fallback) — never hardcode"

requirements-completed: [INFRA-01, INFRA-03, DADOS-01, DADOS-02, DADOS-03, DADOS-04]

# Metrics
duration: ~45min (split across two sessions with human smoke test on Unraid)
completed: 2026-03-30
---

# Phase 5 Plan 03: FastAPI+DB Integration + Docker Smoke Test Summary

**FastAPI app wired to SQLite engine via lifespan, /health endpoint verified on Unraid, full Docker stack smoke-tested with persistence and all 10 tests passing**

## Performance

- **Duration:** ~45 min (Task 1 in first session, Task 2/smoke test on Unraid by user)
- **Started:** 2026-03-30 (continuation from plans 05-01 and 05-02)
- **Completed:** 2026-03-30T12:23:17Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- Wired SQLite engine into FastAPI app using lifespan context manager — DB tables created on startup as dev safety net
- Added `/health` endpoint returning `{"status":"ok","db":"connected"}` with DB connectivity check and 503 on failure
- Fixed `PROJECT_ROOT` path computation to be Docker-compatible via `APP_ROOT` env var
- Alembic `env.py` patched with `sys.path` fix so migrations find project modules inside the container
- Full smoke test on Unraid verified: health endpoint, dashboard HTTP 200, data insert, persistence after restart, no macOS refs, 10/10 tests passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire DB into FastAPI app + add /health endpoint** - `03664d1` (feat)
2. **Task 2: Docker smoke test** - `b783b3f` (fix — env.py sys.path, committed as hotfix during smoke test on Unraid)

**Plan metadata:** (this SUMMARY)

## Files Created/Modified

- `src/web/app.py` — Added lifespan, engine import, /health endpoint, APP_ROOT env var
- `src/db/migrations/env.py` — Added sys.path.insert(0, ...) fix for Docker import resolution

## Decisions Made

- Used `metadata.create_all(engine)` in lifespan as a dev convenience — Docker always uses Alembic via entrypoint.sh, so this is a non-interfering safety net
- `APP_ROOT` env var allows Docker to set `/app` without breaking local dev (defaults to computed path)
- Smoke test run on Unraid (192.168.122.110) instead of locally — Docker not available on dev Mac, Unraid is the target deployment environment anyway

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Alembic env.py missing sys.path for Docker**
- **Found during:** Task 2 (Docker smoke test on Unraid)
- **Issue:** `alembic upgrade head` failed inside container because `src/` was not on Python path, causing `ModuleNotFoundError` when importing project modules in `env.py`
- **Fix:** Added `sys.path.insert(0, str(Path(__file__).resolve().parents[3]))` at the top of `src/db/migrations/env.py`
- **Files modified:** `src/db/migrations/env.py`
- **Verification:** Alembic migrations ran successfully inside Docker container, all 3 tables created
- **Committed in:** `b783b3f` (separate hotfix commit during smoke test)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Critical fix — without it migrations would fail on every container start. No scope creep.

## Issues Encountered

- Docker not available on dev Mac — smoke test delegated to Unraid (192.168.122.110). This is by design for this project (Unraid is the deployment target). No local Docker testing capability needed going forward.

## User Setup Required

None - no external service configuration required. Unraid deployment was already configured in previous plans.

## Next Phase Readiness

- Phase 5 is COMPLETE — all 6 requirements (INFRA-01, INFRA-03, DADOS-01-04) verified
- Phase 6 (UI Design) can start — produces UI-SPEC.md, no code dependency on Phase 5 beyond it being done
- Phase 7 (Upload XLSX) depends on Phase 6 UI-SPEC — do not start before Phase 6 is approved
- Container is running on Unraid at 192.168.122.110:8000 with empty DB, ready to receive data

---
*Phase: 05-docker-sqlite-foundation*
*Completed: 2026-03-30*
