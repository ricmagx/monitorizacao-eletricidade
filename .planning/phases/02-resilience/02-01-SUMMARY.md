---
phase: 02-resilience
plan: 01
subsystem: backend-resilience
tags: [pytest, fallback, resilience, tiagofelicia, energy-compare]
dependency_graph:
  requires: []
  provides: [pytest-infra, res-01-fallback, res-03-supplier-not-found]
  affects: [monthly_workflow, tiagofelicia_compare]
tech_stack:
  added: [pytest, pytest.ini]
  patterns: [try/except fallback, graceful degradation, TDD red-green]
key_files:
  created:
    - pytest.ini
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_tiagofelicia_fallback.py
    - tests/test_supplier_missing.py
    - config/tarifarios.json
  modified:
    - config/system.json
    - src/backend/monthly_workflow.py
    - src/backend/tiagofelicia_compare.py
decisions:
  - render_report refactored with dual-path rendering (tiagofelicia vs local_catalog) because the two analysis structures are incompatible
  - test files mock convert_xlsx_to_monthly_csv to avoid openpyxl dependency on CSV fixtures (deviation auto-fixed)
metrics:
  duration_seconds: 315
  completed_date: "2026-03-29"
  tasks_completed: 2
  files_changed: 8
requirements: [RES-01, RES-03]
---

# Phase 02 Plan 01: Resilience — Fallback tiagofelicia + Supplier Not Found Summary

**One-liner:** Fallback automático para catálogo local (tarifarios.json) quando tiagofelicia.pt inacessível, com campo `supplier_not_found` e aviso explícito no relatório quando o fornecedor actual não tem correspondência no simulador.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Infraestrutura pytest + catálogo local | dc315f7 | pytest.ini, tests/__init__.py, tests/conftest.py, config/tarifarios.json, config/system.json |
| 2 (RED) | Testes falhar para RES-01 e RES-03 | 45a312f | tests/test_tiagofelicia_fallback.py, tests/test_supplier_missing.py |
| 2 (GREEN) | Implementação fallback + supplier_not_found | f5ef7f0 | src/backend/monthly_workflow.py, src/backend/tiagofelicia_compare.py |

## Decisions Made

1. `render_report()` refactorizada com dois ramos independentes: `is_local_catalog` usa a estrutura de `energy_compare.analyse()` (top_3_suppliers, change_recommendation), ramo normal usa `history_summary` de `tiagofelicia_compare`. As duas estruturas são incompatíveis — sem este branching o render crashava em fallback.

2. Os testes mockam `convert_xlsx_to_monthly_csv` para copiar o CSV de fixture directamente para o `processed_csv_path`, evitando a dependência do openpyxl em fixtures que já são CSV.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Testes da plan usavam sample_csv directamente como input_xlsx**
- **Found during:** Task 2 RED phase (primeiro run dos testes)
- **Issue:** O plan passava `input_xlsx=sample_csv` onde `sample_csv` é um CSV, mas `run_workflow` chama `convert_xlsx_to_monthly_csv(xlsx_path, ...)` que usa openpyxl — que rejeita ficheiros .csv
- **Fix:** Testes actualizado para mock `convert_xlsx_to_monthly_csv` com `side_effect=lambda src, dst, **kw: shutil.copy(sample_csv, dst)`
- **Files modified:** tests/test_tiagofelicia_fallback.py, tests/test_supplier_missing.py
- **Commit:** 45a312f (RED), f5ef7f0 (GREEN mantém o mock)

**2. [Rule 1 - Bug] render_report() crashava em modo local_catalog**
- **Found during:** Task 2 GREEN phase (análise da função)
- **Issue:** `render_report` acedia `analysis["history_summary"]` e `analysis["history"]` directamente (linha 35-37), mas `energy_compare.analyse()` não produz essas chaves
- **Fix:** `render_report` refactorizada com branching `is_local_catalog` — ramo local usa `top_3_suppliers`/`change_recommendation`, ramo normal usa `history_summary`/`history`
- **Files modified:** src/backend/monthly_workflow.py
- **Commit:** f5ef7f0

**3. [Rule 1 - Bug] run_workflow status dict acedia history_summary em fallback**
- **Found during:** Task 2 GREEN phase (análise de run_workflow)
- **Issue:** Linhas 237-239 e 245 acediam `analysis["history_summary"]` directamente, crashando quando source=local_catalog
- **Fix:** Bloco condicional `is_local_catalog` extrai valores equivalentes de `change_recommendation`/`period_recommendation`; status dict inclui agora `source` e `fallback_reason`
- **Files modified:** src/backend/monthly_workflow.py
- **Commit:** f5ef7f0

## Known Stubs

Nenhum. Toda a funcionalidade está activa com dados reais (catálogo `config/tarifarios.json` com 6 tarifas públicas, fixture `fornecedor_atual.exemplo.json` existente).

## Verification Results

```
6 passed in 0.18s
tests/test_supplier_missing.py::test_compare_month_marks_supplier_not_found PASSED
tests/test_supplier_missing.py::test_report_warns_when_supplier_not_found PASSED
tests/test_supplier_missing.py::test_pipeline_does_not_crash_on_missing_supplier PASSED
tests/test_tiagofelicia_fallback.py::test_fallback_activated_on_network_error PASSED
tests/test_tiagofelicia_fallback.py::test_report_indicates_local_catalog PASSED
tests/test_tiagofelicia_fallback.py::test_fallback_reason_recorded PASSED
```

## Self-Check: PASSED

- pytest.ini: FOUND
- tests/__init__.py: FOUND
- tests/conftest.py: FOUND
- config/tarifarios.json: FOUND
- tests/test_tiagofelicia_fallback.py: FOUND
- tests/test_supplier_missing.py: FOUND
- .planning/phases/02-resilience/02-01-SUMMARY.md: FOUND
- Commit dc315f7 (Task 1): FOUND
- Commit 45a312f (Task 2 RED): FOUND
- Commit f5ef7f0 (Task 2 GREEN): FOUND
