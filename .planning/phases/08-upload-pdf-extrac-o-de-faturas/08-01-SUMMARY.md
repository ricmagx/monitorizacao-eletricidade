---
phase: 08-upload-pdf-extrac-o-de-faturas
plan: 01
subsystem: pdf-extraction
tags: [pdfplumber, pdf, extraction, sqlite, tdd, meo-energia, endesa]
dependency_graph:
  requires: []
  provides: [extrator_pdf_service, pdfplumber_dependency]
  affects: [08-02-upload-endpoint]
tech_stack:
  added: [pdfplumber==0.11.7]
  patterns: [lazy-import, on_conflict_do_nothing, tdd-red-green]
key_files:
  created:
    - src/web/services/extrator_pdf.py
    - tests/test_extrator_pdf.py
  modified:
    - requirements-docker.txt
    - requirements.txt
decisions:
  - CPE regex usa padrao simples PT[\d ]+[A-Z]{2} para tolerar espaco no CPE do apartamento
  - pdfplumber importado de forma lazy dentro de extrair_texto_pdf() para evitar ImportError ao carregar o modulo
  - Endesa usa TOTAL_ENDESA_PATTERNS com regex Total\s+Ele[ct]ricidade explicitamente para excluir gas
metrics:
  duration: 238s
  completed: 2026-03-31
  tasks: 2
  files: 4
---

# Phase 8 Plan 1: pdfplumber + Extractor Service Summary

pdfplumber adicionado a requirements-docker.txt/requirements.txt; servico extrator_pdf.py implementado com TDD (parsers Meo Energia + Endesa, CPE tolerante a espacos, filtragem explicita de gas, ingestao idempotente em custos_reais SQLite).

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Wave 0 — pdfplumber deps + test stubs RED | a111c03 | Done |
| 2 | Implementar extrator_pdf.py GREEN | a5caf19 | Done |

## What Was Built

### `src/web/services/extrator_pdf.py`

Servico de extraccao com tres funcoes publicas:

- `extrair_fatura(texto: str) -> dict` — parser de texto: detecta formato por keywords, extrai CPE (tolerante a espacos), total EUR e periodo; retorna dict com `erro`, `formato`, `cpe`, `year_month`, `custo_eur`
- `extrair_texto_pdf(pdf_bytes: bytes) -> str` — extrai texto de PDF com pdfplumber (lazy import + BytesIO, sem ficheiro temporario)
- `ingerir_pdf(pdf_bytes: bytes, engine: Engine) -> dict` — fluxo completo: extrai texto + dados + CPE lookup + escrita idempotente em custos_reais

### `tests/test_extrator_pdf.py`

8 testes unitarios: Meo Energia, Endesa (so eletricidade), Endesa com gas (filtragem), formato desconhecido, CPE com espaco, BytesIO pdfplumber, escrita SQLite, idempotencia.

### Dependencias

`pdfplumber==0.11.7` adicionado a `requirements-docker.txt` e `requirements.txt`.

## Test Results

```
7 passed, 1 skipped (test_extrair_texto_pdf_bytesio — fpdf nao instalado no ambiente dev)
Full suite: 86 passed, 14 skipped — sem regressoes
```

## Decisions Made

1. **CPE regex tolerante a espacos:** Padrao `PT[\d ]+[A-Z]{2}\b` em vez de regex estrito — captura tanto `PT0002000084968079SX` (sem espaco) como `PT000200003982208 2NT` (com espaco); normalizado antes de retornar removendo espacos.

2. **Lazy import pdfplumber:** Importado apenas dentro de `extrair_texto_pdf()` para evitar que `import extrator_pdf` quebre em ambientes sem pdfplumber instalado (ex: testes que nao usam PDF real).

3. **Regex Endesa para eletricidade:** `Total\s+Ele[ct]ricidade` explicito — nunca `Total Fatura` nem `Total Gas`. Captura apenas a linha de eletricidade mesmo em faturas multi-energia.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CPE regex demasiado ganancioso**
- **Found during:** Task 2 (GREEN phase, primeira execucao dos testes)
- **Issue:** Regex `PT\d{16,18}[\w ]{1,4}` capturava `PT0002000084968079SXP` (incluia o 'P' de "Periodo") porque `[\w]` inclui letras minusculas e o texto normalizado coloca tudo numa linha
- **Fix:** Substituido por `PT[\d ]+[A-Z]{2}\b` — captura PT, digitos com espacos opcionais, terminando em 2 maiusculas em boundary de palavra
- **Files modified:** `src/web/services/extrator_pdf.py`
- **Commit:** a5caf19 (incluido no commit de implementacao)

## Known Stubs

None — toda a logica de extraccao esta implementada e testada com texto sintetico. Os regex exactos para faturas reais sao LOW confidence (sem PDFs reais de amostra) mas a estrutura suporta adicionar padroes facilmente em TOTAL_MEO_PATTERNS e TOTAL_ENDESA_PATTERNS.

## Self-Check: PASSED

- src/web/services/extrator_pdf.py: FOUND
- tests/test_extrator_pdf.py: FOUND
- requirements-docker.txt contains pdfplumber: FOUND
- requirements.txt contains pdfplumber: FOUND
- Commit a111c03: FOUND
- Commit a5caf19: FOUND
