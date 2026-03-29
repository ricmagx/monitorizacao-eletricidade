---
phase: 03-multi-location-refactor
plan: 01
subsystem: config
tags: [python, json-schema, pytest, regex, multi-location]

requires:
  - phase: 02-resilience
    provides: existing test infrastructure (conftest.py fixtures, pytest.ini)

provides:
  - config/system.json with locations[] array schema (casa + apartamento)
  - src/backend/cpe_routing.py with extract_cpe_from_filename and find_location_by_cpe
  - tests/conftest.py multi_location_config fixture for phase 03 tests
  - tests/test_multi_location_config.py covering MULTI-01 and MULTI-02
  - tests/test_cpe_routing.py covering MULTI-04
  - .gitignore covering nested data/*/raw/, data/*/processed/, data/*/reports/, state/*/

affects: [03-02, 03-03, all phase-03 plans that depend on locations array schema]

tech-stack:
  added: []
  patterns:
    - "Location object as plain dict with keys: id, name, cpe, current_contract, pipeline"
    - "CPE extraction via re.compile(r'Consumos_(PT\\w+?)_') on filename basename"
    - "Backward-compat: test_config fixture preserves old schema for phase 02 tests"

key-files:
  created:
    - src/backend/cpe_routing.py
    - tests/test_multi_location_config.py
    - tests/test_cpe_routing.py
  modified:
    - config/system.json
    - tests/conftest.py
    - .gitignore

key-decisions:
  - "config/system.json migrado completamente para schema locations[] sem fallback legacy - projecto pessoal sem consumidores externos"
  - "test_config fixture mantida com schema antigo para compatibilidade com testes fase 02 (shim temporario)"
  - "CPE apartamento mantido como placeholder PT000200XXXXXXXXXX - CPE real desconhecido"

patterns-established:
  - "TDD (RED/GREEN): testes criados primeiro, implementacao a seguir"
  - "Location dict como unidade de composicao: passar location como argumento explícito"

requirements-completed: [MULTI-01, MULTI-02]

duration: 2min
completed: 2026-03-29
---

# Phase 3 Plan 01: Multi-Location Config + CPE Routing Summary

**Schema locations[] em config/system.json com CPE routing por regex, fixtures pytest para fase 03, e .gitignore cobrindo paths nested**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T22:53:29Z
- **Completed:** 2026-03-29T22:55:43Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- `config/system.json` migrado para schema `locations[]` com `casa` (CPE real) e `apartamento` (CPE placeholder)
- `src/backend/cpe_routing.py` criado com `extract_cpe_from_filename` e `find_location_by_cpe`
- `tests/conftest.py` com nova fixture `multi_location_config` que cria estrutura nested em `tmp_path`
- `.gitignore` actualizado para cobrir `data/*/raw/`, `data/*/processed/`, `data/*/reports/`, `state/*/`
- 12 testes novos, todos passam; 11 testes existentes continuam a passar (23 total)

## Task Commits

1. **Task 1 (RED): Tests for multi-location config and CPE routing** - `7f66d5b` (test)
2. **Task 1 (GREEN): Multi-location config schema, CPE routing module and fixtures** - `1843e9e` (feat)
3. **Task 2: Update .gitignore for nested data paths** - `e66b085` (chore)

## Files Created/Modified

- `config/system.json` - Migrado para schema `locations[]` com `casa` e `apartamento`; removidas secções globais `current_contract` e `pipeline`
- `src/backend/cpe_routing.py` - `extract_cpe_from_filename` e `find_location_by_cpe`
- `tests/conftest.py` - Adicionada fixture `multi_location_config`; `test_config` mantida como shim de compatibilidade
- `tests/test_multi_location_config.py` - 5 testes cobrindo MULTI-01 e MULTI-02
- `tests/test_cpe_routing.py` - 7 testes cobrindo MULTI-04
- `.gitignore` - Adicionadas regras para paths nested `data/*/` e `state/*/`

## Decisions Made

- `config/system.json` migrado completamente para o novo schema sem manter secções legacy (`current_contract` e `pipeline` globais removidas). Projecto pessoal sem consumidores externos — retrocompatibilidade desnecessária.
- `test_config` fixture em `conftest.py` mantida com schema antigo (shim temporário) para que os testes da fase 02 continuem a passar. Será migrada em fase posterior.
- CPE do apartamento mantido como placeholder `PT000200XXXXXXXXXX` — CPE real desconhecido (requer confirmação no portal E-REDES).

## Deviations from Plan

None — plano executado exactamente como especificado.

## Issues Encountered

None.

## User Setup Required

None — nenhuma configuração de serviços externos necessária neste plano.

## Next Phase Readiness

- Schema `locations[]` disponível e testado — base para planos 03-02 e 03-03
- CPE routing (`extract_cpe_from_filename`, `find_location_by_cpe`) pronto para integração em `process_latest_download.py` (Plan 02)
- Fixture `multi_location_config` disponível para todos os testes da fase 03
- CPE real do apartamento ainda desconhecido — placeholder usado; não bloqueia planos seguintes

## Self-Check: PASSED

- src/backend/cpe_routing.py: FOUND
- tests/test_multi_location_config.py: FOUND
- tests/test_cpe_routing.py: FOUND
- 03-01-SUMMARY.md: FOUND
- commit 7f66d5b (RED tests): FOUND
- commit 1843e9e (GREEN implementation): FOUND
- commit e66b085 (.gitignore): FOUND
- config schema locations[] valid: OK
- no top-level current_contract: OK
- no top-level pipeline: OK
- .gitignore nested rules: OK
- 23 tests passing: OK

---
*Phase: 03-multi-location-refactor*
*Completed: 2026-03-29*
