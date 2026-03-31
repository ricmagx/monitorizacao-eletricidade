---
phase: 09-dashboard-ui
plan: 01
subsystem: web-dashboard
tags: [sqlite, data-loader, dashboard, retrocompatibilidade]
dependency_graph:
  requires: [07-multi-location]
  provides: [dashboard-sqlite-source, sqlite-reader-functions]
  affects: [web/routes/dashboard.py, web/services/data_loader.py, web/routes/custos_reais.py]
tech_stack:
  added: [SQLAlchemy Core select queries, StaticPool para testes in-memory]
  patterns: [SQLite-first com fallback CSV, StaticPool para testes com engine partilhada]
key_files:
  created: []
  modified:
    - src/web/services/data_loader.py
    - src/web/routes/dashboard.py
    - src/web/routes/custos_reais.py
    - tests/conftest.py
    - tests/test_web_dashboard.py
    - tests/test_web_data_loader.py
decisions:
  - SQLite como fonte primaria com fallback CSV para locais com pipeline (retrocompatibilidade)
  - StaticPool em engines de teste in-memory para garantir conexoes partilham a mesma BD
  - Context manager TestClient para sobrepor db_engine apos lifespan (evita reset pelo lifespan)
metrics:
  duration_minutes: 20
  completed_date: "2026-03-31"
  tasks_completed: 3
  files_modified: 6
  tests_added: 8
  tests_total: 101
---

# Phase 9 Plan 01: Dashboard SQLite Migration Summary

**One-liner:** Migrou fonte de dados do dashboard de CSV/JSON para SQLite com fallback retrocompativel, expondo 4 novas funcoes reader e reescrevendo `_load_location_data`.

## What Was Built

Quatro funcoes SQLite reader em `data_loader.py` e reescrita de `_load_location_data()` no dashboard para usar SQLite como fonte primaria, com fallback CSV/JSON para locais com pipeline existente.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Test fixtures SQLite + RED tests | 9cc8d7f | tests/conftest.py, test_web_dashboard.py, test_web_data_loader.py |
| 2 | SQLite reader functions | 2c2516f | src/web/services/data_loader.py |
| 3 | Rewrite _load_location_data + fix custos_reais | bcd2779 | src/web/routes/dashboard.py, src/web/routes/custos_reais.py, tests/conftest.py |

## Decisions Made

1. **SQLite-first com fallback CSV:** Para cada fonte de dados (consumo, analise, custos, frescura), tentar SQLite primeiro; se vazio e local tem pipeline, usar fallback CSV/JSON. Preserva retrocompatibilidade total.

2. **StaticPool para engines de teste in-memory:** SQLite in-memory com pool padrao cria uma nova BD por conexao — seed data inserido numa conexao nao esta visivel noutras. StaticPool garante que todas as conexoes partilham a mesma BD. Necessario para testes realistas.

3. **Context manager TestClient + override pos-lifespan:** O lifespan da app faz `app.state.db_engine = engine` (engine real). Se o override do engine de teste acontecer antes de TestClient.__enter__, e sobrescrito. Solucao: usar `with TestClient(app) as client:` e sobrepor `app.state.db_engine` dentro do bloco, apos o lifespan completar.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] web_client fixture sem db_engine causava AttributeError**
- **Found during:** Task 1 (verificacao dos testes existentes)
- **Issue:** `web_client` fixture nao definia `app.state.db_engine`, causando `AttributeError: 'State' object has no attribute 'db_engine'` em todos os testes de dashboard.
- **Fix:** Adicionado `db_engine` com engine in-memory + StaticPool ao fixture `web_client`.
- **Files modified:** tests/conftest.py
- **Commit:** bcd2779

**2. [Rule 1 - Bug] SQLite in-memory sem StaticPool cria BD nova por conexao**
- **Found during:** Task 3 (testes falhavam com 404 apesar do seed data)
- **Issue:** `sqlite:///:memory:` sem StaticPool cria uma BD nova para cada `engine.connect()`. O seed data estava noutra conexao e era invisivel para as queries do dashboard.
- **Fix:** Alterado para `poolclass=StaticPool` em todos os engines de teste in-memory.
- **Files modified:** tests/conftest.py
- **Commit:** bcd2779

**3. [Rule 1 - Bug] Lifespan da app sobrescreve db_engine apos override do fixture**
- **Found during:** Task 3 (debug do 404)
- **Issue:** `TestClient(app)` corre o lifespan que faz `app.state.db_engine = engine` (real), sobrescrevendo o engine de teste definido antes do TestClient.
- **Fix:** Usar `with TestClient(app) as client:` e definir `app.state.db_engine = test_engine` dentro do bloco, depois do lifespan.
- **Files modified:** tests/conftest.py
- **Commit:** bcd2779

## Verification Results

```
101 passed, 14 skipped in 0.82s
```

Todos os testes passam incluindo os 8 novos testes SQLite.

## Known Stubs

None — todos os dados SQLite sao lidos directamente da BD. Locais criados via UI mostram dados reais.

## Self-Check: PASSED
