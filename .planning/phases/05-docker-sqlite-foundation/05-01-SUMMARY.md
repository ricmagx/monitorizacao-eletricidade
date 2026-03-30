---
phase: 05-docker-sqlite-foundation
plan: 01
subsystem: infra
tags: [docker, dockerfile, docker-compose, python, uvicorn, alembic, sqlalchemy, fastapi]

# Dependency graph
requires: []
provides:
  - Dockerfile with python:3.11-slim, HEALTHCHECK, and entrypoint
  - docker-compose.yml with energia_data named volume and DB_PATH env
  - entrypoint.sh running alembic upgrade head then uvicorn
  - requirements-docker.txt without playwright (~500MB saved)
  - config/system.json updated with Docker-safe paths and disabled macOS features
  - All macOS-specific code (osascript, open -a Firefox) replaced with logging stubs
affects:
  - 05-02 (SQLite schema — depends on alembic in entrypoint)
  - 05-03 (Docker build test — builds the Dockerfile created here)
  - 07 (Phase 7 — TODO markers left for web notification replacement)

# Tech tracking
tech-stack:
  added: [sqlalchemy>=2.0.0, alembic>=1.18.0, python-dotenv>=1.0.0, pytest>=7.0.0]
  patterns:
    - "Docker entrypoint: alembic upgrade head before uvicorn start"
    - "requirements-docker.txt excludes playwright to keep image lean"
    - "macOS notifications stubbed as logger.info with TODO Phase 7 markers"

key-files:
  created:
    - Dockerfile
    - docker-compose.yml
    - entrypoint.sh
    - requirements-docker.txt
    - .env.example
  modified:
    - .gitignore
    - src/backend/monthly_workflow.py
    - src/backend/reminder_job.py
    - src/backend/eredes_download.py
    - src/backend/process_latest_download.py
    - config/system.json

key-decisions:
  - "requirements-docker.txt excludes playwright and tf-playwright-stealth — saves ~500MB, E-REDES download is now upload-based"
  - "osascript replaced with logger.info stubs marked TODO Phase 7 — preserves backend files for reuse"
  - "config/system.json: download_mode=disabled, watcher.enabled=false — Docker has no local filesystem watcher"
  - "process_latest_download.py: UPLOAD_DIR env var as fallback instead of Path.home()/Downloads"

patterns-established:
  - "Pattern: macOS stubs use logger.info + TODO Phase 7 marker for traceability"
  - "Pattern: entrypoint.sh runs migrations before app start (alembic upgrade head)"

requirements-completed: [INFRA-01]

# Metrics
duration: 4min
completed: 2026-03-30
---

# Phase 05 Plan 01: Docker Infrastructure and macOS Cleanup Summary

**Dockerfile, docker-compose.yml with energia_data volume, and entrypoint with alembic migrations — all macOS references (osascript, open -a Firefox, /Users/ricmag) removed from src/ and config/**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-30T11:25:50Z
- **Completed:** 2026-03-30T11:29:10Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Docker infrastructure (Dockerfile, docker-compose.yml, entrypoint.sh, requirements-docker.txt, .env.example) created and verified
- All macOS-specific code removed from src/backend (osascript, open -a Firefox) — replaced with logging stubs marked for Phase 7
- config/system.json updated: download_mode=disabled, watcher.enabled=false, all /Users/ricmag paths replaced with /app/data/uploads
- process_latest_download.py now uses UPLOAD_DIR env var instead of Path.home()/Downloads
- .gitignore extended with .env, data/*.db and WAL entries

## Task Commits

1. **Task 1: Create Docker infrastructure files** - `7a58500` (feat)
2. **Task 2: Remove macOS-specific code and paths** - `dcdc3d6` (feat)

## Files Created/Modified
- `Dockerfile` - python:3.11-slim base, HEALTHCHECK, CMD entrypoint
- `docker-compose.yml` - energia service with energia_data named volume
- `entrypoint.sh` - alembic upgrade head + uvicorn src.web.app:app
- `requirements-docker.txt` - all deps except playwright/tf-playwright-stealth
- `.env.example` - DB_PATH and APP_PORT defaults
- `.gitignore` - added .env, data/*.db, WAL/SHM entries
- `src/backend/monthly_workflow.py` - replaced osascript notify_mac with logger.info
- `src/backend/reminder_job.py` - replaced osascript + open_browser with logger stubs
- `src/backend/eredes_download.py` - replaced osascript + open -a Firefox, /Downloads default
- `src/backend/process_latest_download.py` - replaced Path.home()/Downloads with UPLOAD_DIR env
- `config/system.json` - download_mode=disabled, browser_app=none, /app/data/uploads, watcher disabled

## Decisions Made
- Playwright excluded from requirements-docker.txt: E-REDES download is now upload-based (Phase 5+), saving ~500MB
- install_launch_agent.py and install_process_watch_agent.py preserved (not deleted) — contain launchd references but are not imported anywhere in Docker-running code; archived for future reference per plan
- os.environ UPLOAD_DIR pattern used for process_latest_download.py to avoid hardcoded paths

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

The plan's overall verification grep includes `launchd` but explicitly preserves `install_launch_agent.py` and `install_process_watch_agent.py`. These files contain launchd references but are standalone scripts not imported by any Docker-running code. This is intentional per plan section 6 of Task 2 action.

## Issues Encountered
None — all tasks completed on first attempt.

## Known Stubs
- `src/backend/monthly_workflow.py:174` — `logger.info("Notificacao [%s]: %s", ...)` — macOS notification stub, wired to logging only. Phase 7 will replace with web push notification.
- `src/backend/reminder_job.py:27` — same logging stub pattern for reminder notifications
- `src/backend/reminder_job.py:32` — `open_browser` stubbed — no browser in Docker; Phase 7 will provide web-based trigger
- `src/backend/eredes_download.py` — `notify_mac` and `open -a` logging stubs throughout; download_mode=disabled means this code is never reached in Docker

These stubs do NOT prevent the plan's goal (Docker infrastructure creation) from being achieved — they preserve backend logic for future Phase 7 web integration.

## Next Phase Readiness
- Docker infrastructure complete — Plan 05-02 (SQLite schema + Alembic) can proceed
- entrypoint.sh will run alembic upgrade head once migrations are created in Plan 05-02
- No macOS code remains in src/ or config/ — container will start cleanly on Linux

---
*Phase: 05-docker-sqlite-foundation*
*Completed: 2026-03-30*
