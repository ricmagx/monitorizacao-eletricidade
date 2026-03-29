---
phase: 02-resilience
plan: "02"
subsystem: testing
tags: [python, openpyxl, validation, bounds-check, pytest, tdd]

# Dependency graph
requires:
  - phase: 02-01
    provides: pipeline funcional com render_report dual-path e suite de testes inicial
provides:
  - Bounds check de consumo mensal (30-5000 kWh) no parser XLSX antes de qualquer escrita em disco
  - Constantes MIN_MONTHLY_KWH e MAX_MONTHLY_KWH no modulo eredes_to_monthly_csv
  - 5 testes automatizados para RES-02 em tests/test_xlsx_validation.py
affects: [02-03, 02-04, multi-local-refactor, dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [bounds-check-before-disk-write, tdd-red-green]

key-files:
  created:
    - tests/test_xlsx_validation.py
  modified:
    - src/backend/eredes_to_monthly_csv.py

key-decisions:
  - "Bounds check inserido entre drop_partial_last_month e output_path.parent.mkdir — garante que nenhum ficheiro e escrito antes da validacao"
  - "Limites 30 kWh (min) e 5000 kWh (max) definidos como constantes nomeadas no topo do modulo"
  - "ValueError com mensagem explicita incluindo year_month e valor real para diagnostico rapido"

patterns-established:
  - "Validate-before-write: toda a validacao de dados ocorre antes de qualquer abertura/criacao de ficheiro de output"
  - "TDD: RED (testes falhando) commit separado do GREEN (implementacao) para rastreabilidade"

requirements-completed: [RES-02]

# Metrics
duration: 1min
completed: 2026-03-29
---

# Phase 02 Plan 02: Bounds Check XLSX (RES-02) Summary

**Parser XLSX rejeita consumos mensais fora de 30-5000 kWh com ValueError explicito antes de escrever qualquer ficheiro CSV, validado por 5 testes TDD.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-29T22:20:28Z
- **Completed:** 2026-03-29T22:21:43Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Constantes `MIN_MONTHLY_KWH = 30` e `MAX_MONTHLY_KWH = 5000` definidas no topo do modulo
- Bounds check inserido imediatamente antes de `output_path.parent.mkdir` — nenhum ficheiro e criado quando a validacao falha
- 5 testes automatizados cobrindo: 0 kWh, >5000 kWh, <30 kWh, valores normais (800/1200 kWh), e inclusao do year_month na mensagem de erro
- Suite completa (11 testes) continua green apos as alteracoes

## Task Commits

TDD task com dois commits separados:

1. **RED phase: testes falhando** - `086ea48` (test)
2. **GREEN phase: implementacao bounds check** - `f9ebad8` (feat)

**Plan metadata:** `(a registar no commit final de docs)`

_Note: TDD tasks have multiple commits (test → feat)_

## Files Created/Modified

- `tests/test_xlsx_validation.py` - 5 testes de bounds check para RES-02 (criado)
- `src/backend/eredes_to_monthly_csv.py` - Constantes MIN/MAX e bounds check antes do open() (modificado)

## Decisions Made

- Bounds check posicionado ANTES de `output_path.parent.mkdir` (e nao depois) para garantir que nem o directorio nem o ficheiro sao criados quando a validacao falha — padrao "validate-before-write"
- Constantes nomeadas em vez de literais inline para facilitar ajuste futuro dos limites sem risco de inconsistencia
- ValueError com mensagem descritiva incluindo year_month, valor real e intervalo esperado para diagnostico imediato

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None - sem dados hardcoded ou placeholders neste plano.

## Self-Check: PASSED

All files and commits verified present.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RES-02 completo: parser XLSX protegido contra consumos absurdos
- Suite de testes em 11 testes, todos green
- Pronto para planos seguintes da fase 02-resilience (RES-03, RES-04, etc.)

---
*Phase: 02-resilience*
*Completed: 2026-03-29*
