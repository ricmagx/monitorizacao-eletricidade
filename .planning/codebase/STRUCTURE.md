# Codebase Structure

**Analysis Date:** 2026-03-28

## Directory Layout

```
monitorizacao-eletricidade/
├── config/                        # All configuration (system + tariff examples)
│   ├── system.json                # Active system config — the single config file for all scripts
│   ├── alertas.exemplo.json       # Example alert thresholds
│   ├── alertas.exemplo.yaml       # Same, YAML format
│   ├── fornecedor_atual.exemplo.json  # Example current contract (for local engine)
│   ├── tarifarios.exemplo.json    # Example tariff catalogue (for local engine)
│   ├── tarifarios.exemplo.yaml    # Same, YAML format
│   └── README.md
├── data/
│   ├── raw/
│   │   └── eredes/                # XLSX exports downloaded from E-REDES
│   ├── processed/                 # Derived artefacts (CSV, analysis JSON)
│   └── reports/                   # Monthly Markdown reports
├── integracoes/                   # Integration documentation (no code)
│   ├── e-redes/README.md
│   ├── home-assistant/README.md
│   └── tiago-felicia/README.md
├── launchd/                       # macOS LaunchAgent plists
│   ├── com.ricmag.monitorizacao-eletricidade.plist               # Monthly reminder (day 1, 09:00)
│   └── com.ricmag.monitorizacao-eletricidade.process-latest.plist # WatchPaths trigger
├── scripts/                       # Shell wrapper scripts for manual invocation
│   ├── bootstrap_eredes_session.sh
│   ├── process_latest_download.sh
│   └── run_monthly_workflow.sh
├── src/
│   ├── backend/                   # All Python source (flat, no sub-packages)
│   │   ├── __init__.py
│   │   ├── energy_compare.py      # Local tariff catalogue engine + CLI
│   │   ├── eredes_bootstrap_session.py  # One-time interactive login capture
│   │   ├── eredes_download.py     # Automated XLSX download from E-REDES
│   │   ├── eredes_to_monthly_csv.py     # XLSX → monthly CSV normaliser
│   │   ├── install_launch_agent.py      # Helper to install launchd agents
│   │   ├── install_process_watch_agent.py
│   │   ├── monthly_workflow.py    # Main pipeline orchestrator + CLI
│   │   ├── process_latest_download.py   # Idempotent watcher trigger + CLI
│   │   ├── reminder_job.py        # Monthly reminder + browser open
│   │   └── tiagofelicia_compare.py      # Live web simulator engine + CLI
│   └── frontend/
│       └── README.md              # Planned frontend (not implemented)
├── state/                         # Runtime state files (JSON, logs) — gitignored
│   ├── eredes_bootstrap_context.json
│   ├── eredes_storage_state.json  # Playwright session (credentials — never commit)
│   ├── last_processed_download.json
│   ├── monthly_status.json
│   ├── launchd.process.stderr.log
│   └── launchd.process.stdout.log
├── .planning/codebase/            # GSD codebase analysis documents
├── ARQUITETURA.md
├── FONTES-DADOS.md
├── MVP.md
├── OPERACAO.md
├── README.md
├── RISCOS-MANUTENCAO.md
└── ROADMAP.md
```

## Directory Purposes

**`config/`:**
- Purpose: All configuration consumed by scripts
- Contains: Active `system.json` (the only file scripts read at runtime), plus `.exemplo.*` reference files showing expected format for local engine inputs
- Key files: `config/system.json` — referenced by every script via `--config` flag

**`data/raw/eredes/`:**
- Purpose: Downloaded XLSX files from E-REDES, named with timestamp prefix
- Contains: Raw meter export files; naming pattern: `Consumos_PT<CPE>_<YYYYMMDDHHMMSS>.xlsx`
- Generated: Yes (by `eredes_download.py` or copied from `~/Downloads`)
- Committed: No (real data, not committed)

**`data/processed/`:**
- Purpose: Derived artefacts produced by the pipeline
- Contains:
  - `consumo_mensal_atual.csv` — current aggregated monthly consumption (overwritten each run)
  - `analise_tiagofelicia_atual.json` — latest analysis output from tiagofelicia engine (overwritten each run)
  - `consumo_mensal.exemplo.csv` — committed example for testing CLI manually
- Generated: Yes (pipeline outputs)

**`data/reports/`:**
- Purpose: Historical Markdown reports, one per pipeline run
- Contains: `relatorio_eletricidade_YYYY-MM-DD.md` — human-readable monthly summary
- Generated: Yes
- Committed: Yes (analysis history)

**`src/backend/`:**
- Purpose: All executable Python — flat module structure, no sub-packages
- Contains: One `.py` file per concern; each is both a CLI script and an importable module
- Key files: See "Key File Locations" below

**`src/frontend/`:**
- Purpose: Planned dashboard (HTMX + Jinja + Chart.js per README)
- Contains: Only a README placeholder — no implementation exists
- Status: Not started

**`state/`:**
- Purpose: Runtime state between pipeline runs
- Contains: JSON state files and launchd log files
- Committed: Partially — `.gitignore` should exclude `eredes_storage_state.json` (contains session tokens); logs committed incidentally
- Note: `state/eredes_storage_state.json` contains browser session data equivalent to login credentials — must never be committed

**`launchd/`:**
- Purpose: macOS LaunchAgent definitions for scheduling and file-watching
- Contains: Two plist files, ready to load via `launchctl`
- Committed: Yes

**`scripts/`:**
- Purpose: Convenience shell wrappers for manual invocation with hardcoded project root
- Contains: Three `.sh` scripts wrapping Python CLI calls with the correct `--config` path

**`integracoes/`:**
- Purpose: Documentation about each external integration (no code lives here)
- Contains: One `README.md` per integration (E-REDES, Home Assistant, Tiago Felícia)

## Key File Locations

**Entry Points:**
- `src/backend/monthly_workflow.py`: Full pipeline orchestrator; use `--config config/system.json`
- `src/backend/process_latest_download.py`: Watcher trigger; idempotent pipeline run from newest XLSX in Downloads
- `src/backend/reminder_job.py`: Monthly reminder; used by launchd
- `scripts/run_monthly_workflow.sh`: Shell wrapper for monthly_workflow with hardcoded paths
- `scripts/process_latest_download.sh`: Shell wrapper for process_latest_download

**Configuration:**
- `config/system.json`: Single source of truth for all runtime configuration (contract, E-REDES settings, pipeline paths, schedule)

**Core Logic:**
- `src/backend/energy_compare.py`: `MonthlyConsumption` and `Tariff` dataclasses; `analyse()` function; local catalogue engine
- `src/backend/tiagofelicia_compare.py`: `analyse_with_tiago()` function; Playwright automation against `tiagofelicia.pt`
- `src/backend/eredes_to_monthly_csv.py`: `convert_xlsx_to_monthly_csv()` function; vazio classification logic
- `src/backend/eredes_download.py`: `download_latest_xlsx()` function; three download modes

**State:**
- `state/monthly_status.json`: Last pipeline result (read by any monitoring tool)
- `state/eredes_storage_state.json`: Playwright session — required for headless/assisted E-REDES download
- `state/last_processed_download.json`: File signature tracker for idempotency

**Scheduling:**
- `launchd/com.ricmag.monitorizacao-eletricidade.plist`: Day-1 monthly reminder agent
- `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist`: Downloads folder watcher agent

**Session Bootstrap (one-time):**
- `src/backend/eredes_bootstrap_session.py`: Interactive login capture; run once when session expires
- `scripts/bootstrap_eredes_session.sh`: Shell wrapper for bootstrap

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `eredes_to_monthly_csv.py`, `tiagofelicia_compare.py`)
- Shell scripts: `snake_case.sh` (e.g., `run_monthly_workflow.sh`)
- Config files: `snake_case.json` or `snake_case.yaml`; example files suffixed `.exemplo.json`
- Data files: descriptive names with dates or CPE codes (e.g., `consumo_mensal_atual.csv`, `Consumos_PT0002000084968079SX_20260326042940.xlsx`)
- Reports: `relatorio_eletricidade_YYYY-MM-DD.md`
- State files: descriptive noun phrases (e.g., `monthly_status.json`, `last_processed_download.json`)

**Directories:**
- `snake_case` for all directories except `src/backend` and `src/frontend` which use short names
- Plural for data containers (`scripts/`, `integracoes/`, `launchd/`)

**Python symbols:**
- Functions: `snake_case` (e.g., `run_workflow`, `convert_xlsx_to_monthly_csv`)
- Classes/dataclasses: `PascalCase` (e.g., `MonthlyConsumption`, `Tariff`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `SITE_URL`, `HOME_URL`, `LISBON`)

## Where to Add New Code

**New data source (e.g., Home Assistant integration):**
- Implementation: `src/backend/homeassistant_<purpose>.py` following the same module pattern (CLI + importable function)
- Integration docs: `integracoes/home-assistant/README.md`

**New comparison engine (e.g., direct ERSE API):**
- Implementation: `src/backend/<source>_compare.py` following the pattern of `energy_compare.py` or `tiagofelicia_compare.py`
- Entry function signature: `analyse_with_<source>(consumption_path: Path, ...) -> dict[str, Any]`
- Wire into pipeline: Import and call from `monthly_workflow.py`

**New configuration key:**
- Add to `config/system.json` under the appropriate section (`eredes`, `pipeline`, `current_contract`, etc.)
- Update `.exemplo` files if the key is relevant to the local engine

**Frontend (planned):**
- Implementation: `src/frontend/` — planned stack is HTMX + Jinja + Chart.js

**New shell helper:**
- Implementation: `scripts/<verb>_<noun>.sh` following the pattern of existing scripts (hardcode `ROOT` and pass `--config`)

**New launchd agent:**
- Implementation: `launchd/com.ricmag.monitorizacao-eletricidade.<label>.plist`
- Use `WorkingDirectory` and absolute paths consistent with existing plists

## Special Directories

**`state/`:**
- Purpose: Runtime-generated JSON and log files persisted between pipeline runs
- Generated: Yes
- Committed: Partially — logs and non-sensitive state may be committed; `eredes_storage_state.json` must be gitignored (contains session tokens)

**`src/backend/__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (gitignored)

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: By GSD map-codebase command
- Committed: Yes

---

*Structure analysis: 2026-03-28*
