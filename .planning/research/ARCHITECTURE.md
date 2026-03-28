# Architecture Patterns — Multi-Location Refactor

**Domain:** Single-location Python pipeline refactored to N independent locations
**Researched:** 2026-03-28
**Overall confidence:** HIGH (based on direct codebase analysis; no speculative claims)

---

## Context

The existing pipeline is a single-location, config-driven CLI tool.
Every path in `config/system.json` is singular and global. The state in `state/` is also singular and global.
The goal is to support two locations (casa, apartamento) that share one E-REDES account but have different CPEs, different contracts, and produce separate reports.

N=2 is the concrete target. The architecture must generalise to N without requiring structural changes again.

---

## Recommended Architecture

### 1. Config: One file with a `locations` array (not separate files per location)

**Decision:** Keep a single `config/system.json` with a top-level `locations` array.

**Why not separate files (`config/casa.json`, `config/apartamento.json`):**
- The E-REDES session is shared. Bootstrap is done once and reused by both locations. A separate-files model forces duplicating the `eredes` session block or creating a separate "global" section, creating two config schemas.
- The `reminder_job.py` and the launchd reminder plist both fire once per month. They need one entry point, not N.
- A single file makes it trivial to add a third location later without touching launchd or scripts.

**Config schema — new `system.json`:**

```json
{
  "eredes": {
    "home_url": "https://balcaodigital.e-redes.pt/home",
    "storage_state_path": "state/eredes_storage_state.json",
    "bootstrap_context_path": "state/eredes_bootstrap_context.json",
    "download_url": "https://balcaodigital.e-redes.pt/consumptions/history",
    "download_mode": "external_firefox",
    "browser_app": "Firefox",
    "interactive_wait_seconds": 900,
    "local_download_watch_dir": "/Users/ricmag/Downloads",
    "local_download_glob": "Consumos_*.xlsx",
    "download_button_candidates": ["Exportar excel", "Descarregar Excel", "Excel"],
    "download_timeout_seconds": 60
  },
  "schedule": {
    "day": 1,
    "hour": 9,
    "minute": 0,
    "timezone": "Europe/Lisbon"
  },
  "watcher": {
    "enabled": true,
    "watch_paths": ["/Users/ricmag/Downloads"]
  },
  "locations": [
    {
      "id": "casa",
      "label": "Casa",
      "cpe": "PT0002000084968079SX",
      "eredes_download_dir": "data/casa/raw/eredes",
      "current_contract": {
        "supplier": "Meo Energia",
        "current_plan_contains": "Tarifa Variável",
        "power_label": "10.35 kVA"
      },
      "pipeline": {
        "processed_csv_path": "data/casa/processed/consumo_mensal_atual.csv",
        "analysis_json_path": "data/casa/processed/analise_tiagofelicia_atual.json",
        "report_dir": "data/casa/reports",
        "status_path": "state/casa/monthly_status.json",
        "last_processed_tracker_path": "state/casa/last_processed_download.json",
        "drop_partial_last_month": true,
        "notify_on_completion": true,
        "months_limit": null
      }
    },
    {
      "id": "apartamento",
      "label": "Apartamento",
      "cpe": "PT000200XXXXXXXXXX",
      "eredes_download_dir": "data/apartamento/raw/eredes",
      "current_contract": {
        "supplier": "EDP Comercial",
        "current_plan_contains": "Bi-horário",
        "power_label": "6.9 kVA"
      },
      "pipeline": {
        "processed_csv_path": "data/apartamento/processed/consumo_mensal_atual.csv",
        "analysis_json_path": "data/apartamento/processed/analise_tiagofelicia_atual.json",
        "report_dir": "data/apartamento/reports",
        "status_path": "state/apartamento/monthly_status.json",
        "last_processed_tracker_path": "state/apartamento/last_processed_download.json",
        "drop_partial_last_month": true,
        "notify_on_completion": true,
        "months_limit": null
      }
    }
  ]
}
```

**Key design choices in this schema:**
- `eredes` block at the top level is shared (session, credentials, browser settings). Never duplicated.
- Each location has its own `pipeline` sub-block with independent paths.
- `cpe` is a first-class field at the location level — needed for CPE selection during download.
- `id` (snake_case, stable) is the directory key. `label` is the human-readable display name.

---

### 2. Directory Structure: Nested by location ID

**Decision:** Nested directories under `data/` and `state/`, keyed by location `id`.

**Why not flat prefixes (`data/processed/casa_consumo_mensal_atual.csv`):**
- Files accumulate. A flat directory with 2 locations × 5 file types × N months = dozens of similarly-named files that are hard to `ls` or glob.
- Nested directories map cleanly to location-aware CLI arguments (`--location casa`).
- Python `Path` operations are easier: `data_dir / location_id / "processed"`.

**Target directory layout after refactor:**

```
monitorizacao-eletricidade/
├── config/
│   └── system.json                   # Single file, locations array inside
├── data/
│   ├── casa/
│   │   ├── raw/eredes/               # XLSX exports for casa
│   │   ├── processed/                # consumo_mensal_atual.csv, analise_tiagofelicia_atual.json
│   │   └── reports/                  # relatorio_eletricidade_YYYY-MM-DD.md
│   └── apartamento/
│       ├── raw/eredes/
│       ├── processed/
│       └── reports/
├── state/
│   ├── eredes_storage_state.json     # Shared — one session for all locations
│   ├── eredes_bootstrap_context.json # Shared
│   ├── casa/
│   │   ├── monthly_status.json
│   │   ├── last_processed_download.json
│   │   ├── launchd.process.stdout.log
│   │   └── launchd.process.stderr.log
│   └── apartamento/
│       ├── monthly_status.json
│       ├── last_processed_download.json
│       ├── launchd.process.stdout.log
│       └── launchd.process.stderr.log
├── launchd/
│   ├── com.ricmag.monitorizacao-eletricidade.plist            # Shared reminder (unchanged)
│   ├── com.ricmag.monitorizacao-eletricidade.process-latest.plist  # Shared watcher (iterates all locations)
│   └── (no per-location plists needed)
├── src/backend/
│   ├── monthly_workflow.py            # Refactored: accepts location config dict, not full config
│   ├── process_latest_download.py     # Refactored: loops over locations, matches XLSX to CPE
│   ├── eredes_download.py             # CPE-aware: new param for CPE selection
│   ├── eredes_to_monthly_csv.py       # Already location-agnostic (no changes)
│   ├── energy_compare.py              # Already location-agnostic (no changes)
│   ├── tiagofelicia_compare.py        # Already location-agnostic (no changes)
│   ├── reminder_job.py                # Refactored: loops all locations for notification
│   └── eredes_bootstrap_session.py    # Already location-agnostic (no changes)
└── scripts/
    ├── run_monthly_workflow.sh        # Unchanged (no --location = all locations)
    ├── run_monthly_workflow_casa.sh   # New: --location casa
    └── ...
```

---

### 3. Orchestrator: Sequential loop over locations

**Decision:** `run_workflow()` loops over locations sequentially, not in parallel.

**Why sequential:**
- The E-REDES portal is being scraped by the same Playwright session. Running two browser automations against the same authenticated session concurrently risks session invalidation or portal rate-limiting.
- N=2 for this project. The sequential overhead is one extra Playwright run (~1-2 minutes). The complexity cost of thread-safe parallel execution is not justified.
- `tiagofelicia_compare.py` also uses Playwright (headless Chromium). Two concurrent headless browser instances on a Mac Mini M4 Pro are fine, but sequencing avoids any shared-state edge cases.
- If N ever grows large enough to matter, a simple `asyncio.gather()` with a semaphore is the upgrade path, not a full redesign.

**Refactored `run_workflow()` signature:**

The current `run_workflow(config_path, input_xlsx)` processes one global config. After refactor it becomes:

```python
def run_workflow(
    location_config: dict,      # one element from config["locations"]
    shared_eredes: dict,        # config["eredes"]
    project_root: Path,
    input_xlsx: Path | None = None,
) -> dict[str, Any]:
    ...
```

A new top-level `run_all_locations(config_path, location_id=None)` becomes the entry point:

```python
def run_all_locations(config_path: Path, location_id: str | None = None) -> list[dict]:
    config = load_config(config_path)
    project_root = project_root_from_config(config_path)
    locations = config["locations"]
    if location_id:
        locations = [loc for loc in locations if loc["id"] == location_id]
    results = []
    for loc in locations:
        result = run_workflow(loc, config["eredes"], project_root)
        results.append({"location": loc["id"], **result})
    return results
```

This keeps the existing `--config` contract intact while adding optional `--location` filtering.

---

### 4. launchd: One shared plist per function (not per location)

**Decision:** Keep two plists total. The watcher plist calls `process_latest_download.py` without `--location`, which iterates all locations internally.

**Why not one plist per location:**
- Two plists per function × N locations = 2N plists. At N=2, that is four plists with near-identical content. Maintenance burden scales linearly.
- `WatchPaths` watches `~/Downloads` for any new XLSX. The correct resolution is in `process_latest_download.py`: it reads the CPE from the filename and matches it to the right location. The plist does not need to know about locations.
- The reminder plist fires once on day 1 at 09:00. A single notification that says "download both locations" is better UX than two notifications at the same time.

**Watcher plist — unchanged from current:**
The plist remains exactly as-is. Only `process_latest_download.py` changes internally to loop over locations.

**CPE-to-location matching in `process_latest_download.py`:**
E-REDES XLSX filenames follow the pattern `Consumos_PT<CPE>_<YYYYMMDDHHMMSS>.xlsx`. The CPE is extractable from the filename with a simple split. Match against `location["cpe"]` to route to the correct location config.

```python
def location_for_xlsx(filename: str, locations: list[dict]) -> dict | None:
    # filename: "Consumos_PT0002000084968079SX_20260326042940.xlsx"
    parts = Path(filename).stem.split("_")
    if len(parts) >= 2:
        cpe_segment = parts[1]          # "PT0002000084968079SX"
        for loc in locations:
            if loc["cpe"] in cpe_segment or cpe_segment in loc["cpe"]:
                return loc
    return None
```

If no match is found (downloaded XLSX is for an unknown CPE), skip with a warning rather than failing — defensive against manually downloaded files.

---

### 5. Playwright session sharing — gotchas

**Finding:** The current `eredes_download.py` serialises the session after each run:

```python
context.storage_state(path=str(storage_state_path))
```

This updates the shared `state/eredes_storage_state.json` on every Playwright-mode download. Since the architecture runs locations sequentially, this is safe — session N+1 reads the file written by session N.

**Specific gotchas to address:**

**a) CPE selection UI — the real challenge.**
The current `eredes_download.py` does not select a CPE. It assumes the portal shows one meter and exports it. With two CPEs under the same account, the portal likely shows a dropdown or list to select the counter before exporting. This requires new navigation logic — probably clicking on the CPE name or selecting from a switcher before hitting "Exportar excel". This is the most uncertain part of the refactor (no direct documentation available for the E-REDES portal multi-CPE navigation flow). The `navigation_click_texts` array in config is the correct hook for this — per-location navigation sequences.

**Recommended addition to location config:**
```json
"eredes_navigation_click_texts": ["PT0002000084968079SX"]
```

This allows per-location navigation sequences without changing `eredes_download.py`'s core logic.

**b) `external_firefox` mode and CPE matching.**
In `external_firefox` mode, the user downloads manually. The XLSX filename contains the CPE, so `location_for_xlsx()` handles routing. No Playwright session concerns here. This is the current default mode and the safe path for the first multi-location iteration.

**c) Session state invalidation.**
The storage state includes cookies and localStorage for the E-REDES portal. Two sequential Playwright contexts loading the same storage state file will both read valid credentials. The second context writes back an updated state after its download. This is safe sequentially. The risk is only if both ran concurrently (same file being read and written simultaneously) — which sequential execution avoids by design.

**d) Session expiry between locations.**
If the session expires mid-run (after location 1 succeeds but before location 2 starts), location 2 will fail with "Sessão E-REDES inválida". The existing error handling catches this and writes `{"status": "error"}` to `state/apartamento/monthly_status.json`. A macOS notification is sent. The user re-runs bootstrap and then triggers the workflow again with `--location apartamento`. This is acceptable failure behaviour for a personal tool.

---

## Module Impact Analysis

### No changes needed (already location-agnostic)

| Module | Reason |
|--------|--------|
| `eredes_to_monthly_csv.py` | Takes `xlsx_path` and `output_path` as arguments — purely functional |
| `energy_compare.py` | Takes consumption CSV path — no config coupling |
| `tiagofelicia_compare.py` | Takes consumption path + contract params — no config coupling |
| `eredes_bootstrap_session.py` | Session bootstrap is once-per-account, not per-location |

### Needs changes

| Module | Change Required |
|--------|----------------|
| `monthly_workflow.py` | Split `run_workflow()` into location-scoped + top-level `run_all_locations()`. Accept `location_config` dict instead of full config path. |
| `process_latest_download.py` | Loop over all locations. Add `location_for_xlsx()` for CPE-to-location routing. Per-location tracker paths from location config. |
| `reminder_job.py` | Loop over locations array; send one combined notification or per-location notifications. Open browser once (shared URL). |
| `eredes_download.py` | Add `cpe` parameter; add CPE selection navigation before the download click (for headless/assisted modes). `navigation_click_texts` becomes per-location. |
| `install_launch_agent.py` | May need update if it reads hardcoded paths from config for plist generation. |
| `install_process_watch_agent.py` | Same as above. |

### New code needed

| Module | Purpose |
|--------|---------|
| `config_loader.py` (optional) | Extract the repeated `load_config / project_root_from_config / resolve_path` pattern (currently duplicated across 5 files) into a shared utility. Not required for correctness but eliminates duplication. |

---

## Migration Path

### Step 1 — Config migration (no code changes)

Add `locations` array to `config/system.json`. Move per-location fields from the root into the first location entry (`casa`). Keep the top-level `eredes`, `schedule`, and `watcher` blocks as-is.

Verify that the config is valid JSON and contains the correct CPE for `casa` (visible in `state/last_processed_download.json`: `PT0002000084968079SX`).

### Step 2 — Directory migration (file operations only)

Create nested directories:

```bash
mkdir -p data/casa/raw/eredes data/casa/processed data/casa/reports
mkdir -p data/apartamento/raw/eredes data/apartamento/processed data/apartamento/reports
mkdir -p state/casa state/apartamento
```

Move existing files:

```bash
mv data/raw/eredes/*.xlsx data/casa/raw/eredes/
mv data/processed/* data/casa/processed/
mv data/reports/* data/casa/reports/
mv state/monthly_status.json state/casa/monthly_status.json
mv state/last_processed_download.json state/casa/last_processed_download.json
```

Note: `state/eredes_storage_state.json` and `state/eredes_bootstrap_context.json` remain at the root of `state/` — they are shared.

### Step 3 — Module refactoring

Refactor modules in this order (each step is independently testable):

1. `monthly_workflow.py` — refactor `run_workflow()` to accept `location_config` dict. Verify with: `python3 src/backend/monthly_workflow.py --config config/system.json --location casa --input-xlsx data/casa/raw/eredes/<file>.xlsx`

2. `process_latest_download.py` — add `location_for_xlsx()` and loop. Verify by dropping a known XLSX into `~/Downloads` and checking routing.

3. `reminder_job.py` — loop over locations array. Minimal change.

4. `eredes_download.py` — add CPE selection logic. This is the most uncertain step and should be tested interactively with the portal before committing to headless mode.

### Step 4 — launchd plists

Launchd plists need no structural change. If log paths are updated to per-location directories, the plists must be reloaded:

```bash
launchctl unload ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist
launchctl load ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate config files per location
**What:** `config/casa.json`, `config/apartamento.json`, each with a full `eredes` block
**Why bad:** Session state path is duplicated. Adding a third location means creating a new file and editing two other places (scripts, plists). Adding a shared field (e.g., `schedule`) must be done in N files.
**Instead:** Single `system.json` with `locations` array and a shared `eredes` block.

### Anti-Pattern 2: Parallel Playwright runs
**What:** Using `threading.Thread` or `asyncio` to run both locations' downloads simultaneously
**Why bad:** Same storage state JSON written by both threads — last write wins, may corrupt session. Portal may rate-limit or flag concurrent sessions from the same authenticated account.
**Instead:** Sequential loop. Upgrade to parallel only if N > 5 and timing becomes a practical problem, using a file lock or separate state copies per location.

### Anti-Pattern 3: One launchd plist per location
**What:** Four plists: `reminder.casa.plist`, `reminder.apartamento.plist`, `process-latest.casa.plist`, `process-latest.apartamento.plist`
**Why bad:** `WatchPaths` in launchd watches a directory, not a CPE-filtered subset of files. Both plists fire on every download — race condition on which location processes the file first. Maintenance doubles.
**Instead:** One shared plist; CPE routing in Python.

### Anti-Pattern 4: Encoding location in the `--config` flag
**What:** `monthly_workflow.py --config config/casa.json` with separate config files
**Why bad:** See Anti-Pattern 1. Also loses the ability to `run_all_locations()` without a shell loop.
**Instead:** `monthly_workflow.py --config config/system.json --location casa`

---

## Scalability Consideration

At N=2 (the target), none of this matters. For completeness:

| Concern | At N=2 | At N=10 |
|---------|--------|---------|
| Sequential download time | ~2-4 min total | ~20 min — consider parallel with file-lock per state |
| Config file size | Small | Still manageable as JSON |
| `~/Downloads` routing | Trivial | Still trivial (CPE is always in filename) |
| State directory | 2 subdirs | 10 subdirs — still flat enough |

---

## Sources

- Direct codebase analysis: `src/backend/monthly_workflow.py`, `src/backend/eredes_download.py`, `src/backend/process_latest_download.py`, `src/backend/reminder_job.py`
- Current config: `config/system.json`
- Current state: `state/last_processed_download.json` (CPE visible in path: `PT0002000084968079SX`)
- Current launchd: `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist`
- Confidence: HIGH for structural decisions (based on reading actual code). MEDIUM for E-REDES portal CPE selection UI (portal behaviour not directly observable — based on known pattern of `navigation_click_texts` config hook already present in the codebase).

---

*Research date: 2026-03-28*
