---
phase: 03-multi-location-refactor
plan: "03"
subsystem: notifications
tags: [launchd, reminder, notifications, per-location, tdd]

# Dependency graph
requires:
  - phase: 03-01
    provides: multi-location config schema with locations array
  - phase: 03-02
    provides: monthly_workflow and process_latest_download refactored for multi-location
provides:
  - reminder_job.py iterates over config["locations"] sending per-location notifications
  - notification title includes location name (e.g. "Eletricidade -- Casa")
  - status written to per-location paths (state/{location_id}/monthly_status.json)
  - launchd plists verified pointing to config/system.json (no changes needed)
affects: [phase-04-dashboard, launchd-agents]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-location iteration: for loc in config['locations'] pattern now applied to all backend scripts"
    - "run_reminder returns list[dict] (one entry per location) instead of single dict"

key-files:
  created:
    - tests/test_multi_reminder.py
  modified:
    - src/backend/reminder_job.py
    - tests/conftest.py

key-decisions:
  - "Launchd plists require no content changes — reminder_job now handles multi-location internally via config['locations'] iteration"
  - "multi_location_config fixture extended with download_url and browser_app in eredes section (Rule 3 fix)"
  - "run_reminder return type changed from dict to list[dict] — launchd does not parse return value so safe"

patterns-established:
  - "All backend scripts iterate config['locations'] internally — launchd passes single --config flag"

requirements-completed: [MULTI-05]

# Metrics
duration: 9min
completed: "2026-03-29"
---

# Phase 03 Plan 03: Reminder Job Multi-Location Summary

**reminder_job.py refactored to iterate config["locations"], sending one macOS notification per location with location name in title, and writing status to per-location state paths**

## Performance

- **Duration:** ~9 min (TDD task pre-executed in prior agent, checkpoint approved, continuation completes plan)
- **Started:** 2026-03-30T00:07:00Z
- **Completed:** 2026-03-29T23:17:27Z
- **Tasks:** 2 (Task 1 TDD + Task 2 launchd verification)
- **Files modified:** 3

## Accomplishments

- reminder_job.py refactored: `for loc in config["locations"]` loop sends one `notify_mac("Eletricidade -- {name}", ...)` per location
- Status files written to per-location paths: `state/{location_id}/monthly_status.json`
- 5 new tests in `test_multi_reminder.py` covering notification count, status paths, browser calls, message content, and return type
- Launchd plists verified: both point to correct `config/system.json`; no plist content changes needed since scripts handle multi-location internally
- Both launchd agents confirmed registered: `com.ricmag.monitorizacao-eletricidade` (exit 0) and `com.ricmag.monitorizacao-eletricidade.process-latest` (exit 0)

## Task Commits

1. **Task 1 (RED): tests for per-location reminder** - `eb1e1a9` (test)
2. **Task 1 (GREEN): refactor reminder_job.py** - `f60b656` (feat)
3. **Task 2: launchd verification** - approved at checkpoint, no new commits needed

## Files Created/Modified

- `src/backend/reminder_job.py` - Refactored to iterate config["locations"]; per-location notify_mac, status write, open_browser; returns list[dict]
- `tests/test_multi_reminder.py` - 5 tests for per-location reminder behavior (TDD RED)
- `tests/conftest.py` - Added `download_url` and `browser_app` to multi_location_config fixture

## Decisions Made

- Launchd plists do not need changes: the existing `--config config/system.json` argument is sufficient because `reminder_job.py` now reads `config["locations"]` internally and handles all locations in one invocation
- Return type of `run_reminder` changed from `dict` to `list[dict]` — launchd does not parse the return value, so this is a safe breaking change for the API
- `multi_location_config` fixture extended with `eredes` section (`download_url` + `browser_app`) since `reminder_job.py` now reads `config["eredes"]`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extended multi_location_config fixture with eredes section**
- **Found during:** Task 1 (GREEN - refactoring reminder_job.py)
- **Issue:** The refactored `run_reminder` reads `config["eredes"]["browser_app"]` and `config["eredes"]["download_url"]`, but the existing `multi_location_config` fixture in conftest.py lacked those keys — tests would fail with KeyError
- **Fix:** Added `"eredes": {"browser_app": "Firefox", "download_url": "https://balcaodigital.e-redes.pt/consumptions/history"}` to the fixture
- **Files modified:** tests/conftest.py
- **Verification:** All 38 tests pass
- **Committed in:** f60b656 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix essential for tests to run. No scope creep.

## Issues Encountered

- Continuation agent worktree (`agent-ae04ec83`) was initialized before Task 1 commits were made in the prior worktree (`agent-a15e2526`). Resolved by fast-forward merging `worktree-agent-a15e2526` into this worktree before proceeding with Task 2.

## User Setup Required

None — launchd agents already registered. No manual configuration required.

## Next Phase Readiness

- Phase 03 complete: all three plans executed (03-01 config schema, 03-02 workflow refactor, 03-03 reminder refactor)
- Phase 04 (Web Dashboard MVP) can begin: all backend scripts now handle multi-location; state directories at `state/{location_id}/` are created on first run
- Note: CPE for `apartamento` is still a placeholder (`PT000200XXXXXXXXXX`) — must be confirmed in E-REDES portal before Phase 04 tests with real data

---
*Phase: 03-multi-location-refactor*
*Completed: 2026-03-29*
