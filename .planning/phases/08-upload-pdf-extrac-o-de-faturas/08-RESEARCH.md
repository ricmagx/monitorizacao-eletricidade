# Phase 8: Upload PDF + Extracção de Faturas — Research

**Researched:** 2026-03-31
**Domain:** PDF text extraction (pdfplumber), FastAPI file upload, SQLite idempotent write
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UPLD-03 | Utilizador faz upload de PDF de fatura via browser | FastAPI UploadFile pattern já existe em upload.py (XLSX) — replicar para PDF |
| UPLD-04 | Sistema extrai total pago e período do PDF (formatos Meo Energia + Endesa) | pdfplumber 0.11.7 já instalado, aceita BytesIO, extracção por regex em texto estruturado |
</phase_requirements>

---

## Summary

A fase implementa upload de PDF via browser (endpoint `POST /upload/pdf`) e extracção automática de dois campos — total pago em € e período de faturação — para dois formatos conhecidos: Meo Energia e Endesa. A detecção do local é feita por lookup do CPE extraído do texto do PDF na tabela `locais` (SQLite), usando `get_local_by_cpe()` já existente. O resultado é persistido em `custos_reais` com `on_conflict_do_nothing` para idempotência. O gás (presente em faturas Endesa multi-energia) é ignorado por design.

A decisão de stack está completamente fechada: **pdfplumber** (sem IA, texto estruturado) foi escolhido no STATE.md e já está instalado (v0.11.7). O padrão de upload está 100% implementado para XLSX — esta fase replica o mesmo padrão trocando parser e endpoint. A tabela `custos_reais` já existe no schema com as colunas necessárias (`location_id`, `year_month`, `custo_eur`, `source`, `created_at`) e UniqueConstraint `uq_custos_loc_month`.

**Recomendação principal:** Implementar em dois módulos separados — `src/web/services/extrator_pdf.py` (lógica de extracção, sem FastAPI) e `src/web/routes/upload.py` (endpoint POST /upload/pdf, já existente — adicionar route ao ficheiro existente). Sem nova Alembic migration necessária — o schema já suporta tudo.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pdfplumber | 0.11.7 | Extracção de texto de PDF | Decisão locked no STATE.md; já instalado; aceita BytesIO |
| FastAPI UploadFile | (fastapi>=0.104.0) | Recepção do ficheiro no endpoint | Já usado em POST /upload/xlsx |
| SQLAlchemy Core + sqlite_insert | (sqlalchemy>=2.0.0) | Escrita idempotente em custos_reais | Padrão do projecto, `on_conflict_do_nothing` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | — | Regex para extrair valores monetários e datas do texto PDF | Texto estruturado — regex suficiente, sem IA |
| io.BytesIO (stdlib) | — | Passar conteúdo do UploadFile ao pdfplumber sem disco | Evitar ficheiro temporário (diferença face ao XLSX) |
| tempfile (stdlib) | — | Alternativa se BytesIO falhar com pdfplumber | Fallback — pdfplumber.open aceita BytesIO directamente |

### Alternativas Consideradas

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pdfplumber | pypdf2 / pdfminer.six directo | pdfplumber já decidido e instalado; pypdf2 menos preciso no layout |
| pdfplumber | IA/LLM para extracção | Explicitamente out of scope (REQUIREMENTS.md: "Extracção PDF via IA — pdfplumber suficiente") |

**Instalação:** pdfplumber já está em `/usr/local/lib/python3.11`. Precisa de ser adicionado a `requirements-docker.txt`:

```bash
# Adicionar a requirements-docker.txt:
pdfplumber==0.11.7
```

**Verificação de versão:**
```bash
pip show pdfplumber  # Version: 0.11.7
```

---

## Architecture Patterns

### Estrutura de Ficheiros a Criar/Modificar

```
src/
├── web/
│   ├── routes/
│   │   └── upload.py              # MODIFICAR — adicionar POST /upload/pdf
│   ├── services/
│   │   └── extrator_pdf.py        # CRIAR — parsers Meo Energia + Endesa
│   └── templates/
│       └── partials/
│           └── upload_pdf.html    # CRIAR — formulário upload PDF (análogo a upload_xlsx.html)
tests/
└── test_extrator_pdf.py           # CRIAR — testes unitários dos parsers
```

### Pattern 1: Extracção de Texto com pdfplumber (BytesIO)

**O que é:** Ler conteúdo do UploadFile em memória, passar como BytesIO ao pdfplumber, concatenar texto de todas as páginas.
**Quando usar:** Sempre — evita ficheiro temporário no disco (diferença face ao XLSX que usa openpyxl e requer ficheiro).

```python
# Source: pdfplumber docs + anotação de tipo Union[str, Path, BufferedReader, BytesIO]
import pdfplumber
from io import BytesIO

async def extrair_texto_pdf(upload_file) -> str:
    content = await upload_file.read()
    with pdfplumber.open(BytesIO(content)) as pdf:
        texto = "\n".join(
            page.extract_text() or ""
            for page in pdf.pages
        )
    return texto
```

### Pattern 2: Detecção de Formato por CPE no Texto

**O que é:** Extrair CPE do texto do PDF (padrão `PT\d{18}[A-Z0-9]{2}` ou similar) e fazer lookup em `locais` via `get_local_by_cpe()`.
**Quando usar:** Ambos os formatos (Meo Energia e Endesa) incluem CPE no texto da fatura.

```python
# CPE pattern — baseado nos locais reais:
# Casa: PT0002000084968079SX (20 chars alfanuméricos)
# Apartamento: PT000200003982208 2NT (com espaço — normalizar removendo espaços)
import re

CPE_PATTERN_PDF = re.compile(r"(PT\d{16,18}[A-Z0-9 ]{1,4})")

def extrair_cpe_do_pdf(texto: str) -> str | None:
    m = CPE_PATTERN_PDF.search(texto)
    if m:
        return m.group(1).replace(" ", "")  # normalizar espaços
    return None
```

**Nota crítica:** O CPE do apartamento tem um espaço (`PT000200003982208 2NT`). O regex deve capturar com espaço e normalizar antes do lookup. A tabela `locais` guarda sem espaço — confirmar o valor real ao implementar.

### Pattern 3: Extracção de Total e Período por Regex

**O que é:** Regex específico por formato (Meo Energia vs Endesa) para extrair total em € e período.
**Quando usar:** Após identificar o formato pelo nome do fornecedor ou estrutura do texto.

```python
# Meo Energia — padrões prováveis (HIGH confidence na estrutura, LOW no regex exacto sem PDF real):
import re

# Total pago — ex: "Total a pagar: 45,32 €" ou "TOTAL 45,32 EUR"
TOTAL_MEO = re.compile(r"[Tt]otal\s+a\s+pagar[:\s]+(\d+[,\.]\d{2})\s*[€EUR]")

# Período — ex: "01-01-2026 a 31-01-2026" ou "Janeiro 2026"
PERIODO_MEO = re.compile(r"(\d{2}-\d{2}-\d{4})\s+a\s+(\d{2}-\d{2}-\d{4})")

# Endesa — padrões prováveis (estrutura semelhante mas labels diferentes)
TOTAL_ENDESA = re.compile(r"[Tt]otal\s+(?:da\s+)?[Ff]atura[:\s]+(\d+[,\.]\d{2})\s*[€EUR]")
PERIODO_ENDESA = re.compile(r"[Pp]er[íi]odo\s+de\s+[Cc]onsumo[:\s]+(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})")
```

**AVISO:** Os regex exactos para Meo Energia e Endesa são LOW confidence — não há amostras reais de PDF disponíveis no projecto. A implementação deve ser robusta a variações de formatting e testada com PDFs reais antes de validar os critérios de sucesso. Ver secção "Pitfalls".

### Pattern 4: Escrita Idempotente em custos_reais

**O que é:** Reutilizar `on_conflict_do_nothing` com `index_elements=["location_id", "year_month"]` — UniqueConstraint `uq_custos_loc_month` já existe no schema.
**Quando usar:** Sempre — evitar duplicados se o mesmo PDF for feito upload duas vezes.

```python
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from src.db.schema import custos_reais

with engine.begin() as conn:
    stmt = sqlite_insert(custos_reais).values(
        location_id=local["id"],
        year_month=year_month,   # formato "YYYY-MM"
        custo_eur=total_eur,
        source="pdf_upload",
    ).on_conflict_do_nothing(
        index_elements=["location_id", "year_month"]
    )
    result = conn.execute(stmt)
    inserido = result.rowcount > 0
```

### Pattern 5: Estrutura do Serviço de Extracção

**O que é:** Módulo `extrator_pdf.py` com função pública `extrair_fatura(bytes_content: bytes) -> dict`.
**Quando usar:** Manter lógica de extracção separada da route (testável independentemente).

```python
# src/web/services/extrator_pdf.py

def extrair_fatura(pdf_bytes: bytes) -> dict:
    """Extrai dados de fatura de PDF de electricidade.

    Returns:
        Dict com: erro (str|None), formato (str|None), cpe (str|None),
        year_month (str|None), custo_eur (float|None)

    Formatos suportados: 'meo_energia', 'endesa'
    """
    ...
```

### Anti-Patterns a Evitar

- **Usar ficheiro temporário para pdfplumber:** pdfplumber aceita BytesIO directamente — não criar ficheiro no disco como foi necessário para openpyxl/XLSX.
- **Regex sem normalização de whitespace:** PDFs frequentemente têm espaços extras, newlines, ou texto partido entre linhas. Usar `re.sub(r'\s+', ' ', texto)` antes de aplicar regex.
- **Assumir estrutura de página fixa:** PDFs de faturas podem ter layouts ligeiramente diferentes entre meses ou versões do template. Regex deve ser tolerante.
- **Detectar formato pelo nome do ficheiro:** O nome não é fiável — detectar pelo CPE (que mapeia para fornecedor em `locais`) ou por keywords no texto.
- **Importar gás da Endesa:** A fatura Endesa pode conter secções de gás (`GAS`, `Gas Natural`). O extractor deve filtrar explicitamente para apenas electricidade — success criterion 4 exige isto.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Parser PDF caseiro | pdfplumber | Lida com encoding, layout, multi-página, PDF/A |
| CPE lookup por texto | Nova função de lookup | `get_local_by_cpe()` já existente | Reutilizar locais_service.py |
| Idempotência da escrita | Lógica manual de check-before-insert | `on_conflict_do_nothing` SQLite | Já usado para consumo_mensal e comparacoes |
| Upload file handling | Guardar em disco, processar, apagar | BytesIO in-memory | pdfplumber aceita BytesIO; mais simples que padrão XLSX |

---

## Common Pitfalls

### Pitfall 1: Texto PDF com Quebras de Linha no Meio de Valores

**O que corre mal:** pdfplumber pode partir "45,32" como "45," numa linha e "32 €" noutra, ou inserir espaços em valores monetários.
**Porque acontece:** O PDF é um formato de layout — o texto é extraído na ordem visual, não semântica.
**Como evitar:** Normalizar o texto com `re.sub(r'\s+', ' ', texto)` antes de aplicar regex. Testar com PDF real.
**Sinais de alerta:** Regex não devolve match em PDF que visualmente tem o valor correcto.

### Pitfall 2: CPE do Apartamento com Espaço

**O que corre mal:** O CPE do apartamento é `PT000200003982208 2NT` (com espaço). O regex `PT\w+` não captura o espaço.
**Porque acontece:** CPE português pode ter espaço no formato oficial.
**Como evitar:** Regex deve incluir possível espaço: `PT[\w ]+?` ou `PT\d+\s*[A-Z0-9]+`. Normalizar removendo espaços antes do lookup na tabela `locais`.

### Pitfall 3: Fatura Endesa Multi-Energia Inclui Gás

**O que corre mal:** Fatura Endesa pode ter secções de electricidade E gás. Regex que captura o primeiro "Total" pode apanhar o total de gás ou o total combinado.
**Porque acontece:** O layout visual agrupa ambos no mesmo documento.
**Como evitar:** O extractor Endesa deve procurar explicitamente por keywords de electricidade ("Electricidade", "Eletricidade") antes de capturar o total. Nunca usar o "Total Fatura" genérico sem verificar que é da secção eléctrica.

### Pitfall 4: Regex Exacto Desconhecido Sem Amostras Reais

**O que corre mal:** Os labels exactos nas faturas Meo Energia e Endesa são desconhecidos (sem PDFs de amostra no repositório).
**Porque acontece:** Não há dados de teste reais disponíveis.
**Como evitar:** Implementar com múltiplos regex candidatos (lista de padrões alternativos) e testar contra PDF real antes de validar. Estruturar `extrator_pdf.py` para facilitar adicionar/ajustar padrões. Testes unitários devem usar texto de PDF sintético que simule o formato esperado.

### Pitfall 5: pdfplumber não está em requirements-docker.txt

**O que corre mal:** A app corre localmente (pdfplumber instalado em Mac), mas falha no Docker com `ModuleNotFoundError`.
**Porque acontece:** `requirements-docker.txt` foi criado sem pdfplumber (Phase 5 não precisava).
**Como evitar:** Adicionar `pdfplumber==0.11.7` a `requirements-docker.txt` como primeira tarefa.

---

## Code Examples

### Exemplo 1: Usar pdfplumber com BytesIO

```python
# Source: pdfplumber 0.11.7 — anotação de tipo confirmada: Union[str, Path, BufferedReader, BytesIO]
import pdfplumber
from io import BytesIO

def extrair_texto(pdf_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        partes = [page.extract_text() or "" for page in pdf.pages]
    texto = "\n".join(partes)
    # Normalizar whitespace para facilitar regex
    import re
    return re.sub(r"\s+", " ", texto)
```

### Exemplo 2: Padrão de Route Análogo ao XLSX (já implementado)

```python
# Baseado em src/web/routes/upload.py (POST /upload/xlsx existente)
@router.post("/upload/pdf", response_class=HTMLResponse)
async def upload_pdf(
    request: Request,
    ficheiro: UploadFile = File(...),
):
    templates = request.app.state.templates
    engine = request.app.state.db_engine

    content = await ficheiro.read()  # BytesIO — sem ficheiro temporário
    resultado = ingerir_pdf(content, engine)

    return templates.TemplateResponse(
        request=request,
        name="partials/upload_pdf_confirmacao.html",
        context={"erro": resultado.get("erro"), "resultado": resultado},
    )
```

### Exemplo 3: Escrita em custos_reais (schema já existe)

```python
# Source: padrão do projecto — idêntico a consumo_mensal em ingestao_xlsx.py
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from src.db.schema import custos_reais

with engine.begin() as conn:
    stmt = sqlite_insert(custos_reais).values(
        location_id=local["id"],
        year_month=year_month,
        custo_eur=total_eur,
        source="pdf_upload",
    ).on_conflict_do_nothing(
        index_elements=["location_id", "year_month"]
    )
    result = conn.execute(stmt)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Entrada manual de custo (formulário) | Upload PDF → extracção automática | Phase 8 | Elimina entrada manual para os formatos conhecidos |
| pdfminer.six directo | pdfplumber (wrapper sobre pdfminer.six) | — | API mais simples, melhor extracção de layout |

---

## Open Questions

1. **Regex exacto para Meo Energia e Endesa**
   - O que sabemos: Os PDFs têm texto estruturado; pdfplumber é adequado
   - O que não sabemos: Labels exactas ("Total a pagar", "Total fatura", etc.), formato da data, posição no documento
   - Recomendação: Implementar com regex flexíveis e múltiplos candidatos; testar contra PDF real antes de validar os success criteria; documentar os regex usados

2. **CPE do apartamento — valor real com ou sem espaço**
   - O que sabemos: `system.json` tem `PT000200XXXXXXXXXX` (placeholder); STATE.md menciona `PT000200003982208 2NT` com espaço
   - O que não sabemos: Formato exacto no PDF Endesa
   - Recomendação: O regex de CPE no extractor deve ser tolerante a espaços e normalizar antes do lookup

3. **Gás na fatura Endesa — como distinguir secções**
   - O que sabemos: A fatura Endesa pode ter electricidade e gás; gás deve ser ignorado
   - O que não sabemos: Estrutura exacta do layout da fatura Endesa
   - Recomendação: Procurar secção de electricidade por keyword antes de extrair total; se não encontrar keyword, retornar erro claro

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pdfplumber | Extracção PDF | Mac: sim | 0.11.7 | — |
| pdfplumber | requirements-docker.txt | NÃO (em falta) | — | Adicionar como Wave 0 task |
| python-multipart | POST multipart/form-data | já em requirements | >=0.0.6 | — |
| SQLite (custos_reais) | Persistência | ja existe (schema 001) | — | — |

**Dependência em falta sem fallback:**
- `pdfplumber==0.11.7` ausente de `requirements-docker.txt` — a app falha no Docker sem esta linha. Deve ser a primeira tarefa do Wave 0.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pytest.ini` (raiz do projecto) |
| Quick run command | `python3 -m pytest tests/test_extrator_pdf.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UPLD-03 | POST /upload/pdf retorna HTTP 200 com PDF válido | unit | `pytest tests/test_extrator_pdf.py::test_upload_pdf_meo_ok -x` | Wave 0 |
| UPLD-03 | POST /upload/pdf retorna erro claro com PDF não reconhecido | unit | `pytest tests/test_extrator_pdf.py::test_upload_pdf_formato_desconhecido -x` | Wave 0 |
| UPLD-04 | extrator Meo Energia extrai total e período correctos | unit | `pytest tests/test_extrator_pdf.py::test_extrair_meo_energia -x` | Wave 0 |
| UPLD-04 | extrator Endesa extrai total e período correctos | unit | `pytest tests/test_extrator_pdf.py::test_extrair_endesa -x` | Wave 0 |
| UPLD-04 | extrator Endesa não importa gás | unit | `pytest tests/test_extrator_pdf.py::test_endesa_ignora_gas -x` | Wave 0 |
| UPLD-04 | resultado gravado em custos_reais SQLite | unit | `pytest tests/test_extrator_pdf.py::test_ingestao_pdf_escreve_sqlite -x` | Wave 0 |
| UPLD-04 | upload do mesmo PDF não duplica dados | unit | `pytest tests/test_extrator_pdf.py::test_ingestao_pdf_idempotencia -x` | Wave 0 |

### Wave 0 Gaps

- [ ] `tests/test_extrator_pdf.py` — todos os testes acima (ficheiro não existe ainda)
  - Fixtures de texto PDF sintético para Meo Energia e Endesa
  - Fixtures com texto de PDF contendo gás (Endesa)
  - Fixture web_client já existe em conftest.py — reutilizável para testes de route

*(Se não houver PDFs reais disponíveis, os testes devem usar texto sintético que simule o output de `pdfplumber.extract_text()`)*

---

## Sources

### Primary (HIGH confidence)
- pdfplumber 0.11.7 — instalado localmente; anotação de tipo `Union[str, Path, BufferedReader, BytesIO]` confirmada por inspecção directa
- `src/db/schema.py` — colunas e constraints de `custos_reais` confirmados por inspecção directa
- `src/web/routes/upload.py` — padrão de UploadFile + BytesIO vs tempfile confirmado por leitura
- `.planning/STATE.md` — decisão "PDF: pdfplumber (Meo Energia + Endesa — texto estruturado, sem IA)" confirmada
- `requirements-docker.txt` — ausência de pdfplumber confirmada por leitura directa

### Secondary (MEDIUM confidence)
- Locais reais (STATE.md + system.json): Casa CPE `PT0002000084968079SX` (Meo Energia), Apartamento CPE com espaço `PT000200003982208 2NT` (Endesa)

### Tertiary (LOW confidence)
- Regex exactos para labels nas faturas Meo Energia e Endesa — não há PDFs reais disponíveis para verificar; estimativas baseadas em padrões típicos de faturas PT

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pdfplumber decidido e instalado; patterns do projecto verificados por leitura directa do código
- Architecture: HIGH — padrão XLSX já implementado é um modelo directo; schema DB já suporta tudo
- Pitfalls: HIGH (infra) / LOW (regex exactos) — os pitfalls de infra são factuais; os regex são LOW porque não há PDFs reais
- Wave 0 gaps: HIGH — test file ausente confirmado

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (30 dias — stack estável)
