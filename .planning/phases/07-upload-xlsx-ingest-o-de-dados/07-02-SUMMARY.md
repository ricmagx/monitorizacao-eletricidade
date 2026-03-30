---
phase: 07-upload-xlsx-ingest-o-de-dados
plan: 02
subsystem: api
tags: [fastapi, htmx, playwright, sqlalchemy, jinja2, upload, sqlite]

# Dependency graph
requires:
  - phase: 07-01
    provides: ingestao_xlsx.py, locais_service.py, tabela locais em SQLite, migration 002

provides:
  - POST /upload/xlsx endpoint com background task tiagofelicia idempotente
  - GET/POST /locais e POST /locais/{id}/fornecedor endpoints
  - Templates HTMX upload_xlsx.html, upload_confirmacao.html, locais_form.html
  - load_locations() com merge SQLite para locais criados via UI
  - Dockerfile com playwright + Chromium para COMP-01

affects: [phase-09-ui, comparacao-tiagofelicia, dashboard-selector]

# Tech tracking
tech-stack:
  added: [playwright==1.49.1, chromium (via playwright install)]
  patterns: [HTMX multipart upload, FastAPI BackgroundTasks, on_conflict_do_nothing idempotency, engine merge in data_loader]

key-files:
  created:
    - src/web/routes/upload.py
    - src/web/routes/locais.py
    - src/web/templates/partials/upload_xlsx.html
    - src/web/templates/partials/upload_confirmacao.html
    - src/web/templates/partials/locais_form.html
  modified:
    - src/web/app.py
    - src/web/services/data_loader.py
    - src/web/routes/dashboard.py
    - src/web/routes/custos_reais.py
    - Dockerfile
    - requirements-docker.txt
    - tests/test_web_custos_reais.py

key-decisions:
  - "Background task tiagofelicia usa FastAPI BackgroundTasks (sincrono em thread pool) — nao async def"
  - "load_locations() aceita engine= opcional para backward compatibility — chamadas sem engine continuam a funcionar"
  - "Locais criados via UI sem pipeline retornam dados vazios em _load_location_data — Phase 9 migrara para SQLite"
  - "locais_form.html usa hx-swap=outerHTML no elemento raiz com id=locais-container para substituicao correcta"

patterns-established:
  - "HTMX multipart upload: hx-encoding=multipart/form-data no form, UploadFile = File(...) no endpoint"
  - "Background task idempotente: on_conflict_do_nothing com index_elements=[location_id, year_month]"
  - "Graceful degradation playwright: ImportError catch no bg task, loga aviso e retorna sem erro"
  - "Merge config.json + SQLite em load_locations: IDs de config.json tem precedencia"

requirements-completed: [UPLD-01, CONF-01, CONF-02, COMP-01]

# Metrics
duration: 5min
completed: 2026-03-30
---

# Phase 07 Plan 02: Upload XLSX Ingestao de Dados Summary

**FastAPI routes upload/locais wired com HTMX, background task tiagofelicia idempotente, Dockerfile com Chromium playwright, e dashboard selector ligado ao SQLite**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-30T15:33:18Z
- **Completed:** 2026-03-30T15:38:30Z
- **Tasks:** 5
- **Files modified:** 11

## Accomplishments
- POST /upload/xlsx endpoint com ingestao XLSX E-REDES e background task tiagofelicia idempotente (ON CONFLICT DO NOTHING)
- GET/POST /locais + POST /locais/{id}/fornecedor com templates HTMX completos
- load_locations() extendida com merge SQLite — locais criados via UI aparecem no dashboard selector
- Dockerfile actualizado com playwright + Chromium para COMP-01

## Task Commits

1. **Task 1: Upload route + templates HTMX + background task tiagofelicia** - `5ce7190` (feat)
2. **Task 2: Locais routes + app.py wiring dos novos routers** - `e586c0e` (feat)
3. **Task 3: Dashboard wiring — upload section + link gerir locais** - `cb7b122` (feat)
4. **Task 4: Dockerfile + requirements-docker.txt — playwright para COMP-01** - `9cf6df6` (chore)
5. **Task 5: Ligar load_locations() ao SQLite** - `1369ab8` (feat)
6. **Deviation fix: test fixture db_engine** - `1b0adb8` (fix)

## Files Created/Modified
- `src/web/routes/upload.py` - POST /upload/xlsx com background task tiagofelicia idempotente
- `src/web/routes/locais.py` - GET/POST /locais, POST /locais/{id}/fornecedor
- `src/web/templates/partials/upload_xlsx.html` - Formulario upload XLSX com HTMX
- `src/web/templates/partials/upload_confirmacao.html` - Partial confirmacao/erro pos-upload
- `src/web/templates/partials/locais_form.html` - Formulario criacao + tabela de locais
- `src/web/app.py` - Registar upload_router e locais_router
- `src/web/services/data_loader.py` - load_locations() com parametro engine opcional + merge SQLite
- `src/web/routes/dashboard.py` - Passar engine= a load_locations + guard pipeline
- `src/web/routes/custos_reais.py` - Passar engine= a load_locations
- `Dockerfile` - RUN playwright install chromium --with-deps
- `requirements-docker.txt` - playwright==1.49.1

## Decisions Made
- Background task tiagofelicia usa `BackgroundTasks.add_task()` com funcao sincrona — FastAPI corre automaticamente em thread pool, sem bloquear resposta HTTP
- `load_locations()` aceita `engine=None` para backward compatibility total — chamadas sem engine continuam a funcionar como antes
- Locais sem `pipeline` em `_load_location_data` retornam estrutura de dados vazios — Phase 9 migrara leitura de dados de CSV para SQLite

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture web_client_with_csv sem db_engine apos Task 5**
- **Found during:** Verificacao final (pos Task 5)
- **Issue:** Ao passar `engine=request.app.state.db_engine` em custos_reais.py, o test fixture que apenas definia `config_path` e `project_root` falhou com `AttributeError: 'State' object has no attribute 'db_engine'`
- **Fix:** Adicionado in-memory SQLite engine ao test fixture: `test_engine = create_engine("sqlite:///:memory:")` + `metadata.create_all(test_engine)` + `app.state.db_engine = test_engine`
- **Files modified:** `tests/test_web_custos_reais.py`
- **Verification:** `pytest tests/test_web_custos_reais.py` — 7 passed
- **Committed in:** `1b0adb8` (fix commit separado)

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Fix necessario para correctness dos testes. Sem scope creep.

## Issues Encountered
- `locais_form.html` do plano usava `hx-target="#locais-container" hx-swap="innerHTML"` mas o div raiz nao tinha `id=locais-container`. Corrigido adicionando o id ao div raiz e usando `hx-swap="outerHTML"` para substituicao correcta do elemento.

## Known Stubs
- Locais criados via UI no dashboard selector mostram entrada vazia nos graficos — comportamento intencional documentado, Phase 9 resolvera com leitura directa de SQLite.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 07 completa: servicos + routes + templates + Docker com playwright
- UPLD-01, CONF-01, CONF-02, COMP-01 satisfeitos
- Phase 08 (PDF fatura upload) pode comecar — pdfplumber ja previsto em requirements

---
*Phase: 07-upload-xlsx-ingest-o-de-dados*
*Completed: 2026-03-30*

## Self-Check: PASSED

All files present and all commits verified in git history.
