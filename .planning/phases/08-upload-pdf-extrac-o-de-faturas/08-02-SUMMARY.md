---
phase: 08-upload-pdf-extrac-o-de-faturas
plan: "02"
subsystem: web-upload
tags: [fastapi, htmx, pdf-upload, custos-reais, integration-tests]
dependency_graph:
  requires: ["08-01"]
  provides: ["POST /upload/pdf endpoint", "upload_pdf.html form", "upload_pdf_confirmacao.html"]
  affects: ["dashboard custos_reais.json", "src/web/routes/upload.py"]
tech_stack:
  added: []
  patterns:
    - "HTMX multipart form upload with hx-post, hx-encoding, hx-indicator"
    - "FastAPI UploadFile with BytesIO (no tempfile needed for pdfplumber)"
    - "Dual persistence: SQLite via ingerir_pdf + JSON via save_custo_real"
    - "Mock-based integration tests with web_client fixture + in-memory SQLite"
key_files:
  created:
    - src/web/templates/partials/upload_pdf.html
    - src/web/templates/partials/upload_pdf_confirmacao.html
    - tests/test_upload_endpoint.py
  modified:
    - src/web/routes/upload.py
decisions:
  - "No BackgroundTasks for PDF upload (unlike XLSX) — PDF extraction is fast, no tiagofelicia.pt call needed"
  - "No tempfile for PDF — pdfplumber accepts BytesIO directly, avoiding disk I/O"
  - "web_client_pdf fixture sets app.state.db_engine explicitly — lifespan not triggered in TestClient without context manager"
  - "Tests mock ingerir_pdf at route level to avoid pdfplumber dependency in test environment"
metrics:
  duration_seconds: 231
  completed_date: "2026-03-31"
  tasks_completed: 2
  files_changed: 4
---

# Phase 08 Plan 02: Upload PDF Endpoint + Integration Tests Summary

POST /upload/pdf endpoint ligando o servico extrator_pdf ao browser via HTMX, com dupla persistencia SQLite + JSON e 3 testes de integracao verdes.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Endpoint POST /upload/pdf + templates HTML + escrita custos_reais.json | 4266b3a | upload.py, upload_pdf.html, upload_pdf_confirmacao.html |
| 2 | Teste de integracao do endpoint POST /upload/pdf | 4f2af3a | tests/test_upload_endpoint.py |

## What Was Built

### POST /upload/pdf endpoint (src/web/routes/upload.py)

Adicionado endpoint ao router existente seguindo o pattern do XLSX:
- Lê bytes do PDF sem ficheiro temporario (pdfplumber usa BytesIO)
- Chama `ingerir_pdf(content, engine)` — escreve em SQLite com idempotencia
- Em caso de sucesso, chama `save_custo_real()` para escrever em `data/{local_id}/custos_reais.json`
- Retorna template `upload_pdf_confirmacao.html` com dados ou erro

A dupla persistencia (SQLite + JSON) e critica: o dashboard le `custos_reais.json`, nao a tabela SQLite.

### Templates HTML

**upload_pdf.html** — formulario HTMX com:
- `hx-post="/upload/pdf"`, `hx-encoding="multipart/form-data"`, indicador de progresso
- `accept=".pdf"` no input para filtrar ficheiros no browser
- Target `#upload-pdf-resultado` para swap HTMX

**upload_pdf_confirmacao.html** — confirmacao ou erro:
- Erro: div com background vermelho, mensagem clara
- Sucesso: lista com formato, local (nome + CPE), periodo, total EUR
- Nota de idempotencia quando `inserido=False` (custo ja existia para o periodo)

### Testes de Integracao (tests/test_upload_endpoint.py)

3 testes com fixture `web_client_pdf` (db_engine in-memory explicitamente configurado):
- `test_upload_pdf_returns_200` — HTTP 200 mesmo com erro (sem crash 500)
- `test_upload_pdf_erro_formato` — HTML contem mensagem de erro de formato
- `test_upload_pdf_renders_confirmacao` — confirmacao mostra "Fatura importada com sucesso" e valor

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] web_client fixture nao configura app.state.db_engine**

- **Found during:** Task 2 — primeiro run dos testes falhou com `AttributeError: 'State' object has no attribute 'db_engine'`
- **Issue:** A fixture `web_client` do conftest.py nao invoca o lifespan (que configura db_engine). O endpoint `/upload/pdf` acede a `request.app.state.db_engine` antes de qualquer mock poder interceptar.
- **Fix:** Criada fixture `web_client_pdf` local no test file que configura explicitamente `app.state.db_engine` com SQLite in-memory, seguindo o pattern de `web_client_with_csv` em `test_web_custos_reais.py`.
- **Files modified:** tests/test_upload_endpoint.py
- **Commit:** 4f2af3a

## Known Stubs

None — todos os dados fluem do mock/engine real, sem placeholders hardcoded.

## Self-Check: PASSED

- src/web/routes/upload.py — FOUND
- src/web/templates/partials/upload_pdf.html — FOUND
- src/web/templates/partials/upload_pdf_confirmacao.html — FOUND
- tests/test_upload_endpoint.py — FOUND
- Commit 4266b3a — FOUND
- Commit 4f2af3a — FOUND
- 89 tests pass, 14 skipped — VERIFIED
