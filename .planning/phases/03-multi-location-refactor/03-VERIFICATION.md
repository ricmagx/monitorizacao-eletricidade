---
phase: 03-multi-location-refactor
verified: 2026-03-29T00:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Reload launchd agents and trigger a smoke test"
    expected: "Both agents registered via launchctl list | grep ricmag, no errors in state/launchd.*.log after a test XLSX drop"
    why_human: "launchctl load requires an interactive shell session; agents show exit code 0 but smoke test with a real XLSX requires the user to place a file"
---

# Phase 03: Multi-Location Refactor — Verification Report

**Phase Goal:** Refactor the backend pipeline to support multiple locations (CPE routing, per-location config, multi-location workflows).
**Verified:** 2026-03-29
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | `config/system.json` has a `locations` array with `casa` entry containing CPE `PT0002000084968079SX` | VERIFIED | `"locations"` key exists, `locations[0]["id"] == "casa"`, `locations[0]["cpe"] == "PT0002000084968079SX"` |
| 2 | `config/system.json` has an `apartamento` entry with placeholder CPE | VERIFIED | `locations[1]["id"] == "apartamento"`, `"cpe": "PT000200XXXXXXXXXX"` |
| 3 | `config/system.json` no longer has top-level `current_contract` or `pipeline` sections | VERIFIED | grep for `config["current_contract"]` and `config["pipeline"]` across all `src/backend/` returns no matches |
| 4 | `monthly_workflow.py --location casa` processes only casa; without `--location` processes all locations sequentially | VERIFIED | `main()` loads `config["locations"]`, filters by `args.location`, loops sequentially; `test_main_location_filter` and `test_main_all_locations` pass |
| 5 | `process_latest_download.py` routes XLSX to correct location by CPE in filename; skips unknown CPE | VERIFIED | Imports `extract_cpe_from_filename` / `find_location_by_cpe` from `cpe_routing`; returns `{"status": "skipped", "reason": "unknown_cpe"}` for unrecognised CPE |
| 6 | `reminder_job.py` sends one notification per location with location name in title; writes status to per-location path | VERIFIED | `for loc in config["locations"]` loop; `f"Eletricidade -- {location_name}"` title; `loc["pipeline"]["status_path"]` used for writes |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|---------|--------|---------|
| `config/system.json` | Multi-location schema with `"locations"` array | VERIFIED | Contains `"locations"`, `"id": "casa"`, `"cpe": "PT0002000084968079SX"`, `"id": "apartamento"`; no top-level `current_contract` or `pipeline` |
| `src/backend/cpe_routing.py` | CPE extraction and location lookup functions | VERIFIED | `extract_cpe_from_filename` and `find_location_by_cpe` present; 44 lines, substantive implementation |
| `tests/conftest.py` | `multi_location_config` fixture + backward-compat `test_config` | VERIFIED | Both fixtures present; `multi_location_config` creates nested dirs and two-location schema |
| `tests/test_multi_location_config.py` | Tests for config loading and directory structure | VERIFIED | 5 test functions; tests against real `config/system.json` and `multi_location_config` fixture |
| `tests/test_cpe_routing.py` | Tests for CPE extraction and location lookup | VERIFIED | 7 test functions including real filename formats, path strings, unknown CPE |
| `src/backend/monthly_workflow.py` | Multi-location workflow with `--location` filter | VERIFIED | Signature `def run_workflow(config: dict, location: dict, project_root: Path, ...)`, `config["locations"]` in `main()`, `--location` CLI arg |
| `src/backend/process_latest_download.py` | CPE-based XLSX routing | VERIFIED | Imports `from cpe_routing import extract_cpe_from_filename, find_location_by_cpe`; routes by CPE; per-location tracker path |
| `src/backend/eredes_download.py` | CPE hint notification in `external_firefox` mode | VERIFIED | `cpe_hint: str | None = None` parameter; `notify_mac("E-REDES", f"CPE: {cpe_hint} -- ...")` before opening browser |
| `src/backend/reminder_job.py` | Per-location reminder notifications and status files | VERIFIED | `for loc in config["locations"]` loop; `f"Eletricidade -- {location_name}"` title; `loc["pipeline"]["status_path"]` |
| `tests/test_multi_workflow.py` | Tests for multi-location workflow and CPE routing integration | VERIFIED | 10 test functions covering workflow, main() filter, CPE routing, tracker, eredes CPE hint |
| `tests/test_multi_reminder.py` | Tests for per-location reminder behavior | VERIFIED | 5 test functions covering notification count, titles, messages, status files, return value |
| `.gitignore` | Nested data paths `data/*/raw/`, `data/*/processed/`, `data/*/reports/`, `state/*/monthly_status.json` | VERIFIED | All four nested patterns present |
| `launchd/com.ricmag.monitorizacao-eletricidade.plist` | Points to `config/system.json` | VERIFIED | `--config .../config/system.json` present |
| `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` | Points to `config/system.json` | VERIFIED | `--config .../config/system.json` present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/conftest.py` | `config/system.json` schema | `multi_location_config` fixture mirrors real schema | WIRED | Fixture creates identical two-location structure with `"locations"`, `"id"`, `"casa"` |
| `src/backend/process_latest_download.py` | `src/backend/cpe_routing.py` | `from cpe_routing import extract_cpe_from_filename, find_location_by_cpe` | WIRED | Import confirmed on line 9 |
| `src/backend/monthly_workflow.py` | `config/system.json` locations array | `config["locations"]` iteration in `main()` | WIRED | Line 298: `locations = config["locations"]` |
| `src/backend/monthly_workflow.py` | `location` dict | `location["current_contract"]` and `location["pipeline"]` (not `config["current_contract"]`) | WIRED | `render_report(location, ...)` uses `location['current_contract']['supplier']`; no `config["current_contract"]` anywhere in file |
| `src/backend/reminder_job.py` | `config/system.json` | `for loc in config["locations"]` | WIRED | Line 43: `for loc in config["locations"]` |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces pipeline scripts and configuration, not UI components that render dynamic data. All artifacts are backend processing modules verified at Level 3.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 38 tests pass | `python3 -m pytest tests/ -x -q` | `38 passed in 0.26s` | PASS |
| Config schema valid (locations array, 2 entries) | `python3 -c "import json; c=json.load(open('config/system.json')); assert 'locations' in c; assert len(c['locations']) == 2"` | No error | PASS |
| No old `config["current_contract"]` pattern in backend | `grep -r 'config\["current_contract"\]' src/backend/` | No matches | PASS |
| CPE module exports expected functions | Imported in `test_cpe_routing.py` and 38 tests pass | Confirmed | PASS |
| launchd agents loaded | `launchctl list \| grep ricmag` | Both `com.ricmag.monitorizacao-eletricidade` and `com.ricmag.monitorizacao-eletricidade.process-latest` listed with exit code 0 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| MULTI-01 | Plan 01 | Extend `config/system.json` with `"locations": [...]` schema | SATISFIED | `config/system.json` has `locations` array; tests `test_config_has_locations_array`, `test_location_has_required_keys`, `test_casa_cpe_matches` pass |
| MULTI-02 | Plan 01 | Migrate directory structure to nested (`data/casa/`, `data/apartamento/`, `state/casa/`, etc.) | SATISFIED | Schema uses `data/{id}/raw/eredes`, `data/{id}/processed/`, etc.; `test_directory_structure` verifies nested dirs; `.gitignore` covers nested paths |
| MULTI-03 | Plan 02 | Refactor `monthly_workflow.py` to iterate over locations | SATISFIED | `run_workflow(config, location, project_root, ...)` signature; `main()` iterates `config["locations"]` with `--location` filter; 6 tests pass |
| MULTI-04 | Plan 02 | Refactor `process_latest_download.py` for CPE routing | SATISFIED | Imports `cpe_routing`; routes by CPE; returns `unknown_cpe` skip; per-location tracker; 3 tests pass |
| MULTI-05 | Plan 03 | Refactor `reminder_job.py` for per-location notifications | SATISFIED | `for loc in config["locations"]`; per-location title, message and status file; 5 tests pass |
| MULTI-06 | Plan 02 | Extend `eredes_download.py` to show CPE hint notification | SATISFIED | `download_latest_xlsx(cpe_hint=...)` parameter; `notify_mac("E-REDES", f"CPE: {cpe_hint} -- ...")` before browser open; `test_eredes_cpe_hint_in_notification` passes |

All 6 phase requirements are satisfied. No orphaned requirements detected.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| (none) | — | — | — |

No stubs, placeholder returns, or hardcoded empty data found. All implementations are substantive and connected. The `test_config` fixture in `conftest.py` intentionally retains the old schema as a backward-compatibility shim for Phase 02 tests — this is by design (documented in Plan 01) and not an anti-pattern.

---

### Human Verification Required

#### 1. Launchd Agents — Real Smoke Test

**Test:** Place a real E-REDES XLSX file (named `Consumos_PT0002000084968079SX_*.xlsx`) into `~/Downloads` and wait for `com.ricmag.monitorizacao-eletricidade.process-latest` to fire (or trigger manually with `launchctl start com.ricmag.monitorizacao-eletricidade.process-latest`).

**Expected:** `state/launchd.process.stdout.log` shows `"status": "ok"` for casa, and a processed CSV appears at `data/casa/processed/consumo_mensal_atual.csv`.

**Why human:** Requires a real XLSX file with valid E-REDES format and the launchd agent to be running. The test suite mocks all I/O — end-to-end requires the actual filesystem trigger.

#### 2. Reminder Job — macOS Notification Delivery

**Test:** Run `python3 src/backend/reminder_job.py --config config/system.json` from the project root.

**Expected:** Two macOS notifications appear with titles "Eletricidade -- Casa" and "Eletricidade -- Apartamento", and Firefox opens the E-REDES URL twice. Files `state/casa/monthly_status.json` and `state/apartamento/monthly_status.json` are created.

**Why human:** macOS notification delivery cannot be verified programmatically; `subprocess.run(["osascript", ...])` is called with `check=False` so it does not raise on failure.

---

### Gaps Summary

No gaps found. All 6 phase requirements (MULTI-01 through MULTI-06) are fully implemented and verified. The full test suite of 38 tests passes, including both the new Phase 03 tests and all legacy Phase 02 tests. Key implementation correctness checks:

- `config/system.json` fully migrated to locations-array schema with no top-level `current_contract` or `pipeline`.
- All three core workflow scripts (`monthly_workflow.py`, `process_latest_download.py`, `reminder_job.py`) iterate over or route by `config["locations"]`.
- Old `config["current_contract"]` and `config["pipeline"]` patterns are completely absent from all backend modules.
- launchd plists point to the correct config file and are loaded (exit code 0).

The only items requiring human attention are the live smoke test (placing a real XLSX) and confirming macOS notification delivery — neither blocks the phase goal.

---

_Verified: 2026-03-29_
_Verifier: Claude (gsd-verifier)_
