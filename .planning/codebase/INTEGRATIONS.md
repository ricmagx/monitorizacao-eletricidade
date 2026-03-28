# External Integrations

**Analysis Date:** 2026-03-28

## APIs & External Services

**Electricity distributor portal (E-REDES):**
- Service: E-REDES Balcão Digital — `https://balcaodigital.e-redes.pt`
- Purpose: Download official monthly consumption XLSX files (15-minute interval data)
- SDK/Client: Playwright 1.58.0 (`playwright.sync_api`)
- Auth: Session-based — browser session bootstrapped manually via `eredes_bootstrap_session.py`, persisted to `state/eredes_storage_state.json`
- Integration files: `src/backend/eredes_download.py`, `src/backend/eredes_bootstrap_session.py`
- Download modes supported:
  - `external_firefox` (current config) — opens Firefox, watches `~/Downloads` for new XLSX
  - `assisted` — opens Chromium with Playwright, user completes captcha/security check manually
  - `headless` — fully automated Chromium (requires no security challenge)
- No official API — integration relies on web scraping and browser automation

**Electricity price simulator (Tiago Felicia):**
- Service: `https://www.tiagofelicia.pt/eletricidade-tiagofelicia.html`
- Purpose: Scrape ranked comparison of Portuguese electricity suppliers for given consumption values
- SDK/Client: Playwright 1.58.0 (headless Chromium)
- Auth: None — public website, no authentication required
- Integration file: `src/backend/tiagofelicia_compare.py`
- Method: Fills web form with monthly consumption (kWh totals for `simples` and `bi-horário` cycles), reads results table
- No official API — integration relies entirely on web scraping; fragile to site layout changes

## Data Storage

**Databases:**
- None — no database of any kind

**File Storage:**
- Local filesystem only
  - Raw XLSX downloads: `data/raw/eredes/`
  - Processed monthly CSV: `data/processed/consumo_mensal_atual.csv`
  - Analysis JSON: `data/processed/analise_tiagofelicia_atual.json`
  - Reports (Markdown): `data/reports/`
  - Runtime state: `state/` (session cookies, tracker JSON, launchd logs, monthly status)

**Caching:**
- Lightweight file-based deduplication only: `state/last_processed_download.json` stores mtime+size of last processed XLSX to avoid reprocessing the same file

## Authentication & Identity

**Auth Provider:**
- None (no user accounts, no OAuth)
- E-REDES session: stored as Playwright browser storage state JSON at `state/eredes_storage_state.json`
  - Must be refreshed manually via `eredes_bootstrap_session.py` when session expires
  - Contains cookies and local storage — treat as credential file

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, Rollbar, or equivalent

**Notifications:**
- macOS native notifications via `osascript` (`display notification`)
  - Triggered on: monthly reminder, workflow completion, workflow failure
  - Called from: `reminder_job.py`, `monthly_workflow.py`

**Logs:**
- launchd stdout/stderr captured to:
  - `state/launchd.stdout.log` / `state/launchd.stderr.log` (reminder job)
  - `state/launchd.process.stdout.log` / `state/launchd.process.stderr.log` (process-latest job)
- Status JSON written after each run to `state/monthly_status.json`

## CI/CD & Deployment

**Hosting:**
- Local macOS machine only (Mac Mini M4 Pro)

**Scheduling:**
- macOS launchd (no cron, no cloud scheduler)
- Plist files in `launchd/` — must be installed to `~/Library/LaunchAgents/` via `launchctl`
- Generator scripts: `src/backend/install_launch_agent.py`, `src/backend/install_process_watch_agent.py`

**CI Pipeline:**
- None

## Environment Configuration

**Required env vars:**
- None — all configuration is in `config/system.json`

**Key config values (non-secret, in `config/system.json`):**
- `current_contract.supplier` — current electricity supplier name
- `current_contract.power_label` — contracted power (e.g., `"10.35 kVA"`)
- `eredes.download_mode` — `"external_firefox"` | `"assisted"` | `"headless"`
- `eredes.browser_app` — browser name for `open -a` (e.g., `"Firefox"`)
- `eredes.local_download_watch_dir` — directory to watch for new XLSX files (e.g., `"/Users/ricmag/Downloads"`)
- `pipeline.notify_on_completion` — boolean, enables macOS notifications

**Secrets location:**
- `state/eredes_storage_state.json` — E-REDES browser session (cookies). Not committed to git (`.gitignore` should exclude `state/`)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Planned Integrations (not yet implemented)

**Home Assistant:**
- Described in `integracoes/home-assistant/README.md`
- Intent: publish sensors with best supplier, potential savings, last simulation date
- No code exists yet — placeholder documentation only

---

*Integration audit: 2026-03-28*
