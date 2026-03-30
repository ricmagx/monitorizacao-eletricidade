---
phase: 07-upload-xlsx-ingest-o-de-dados
plan: "01"
subsystem: data-layer
tags: [sqlite, sqlalchemy, alembic, xlsx, ingestao, locais, tdd]
dependency_graph:
  requires: []
  provides: [tabela-locais, migration-002, parse-xlsx-to-dict, ingestao-xlsx-service, locais-service, wave0-stubs]
  affects: [07-02]
tech_stack:
  added: []
  patterns: [SQLAlchemy Core insert with on_conflict_do_nothing, Alembic migration chaining, SQLite in-memory testing]
key_files:
  created:
    - tests/test_web_upload.py
    - tests/test_ingestao_xlsx.py
    - tests/test_web_locais.py
    - tests/test_comparacao.py
    - src/db/migrations/versions/002_add_locais.py
    - src/web/services/ingestao_xlsx.py
    - src/web/services/locais_service.py
  modified:
    - tests/conftest.py
    - src/db/schema.py
    - src/web/app.py
    - src/backend/eredes_to_monthly_csv.py
decisions:
  - "Seed de locais idempotente: verificar count(*) antes de inserir — nunca duplicar ao reiniciar container"
  - "UniqueConstraint em comparacoes adicionado na migration 002 (nao 001) para nao quebrar DB existentes"
  - "ingerir_xlsx usa sqlite_insert(...).on_conflict_do_nothing para idempotencia — mais explicito que INSERT OR IGNORE"
metrics:
  duration: "234s"
  completed_date: "2026-03-30"
  tasks_completed: 3
  files_modified: 11
---

# Phase 07 Plan 01: Test Stubs Wave 0 + Data Layer Summary

Wave 0 test stubs para todos os requisitos Phase 7 (UPLD/CONF/COMP) + tabela locais em SQLite com seed automatico + refactoring XLSX parser para uso em memoria + servicos de ingestao e CRUD de locais.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 0 | Wave 0 test stubs para requisitos Phase 7 | 9bb07c3 | 5 |
| 1 | Tabela locais, migration 002, seed lifespan | ea9ca02 | 3 |
| 2 | Refactoring eredes_to_monthly_csv: parse_xlsx_to_dict() | 373c049 | 1 |
| 3 | Servicos ingestao_xlsx.py e locais_service.py | 18e39ab | 2 |

## Decisions Made

1. **Seed idempotente via count(*):** A funcao `_seed_locais_from_config` verifica `SELECT count(*) FROM locais` antes de inserir. Se a tabela ja tiver dados, retorna sem fazer nada. Isto e seguro para restarts de container sem risco de duplicacao.

2. **UniqueConstraint em comparacoes na migration 002:** O constraint `uq_comparacao_loc_month` foi adicionado na migration 002 (e nao na 001 original). Isto preserva compatibilidade com bases de dados ja criadas pela migration 001 — a constraint e aplicada incrementalmente.

3. **on_conflict_do_nothing para idempotencia de ingestao:** `ingerir_xlsx` usa `sqlite_insert(...).on_conflict_do_nothing(index_elements=["location_id", "year_month"])` em vez de INSERT OR IGNORE. Mais explicito e compativel com o dialecto SQLite do SQLAlchemy.

4. **parse_xlsx_to_dict() como funcao publica separada:** A logica de parsing foi extraida de `convert_xlsx_to_monthly_csv` para uma funcao reutilizavel que retorna dict em memoria. A funcao original foi mantida como wrapper backward-compatible.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

Os seguintes stubs existem intencionalmente — sao Wave 0 para Plan 02:

| File | Stub | Plan para resolver |
|------|------|-------------------|
| tests/test_web_upload.py | test_upload_xlsx_ok, test_upload_xlsx_cpe_nao_detectado, test_background_task_registada, test_upload_sem_playwright_retorna_200 | Plan 02 |
| tests/test_ingestao_xlsx.py | test_ingestao_escreve_sqlite, test_cpe_routing, test_idempotencia, test_cpe_nao_detectado | Plan 02 |
| tests/test_web_locais.py | test_criar_local, test_editar_fornecedor, test_listar_locais | Plan 02 |
| tests/test_comparacao.py | test_comparacao_guardada, test_comparacao_idempotente | Plan 02 |

Todos marcados com `@pytest.mark.skip(reason="Wave 0 stub — implementar em Plan 02")`. Sao stubs intencionais que definem contratos para Plan 02 — nao impedem o objectivo deste plano.

## Self-Check: PASSED

Files verified:
- tests/test_web_upload.py: FOUND
- tests/test_ingestao_xlsx.py: FOUND
- tests/test_web_locais.py: FOUND
- tests/test_comparacao.py: FOUND
- src/db/migrations/versions/002_add_locais.py: FOUND
- src/web/services/ingestao_xlsx.py: FOUND
- src/web/services/locais_service.py: FOUND

Commits verified:
- 9bb07c3: test(07-01): Wave 0 stubs - FOUND
- ea9ca02: feat(07-01): tabela locais - FOUND
- 373c049: refactor(07-01): parse_xlsx_to_dict - FOUND
- 18e39ab: feat(07-01): servicos - FOUND
