# Technology Stack

**Analysis Date:** 2026-03-28

## Languages

**Primary:**
- Python 3.11 - All backend logic in `src/backend/`

**Secondary:**
- Shell (zsh) - Wrapper scripts in `scripts/`
- XML (Apple plist) - launchd scheduling in `launchd/`
- JSON/YAML - Configuration files in `config/`

## Runtime

**Environment:**
- Python 3.11.14 (confirmed via `python3 --version`)
- Platform: macOS (Darwin) — project is macOS-only by design

**Package Manager:**
- pip (system pip3)
- No lockfile detected (no `requirements.txt`, `pyproject.toml`, or `poetry.lock`)

## Frameworks

**Browser Automation:**
- Playwright 1.58.0 (`playwright.sync_api`) — used for two distinct purposes:
  1. Headless scraping of `tiagofelicia.pt` simulator (`src/backend/tiagofelicia_compare.py`)
  2. Session-based download from `balcaodigital.e-redes.pt` (`src/backend/eredes_download.py`, `eredes_bootstrap_session.py`)

**Spreadsheet Processing:**
- openpyxl 3.1.5 — reads E-REDES `.xlsx` exports (`src/backend/eredes_to_monthly_csv.py`)

**Build/Dev:**
- None — no build system, no virtual environment manifest detected
- Scripts invoked directly via `python3`

## Key Dependencies

**Critical:**
- `playwright` 1.58.0 — central to two integration paths; loss of Playwright breaks both E-REDES download and Tiago Felicia simulation
- `openpyxl` 3.1.5 — required for XLSX parsing; cannot process E-REDES exports without it

**Standard Library Only (no extra install needed):**
- `csv`, `json`, `pathlib`, `argparse`, `subprocess`, `datetime`, `zoneinfo`, `dataclasses`, `statistics`, `collections`

## Configuration

**Environment:**
- No `.env` files — all config lives in `config/system.json`
- No secrets or credentials in config files (session state stored separately in `state/eredes_storage_state.json`)

**Build:**
- No build config files (no `tsconfig.json`, `webpack`, `pyproject.toml`, etc.)

**Scheduling:**
- macOS launchd via `.plist` files in `launchd/`
- Two agents:
  - `com.ricmag.monitorizacao-eletricidade` — fires day 1 of month at 09:00, runs `reminder_job.py`
  - `com.ricmag.monitorizacao-eletricidade.process-latest` — fires on `WatchPaths` change (`~/Downloads`), runs `process_latest_download.py`

## Platform Requirements

**Development:**
- macOS required (uses `osascript` for notifications, `open -a` for browser control, launchd for scheduling)
- Python 3.11+
- Playwright 1.58+ with Chromium browser installed (`playwright install chromium`)
- openpyxl 3.1+
- Firefox installed (for `external_firefox` download mode configured in `config/system.json`)

**Production:**
- Same Mac machine (Mac Mini M4 Pro per user profile)
- No cloud deployment — fully local pipeline
- State persisted to `state/` directory on local filesystem

---

*Stack analysis: 2026-03-28*
