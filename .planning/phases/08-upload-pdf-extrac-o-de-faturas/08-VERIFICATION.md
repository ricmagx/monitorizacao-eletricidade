---
phase: 08-upload-pdf-extrac-o-de-faturas
verified: 2026-03-31T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 8: Upload PDF + Extracção de Faturas — Verification Report

**Phase Goal:** O utilizador faz upload de PDF de fatura via browser e o sistema extrai automaticamente o total pago e período, detectando o local pelo CPE presente no documento, para os formatos Meo Energia e Endesa.
**Verified:** 2026-03-31
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                       | Status     | Evidence                                                                                    |
|----|---------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------|
| 1  | Upload de um PDF Meo Energia extrai o total pago e período correctos                        | VERIFIED  | `test_extrair_meo_energia` PASSED: total=45.32, year_month=2026-01                         |
| 2  | Upload de um PDF Endesa extrai o total pago e período correctos                             | VERIFIED  | `test_extrair_endesa` PASSED: total=42.75, year_month=2026-03                              |
| 3  | PDF não reconhecido mostra mensagem de erro clara sem crash                                 | VERIFIED  | `test_formato_desconhecido` + `test_upload_pdf_erro_formato` PASSED; HTTP 200, não 500      |
| 4  | Gás presente na fatura Endesa não é importado                                               | VERIFIED  | `test_endesa_ignora_gas` PASSED: custo_eur=38.50, não 60.60 (total fatura)                 |
| 5  | O utilizador pode fazer upload de PDF via formulário web                                    | VERIFIED  | `upload_pdf.html` com `hx-post="/upload/pdf"` e `accept=".pdf"`                            |
| 6  | Custo extraído fica gravado em custos_reais SQLite                                          | VERIFIED  | `test_ingestao_pdf_escreve_sqlite` PASSED; `on_conflict_do_nothing` implementado            |
| 7  | Custo extraído fica gravado em custos_reais.json para que o dashboard o exiba               | VERIFIED  | `save_custo_real()` chamado no endpoint após sucesso; `test_upload_pdf_renders_confirmacao` valida que foi chamado com year_month e custo_eur correctos |
| 8  | CPE com espaço no texto é normalizado antes do lookup                                       | VERIFIED  | `test_cpe_com_espaco` PASSED: "PT000200003982208 2NT" -> "PT0002000039822082NT"             |
| 9  | Ingestão duplicada da mesma fatura não cria dados duplicados (idempotência)                 | VERIFIED  | `test_ingestao_pdf_idempotencia` PASSED: 2 inserções -> 1 row                              |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact                                                         | Expected                                | Status    | Details                              |
|------------------------------------------------------------------|-----------------------------------------|-----------|--------------------------------------|
| `requirements-docker.txt`                                        | pdfplumber dependency for Docker        | VERIFIED | Linha `pdfplumber==0.11.7` presente  |
| `requirements.txt`                                               | pdfplumber dependency for dev/test      | VERIFIED | Linha `pdfplumber==0.11.7` presente  |
| `src/web/services/extrator_pdf.py`                               | PDF extraction service (Meo + Endesa)   | VERIFIED | 273 linhas; funções extrair_fatura, extrair_texto_pdf, ingerir_pdf presentes |
| `tests/test_extrator_pdf.py`                                     | Unit tests for PDF extraction           | VERIFIED | 237 linhas; 8 testes (7 PASSED, 1 SKIPPED — fpdf não instalado) |
| `src/web/routes/upload.py`                                       | POST /upload/pdf endpoint               | VERIFIED | Endpoint registado; upload_pdf, ingerir_pdf, save_custo_real presentes |
| `src/web/templates/partials/upload_pdf.html`                     | Upload PDF form partial                 | VERIFIED | hx-post="/upload/pdf", accept=".pdf", hx-encoding multipart |
| `src/web/templates/partials/upload_pdf_confirmacao.html`         | Upload PDF confirmation partial         | VERIFIED | Renderiza formato, local, período, custo_eur, nota idempotência |
| `tests/test_upload_endpoint.py`                                  | Integration tests for upload PDF        | VERIFIED | 3 testes todos PASSED                |

---

### Key Link Verification

| From                                    | To                                           | Via                                    | Status    | Details                                                        |
|-----------------------------------------|----------------------------------------------|----------------------------------------|-----------|----------------------------------------------------------------|
| `src/web/services/extrator_pdf.py`      | `pdfplumber`                                 | `import pdfplumber; pdfplumber.open`   | WIRED    | Lazy import dentro de `extrair_texto_pdf()` — confirmado linha 196 |
| `src/web/services/extrator_pdf.py`      | `src/web/services/locais_service.py`         | `get_local_by_cpe`                     | WIRED    | Import no topo + chamado em `ingerir_pdf()` linha 243          |
| `src/web/routes/upload.py`              | `src/web/services/extrator_pdf.py`           | `from src.web.services.extrator_pdf import ingerir_pdf` | WIRED | Linha 10 do upload.py; chamado na linha 125 |
| `src/web/routes/upload.py`              | `src/web/services/data_loader.py`            | `save_custo_real`                      | WIRED    | Import linha 11; chamado linha 138 com custos_path, year_month, custo_eur |
| `src/web/routes/upload.py`              | `upload_pdf_confirmacao.html`                | `TemplateResponse`                     | WIRED    | Linhas 130-133 (erro) e 140-143 (sucesso)                     |
| `upload_pdf.html`                       | `POST /upload/pdf`                           | `hx-post="/upload/pdf"`                | WIRED    | Linha 5 do template; rota confirmada em router.routes          |

---

### Data-Flow Trace (Level 4)

| Artifact                              | Data Variable           | Source                         | Produces Real Data | Status   |
|---------------------------------------|-------------------------|--------------------------------|--------------------|----------|
| `upload_pdf_confirmacao.html`         | `resultado.custo_eur`   | `ingerir_pdf()` → `extrair_fatura()` → regex em texto PDF | Sim — extrai de regex sobre texto real do PDF | FLOWING |
| `upload_pdf_confirmacao.html`         | `resultado.year_month`  | `ingerir_pdf()` → `_parse_periodo_para_year_month()` | Sim | FLOWING |
| `upload_pdf_confirmacao.html`         | `resultado.location_name` | `get_local_by_cpe()` → SQLite `locais` | Sim — lookup na BD | FLOWING |
| `custos_reais.json`                   | `custo_eur`, `year_month` | `save_custo_real()` chamado no endpoint após ingestão SQLite | Sim — dupla persistência confirmada | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                         | Command                                                                                    | Result              | Status  |
|--------------------------------------------------|--------------------------------------------------------------------------------------------|---------------------|---------|
| /upload/pdf rota registada no router             | `python3 -c "from src.web.routes.upload import router; assert '/upload/pdf' in [r.path for r in router.routes]"` | OK | PASS |
| Testes de extracção passam                       | `pytest tests/test_extrator_pdf.py -q`                                                     | 7 passed, 1 skipped | PASS    |
| Testes de integração do endpoint passam          | `pytest tests/test_upload_endpoint.py -q`                                                  | 3 passed            | PASS    |
| Suite completa sem regressões                    | `pytest tests/ -x -q`                                                                      | 89 passed, 14 skipped | PASS  |

**Nota sobre o skip:** `test_extrair_texto_pdf_bytesio` é ignorado porque `fpdf2` não está instalado no ambiente de dev. O teste usa `pytest.importorskip("fpdf")` correctamente — não é falha, é comportamento esperado documentado no SUMMARY.

---

### Requirements Coverage

| Requirement | Source Plan  | Description                                                         | Status    | Evidence                                                                      |
|-------------|-------------|---------------------------------------------------------------------|-----------|-------------------------------------------------------------------------------|
| UPLD-03     | 08-01, 08-02 | Utilizador faz upload de PDF de fatura via browser                 | SATISFIED | Endpoint POST /upload/pdf funcional; formulário HTML com hx-post; 3 testes de integração verdes |
| UPLD-04     | 08-01, 08-02 | Sistema extrai total pago e período do PDF (Meo Energia + Endesa)   | SATISFIED | `extrair_fatura()` com parsers Meo e Endesa; gas explicitamente ignorado; 7 testes unitários verdes |

**Nota REQUIREMENTS.md:** Os requisitos UPLD-03 e UPLD-04 aparecem como `[x]` (completos) no ficheiro de requisitos. A tabela de rastreabilidade confirma ambos mapeados para Phase 8.

**Orphaned requirements:** Nenhum. Apenas UPLD-03 e UPLD-04 estão mapeados para Phase 8 em REQUIREMENTS.md — ambos cobertos pelos dois PLANs.

---

### Anti-Patterns Found

| File                                      | Line | Pattern                        | Severity | Impact  |
|-------------------------------------------|------|--------------------------------|----------|---------|
| Nenhum encontrado                         | —    | —                              | —        | —       |

**Verificação manual efectuada em:**
- `src/web/services/extrator_pdf.py` — sem TODO/FIXME/placeholder; lógica completa
- `src/web/routes/upload.py` — sem retornos estáticos; endpoint ligado a serviço real
- `src/web/templates/partials/upload_pdf_confirmacao.html` — renderiza variáveis dinâmicas (`resultado.custo_eur`, `resultado.year_month`, etc.); sem hardcoded values

---

### Human Verification Required

#### 1. Upload de PDF real Meo Energia

**Test:** Fazer upload de uma fatura PDF real da Meo Energia via browser (POST /upload/pdf).
**Expected:** A página de confirmação mostra o total correcto em EUR, o período correcto, e o local correspondente ao CPE do documento.
**Why human:** Os testes unitários usam texto sintético. A extracção de texto real por pdfplumber pode diferir do sintético (encoding, espaços, quebras de linha inesperadas). As regex têm confiança LOW para PDFs reais (sem amostra real disponível durante implementação — documentado no SUMMARY).

#### 2. Upload de PDF real Endesa (fatura com gás)

**Test:** Fazer upload de uma fatura Endesa real que inclua gás via browser.
**Expected:** A confirmação mostra apenas o total de electricidade, não o total da fatura ou o valor do gás.
**Why human:** Mesmo motivo — regex validadas contra texto sintético, não PDFs reais.

#### 3. Visibilidade no dashboard após upload

**Test:** Após upload bem-sucedido de um PDF, navegar ao dashboard e seleccionar o local correspondente.
**Expected:** O custo do mês importado aparece visível no gráfico ou tabela de custos reais.
**Why human:** Requer interacção entre o endpoint, o ficheiro `custos_reais.json` escrito, e o dashboard que o lê. Verificado programaticamente que `save_custo_real` é chamado, mas o rendering final no dashboard requer validação visual.

---

### Gaps Summary

Nenhum gap identificado. Todos os artefactos existem, são substantivos (não stubs), estão ligados, e os dados fluem correctamente desde a extracção PDF até à persistência dual (SQLite + JSON).

A única nota de atenção é a confiança LOW das regex para PDFs reais (sem amostras reais durante implementação), documentada pelo próprio executor no SUMMARY. Isto não é um gap — é um risco de qualidade que só pode ser validado com PDFs reais (ver Human Verification acima).

---

_Verified: 2026-03-31_
_Verifier: Claude (gsd-verifier)_
