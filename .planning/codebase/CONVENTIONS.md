# Coding Conventions

**Analysis Date:** 2026-03-28

## Naming Patterns

**Files:**
- `snake_case` throughout: `energy_compare.py`, `eredes_to_monthly_csv.py`, `tiagofelicia_compare.py`
- Descriptive names that reflect the module's single responsibility
- No abbreviations (full words: `monthly_workflow`, not `mwf`)

**Functions:**
- `snake_case` for all functions: `load_monthly_consumption()`, `convert_xlsx_to_monthly_csv()`, `build_parser()`
- Verb-noun pattern for actions: `load_*`, `convert_*`, `run_*`, `build_*`, `resolve_*`, `write_*`, `notify_*`
- Boolean-returning functions use interrogative prefix: `is_daily_cycle_vazio()`, `is_complete_month()`

**Variables:**
- `snake_case` throughout: `year_month`, `total_kwh`, `storage_state_path`
- Domain-specific names in Portuguese: `vazio_kwh`, `fora_vazio_kwh`, `tarifarios`
- Loop variables are short but descriptive: `row`, `tariff`, `item`
- Path variables always use `_path` suffix: `config_path`, `output_path`, `status_path`

**Types and Dataclasses:**
- `PascalCase` for dataclasses: `MonthlyConsumption`, `Tariff`
- Constants in `UPPER_SNAKE_CASE`: `HOME_URL`, `SITE_URL`, `LISBON`

**JSON/Config keys:**
- `snake_case` for all JSON config keys: `current_tariff_id`, `energy_simple`, `fixed_daily_power`
- Domain terms in Portuguese: `vazio`, `fora_vazio`, `tarifario`

## Code Style

**Formatting:**
- No formatter config file detected (no `.prettierrc`, `ruff.toml`, `.flake8`, `pyproject.toml`)
- Style is manually consistent across all modules: 4-space indentation, blank lines between functions
- Line length appears to target ~100 characters (some lines reach ~110)

**Type Annotations:**
- All function signatures are fully annotated: parameters and return types
- `from __future__ import annotations` at the top of every module (deferred evaluation)
- `typing.Any` used for config dicts and flexible JSON payloads
- Union types use modern `X | Y` syntax: `float | None`, `Path | None`, `dict[str, Any] | None`
- Return type `int` for all `main()` functions
- Collections use lowercase generics: `list[MonthlyConsumption]`, `dict[str, Any]`

**Frozen Dataclasses:**
- Core domain objects are `@dataclass(frozen=True)`: `MonthlyConsumption`, `Tariff`
- Computed properties exposed as `@property` on dataclasses

## Import Organization

**Order (consistent across all modules):**
1. `from __future__ import annotations` (always first line)
2. Blank line
3. Standard library imports (alphabetical): `argparse`, `csv`, `json`, `pathlib`, ...
4. Blank line
5. Third-party imports: `openpyxl`, `playwright`
6. Blank line
7. Local intra-package imports: `from energy_compare import ...`, `from eredes_download import ...`

**Example from `monthly_workflow.py`:**
```python
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from eredes_download import download_latest_xlsx
from eredes_to_monthly_csv import convert_xlsx_to_monthly_csv
from tiagofelicia_compare import analyse_with_tiago
```

**Path Aliases:**
- None. All imports are by module name or absolute standard library paths.
- Intra-package imports use bare module names (modules run from `src/backend/` working directory).

## Error Handling

**Strategy:**
- Raise `ValueError` for invalid/missing data (config fields, CSV columns, empty files)
- Raise `RuntimeError` for operational failures (session expired, file not found, download failed, no results from web scraping)
- `PlaywrightTimeoutError` caught and re-raised as `RuntimeError` with a user-facing message in Portuguese
- Errors bubble up to `main()` which lets them propagate to the process exit code
- In `monthly_workflow.py` and `process_latest_download.py`, exceptions in the workflow body are caught with a broad `except Exception as exc`, write an error status JSON to disk, optionally send a macOS notification, then re-raise

**Pattern — workflow top-level error handling:**
```python
try:
    # ... pipeline steps ...
    return status
except Exception as exc:
    status = {
        "status": "error",
        "generated_at": datetime.now().isoformat(),
        "error": str(exc),
    }
    write_status(status_path, status)
    if pipeline.get("notify_on_completion", False):
        notify_mac("Eletricidade", f"Falha no job mensal: {exc}")
    raise
```

**Pattern — validation at load time:**
```python
missing = required.difference(reader.fieldnames or [])
if missing:
    missing_str = ", ".join(sorted(missing))
    raise ValueError(f"Faltam colunas no CSV de consumo: {missing_str}")
```

**Error messages:** written in Portuguese (user-facing context), matching the project's locale.

## Logging

**Framework:** `print()` to stdout only — no logging framework.

**Patterns:**
- `main()` functions print the final JSON result: `print(json.dumps(result, indent=2, ensure_ascii=True))`
- Operational progress messages printed in Portuguese: `print("Browser aberto em modo assistido...")`
- No log levels, no timestamps in stdout output
- macOS notifications sent via `osascript` for user-visible events (job completion, errors)
- Machine-readable status written to `state/monthly_status.json` as structured JSON

## Comments

**When to Comment:**
- Inline comments explain non-obvious behaviour, especially around the Playwright portal automation
- Single comment in `eredes_download.py` documents why a `PlaywrightTimeoutError` is silently ignored during page load (portal-specific quirk):
  ```python
  # The E-REDES portal may hold long-lived network requests on the security page.
  ```
- No docstrings on functions — naming and type annotations are considered self-documenting

**JSDoc/TSDoc:** Not applicable (Python codebase).

## Function Design

**Size:** Functions are concise and single-purpose. The longest meaningful function is `download_latest_xlsx()` at ~90 lines, which handles three download modes — all others are under 40 lines.

**Parameters:**
- `Path` objects passed (not raw strings) for all file system operations
- Config dicts (`dict[str, Any]`) passed from caller rather than re-loaded inside helpers
- Optional parameters use `= None` with `| None` type: `alerts_path: Path | None = None`

**Return Values:**
- Pure data functions return typed dataclasses or typed dicts
- Pipeline functions return `dict[str, Any]` with a `"status"` key (`"ok"` / `"error"` / `"skipped"`)
- `main()` always returns `int` (0 for success); launched with `raise SystemExit(main())`

## Module Design

**Exports:**
- No `__all__` declarations; all public functions are importable by name
- Each module exposes one primary function (the "verb" of the module): `analyse()`, `convert_xlsx_to_monthly_csv()`, `download_latest_xlsx()`, `run_workflow()`, `process_latest_download()`, `run_reminder()`

**Barrel Files:** None. No `__init__.py` re-exports — the `__init__.py` in `src/backend/` is empty.

**Module Entry Point Pattern (consistent in every module):**
```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument(...)
    return parser

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = primary_function(Path(args.x))
    print(json.dumps(result, ...))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```
Every module is independently executable as a CLI script and importable as a library.

## Configuration

**Config loading pattern (duplicated across modules):**
```python
def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def project_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parent.parent

def resolve_path(project_root: Path, relative_path: str) -> Path:
    return (project_root / relative_path).resolve()
```
This trio (`load_config`, `project_root_from_config`, `resolve_path`) is copy-pasted into `monthly_workflow.py`, `eredes_download.py`, `reminder_job.py`, `process_latest_download.py`, and `install_launch_agent.py`.

**JSON output:**
- All JSON written with `json.dumps(payload, indent=2, ensure_ascii=True)` + trailing newline
- `ensure_ascii=True` is consistent throughout to avoid encoding issues in log files

---

*Convention analysis: 2026-03-28*
