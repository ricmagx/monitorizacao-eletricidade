# Architecture

**Analysis Date:** 2026-03-28

## Pattern Overview

**Overall:** Pipeline-Oriented CLI Scripts (no web server, no framework)

**Key Characteristics:**
- Each Python module is an independent CLI tool with `main()` and `argparse`
- All modules are also importable as libraries (no side-effects at import time)
- A central orchestrator (`monthly_workflow.py`) composes the other modules into a pipeline
- Configuration is externalised to a single JSON file (`config/system.json`)
- State is persisted as JSON files in `state/` between runs
- No database — data is stored as flat files (CSV, JSON, XLSX, Markdown)
- macOS `launchd` drives scheduling; no in-process scheduler

## Layers

**Data Acquisition:**
- Purpose: Obtain the raw XLSX from E-REDES (official meter data)
- Location: `src/backend/eredes_download.py`, `src/backend/eredes_bootstrap_session.py`
- Contains: Playwright browser automation, session persistence, three download modes (`headless`, `assisted`, `external_firefox`)
- Depends on: `state/eredes_storage_state.json` (persisted browser session), `config/system.json`
- Used by: `monthly_workflow.py`

**Normalisation:**
- Purpose: Transform 15-minute interval XLSX readings into monthly CSV aggregates (total, vazio, fora_vazio kWh)
- Location: `src/backend/eredes_to_monthly_csv.py`
- Contains: XLSX parsing with `openpyxl`, timezone handling (`Europe/Lisbon`), daily-cycle vazio classification, partial-month detection
- Depends on: `data/raw/eredes/*.xlsx`
- Used by: `monthly_workflow.py`

**Comparison Engine:**
- Purpose: Calculate tariff costs and rank suppliers
- Location: `src/backend/energy_compare.py` (local catalogue), `src/backend/tiagofelicia_compare.py` (live web simulator)
- Contains: `MonthlyConsumption` and `Tariff` dataclasses, cost simulation (simples and bihorario), seasonal summary, change recommendation
- Depends on: `data/processed/consumo_mensal_atual.csv`, `config/tarifarios.json` (for local engine) or `tiagofelicia.pt` (for web engine)
- Used by: `monthly_workflow.py`, directly via CLI

**Orchestration:**
- Purpose: Glue all stages into one monthly run
- Location: `src/backend/monthly_workflow.py`
- Contains: `run_workflow()`, report rendering (Markdown), macOS notification, status persistence
- Depends on: all modules above, `config/system.json`
- Used by: `scripts/run_monthly_workflow.sh`, `process_latest_download.py`

**Watch/Trigger Layer:**
- Purpose: Detect newly downloaded XLSX files and trigger pipeline automatically
- Location: `src/backend/process_latest_download.py`
- Contains: file-signature tracker (mtime + size), idempotency guard against reprocessing the same file
- Depends on: `state/last_processed_download.json`, `monthly_workflow.py`
- Used by: `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` (watches `~/Downloads`)

**Reminder Layer:**
- Purpose: Monthly nudge to initiate the download
- Location: `src/backend/reminder_job.py`
- Contains: macOS notification + browser open, status write
- Depends on: `config/system.json`
- Used by: `launchd/com.ricmag.monitorizacao-eletricidade.plist` (day 1 of each month, 09:00)

## Data Flow

**Monthly Automated Flow:**

1. `launchd` fires `reminder_job.py` on day 1 at 09:00 — sends macOS notification, opens E-REDES URL in Firefox
2. User downloads XLSX manually from E-REDES portal
3. `launchd` watches `~/Downloads` via `WatchPaths`; on new file, fires `process_latest_download.py`
4. `process_latest_download.py` checks file signature against `state/last_processed_download.json` — skips if already processed
5. `monthly_workflow.py` is called with the new XLSX path
6. `eredes_to_monthly_csv.py` converts XLSX → `data/processed/consumo_mensal_atual.csv`
7. `tiagofelicia_compare.py` launches headless Chromium, fills the web simulator for each month in the CSV, extracts results table
8. Analysis JSON written to `data/processed/analise_tiagofelicia_atual.json`
9. Markdown report written to `data/reports/relatorio_eletricidade_YYYY-MM-DD.md`
10. Status written to `state/monthly_status.json`
11. macOS notification sent with recommendation

**Manual / Direct CLI Flow:**

```bash
# Normalise only
python3 src/backend/eredes_to_monthly_csv.py --input data/raw/eredes/file.xlsx --output data/processed/consumo_mensal_atual.csv

# Compare with local catalogue
python3 src/backend/energy_compare.py --consumption data/processed/consumo_mensal.csv --tariffs config/tarifarios.json --contract config/fornecedor_atual.json

# Compare via tiagofelicia.pt
python3 src/backend/tiagofelicia_compare.py --consumption data/processed/consumo_mensal.csv --power "10.35 kVA" --current-supplier "Meo Energia"

# Full workflow
python3 src/backend/monthly_workflow.py --config config/system.json
```

**State Management:**
- `state/eredes_storage_state.json` — Playwright browser session (persisted cookies/localStorage) for E-REDES login
- `state/eredes_bootstrap_context.json` — URL and visible actions captured during login bootstrap
- `state/last_processed_download.json` — file signature of the last processed XLSX (idempotency)
- `state/monthly_status.json` — result of the last pipeline run (status, paths, recommendation, saving)
- `state/launchd.*.log` — stdout/stderr from launchd-triggered jobs

## Key Abstractions

**MonthlyConsumption (dataclass):**
- Purpose: Canonical unit of consumption data — one month, with total/vazio/fora_vazio kWh
- Location: `src/backend/energy_compare.py` (defined), imported by `tiagofelicia_compare.py`
- Pattern: Frozen dataclass; computed properties for `year`, `month`, `vazio_ratio`, `days_in_month`

**Tariff (dataclass):**
- Purpose: Represents a supplier tariff plan with energy prices, fixed daily cost, validity dates
- Location: `src/backend/energy_compare.py`
- Pattern: Frozen dataclass; supports both `simples` and `bihorario` types

**run_workflow() function:**
- Purpose: Single entry point for the full pipeline; accepts an optional pre-downloaded XLSX to bypass download
- Location: `src/backend/monthly_workflow.py`
- Pattern: Returns a status dict; writes side-effects to files; raises on failure after writing error status

**load_config() / resolve_path() pattern:**
- Purpose: All modules accept a `--config` JSON path; paths inside config are relative to project root
- Location: Repeated across `monthly_workflow.py`, `eredes_download.py`, `process_latest_download.py`, `reminder_job.py`
- Pattern: `project_root = config_path.resolve().parent.parent` — config lives in `config/`, project root is two levels up

## Entry Points

**launchd reminder (monthly, day 1 at 09:00):**
- Location: `launchd/com.ricmag.monitorizacao-eletricidade.plist`
- Triggers: macOS scheduler
- Responsibilities: Notify user, open browser, write waiting status

**launchd watcher (on file change in ~/Downloads):**
- Location: `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist`
- Triggers: New or modified file in `~/Downloads`
- Responsibilities: Check idempotency, run full pipeline, write report and status

**Manual full workflow:**
- Location: `scripts/run_monthly_workflow.sh`, or directly `src/backend/monthly_workflow.py --config config/system.json`
- Triggers: Manual execution
- Responsibilities: Entire pipeline including optional auto-download

**Manual process-latest:**
- Location: `scripts/process_latest_download.sh`, or directly `src/backend/process_latest_download.py --config config/system.json`
- Triggers: Manual execution after placing XLSX in watched directory

## Error Handling

**Strategy:** Fail loudly; write error status to `state/monthly_status.json` before re-raising

**Patterns:**
- `run_workflow()` wraps the entire pipeline in `try/except Exception`; on failure writes `{"status": "error", "error": str(exc)}` to the status file, then optionally sends macOS notification, then re-raises
- Individual modules raise `RuntimeError` or `ValueError` with Portuguese-language messages describing the failure condition
- Playwright timeout errors are caught and re-raised as `RuntimeError` with descriptive messages
- `process_latest_download.py` returns `{"status": "skipped"}` (not an error) when the same XLSX has already been processed

## Cross-Cutting Concerns

**Logging:** No structured logging framework; `print()` for informational output; stdout/stderr captured by launchd to `state/launchd.*.log`
**Validation:** Input validation at data load time (CSV column presence, tariff catalogue non-empty, contract tariff ID present in catalogue)
**Authentication:** E-REDES session managed via Playwright storage state bootstrap (`eredes_bootstrap_session.py`); session serialised to `state/eredes_storage_state.json` and reloaded on each automated download
**Notifications:** macOS `osascript` notifications used as the user-facing output channel for both reminders and completion alerts

---

*Architecture analysis: 2026-03-28*
