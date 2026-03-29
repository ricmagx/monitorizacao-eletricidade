---
phase: "03"
plan: "02"
subsystem: backend
tags: [multi-location, workflow, cpe-routing, eredes]
dependency_graph:
  requires: [03-01]
  provides: [multi-location-workflow, cpe-routing-integration, eredes-cpe-hint]
  affects: [monthly_workflow, process_latest_download, eredes_download]
tech_stack:
  added: []
  patterns: [location-dict-as-unit-of-composition, cpe-filename-routing, per-location-tracker]
key_files:
  created:
    - tests/test_multi_workflow.py
  modified:
    - src/backend/monthly_workflow.py
    - src/backend/process_latest_download.py
    - src/backend/eredes_download.py
    - tests/test_tiagofelicia_fallback.py
    - tests/test_supplier_missing.py
decisions:
  - "location dict passed as explicit parameter to run_workflow — avoids config root access for contract/pipeline data"
  - "process_latest_download routing is fully automatic by CPE in filename — no --location flag needed"
  - "eredes_download.py cpe_hint is optional — callers that don't pass it get identical behaviour"
  - "_make_location_from_test_config helper wraps legacy test_config into location dict with raw_dir from eredes.download_dir"
metrics:
  duration: "6m"
  completed_date: "2026-03-30"
  tasks_completed: 2
  files_modified: 5
  files_created: 1
---

# Phase 03 Plan 02: Multi-location Workflow Refactor Summary

Multi-location pipeline: monthly_workflow accepts location dict with --location CLI filter and sequential loop, process_latest_download routes XLSX to correct location by CPE in filename, eredes_download shows CPE hint before opening browser.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Refactor monthly_workflow.py for multi-location + tests | 59fef7f | src/backend/monthly_workflow.py, tests/test_multi_workflow.py, tests/test_tiagofelicia_fallback.py, tests/test_supplier_missing.py |
| 2 | Refactor process_latest_download.py for CPE routing + eredes_download.py CPE hint | 885f6c3 | src/backend/process_latest_download.py, src/backend/eredes_download.py, tests/test_multi_workflow.py, tests/test_tiagofelicia_fallback.py, tests/test_supplier_missing.py |

## What Was Built

### monthly_workflow.py

- `run_workflow` signature changed from `(config_path, input_xlsx)` to `(config: dict, location: dict, project_root: Path, input_xlsx)`
- All path resolution now uses `location["pipeline"]` instead of `config["pipeline"]`
- `render_report` changed from `config` parameter to `location` — reads `location["current_contract"]["supplier"]` and `location["current_contract"]["power_label"]`
- Notification message includes `location["name"]`: `f"[{location['name']}] Relatorio pronto. Melhor ciclo: ..."`
- `main()` adds `--location` flag (optional), iterates `config["locations"]` sequentially, exits 1 for unknown location id
- Results collected as `[{"location": loc["id"], **result}]` and printed as JSON array

### process_latest_download.py

- Imports `extract_cpe_from_filename` and `find_location_by_cpe` from `cpe_routing`
- Extracts CPE from XLSX filename and finds matching location in `config["locations"]`
- Returns `{"status": "skipped", "reason": "unknown_cpe", "cpe": ..., "xlsx_path": ...}` for unrecognised CPE
- Tracker saved to `location["pipeline"]["last_processed_tracker_path"]` (per-location, not global)
- Calls `run_workflow(config=config, location=location, project_root=project_root, input_xlsx=latest)` with new signature
- No `--location` flag — routing is automatic by CPE

### eredes_download.py

- `download_latest_xlsx` gains optional `cpe_hint: str | None = None` parameter
- In `external_firefox` mode, if `cpe_hint` is given, sends `notify_mac("E-REDES", f"CPE: {cpe_hint} -- Seleccione o CPE correcto no portal e descarregue o Excel.")` before opening browser
- Callers that don't pass `cpe_hint` get identical behaviour

## Test Results

- **33/33 tests pass** (10 new tests in test_multi_workflow.py, 23 existing tests updated/maintained)

New tests:
- `test_run_workflow_accepts_location_dict` — run_workflow with new signature returns status "ok"
- `test_run_workflow_reads_contract_from_location` — report contains location's supplier name
- `test_run_workflow_writes_to_location_paths` — CSV and report paths contain "casa"
- `test_main_location_filter` — --location casa calls run_workflow once with location id "casa"
- `test_main_all_locations` — no --location flag processes all locations
- `test_main_unknown_location_exits_1` — --location xyz exits with code 1
- `test_process_routes_xlsx_by_cpe` — XLSX with casa CPE routed to casa
- `test_process_skips_unknown_cpe` — XLSX with unknown CPE returns skipped/unknown_cpe
- `test_process_tracker_per_location` — tracker saved to per-location path
- `test_eredes_cpe_hint_in_notification` — notify_mac called with CPE in message

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_config fixture uses legacy schema without raw_dir**

- **Found during:** Task 2 (GREEN phase run)
- **Issue:** `test_config` fixture (legacy schema) had `pipeline` without `raw_dir` key. After refactor, `run_workflow` reads `location["pipeline"]["raw_dir"]` — existing tests calling via `_make_location_from_test_config` would fail with `KeyError: 'raw_dir'`
- **Fix:** Added `raw_dir` to the pipeline dict in `_make_location_from_test_config` helper, sourced from `config["eredes"]["download_dir"]`
- **Files modified:** `tests/test_tiagofelicia_fallback.py`, `tests/test_supplier_missing.py`
- **Commit:** 885f6c3

**2. [Rule 1 - Bug] eredes_download.py used old config["eredes"]["download_dir"] key**

- **Found during:** Task 2 refactor
- **Issue:** `download_latest_xlsx` used `eredes["download_dir"]` but new multi-location schema uses `eredes["download_dir_base"]`
- **Fix:** Updated to `eredes.get("download_dir_base") or eredes.get("download_dir", "data/raw/eredes")` for backward compatibility
- **Files modified:** `src/backend/eredes_download.py`
- **Commit:** 885f6c3

**3. [Rule 2 - Missing] analysis_json_path.parent.mkdir needed in run_workflow**

- **Found during:** Task 1 GREEN phase (test run)
- **Issue:** `analysis_json_path.write_text(...)` would fail if parent directory didn't exist (can happen in multi-location paths like `data/casa/processed/`)
- **Fix:** Added `analysis_json_path.parent.mkdir(parents=True, exist_ok=True)` before the write
- **Files modified:** `src/backend/monthly_workflow.py`
- **Commit:** 59fef7f

## Known Stubs

None — all data flows are wired. The multi-location config in `config/system.json` uses `PT000200XXXXXXXXXX` as placeholder CPE for `apartamento` (acknowledged in RESEARCH.md as requiring manual confirmation). This is a config value, not a code stub, and it does not prevent any plan goal from being achieved.

## Requirements Satisfied

- MULTI-03: monthly_workflow iterates over locations with --location filter
- MULTI-04: process_latest_download routes XLSX by CPE in filename
- MULTI-06: eredes_download shows CPE hint notification in external_firefox mode

## Self-Check: PASSED

- All 5 key files exist
- Both task commits exist (59fef7f, 885f6c3)
- 33/33 tests pass
