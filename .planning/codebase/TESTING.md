# Testing Patterns

**Analysis Date:** 2026-03-28

## Test Framework

**Runner:**
- Not configured. No test framework is installed or referenced.
- No `pytest`, `unittest`, `jest`, or any other test runner found.
- No config files: no `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`.

**Assertion Library:**
- None.

**Run Commands:**
```bash
# No test commands available — no tests exist.
```

## Test File Organization

**Location:**
- No test files exist in the project.
- No `tests/` directory.
- No files matching `test_*.py`, `*_test.py`, or `*.spec.*`.

**Naming:**
- Not established.

**Structure:**
```
(no test directory structure)
```

## Test Structure

No tests have been written. The codebase has no test suite.

## Mocking

**Framework:** Not applicable — no tests.

**What currently requires mocking (for future tests):**
- `playwright.sync_api.sync_playwright` — used in `tiagofelicia_compare.py` and `eredes_download.py` for browser automation
- `subprocess.run` — used in `eredes_download.py` and `reminder_job.py` for `osascript` macOS notifications
- `time.sleep` / `time.time` — used in `eredes_download.py` polling loops
- File I/O via `pathlib.Path` — all modules read/write files directly without injection

## Fixtures and Factories

**Test Data:**
- No fixtures defined.
- Sample/example data files exist in `config/` and `data/processed/` that could serve as test fixtures:
  - `config/tarifarios.exemplo.json` — sample tariff catalogue
  - `config/alertas.exemplo.json` — sample alert config
  - `config/alertas.exemplo.yaml` — YAML variant
  - `config/tarifarios.exemplo.yaml` — YAML variant
  - `data/processed/consumo_mensal.exemplo.csv` — sample monthly consumption CSV
  - `data/processed/consumo_mensal_atual.csv` — real processed data (11 months)

**Location:**
- Example data: `config/*.exemplo.*` and `data/processed/consumo_mensal.exemplo.csv`
- Real data: `data/processed/consumo_mensal_atual.csv`, `data/processed/analise_tiagofelicia_atual.json`

## Coverage

**Requirements:** None enforced.

**View Coverage:**
```bash
# No coverage tooling configured.
```

## Test Types

**Unit Tests:**
- Not present. High-value targets for unit tests:
  - `src/backend/energy_compare.py` — pure functions with no I/O side effects:
    - `is_daily_cycle_vazio()` (timezone/DST-sensitive logic)
    - `annual_cost_for_tariff()` (financial calculation)
    - `seasonal_summary()` (aggregation logic)
    - `recommendation_text()` (threshold logic)
    - `load_monthly_consumption()` (CSV parsing with validation)
    - `load_tariffs()` (JSON parsing with validation)
  - `src/backend/eredes_to_monthly_csv.py`:
    - `is_complete_month()` (month-end boundary logic)
    - `extract_date_time_and_kwh()` (row parsing with fallback candidates)
    - `detect_data_start_row()` (header detection)

**Integration Tests:**
- Not present. Would require real or mocked Playwright sessions for:
  - `src/backend/tiagofelicia_compare.py` — scrapes live website
  - `src/backend/eredes_download.py` — automates E-REDES portal

**E2E Tests:**
- Not applicable at this stage.

## Common Patterns

**Async Testing:**
- Not applicable — all code is synchronous. Playwright used in sync mode (`sync_playwright`).

**Error Testing:**
- Not applicable — no tests. Functions raise `ValueError` and `RuntimeError` with specific messages; these are well-suited for `pytest.raises()` assertions if tests are added.

## Testing Gap Summary

The codebase has **zero test coverage**. The most critical gaps, ranked by risk:

1. `is_daily_cycle_vazio()` in `src/backend/eredes_to_monthly_csv.py` — timezone/DST boundary logic that determines vazio/fora-vazio classification; silent errors would corrupt all financial comparisons.

2. `annual_cost_for_tariff()` in `src/backend/energy_compare.py` — financial calculation at the core of supplier recommendations.

3. `extract_date_time_and_kwh()` in `src/backend/eredes_to_monthly_csv.py` — fragile row-parsing logic with multiple column-index fallback candidates; breaks silently if E-REDES changes the XLSX layout.

4. `load_monthly_consumption()` and `load_tariffs()` in `src/backend/energy_compare.py` — input validation; if validation is wrong, downstream calculations produce bad results without any error.

5. `process_latest_download()` in `src/backend/process_latest_download.py` — idempotency logic (file signature tracker); a regression would cause double-processing.

## Recommended Test Setup

If tests are added, the natural framework is `pytest` with `pytest-mock` for patching:

```bash
pip install pytest pytest-mock
```

Suggested structure:
```
tests/
  unit/
    test_energy_compare.py
    test_eredes_to_monthly_csv.py
    test_tiagofelicia_compare.py
  fixtures/
    consumo_mensal.csv      # copy from data/processed/consumo_mensal.exemplo.csv
    tarifarios.json         # copy from config/tarifarios.exemplo.json
    alertas.json            # copy from config/alertas.exemplo.json
```

Example pattern for pure function tests (no mocking needed):
```python
from pathlib import Path
from src.backend.energy_compare import load_monthly_consumption, annual_cost_for_tariff

def test_load_monthly_consumption_missing_columns(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("year_month,total_kwh\n2025-01,100\n")
    with pytest.raises(ValueError, match="Faltam colunas"):
        load_monthly_consumption(bad_csv)
```

---

*Testing analysis: 2026-03-28*
