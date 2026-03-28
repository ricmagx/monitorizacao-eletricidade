# Project Research Summary

**Project:** Monitorização de Eletricidade — Multi-Local
**Domain:** Personal electricity monitoring + supplier comparison (Portugal, E-REDES)
**Researched:** 2026-03-28
**Confidence:** HIGH (architecture and pitfalls based on direct codebase analysis; stack HIGH; features MEDIUM)

---

## Executive Summary

This is a macOS-only personal tool that automates monthly electricity consumption monitoring across two properties (same E-REDES account, two CPEs), compares tariffs using a live external simulator (tiagofelicia.pt) and a local catalogue, and presents results via a lightweight local web dashboard. The backend pipeline is fully implemented but never run end-to-end in production. The multi-location layer and dashboard are net-new. Research confirms that the chosen stack (FastAPI + Jinja2 + HTMX + Chart.js, files as storage, macOS launchd) is correct for the scope and constraints, with no need for rethinking core architecture.

Two blockers must be resolved before any automated pipeline run is attempted. First, the launchd watcher is 100% non-functional: 21 confirmed TCC permission errors show the plist is calling the system CLT Python (no Full Disk Access) instead of the project venv. Second, the E-REDES session in `state/eredes_storage_state.json` has an expired JWT (exp: 2026-03-22). Neither blocker is architecturally complex — both are single-session fixes — but both must be resolved in Phase 1 or all subsequent work cannot be validated end-to-end.

The dominant design decision confirmed by research is that `external_firefox` is the correct permanent production mode for E-REDES downloads. reCAPTCHA on the portal makes headless Playwright infeasible; this is confirmed by both the storage state cookies and the known behaviour of Chromium with reCAPTCHA. The tool's external dependency risk is concentrated in tiagofelicia.pt, which has four identified failure modes and no fallback currently wired — this must be addressed before the tool can be trusted for monthly decisions. The multi-location refactor is well-understood: three of the five backend modules are already location-agnostic and require no changes.

---

## Key Findings

### Recommended Stack

The new stack layer adds only four Python packages to the existing backend (FastAPI 0.115.x, uvicorn 0.29.x, Jinja2 3.1.x, python-multipart). HTMX and Chart.js are downloaded once and served as local static files — no CDN dependency, no npm, no build step. This aligns with the project's constraint of a macOS-only personal tool. The dashboard is a read-only view over files the pipeline already produces; FastAPI reads them from disk at request time with no database, IPC, or cache layer.

For multi-location configuration, a single `config/system.json` with a top-level `locations` array is the correct pattern (not separate files per location). The `eredes` block at the root is shared across all locations. Each location carries its own `cpe`, `data_dir`, and `pipeline` sub-block. Python 3.11 dataclasses loaded from plain JSON are sufficient — pydantic-settings and dynaconf add dependency weight with no benefit for a static local config.

**Core technologies:**
- FastAPI 0.115.x: HTTP server + Jinja2 templates + StaticFiles — built-in integrations, async, zero adapter needed
- uvicorn 0.29.x: ASGI server — standard FastAPI pairing, zero config for local use
- Jinja2 3.1.x: Server-side HTML rendering — template inheritance keeps layout DRY across pages
- HTMX 2.0.x (local static): Partial HTML updates via hx-get/hx-target — no JS logic for a read-only display tool
- Chart.js 4.4.x (local static): Bar/line charts from inline JSON — CDN-free UMD build, no bundler required
- Python dataclasses + json.load: Config loader — no extra dependency, full type hints, stdlib-only

### Expected Features

All table-stakes dashboard features are Low complexity because the pipeline already produces the underlying data — the dashboard only renders it. The MVP ordering is: per-location selector first (prerequisite), then monthly history chart (core visual), then supplier ranking table (primary output), then savings recommendation with confidence threshold, then data freshness indicator, then year-over-year delta badge, then tiagofelicia vs local catalogue agreement indicator.

**Must have (table stakes):**
- Monthly consumption history chart (stacked bar: vazio / fora de vazio) — core reason to open the tool
- Current supplier ranking table — primary decision output, already computed by pipeline
- Savings recommendation (current vs best, euros/year) — answers "compensa mudar?"
- Per-location view with selector — tool manages two properties; prerequisite for everything else
- Data freshness indicator — user must know if data is current or stale
- Bi-horário / mono-horário split — legally-defined ERSE tariff structure must be surfaced

**Should have (differentiators to build in Phase 4):**
- Year-over-year monthly delta badge — Low complexity, high insight, no new data needed
- tiagofelicia.pt vs local catalogue agreement indicator — validates pipeline reliability
- Recommendation confidence threshold badge — flag when delta is marginal (< 5%)

**Defer to v2+:**
- Side-by-side location comparison — after multi-location is validated end-to-end
- Savings accumulation since switch — requires manual active-supplier input
- Best tariff trajectory chart — requires historical tariff snapshot persistence
- PDF export — adds WeasyPrint/wkhtmltopdf dependency, low priority

**Anti-features (never build):**
- Real-time/daily consumption — E-REDES provides monthly only; Shelly integration is out of scope
- User authentication — localhost personal tool, zero security benefit
- Supplier auto-switching — contractual risk, no public Portuguese supplier API
- ML forecasting — sample too small (< 24 data points/year per location)

### Architecture Approach

The multi-location refactor follows a clean separation: one shared `eredes` block at the config root (session, credentials, browser), N independent `locations` entries each with their own `cpe`, `data_dir`, and `pipeline` paths. Directories nest as `data/{location_id}/` and `state/{location_id}/`. The orchestrator loops locations sequentially (not in parallel) because both use the same Playwright session file — concurrent writes would corrupt it. launchd keeps two plists total (reminder + watcher); CPE routing is handled inside `process_latest_download.py` by extracting the CPE from the XLSX filename pattern `Consumos_PT{CPE}_{timestamp}.xlsx`.

**Major components:**
1. `config/system.json` (extended) — single config file, `locations` array, shared `eredes` block
2. `src/backend/monthly_workflow.py` (refactored) — `run_all_locations()` entry point; `run_workflow(location_config, shared_eredes)` per location
3. `src/backend/process_latest_download.py` (refactored) — loops all locations; `location_for_xlsx()` routes by CPE in filename
4. `src/backend/eredes_download.py` (extended) — new `cpe` param; `eredes_navigation_click_texts` per location for CPE selection UI
5. `src/web/app.py` (new) — FastAPI routes reading pipeline output files; Jinja2 templates; HTMX partials
6. launchd plists (unchanged structurally) — one reminder, one watcher; reload only if log paths change

**Modules requiring NO changes (already location-agnostic):**
- `eredes_to_monthly_csv.py` — purely functional (xlsx_path → output_path)
- `energy_compare.py` — takes consumption CSV, no config coupling
- `tiagofelicia_compare.py` — takes consumption path + contract params, no config coupling
- `eredes_bootstrap_session.py` — once-per-account, not per-location

### Critical Pitfalls

1. **launchd watcher broken (BLOCKER)** — Plist calls system CLT `python3` which has no TCC/FDA access to `~/Documents`. Fix: replace bare `python3` in plist with absolute venv path (e.g. `$(which python3)` in activated venv). May also need FDA grant in System Settings. Evidence: 21 confirmed errors in `state/launchd.process.stderr.log`.

2. **E-REDES session expired (BLOCKER)** — JWT `exp: 1774503078` (2026-03-22) is already expired. Re-run `eredes_bootstrap_session.py` before any pipeline test. Add session age check: if `aat` JWT exp is within 24 hours, abort and prompt re-bootstrap.

3. **external_firefox is the correct permanent architecture** — reCAPTCHA on E-REDES portal (`_GRECAPTCHA` cookies confirmed in storage state) blocks headless Playwright. Do not attempt to make headless work. `external_firefox` mode (user downloads manually, watcher picks up file) is the correct long-term design. Mark `download_mode: headless` as explicitly unsupported.

4. **tiagofelicia.pt has no fallback wired despite being flagged critical** — Four failure modes identified. Three crash loudly (detectable). One fails silently: if the current supplier name in the table changes, `pick_current_result` returns `None` and the report shows no current supplier with no error. Mitigation: wrap `tiagofelicia_compare.py` call in try/except in `monthly_workflow.py`; on failure, generate report using local catalogue only and note the fallback. This is a 15-line change and must be in the first production milestone.

5. **No .gitignore — session credentials at risk** — `state/eredes_storage_state.json` contains live JWT tokens, SimpleSAML cookies, and reCAPTCHA tokens. No `.gitignore` exists. A `git add .` would expose credentials permanently. Create `.gitignore` immediately: `state/`, `data/raw/`, `data/processed/`, `__pycache__/`, `*.pyc`.

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Unblock & Validate End-to-End (Single Location)
**Rationale:** Two confirmed blockers make all other work untestable. The pipeline has never run in production. Fix blockers, then validate with real XLSX before expanding scope.
**Delivers:** A working pipeline for `casa` with real data — first end-to-end proof that the system functions
**Addresses:** Launchd TCC fix, session expiry, .gitignore, requirements.txt
**Avoids:** Pitfall 1 (launchd broken), Pitfall 3 (expired session), Pitfall 10 (credentials in git)
**Key tasks:**
- Fix `.gitignore` immediately (before any git operations)
- Create `requirements.txt` (playwright, openpyxl, fastapi, uvicorn, jinja2)
- Fix launchd plist to use absolute venv Python path (+ FDA grant if needed)
- Re-run bootstrap to refresh E-REDES session
- Run pipeline end-to-end against the three real XLSX files in `data/raw/eredes/`
- Validate XLSX column detection against all three files (Pitfall 5 — heuristic parser)
- Confirm tiagofelicia.pt scraping produces valid output
- Add sanity bounds check: monthly kWh must be 30–1000 for residential

### Phase 2: tiagofelicia.pt Resilience
**Rationale:** The tool cannot be trusted for monthly decisions until the critical dependency has a fallback. This is a small code change with large reliability impact. Do it before adding more features on top of a fragile foundation.
**Delivers:** Pipeline completes and produces a report even when tiagofelicia.pt is unavailable or returns bad data
**Addresses:** Pitfall 2 (silent failures), Pitfall 8 (no fallback), Pitfall 9 (hardcoded waits)
**Key tasks:**
- Wrap tiagofelicia scraper call in try/except; fall back to `energy_compare.py` on any failure
- Validate `total_eur > 0` for every row; validate `len(results) >= 3`
- Validate `current_supplier_result is not None`; warn (not crash) if supplier unmatched
- Replace `wait_for_timeout(4000)` with selector-based DOM wait

### Phase 3: Multi-Location Refactor
**Rationale:** Config and directory structure changes must happen before the dashboard is built — the dashboard depends on location-scoped paths. Do the refactor while the codebase is small and before dashboard routes are written.
**Delivers:** Both `casa` and `apartamento` run through the complete pipeline independently; CPE-based filename routing works
**Uses:** Single `system.json` with `locations` array (STACK.md pattern); nested `data/{id}/` and `state/{id}/` directories
**Implements:** `run_all_locations()` orchestrator; `location_for_xlsx()` CPE router; `eredes_download.py` CPE selection
**Avoids:** Pitfall 6 (multi-CPE wrong data routing), Anti-Patterns 1-4 from ARCHITECTURE.md
**Key tasks:**
- Migrate `config/system.json` to locations array schema
- Create nested directory layout (`data/casa/`, `data/apartamento/`, `state/casa/`, `state/apartamento/`)
- Move existing files to `data/casa/` (Step 2 of migration path from ARCHITECTURE.md)
- Refactor `monthly_workflow.py` → `run_workflow(location_config, shared_eredes)` + `run_all_locations()`
- Refactor `process_latest_download.py` → add `location_for_xlsx()` loop
- Refactor `reminder_job.py` → loop over locations array
- Add `eredes_navigation_click_texts` per location for CPE selection (MEDIUM confidence — portal UI not directly observed)
- Reload launchd plists if log paths change

### Phase 4: Web Dashboard MVP
**Rationale:** Dashboard is read-only over files the pipeline already produces. Build it after the pipeline is reliable and multi-location is validated — otherwise the dashboard shows stale or single-location data.
**Delivers:** Local FastAPI dashboard with per-location history chart, supplier ranking, and savings recommendation
**Uses:** FastAPI 0.115.x + Jinja2 + HTMX 2.0.x + Chart.js 4.4.x (all served locally, no CDN, no build step)
**Implements:** `src/web/app.py` routes; Jinja2 templates with base layout + partials; HTMX location selector
**Avoids:** Anti-features (auth, real-time, ML, dark mode toggle, i18n)
**Key tasks:**
- Install FastAPI, uvicorn, jinja2, python-multipart
- Download HTMX and Chart.js to `src/web/static/js/` (served locally)
- Implement `src/web/app.py` with StaticFiles mount and Jinja2Templates
- Create `base.html`, `index.html`, and HTMX partials for history and ranking
- Per-location selector via HTMX `hx-get` + `hx-target`
- Monthly consumption history stacked bar chart (vazio / fora de vazio)
- Supplier ranking table from pipeline JSON output
- Savings recommendation display with confidence threshold badge
- Data freshness indicator (date of most recent processed CSV)
- Year-over-year monthly delta badge (Low complexity, high value)
- tiagofelicia.pt vs local catalogue agreement indicator

### Phase Ordering Rationale

- Phase 1 before everything: two confirmed blockers make the codebase untestable. No other work is verifiable until the pipeline actually runs.
- Phase 2 before multi-location: the fallback must exist before the orchestrator loops two locations. If tiagofelicia.pt fails mid-run on location 1, it must not abort location 2.
- Phase 3 before dashboard: dashboard routes reference `data/{location_id}/` paths. Building routes before the directory structure is finalised creates throwaway code.
- Phase 4 last: all inputs (pipeline output files, multi-location paths) are stable before any UI is built.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (CPE selection UI):** The E-REDES portal's multi-CPE navigation flow is not directly documented. `eredes_download.py` needs new navigation logic to select the correct CPE before downloading. Needs interactive testing against the live portal. ARCHITECTURE.md flags this as the most uncertain part of the refactor.
- **Phase 3 (apartamento CPE):** The CPE for the second property is a placeholder (`PT000200XXXXXXXXXX`) in ARCHITECTURE.md. Must be confirmed from the E-REDES portal before the second location can be configured.

Phases with well-documented patterns (skip research-phase):
- **Phase 1:** All fixes are diagnosed with evidence. Standard Python venv + launchd + TCC patterns.
- **Phase 2:** tiagofelicia.pt scraper already exists; resilience additions are standard try/except + DOM-wait patterns.
- **Phase 4:** FastAPI + Jinja2 + HTMX + Chart.js stack is well-documented. STACK.md has confirmed code patterns with HIGH confidence from official docs.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | FastAPI/Jinja2 patterns verified from official docs; HTMX and Chart.js version numbers from Aug 2025 training cutoff — verify patch versions before pinning |
| Features | MEDIUM | Domain knowledge from PROJECT.md (HIGH) + Portuguese ERSE market specifics from training data (MEDIUM — no web verification possible) |
| Architecture | HIGH | Decisions based on direct codebase analysis, not speculation. CPE selection UI is the one MEDIUM-confidence element |
| Pitfalls | HIGH | Blockers confirmed with hard evidence (log file, JWT exp timestamp). tiagofelicia.pt failure modes from code inspection |

**Overall confidence:** HIGH for Phases 1–3. MEDIUM for Phase 4 (UI details depend on pipeline output format being stable after Phase 3 refactor).

### Gaps to Address

- **apartamento CPE code:** Placeholder in config schema. Must be retrieved from the E-REDES portal before Phase 3 can be completed. No workaround — the CPE is needed for filename routing.
- **E-REDES multi-CPE portal UX:** No documentation exists for how the portal presents multiple meters under one account. Phase 3 task for CPE selection in `eredes_download.py` requires interactive exploration of the live portal. Time-box to 1 session; if selection is not automatable cleanly, `external_firefox` mode handles it gracefully (user selects CPE manually, filename routing handles the rest).
- **ERSE tariff seasonality:** Tariffs are adjusted annually by ERSE (typically January). The local catalogue's staleness warning (> 90 days old) should be implemented in Phase 4 but the specific ERSE schedule needs validation against current documentation.
- **tiagofelicia.pt current layout:** Web access was blocked during research. The scraper code documents the expected selectors, but they should be verified against the live site before Phase 2 work is considered done.

---

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — project requirements, constraints, key decisions
- `src/backend/` codebase (direct analysis) — module impact assessment, session state, config structure
- `state/launchd.process.stderr.log` — confirmed 21 TCC errors (launchd blocker)
- `state/eredes_storage_state.json` — confirmed expired JWT exp claim (session blocker)
- FastAPI official docs (Jinja2Templates, StaticFiles) — stack patterns
- `.planning/codebase/CONCERNS.md` — prior audit findings

### Secondary (MEDIUM confidence)
- Portuguese ERSE tariff structure and bi-horário rules — training knowledge (Aug 2025 cutoff)
- tiagofelicia.pt selector structure — code inspection (live site not verified during research)
- E-REDES portal multi-CPE UI — inferred from `navigation_click_texts` config hook in codebase
- HTMX 2.0.x and Chart.js 4.4.x version numbers — training knowledge; verify with PyPI/npm before pinning

### Tertiary (LOW confidence)
- `simulador.erse.pt` as alternative comparison target — mentioned in PITFALLS.md as training knowledge; not verified
- E-REDES OpenData portal scope — training knowledge; no public API confirmed

---
*Research completed: 2026-03-28*
*Ready for roadmap: yes*
