# Domain Pitfalls — Monitorização de Eletricidade

**Domain:** Electricity monitoring pipeline with portal scraping + external simulator scraping
**Researched:** 2026-03-28
**Overall Confidence:** HIGH for launchd/macOS (evidence from logs + code), HIGH for XLSX parsing (code + real files), MEDIUM for E-REDES portal behaviour (code + session state), MEDIUM for tiagofelicia.pt (code inspection only — web access blocked during research)

---

## Critical Pitfalls

### Pitfall 1: launchd WatchPaths — python3 is the system CLT interpreter, not the venv

**What goes wrong:** The watcher plist calls `python3` (bare name) which resolves to `/Library/Developer/CommandLineTools/usr/bin/python3`. This interpreter runs as the launchd daemon user, which has no Full Disk Access. It cannot open files inside `~/Documents/AI/...` due to macOS TCC (Transparency, Consent and Control). Result: `[Errno 1] Operation not permitted` on every trigger.

**Evidence:** Confirmed in `state/launchd.process.stderr.log` — 21 consecutive identical errors, one per any file downloaded to `~/Downloads`.

**Why it happens:** macOS launchd agents run with a minimal PATH. `python3` resolves to the CLT shim, not the user's pyenv/homebrew Python. The CLT Python has no FDA grant, and neither does the project directory path.

**Consequences:** The watcher is 100% inoperational right now. Every download to `~/Downloads` triggers a useless process that immediately fails. The pipeline never auto-starts.

**Likelihood:** CERTAIN (already in production failure state)
**Impact:** CRITICAL — the entire automated trigger mechanism is broken

**Prevention / Fix:**
- Replace `python3` in the plist with the absolute path to the correct interpreter: e.g. `/Users/ricmag/.pyenv/shims/python3` or the output of `which python3` in the activated venv.
- Grant Full Disk Access to the specific Python binary in System Settings > Privacy & Security > Full Disk Access, OR keep the project outside ~/Documents (using a path not protected by TCC — though `~/Downloads` itself is user-accessible, the script it tries to read is under `~/Documents`).
- Preferred pattern: use a wrapper shell script as the plist entry point, which sources the venv activate before calling python. The shell script itself can be granted FDA or placed in an FDA-exempt path.

**Detection:** Check `state/launchd.process.stderr.log` for `[Errno 1] Operation not permitted`.

---

### Pitfall 2: tiagofelicia.pt DOM changes break the entire comparison engine silently

**What goes wrong:** The scraper depends on: (a) a button with text "Simulacao Completa" (emoji included: `📝`), (b) form IDs `#potencia`, `#ciclo`, `#kwh_S`, `#kwh_V`, `#kwh_F`, (c) a `<table><tbody><tr><td>` structure with a specific cell layout (supplier+plan+product type in cell 0, total EUR in cell 1, energy rate in cell 2, power rate in cell 3), (d) supplier names matching what the user configured.

**Why it happens:** tiagofelicia.pt is a personal site maintained by a private individual. No API, no versioning, no stability guarantee. Any frontend refresh (new CSS framework, React migration, field renaming) breaks one or more of these selectors.

**Consequences:** Three distinct silent failure modes:
1. Button text changes → `page.click()` throws `TimeoutError` → pipeline crashes loudly (detectable)
2. Form IDs change → `page.select_option("#potencia")` fails → crashes loudy (detectable)
3. Table structure changes → `parse_results_table` returns partial data OR `euros_to_float` raises `ValueError` → crashes loudly
4. Supplier name changes in table (e.g. "MEO" → "Meo Energia") → `pick_current_result` returns `None`, `needs_change` is None, report silently shows no current supplier — **this fails silently and produces a misleading report**

**Likelihood:** MEDIUM (site appears stable since CONCERNS.md was written, but unverified)
**Impact:** HIGH — the main comparison output is garbage without catching it

**Prevention / Fix (partially missing):**
- Already in place: `RuntimeError` raised when table extraction yields zero rows.
- Still needed: Validate `total_eur > 0` for every row. Validate that `len(results) >= 3` (fewer suppliers than expected = layout change). Validate `current_supplier_result is not None` and raise a warning (not crash) if the current supplier cannot be matched.
- Add a snapshot/hash of the page DOM structure after each successful run. Alert if it changes.
- Implement the fallback to the local catalogue (`energy_compare.py`) when scraping fails.

---

### Pitfall 3: E-REDES session expiry — JWT has a 90-minute TTL

**What goes wrong:** The `aat` JWT in `state/eredes_storage_state.json` has `exp: 1774503078` (2026-03-22 ~13:44 UTC). The `PHPSESSID` cookie has `expires: 1774503195` (same window). Both expire within ~90 minutes of the bootstrap. The `SimpleSAML` session has `expires: -1` (session cookie, cleared when browser closes). The `_GRECAPTCHA` cookie lasts ~1 year.

**Why it happens:** The E-REDES Balcao Digital uses a multi-layer auth stack: SimpleSAML (SSO federated auth), a short-lived JWT (`aat`), and a PHP session. The `storage_state.json` captures a moment-in-time snapshot. When replayed days or months later, only the GRECAPTCHA cookie is still valid.

**Consequences:** The headless download mode calls `assert_logged_in(page)` which checks for "Bem-vindo ao Balcão Digital" in the body text. If the session has expired, the portal likely shows a login page — the assert will catch this and raise `RuntimeError("Sessao E-REDES invalida ou expirada...")`. This is a **loud** failure (crash + notification). However, the current `download_mode` is `external_firefox` (not headless), so `assert_logged_in` is never called, and the user has to notice themselves.

**Likelihood:** CERTAIN (session in state file is already expired as of 2026-03-28)
**Impact:** MEDIUM — download fails, user gets macOS notification, must re-bootstrap manually. Not a silent failure.

**Prevention / Fix:**
- The bootstrap process (`eredes_bootstrap_session.py`) must be re-run before each automated download. Consider adding a session age check: if `aat` JWT `exp` claim is within 24 hours, abort and prompt re-bootstrap.
- The `external_firefox` mode is the current fallback: the user manually logs in and downloads, and the watcher picks it up. This is actually the correct operating mode while the headless mode is not viable.
- For headless to work: needs a way to handle the SimpleSAML redirect + possible reCAPTCHA challenge. This is a significant engineering problem (see Pitfall 4).

---

### Pitfall 4: reCAPTCHA on the E-REDES portal blocks headless Playwright

**What goes wrong:** The `eredes_storage_state.json` reveals `_GRECAPTCHA` cookies on `www.google.com` — confirming the portal uses reCAPTCHA. The bootstrap captures these, but reCAPTCHA challenges are dynamic and session-bound. A headless Chromium replaying an old storage state will likely trigger a new reCAPTCHA challenge on navigation.

**Why it happens:** reCAPTCHA v2/v3 uses browser fingerprinting signals (canvas, WebGL, mouse movement, browser version) to score requests. Headless Chromium without stealth patches scores poorly. Google's reCAPTCHA service also checks if the challenge token is stale.

**Consequences:** Headless download mode (`download_mode: headless`) is not viable for the E-REDES portal without additional anti-detection measures. The current default is `external_firefox` which bypasses this entirely.

**Likelihood:** HIGH (reCAPTCHA confirmed in storage state; headless Chromium is a known reCAPTCHA trigger)
**Impact:** MEDIUM — affects only the unimplemented headless path; current `external_firefox` mode is unaffected

**Prevention / Fix:**
- The `external_firefox` mode is the correct long-term architecture for this portal: open a real browser, let the user download, watch for the file. Do not attempt to make the headless path work through reCAPTCHA — this is an arms race with poor odds.
- If headless is ever needed: use `playwright-stealth` (Python port) + `p.chromium.launch_persistent_context()` with a real user data directory, and pre-warm the browser state from a real session.
- Mark `download_mode: headless` as explicitly unsupported for E-REDES in the README.

---

## Moderate Pitfalls

### Pitfall 5: E-REDES XLSX format — heuristic column detection is fragile

**What goes wrong:** `eredes_to_monthly_csv.py` uses two layers of heuristics: (1) `pick_sheet` tries "Leituras" then "Consumos" then falls back to the first sheet, (2) `detect_data_start_row` scans the first 40 rows for "Data"/"Hora" headers, (3) `extract_date_time_and_kwh` tries columns [7, 6, 3, 2] as power candidates in order.

The actual XLSX files in `data/raw/eredes/` show two naming conventions: the 2025 file uses `Consumos_CPE_startdate_enddate_timestamp.xlsx` while the 2026 files use `Consumos_CPE_timestamp.xlsx`. This suggests the export interface already changed at least once.

**Why it happens:** E-REDES does not publish an XLSX schema. The export is generated server-side from their data warehouse. Column positions or sheet names may change with portal upgrades.

**Consequences:** Silent wrong results if a new column is inserted before column 7 (power moves to column 8, code reads column 7 which is now a different field, produces incorrect kWh values with no error). The `power_kw * 0.25` conversion would produce a plausible-looking number from an unrelated field.

**Likelihood:** LOW-MEDIUM (format has been stable for 2025-2026 data so far; but confirmed one change already in filename convention)
**Impact:** HIGH (silently wrong energy consumption = wrong tariff recommendation)

**Prevention / Fix:**
- Run the parser against all three available XLSX files now before any other work — this is the immediate validation milestone.
- Add a sanity check: monthly `total_kwh` should be between 30 and 1000 kWh for a residential installation. If outside this range, abort with a loud error.
- Add explicit column name detection: after finding the header row, map column indices by name ("Potência Ativa Registada", "Potência Medida", etc.) rather than positional guessing.
- Zero test coverage on this module is the root problem — add at least one pytest parametrised test per XLSX file in `data/raw/eredes/`.

---

### Pitfall 6: Multi-CPE selection is not implemented — same-session download will download the wrong meter

**What goes wrong:** The current `eredes_download.py` navigates to `https://balcaodigital.e-redes.pt/consumptions/history` and immediately proceeds to click "Exportar Excel". The portal defaults to one CPE (whichever was last active). For the second property, the user must manually select the other CPE before downloading. No automation exists for CPE selection.

**Why it happens:** This is explicitly listed as an "Active" requirement in PROJECT.md, not yet built.

**Consequences:** In `external_firefox` mode (current default), the user must manually navigate to the correct CPE before downloading. With the watcher watching `~/Downloads`, if the user downloads the wrong CPE first, the pipeline will process and store wrong data for the wrong location.

**Likelihood:** HIGH (architecturally unresolved)
**Impact:** HIGH (wrong data processed for wrong local; stored results mix up the two properties)

**Prevention / Fix:**
- Before implementing multi-CPE, establish a per-CPE naming convention. The E-REDES filename already includes the CPE (`Consumos_PT0002000084968079SX_...`). The watcher/pipeline can use the CPE code in the filename to route to the correct location.
- The `local_download_glob` is already `Consumos_*.xlsx` — extend it to per-location patterns like `Consumos_PT0002000084968079SX_*.xlsx` and `Consumos_PT00..._*.xlsx`.
- The pipeline's file routing must be refactored before processing both locations.

---

### Pitfall 7: launchd watcher fires for every file in ~/Downloads, not just E-REDES files

**What goes wrong:** `WatchPaths` triggers on any inotify-equivalent event in `~/Downloads` — every browser download, every file move. The `process_latest_download.py` script is invoked, looks for `Consumos_*.xlsx`, and exits cleanly if nothing matches. This is functionally harmless but creates a continuous background noise of launchd invocations.

**More serious variant:** If the user has any XLSX file called `Consumos_something.xlsx` from an unrelated source in `~/Downloads`, it will be picked up and processed as E-REDES data. `eredes_to_monthly_csv.py` will attempt parsing, likely fail with `ValueError: Nao foi possivel localizar a linha de cabecalho`, and the pipeline crashes.

**Likelihood:** LOW for false-positive XLSX; HIGH for noisy triggering
**Impact:** LOW for noisy triggering (wastes ~1 second per event); MEDIUM for false-positive XLSX (pipeline crash, macOS error notification)

**Prevention / Fix:**
- The `local_download_glob` filter `Consumos_*.xlsx` is already a good filter.
- Add a secondary check in `process_latest_download.py`: after finding the file, verify the CPE code in the filename matches an expected pattern (`PT[0-9]{18}[A-Z]{2}`) before processing.
- Accept the noisy triggering as a known cost of WatchPaths on `~/Downloads`.

---

### Pitfall 8: tiagofelicia.pt — no fallback implemented despite being flagged as critical dependency

**What goes wrong:** PROJECT.md explicitly states "preferir fallback para catálogo local se o site estiver indisponível" but `monthly_workflow.py` runs `tiagofelicia_compare.py` with no try/except around the Playwright call. A network error, DNS failure, or site downtime will propagate as an uncaught exception that terminates the workflow.

**Why it happens:** The fallback to `energy_compare.py` (local catalogue) is planned but not implemented.

**Consequences:** Monthly workflow fails entirely if tiagofelicia.pt is unreachable, even though the XLSX was successfully downloaded and parsed.

**Likelihood:** LOW (site appears maintained), but CERTAIN to happen eventually
**Impact:** HIGH (whole pipeline stops; no report generated; user gets no recommendation that month)

**Prevention / Fix:**
- Wrap the `tiagofelicia_compare.py` call in a try/except in `monthly_workflow.py`. On failure: log the error, generate the report using the local catalogue only, note in the report that the tiagofelicia.pt comparison was unavailable.
- This is a straightforward 15-line change and should be in the first production milestone.

---

### Pitfall 9: Hardcoded 4-second waits in tiagofelicia.pt scraper accumulate per month

**What goes wrong:** Each call to `run_simple_simulation` and `run_bi_simulation` has `page.wait_for_timeout(4000)`. For N months of history, that is `N * 2 * 4 = 8N seconds` of unconditional waiting, plus the initial `wait_until="networkidle"` on page load.

With 11 months of history (available in the 2025 XLSX): `11 * 8 = 88 seconds` minimum. Add page load, form interaction, and network latency: realistically 2-3 minutes per full analysis.

**Why it happens:** The 4-second wait is a proxy for "table finished reacting to input". It is not waiting for a DOM selector to appear — it is a blind sleep.

**Consequences:** Not a correctness issue, but makes the monthly workflow slow and fragile to network latency spikes. If the table loads in <4 seconds, the wait is wasted. If the table loads in >4 seconds (slow network), the scraper reads stale data from the previous simulation.

**Likelihood:** CERTAIN (already in the code)
**Impact:** LOW-MEDIUM (slow but correct when network is fast; potentially wrong when network is slow)

**Prevention / Fix:**
- Replace `wait_for_timeout(4000)` with `page.wait_for_function("document.querySelector('table tbody tr td') !== null && document.querySelector('table tbody tr td').textContent.trim().length > 0")` or a similar selector-based wait.
- This requires knowing what DOM change signals "table updated" — needs validation against the live site.

---

## Minor Pitfalls

### Pitfall 10: Session state file not in .gitignore — credentials at risk

**What goes wrong:** `state/eredes_storage_state.json` contains live JWT tokens, session cookies (SimpleSAML, PHPSESSID, aat), and a reCAPTCHA token. No `.gitignore` exists. A `git add .` or `git commit -A` would include this file in version history, permanently exposing credentials even after deletion.

**Likelihood:** MEDIUM (no .gitignore is a confirmed fact; depends on user's git habits)
**Impact:** HIGH (E-REDES account compromise)

**Prevention / Fix:** Create `.gitignore` immediately with: `state/`, `data/raw/`, `data/processed/`, `__pycache__/`, `*.pyc`. Verify `state/` is not already in git history with `git log --all --full-history -- state/`.

---

### Pitfall 11: Date/time parsing assumes YYYY/MM/DD HH:MM format — brittle

**What goes wrong:** `eredes_to_monthly_csv.py` line 115: `datetime.strptime(f"{row_date} {row_time}", "%Y/%m/%d %H:%M")`. This format is hardcoded. If E-REDES changes the date format (e.g. to ISO 8601 `YYYY-MM-DD`, or to Portuguese locale `DD/MM/YYYY`), `strptime` raises `ValueError` on the first data row, which propagates silently (the `if extracted is None: continue` guard would not catch it — the `ValueError` is raised inside `strptime`, not returned as None).

**Likelihood:** LOW (format has been stable in available files)
**Impact:** HIGH (all rows skipped or crash; output CSV is empty or missing months)

**Prevention / Fix:** Wrap the `strptime` call in a try/except inside `extract_date_time_and_kwh`, return `None` on parse failure, and add a counter for failed rows. If > 10% of rows fail to parse, abort with a loud error.

---

### Pitfall 12: osascript f-string injection in notify_mac

**What goes wrong:** `notify_mac(title, message)` constructs `f'display notification "{message}" with title "{title}"'`. If either string contains a double-quote character, the AppleScript command is malformed and `osascript` returns an error. The `check=False` in `subprocess.run` means the error is silently swallowed.

**Likelihood:** LOW (messages are hardcoded literals)
**Impact:** LOW (notification silently not sent; pipeline continues)

**Prevention / Fix:** Escape quotes: `message.replace('"', '\\"')`. Low priority but trivially fixed.

---

### Pitfall 13: Deduplication tracker uses mtime+size — fragile against clock skew

**What goes wrong:** `process_latest_download.py` stores `{path, mtime, size}` to detect already-processed files. The `mtime` is the filesystem modification time at the moment of detection. If the user downloads the same period's data twice (E-REDES allows re-downloading), the second file will have a different timestamp and will be processed again, overwriting the processed CSV for that month.

**Likelihood:** LOW (re-download is uncommon but not impossible)
**Impact:** LOW (processed CSV overwritten with identical data; no data loss)

**Prevention / Fix:** Add a content hash (SHA-256) of the XLSX file to the tracker. Same hash = already processed, regardless of filename or mtime.

---

### Pitfall 14: macOS launchd StartCalendarInterval does not fire if machine is asleep

**What goes wrong:** The monthly reminder plist uses `StartCalendarInterval` for day 1 at 09:00. If the Mac Mini is asleep at that exact time, launchd will fire the job as soon as the machine wakes up next — but only within the same day. If it is still day 1 when the machine wakes, the reminder fires. If it is now day 2, the event is skipped entirely until next month.

**Likelihood:** LOW (Mac Mini M4 Pro is described as a server — likely always on)
**Impact:** LOW (reminder not sent; user must remember manually that month)

**Prevention / Fix:** No action needed given the Mac Mini is a server. Document the behaviour for future reference.

---

## Phase-Specific Warnings

| Phase / Topic | Likely Pitfall | Mitigation |
|---------------|---------------|------------|
| End-to-end validation with real XLSX | Heuristic column detection may fail on 2026 format (filenames already differ) | Run parser against all 3 files before any other work |
| launchd watcher fix | Wrong Python interpreter + TCC denial is confirmed broken | Use absolute path to venv Python; may need FDA grant |
| tiagofelicia.pt integration | No fallback; hardcoded waits; supplier name mismatch | Add try/except + fallback before marking integration as done |
| Multi-CPE support | No CPE routing logic; second property download risks overwriting first | Implement CPE-based filename routing before any multi-local work |
| Headless E-REDES download | reCAPTCHA + short-lived JWT makes headless infeasible | Accept `external_firefox` as the production mode; do not pursue headless |
| Session bootstrap | JWT expires in ~90 minutes; session in state/ is already expired | Always re-bootstrap before testing automated download |
| Dashboard (FastAPI) | No data validation layer exists; wrong kWh values will be displayed without warning | Add sanity bounds checks in the pipeline before building UI |

---

## Official E-REDES API Alternatives

**Verdict: No public API exists. The official alternative is the ERSE simulator.**

**E-REDES:** No official REST API is documented at developer.e-redes.pt or in any public ERSE regulatory filing. The portal (`balcaodigital.e-redes.pt`) is the only interface for consumption data access by end users. The E-REDES OpenData portal (`opendata.e-redes.pt`) provides aggregate network data, not per-installation consumption. [Confidence: MEDIUM — verified from code inspection and storage state analysis; web access blocked during research]

**ERSE Simulador:** ERSE (Entidade Reguladora dos Serviços Energéticos) operates a simulator at `simulador.erse.pt`. This is a more stable and officially maintained alternative to tiagofelicia.pt as it is operated by the regulator. However, it may have different UX/API structure and would require its own scraper. [Confidence: MEDIUM — based on training knowledge]

**Data Mediator approach:** For multi-installation consumption data, ERSE regulations require distribuidores to provide data on request via the "Comparador de Tarifários" infrastructure. This is a regulatory right, not a technical API. In practice it means the user can request historical data export — which is what the E-REDES portal provides via the XLSX export. There is no push/pull API.

**Recommendation:** Accept the portal scraping + `external_firefox` mode as the correct long-term architecture for E-REDES data. Do not invest engineering effort in headless automation of the E-REDES portal. For the comparison engine, consider adding `simulador.erse.pt` as a secondary scraping target to have a regulator-maintained fallback alongside tiagofelicia.pt.

---

## Sources

- Codebase analysis: `src/backend/eredes_download.py`, `src/backend/tiagofelicia_compare.py`, `src/backend/eredes_to_monthly_csv.py`, `src/backend/eredes_bootstrap_session.py`
- Confirmed evidence: `state/launchd.process.stderr.log` (21 TCC errors), `state/eredes_storage_state.json` (expired JWT exp claim)
- Configuration: `config/system.json`, `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist`
- Existing analysis: `.planning/codebase/CONCERNS.md` (2026-03-28 audit)
- macOS launchd TCC behaviour: HIGH confidence based on Apple Platform Security documentation (training knowledge, consistent with error log evidence)
- E-REDES API existence: MEDIUM confidence (no web access during research; based on training knowledge of Portuguese utility regulatory environment)
