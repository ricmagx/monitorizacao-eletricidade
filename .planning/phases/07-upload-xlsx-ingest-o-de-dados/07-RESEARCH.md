# Phase 7: Upload XLSX + Ingestão de Dados - Research

**Researched:** 2026-03-30
**Domain:** FastAPI file upload, HTMX forms, SQLAlchemy Core, CPE routing, tiagofelicia.pt integration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UPLD-01 | Utilizador faz upload de XLSX da E-REDES via browser | FastAPI `UploadFile` + `python-multipart` (já em requirements-docker.txt) |
| UPLD-02 | Sistema normaliza XLSX e armazena consumo em SQLite automaticamente | `eredes_to_monthly_csv.convert_xlsx_to_monthly_csv()` já existe — adaptar para escrever em SQLite |
| UPLD-05 | Sistema detecta o local correcto via CPE presente no ficheiro | `cpe_routing.extract_cpe_from_filename()` já existe — usar no endpoint de upload |
| CONF-01 | Utilizador pode criar e editar locais no UI (nome livre + CPE) | Nova tabela `locais` em SQLite + formulário HTMX + novo router |
| CONF-02 | Utilizador pode definir fornecedor actual por local | Campo `current_supplier` em tabela `locais` + formulário de edição |
| COMP-01 | Sistema consulta tiagofelicia.pt após cada upload de XLSX | `tiagofelicia_compare.analyse_with_tiago()` já existe — invocar em background após ingestão |
| COMP-02 | Resultado guardado em cache SQLite com data | Tabela `comparacoes` já existe em SQLite schema |
</phase_requirements>

---

## Summary

Phase 7 implementa o fluxo central do sistema v2.0: upload de XLSX via browser, ingestão em SQLite, e consulta a tiagofelicia.pt. O código de backend (parser XLSX, CPE routing) já existe e funciona — o trabalho é ligar estas peças via endpoints FastAPI novos, adaptar a escrita para SQLite em vez de CSV, e criar a tabela `locais` que ainda não existe no schema.

A dependência crítica é a gestão de locais: actualmente os locais vivem **apenas** em `config/system.json`. Phase 7 precisa de criar uma tabela `locais` em SQLite e um CRUD básico via UI, mas é necessário manter retrocompatibilidade com o `config/system.json` existente durante a transição — ou decidir explicitamente que o config.json passa a ser read-only e a verdade passa para SQLite.

A consulta a tiagofelicia.pt usa Playwright (síncrono, headless Chromium) e é lenta (~30-60s por mês analisado). Não pode bloquear o request HTTP de upload. O padrão correcto é invocar esta tarefa em `asyncio.get_event_loop().run_in_executor()` ou via thread separada após responder ao utilizador com confirmação imediata.

**Primary recommendation:** Criar endpoint `POST /upload/xlsx`, adaptar `convert_xlsx_to_monthly_csv()` para retornar dados em memória (sem escrever CSV), escrever directamente em tabela `consumo_mensal` via SQLAlchemy Core com `INSERT OR IGNORE` para idempotência, invocar tiagofelicia em background via `BackgroundTasks` do FastAPI.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.104.0 (já instalado) | Endpoint de upload + router locais | Stack existente |
| python-multipart | 0.0.22 (já instalado) | Parsing de `multipart/form-data` | Obrigatório para FastAPI UploadFile |
| openpyxl | 3.1.5 (já instalado) | Leitura do XLSX E-REDES | Já usado em `eredes_to_monthly_csv` |
| sqlalchemy | 2.0.23 (já instalado) | Escrita em tabela `consumo_mensal` + nova tabela `locais` | Stack existente (SQLAlchemy Core) |
| alembic | >=1.18.0 (já instalado) | Migração para adicionar tabela `locais` | Stack existente |
| htmx | 2.0.8 (já vendored) | Formulários de upload sem reload + feedback inline | Stack existente |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastapi.BackgroundTasks` | parte do FastAPI | Invocar tiagofelicia.pt após resposta | Sempre que a consulta tiagofelicia seja despoletada por upload |
| `playwright` (sync) | já em requirements.txt (não docker) | Consulta tiagofelicia.pt | Disponível no ambiente — NÃO está em requirements-docker.txt por design (poupa 500MB) |

**ATENÇÃO — playwright e Docker:** `requirements-docker.txt` exclui playwright deliberadamente (decisão v2.0 documentada em STATE.md). A consulta a tiagofelicia.pt via Playwright não pode correr dentro do container sem adicionar playwright + chromium. Ver secção Pitfalls.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `BackgroundTasks` | `asyncio.create_task` | BackgroundTasks é mais simples e integrado com FastAPI lifecycle — preferir |
| Playwright sync em thread | httpx para scraping directo | tiagofelicia.pt é JS-rendered — httpx sozinho não funciona; seria necessário Playwright de qualquer forma |

**Installation:** Sem instalações novas necessárias. Tudo já está em `requirements-docker.txt`.

---

## Architecture Patterns

### Recommended Project Structure

Novos ficheiros a criar em Phase 7:

```
src/
├── db/
│   ├── schema.py              # MODIFICAR: adicionar tabela locais
│   └── migrations/versions/
│       └── 002_add_locais.py  # NOVO: migração Alembic
├── web/
│   ├── routes/
│   │   ├── upload.py          # NOVO: POST /upload/xlsx
│   │   └── locais.py          # NOVO: GET/POST /locais, POST /locais/{id}/fornecedor
│   ├── services/
│   │   ├── ingestao_xlsx.py   # NOVO: adaptador eredes_to_monthly_csv → SQLite
│   │   └── locais_service.py  # NOVO: CRUD locais em SQLite
│   └── templates/
│       └── partials/
│           ├── upload_xlsx.html      # NOVO: formulário upload XLSX
│           ├── upload_confirmacao.html # NOVO: resposta HTMX após upload
│           └── locais_form.html      # NOVO: criar/editar local
```

### Pattern 1: FastAPI UploadFile + python-multipart

**What:** Receber ficheiro XLSX via `multipart/form-data`, processar em memória, responder com fragmento HTML (HTMX swap).
**When to use:** Sempre no endpoint de upload.

```python
# src/web/routes/upload.py
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
import tempfile, os
from pathlib import Path
from src.db.engine import engine
from src.web.services.ingestao_xlsx import ingerir_xlsx

router = APIRouter()

@router.post("/upload/xlsx", response_class=HTMLResponse)
async def upload_xlsx(
    request: Request,
    background_tasks: BackgroundTasks,
    ficheiro: UploadFile = File(...),
):
    templates = request.app.state.templates
    # Guardar temporariamente para openpyxl (que requer ficheiro no disco)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(await ficheiro.read())
        tmp_path = Path(tmp.name)
    try:
        resultado = ingerir_xlsx(tmp_path, ficheiro.filename, engine)
    finally:
        os.unlink(tmp_path)

    if resultado["erro"]:
        return templates.TemplateResponse(
            request=request,
            name="partials/upload_confirmacao.html",
            context={"erro": resultado["erro"]},
        )

    # Lançar consulta tiagofelicia em background
    background_tasks.add_task(
        consultar_tiagofelicia_bg, resultado["location_id"], engine
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/upload_confirmacao.html",
        context={"resultado": resultado},
    )
```

### Pattern 2: Ingestão XLSX → SQLite com idempotência

**What:** Adaptar `convert_xlsx_to_monthly_csv()` para retornar dados em memória e escrever em `consumo_mensal` com `INSERT OR REPLACE` (ou `ON CONFLICT DO NOTHING`).
**When to use:** Em `src/web/services/ingestao_xlsx.py`.

```python
# src/web/services/ingestao_xlsx.py
from sqlalchemy import insert
from src.db.schema import consumo_mensal
from src.backend.eredes_to_monthly_csv import convert_xlsx_to_monthly_csv_to_dict
from src.backend.cpe_routing import extract_cpe_from_filename, find_location_by_cpe

def ingerir_xlsx(tmp_path: Path, filename: str, engine) -> dict:
    # 1. Extrair CPE do nome de ficheiro
    cpe = extract_cpe_from_filename(filename)
    if not cpe:
        return {"erro": "CPE não detectado no ficheiro. Associe o ficheiro ao local manualmente."}

    # 2. Resolver location_id via SQLite (tabela locais)
    location = find_location_by_cpe_db(cpe, engine)
    if not location:
        return {"erro": f"CPE {cpe} não corresponde a nenhum local configurado."}

    # 3. Parser XLSX → dict em memória (sem escrever CSV)
    monthly_data = parse_xlsx_to_dict(tmp_path)  # Adaptar eredes_to_monthly_csv

    # 4. Escrever em SQLite com idempotência (UniqueConstraint já existe)
    meses_inseridos = 0
    with engine.begin() as conn:
        for ym, totals in monthly_data.items():
            stmt = insert(consumo_mensal).values(
                location_id=location["id"],
                year_month=ym,
                total_kwh=totals["total_kwh"],
                vazio_kwh=totals["vazio_kwh"],
                fora_vazio_kwh=totals["fora_vazio_kwh"],
            ).prefix_with("OR IGNORE")  # SQLite syntax para idempotência
            result = conn.execute(stmt)
            meses_inseridos += result.rowcount

    return {
        "erro": None,
        "location_id": location["id"],
        "location_name": location["name"],
        "cpe": cpe,
        "meses_inseridos": meses_inseridos,
        "meses_total": len(monthly_data),
        "periodo_inicio": min(monthly_data.keys()),
        "periodo_fim": max(monthly_data.keys()),
    }
```

**Nota crítica:** `eredes_to_monthly_csv.convert_xlsx_to_monthly_csv()` escreve para ficheiro CSV. Precisa de uma variante que retorne `dict[str, dict]` em vez de escrever para disco. A função existente tem toda a lógica de parsing — criar `parse_xlsx_to_dict(path)` que reutilize a lógica interna sem a parte de escrita CSV.

### Pattern 3: Tabela `locais` em SQLite

**What:** Nova tabela para substituir a leitura de locais de `config/system.json`. Permite CRUD via UI.
**When to use:** Alembic migration + schema.py.

```python
# src/db/schema.py — adicionar
locais = Table(
    "locais", metadata,
    Column("id", String(64), primary_key=True),   # slug: "casa", "apartamento"
    Column("name", String(128), nullable=False),
    Column("cpe", String(64), nullable=False, unique=True),
    Column("current_supplier", String(128)),
    Column("current_plan_contains", String(128)),
    Column("power_label", String(32)),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)
```

**Estratégia de migração config → SQLite:** No arranque (lifespan), se a tabela `locais` estiver vazia e `config/system.json` tiver locations, copiar automaticamente os locais para SQLite. Isto garante que o sistema existente não quebra.

### Pattern 4: BackgroundTasks para tiagofelicia.pt

**What:** Após upload bem-sucedido, responder imediatamente ao utilizador e lançar consulta tiagofelicia em background.
**When to use:** Sempre que COMP-01 for despoletado.

```python
def consultar_tiagofelicia_bg(location_id: str, engine):
    """Executado em background após upload XLSX."""
    # Ler consumo de SQLite
    # Invocar analyse_with_tiago() de tiagofelicia_compare.py
    # Guardar resultado em tabela comparacoes com cached_at = now()
    pass
```

**PROBLEMA CRÍTICO:** `tiagofelicia_compare.analyse_with_tiago()` usa `playwright.sync_api` — código síncrono bloqueante que corre Chromium. O FastAPI `BackgroundTasks` corre na thread do event loop assíncrono. Chamar código síncrono bloqueante directamente vai bloquear o event loop.

**Solução correcta:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1)

async def consultar_tiagofelicia_async(location_id: str, engine):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, consultar_tiagofelicia_sync, location_id, engine)
```

Ou mais simplesmente, dado que `BackgroundTasks` já corre em thread pool por padrão no FastAPI quando a função é síncrona (não `async def`): **definir `consultar_tiagofelicia_bg` como função síncrona regular** (não `async def`) — FastAPI detecta automaticamente e corre em thread pool.

**BLOQUEADOR DOCKER:** playwright não está em `requirements-docker.txt`. Ver Pitfall 3.

### Pattern 5: HTMX Upload Form + Feedback Inline

**What:** Formulário com `enctype="multipart/form-data"`, HTMX POST, resposta com partial HTML.
**When to use:** `partials/upload_xlsx.html`.

```html
<!-- partials/upload_xlsx.html — conforme UI-SPEC Phase 6 -->
<div class="card">
  <h2>Importar XLSX E-REDES</h2>
  <form hx-post="/upload/xlsx"
        hx-target="#upload-xlsx-resultado"
        hx-swap="innerHTML"
        hx-encoding="multipart/form-data"
        hx-indicator="#upload-xlsx-spinner">
    <div class="form-inline">
      <input type="file" name="ficheiro" accept=".xlsx" required id="xlsx-input">
      <span id="xlsx-filename" class="text-muted"></span>
      <button type="submit" class="btn-primary" id="xlsx-submit">Importar XLSX</button>
      <span id="upload-xlsx-spinner" class="htmx-indicator">A processar...</span>
    </div>
  </form>
  <div id="upload-xlsx-resultado"></div>
</div>
```

### Anti-Patterns to Avoid

- **Guardar ficheiro XLSX permanentemente:** Ficheiro é temporário — processar em memória e eliminar. Não criar `data/uploads/` como armazenamento permanente.
- **Escrever em CSV E em SQLite:** A versão v2.0 usa SQLite como source of truth. Não escrever o CSV processado — só SQLite.
- **Chamar tiagofelicia de forma síncrona no request:** Bloqueia o browser durante 30-180s. Usar BackgroundTasks.
- **Gerir locais apenas em config/system.json:** Phase 7 move a verdade para SQLite. O config.json deve ser migrado automaticamente para SQLite no arranque.
- **UniqueConstraint silencioso sem feedback:** Idempotência deve ter resposta explícita ao utilizador — "Dados já importados para este período."

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing XLSX | Parser novo | `eredes_to_monthly_csv.convert_xlsx_to_monthly_csv()` adaptado | Lógica de CPE, vazio/fora vazio, bounds check já existe e testada |
| CPE detection | Regex nova | `cpe_routing.extract_cpe_from_filename()` | Já existe, testada, baseada em ficheiros reais |
| Idempotência de upload | Lógica de dedup manual | `UniqueConstraint("location_id", "year_month")` já em schema + `INSERT OR IGNORE` | Constraint a nível de BD é mais robusto |
| File upload handling | Parsing manual de multipart | `FastAPI UploadFile` + `python-multipart` | Já em requirements, padrão oficial FastAPI |
| Background tasks | Thread manual / subprocess | `fastapi.BackgroundTasks` (sync function) | Integrado no lifecycle FastAPI |
| Schema migrations | ALTER TABLE manual | Alembic migration `002_add_locais.py` | Stack existente, padrão do projecto |

**Key insight:** O backend de processamento (XLSX parser, CPE routing) é 100% reutilizável. Phase 7 é principalmente "ligação de peças" + nova tabela `locais` + endpoints de upload e gestão de locais.

---

## Common Pitfalls

### Pitfall 1: CPE em XLSX interno vs. nome de ficheiro

**What goes wrong:** `cpe_routing.extract_cpe_from_filename()` extrai CPE do **nome do ficheiro** (ex: `Consumos_PT0002000084968079SX_2026-02-07.xlsx`). Se o utilizador renomear o ficheiro antes de fazer upload, o CPE fica perdido.

**Why it happens:** O XLSX da E-REDES também contém o CPE em células internas (cabeçalho da folha). O código actual não usa essa informação.

**How to avoid:** Implementar fallback: se CPE não for encontrado no nome de ficheiro, tentar extrair do conteúdo interno do XLSX (procurar "PT000..." nas primeiras linhas da folha). Alternativa mais simples: se CPE não detectado, mostrar selector manual de local ao utilizador em vez de erro imediato.

**Warning signs:** Upload falha sempre com "CPE não detectado" quando ficheiros são renomeados.

### Pitfall 2: `convert_xlsx_to_monthly_csv()` escreve para disco

**What goes wrong:** A função existente em `eredes_to_monthly_csv.py` **escreve obrigatoriamente** para um ficheiro CSV de saída. Não tem modo "retornar dict em memória".

**Why it happens:** Foi desenhada para uso como CLI tool e módulo de pipeline.

**How to avoid:** Refactorizar para extrair a lógica de parsing num método privado `_parse_xlsx_to_monthly_dict(path) -> dict[str, dict]` e manter a função pública existente como wrapper que chama este método + escreve CSV. O serviço de ingestão SQLite usa o método privado directamente.

**Warning signs:** Upload cria ficheiros CSV temporários no filesystem do container.

### Pitfall 3: Playwright não está em requirements-docker.txt

**What goes wrong:** `tiagofelicia_compare.analyse_with_tiago()` usa `from playwright.sync_api import sync_playwright`. Este import falha dentro do container Docker porque playwright não está em `requirements-docker.txt` (decisão deliberada — poupa 500MB).

**Why it happens:** Decisão documentada em STATE.md: "requirements-docker.txt exclui playwright — upload manual substituiu E-REDES download, poupa ~500MB."

**How to avoid:** Há duas opções:
  - **Opção A (recomendada):** Adicionar playwright a `requirements-docker.txt` + `RUN playwright install chromium --with-deps` no Dockerfile. Aumenta imagem em ~500MB mas COMP-01 fica completo.
  - **Opção B:** Substituir tiagofelicia.pt scraping por `httpx` + `beautifulsoup4` se o site tiver conteúdo sem JS. **Verificar:** o site usa JavaScript para renderizar a tabela (a função existente usa `page.wait_for_timeout(4000)` — claramente JS-rendered). Opção B provavelmente não funciona.
  - **Opção C (defer):** COMP-01/COMP-02 são requisitos de Phase 7 mas a consulta tiagofelicia pode ser marcada como "em progress" na UI sem bloquear o upload — completar em Phase 10.

**DECISÃO NECESSÁRIA antes de planear:** Confirmar se Playwright entra no Docker em Phase 7 ou se COMP-01/COMP-02 ficam diferidos para Phase 10.

**Warning signs:** `ModuleNotFoundError: No module named 'playwright'` nos logs do container.

### Pitfall 4: Locais em config/system.json vs SQLite — dupla fonte de verdade

**What goes wrong:** O sistema actual lê locais de `config/system.json`. Phase 7 cria tabela `locais` em SQLite. Se o dashboard continua a ler de config.json e o upload escreve em SQLite, há divergência.

**Why it happens:** Migração incremental sem definir qual é a source of truth.

**How to avoid:** No arranque (lifespan), migrar locais de config.json para SQLite se tabela estiver vazia. Depois de Phase 7, todos os componentes lêem locais de SQLite. O config.json pode ficar como bootstrap inicial mas não deve ser mais a fonte operacional.

**Warning signs:** Local criado via UI não aparece no selector; upload detecta CPE mas não encontra local.

### Pitfall 5: HTMX encoding para file upload

**What goes wrong:** HTMX por defeito usa `application/x-www-form-urlencoded`. Para file upload é obrigatório `multipart/form-data`. Sem `hx-encoding="multipart/form-data"`, o ficheiro não é enviado.

**Why it happens:** HTMX não detecta automaticamente `<input type="file">`.

**How to avoid:** Sempre usar `hx-encoding="multipart/form-data"` em formulários com file inputs. Verificar também que FastAPI recebe `UploadFile` (não `str`).

**Warning signs:** Ficheiro chega com tamanho 0 ou conteúdo vazio; FastAPI lança `422 Unprocessable Entity`.

### Pitfall 6: `eredes_to_monthly_csv.py` tem `from __future__ import annotations` mas usa `Any` sem import

**What goes wrong:** A linha 40 de `eredes_to_monthly_csv.py` usa `Any` em `def pick_sheet(workbook) -> Any:` mas `Any` não está importado no topo do ficheiro (só `from __future__ import annotations`).

**Why it happens:** Bug latente no código existente — `from __future__ import annotations` adia a avaliação das type hints, por isso o erro não é visível em runtime normal, mas pode falhar em análise estática ou quando o módulo é importado em contextos diferentes.

**How to avoid:** Adicionar `from typing import Any` ao ficheiro ao refactorizar.

---

## Code Examples

### Inserção idempotente em SQLite (SQLAlchemy Core)

```python
# Source: SQLAlchemy Core docs + SQLite INSERT OR IGNORE syntax
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

stmt = sqlite_insert(consumo_mensal).values(
    location_id=location_id,
    year_month=ym,
    total_kwh=totals["total_kwh"],
    vazio_kwh=totals["vazio_kwh"],
    fora_vazio_kwh=totals["fora_vazio_kwh"],
).on_conflict_do_nothing(
    index_elements=["location_id", "year_month"]  # referencia à UniqueConstraint
)
with engine.begin() as conn:
    result = conn.execute(stmt)
    # result.rowcount == 0 se linha já existia (idempotente)
```

**Nota:** `sqlalchemy.dialects.sqlite.insert` tem suporte nativo para `on_conflict_do_nothing()` — preferir a este em vez de `INSERT OR IGNORE` literal.

### FastAPI BackgroundTasks com função síncrona

```python
# Source: FastAPI docs — BackgroundTasks
# Funções síncronas (sem async def) são corridas em thread pool automaticamente
from fastapi import BackgroundTasks

def tarefa_sincrona(arg1: str):
    # Código bloqueante aqui (ex: playwright)
    pass

@router.post("/upload/xlsx")
async def upload_xlsx(background_tasks: BackgroundTasks, ...):
    # ... processar upload ...
    background_tasks.add_task(tarefa_sincrona, arg1="valor")
    return response  # Retorna imediatamente; tarefa_sincrona corre depois
```

### Alembic migration para tabela locais

```python
# src/db/migrations/versions/002_add_locais.py
def upgrade():
    op.create_table(
        'locais',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('cpe', sa.String(64), nullable=False, unique=True),
        sa.Column('current_supplier', sa.String(128)),
        sa.Column('current_plan_contains', sa.String(128)),
        sa.Column('power_label', sa.String(32)),
        sa.Column('created_at', sa.DateTime),
    )

def downgrade():
    op.drop_table('locais')
```

### Seed automático de locais (lifespan)

```python
# src/web/app.py — lifespan update
from src.db.schema import locais
from sqlalchemy import select

@asynccontextmanager
async def lifespan(app: FastAPI):
    metadata.create_all(engine)
    # Seed locais de config/system.json se tabela vazia
    _seed_locais_from_config(engine, PROJECT_ROOT / "config" / "system.json")
    app.state.db_engine = engine
    yield

def _seed_locais_from_config(engine, config_path: Path):
    """Migra locais de config/system.json para SQLite se tabela estiver vazia."""
    try:
        config = json.loads(config_path.read_text())
        locations = config.get("locations", [])
    except Exception:
        return
    with engine.begin() as conn:
        existing = conn.execute(select(locais)).fetchall()
        if existing:
            return  # Já tem dados — não sobrescrever
        for loc in locations:
            conn.execute(insert(locais).values(
                id=loc["id"],
                name=loc["name"],
                cpe=loc.get("cpe", ""),
                current_supplier=loc.get("current_contract", {}).get("supplier"),
                current_plan_contains=loc.get("current_contract", {}).get("current_plan_contains"),
                power_label=loc.get("current_contract", {}).get("power_label"),
            ))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Locais em config/system.json | Locais em SQLite (tabela `locais`) | Phase 7 | Permite CRUD via UI sem editar ficheiros |
| Consumo em CSV ficheiros planos | Consumo em SQLite (`consumo_mensal`) | Phase 5 decidido, Phase 7 implementa | Histórico multi-ano, queries SQL |
| Pipeline CLI batch | Upload web individual | Phase 7 | Utilizador controla quando ingerir dados |
| `data_loader.load_locations()` lê JSON | `locais_service.get_all_locais()` lê SQLite | Phase 7 | Todas as rotas devem usar o novo service |

---

## Open Questions

1. **Playwright no Docker (COMP-01/COMP-02)**
   - What we know: tiagofelicia.pt requer JavaScript rendering; playwright não está em requirements-docker.txt; imagem aumenta ~500MB com playwright + chromium.
   - What's unclear: Se o utilizador quer playwright no Docker em Phase 7 ou prefere diferir a consulta tiagofelicia para Phase 10 (onde está COMP-03/COMP-04 de qualquer forma).
   - Recommendation: **Confirmar com o utilizador.** Se COMP-01/COMP-02 devem ser completados em Phase 7, adicionar playwright ao Dockerfile. Se aceitável diferir, o upload XLSX pode completar sem disparar tiagofelicia e o plano de Phase 7 omite COMP-01/COMP-02 temporariamente.

2. **Formato de CPE em nome de ficheiro vs. conteúdo interno**
   - What we know: `cpe_routing.extract_cpe_from_filename()` usa regex no nome; funciona para ficheiros com nome padrão E-REDES.
   - What's unclear: Se utilizadores podem fazer upload de ficheiros renomeados (sem CPE no nome).
   - Recommendation: Implementar fallback de extracção do conteúdo interno XLSX como segundo nível; se falhar ambos, mostrar selector manual de local.

3. **Compatibilidade data_loader com SQLite**
   - What we know: `src/web/services/data_loader.py` lê de ficheiros CSV e JSON. O dashboard usa estas funções. Em Phase 7, consumo passa a viver em SQLite.
   - What's unclear: Se o dashboard deve continuar a ler de CSV (backward compat) ou migrar para SQLite em Phase 7.
   - Recommendation: Phase 7 foca no upload/ingestão. Dashboard leitura pode continuar de CSV/JSON para não quebrar Phase 4-era code. A migração completa do dashboard para SQLite acontece em Phase 9.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Runtime | ✓ | 3.11.14 | — |
| openpyxl | XLSX parsing | ✓ | 3.1.5 | — |
| python-multipart | File upload | ✓ | 0.0.22 | — |
| sqlalchemy | DB writes | ✓ | 2.0.23 | — |
| alembic | Migrations | ✓ | (em requirements-docker.txt) | — |
| fastapi | HTTP endpoints | ✓ | (em requirements-docker.txt) | — |
| playwright | tiagofelicia scraping | ✗ (não em Docker) | — | Diferir COMP-01/COMP-02 para Phase 10 |

**Missing dependencies with no fallback:** Nenhuma que bloqueie upload XLSX.

**Missing dependencies with fallback:**
- playwright: não está em requirements-docker.txt. Fallback = diferir consulta tiagofelicia. Se COMP-01/COMP-02 são obrigatórios em Phase 7, adicionar playwright ao Dockerfile (Wave 0 task).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pytest.ini` (existe — `testpaths = tests`, `pythonpath = . src/backend`) |
| Quick run command | `pytest tests/test_web_upload.py tests/test_ingestao_xlsx.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UPLD-01 | Upload de ficheiro XLSX via POST /upload/xlsx retorna HTTP 200 | integration | `pytest tests/test_web_upload.py::test_upload_xlsx_ok -x` | ❌ Wave 0 |
| UPLD-02 | Após upload, linha inserida em consumo_mensal SQLite | integration | `pytest tests/test_ingestao_xlsx.py::test_ingestao_escreve_sqlite -x` | ❌ Wave 0 |
| UPLD-05 | CPE detectado do nome de ficheiro → location_id correcto | unit | `pytest tests/test_ingestao_xlsx.py::test_cpe_routing -x` | ❌ Wave 0 |
| CONF-01 | POST /locais cria local e fica visível no selector | integration | `pytest tests/test_web_locais.py::test_criar_local -x` | ❌ Wave 0 |
| CONF-02 | POST /locais/{id}/fornecedor actualiza current_supplier | integration | `pytest tests/test_web_locais.py::test_editar_fornecedor -x` | ❌ Wave 0 |
| COMP-01 | Após upload, BackgroundTask é registada (não bloqueia response) | unit | `pytest tests/test_web_upload.py::test_background_task_registada -x` | ❌ Wave 0 |
| COMP-02 | Resultado tiagofelicia gravado em comparacoes com cached_at | unit/mock | `pytest tests/test_ingestao_xlsx.py::test_comparacao_guardada -x` | ❌ Wave 0 |
| — | Upload idempotente: segundo upload não duplica dados | unit | `pytest tests/test_ingestao_xlsx.py::test_idempotencia -x` | ❌ Wave 0 |
| — | Upload com ficheiro sem CPE no nome retorna erro útil | unit | `pytest tests/test_ingestao_xlsx.py::test_cpe_nao_detectado -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_web_upload.py tests/test_ingestao_xlsx.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green antes de `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_web_upload.py` — testes de integração do endpoint POST /upload/xlsx
- [ ] `tests/test_ingestao_xlsx.py` — testes unitários de ingestão XLSX → SQLite, CPE routing, idempotência
- [ ] `tests/test_web_locais.py` — testes de integração dos endpoints de gestão de locais
- [ ] `conftest.py` — adicionar fixtures: `sample_xlsx_file`, `db_engine_test`, `locais_seed`

*(Infraestrutura pytest existente — pytest.ini + conftest.py base já existem. Só faltam os novos ficheiros de teste.)*

---

## Project Constraints (from CLAUDE.md)

Sem CLAUDE.md local no projecto. Constraints do CLAUDE.md global aplicáveis:

- Responder em português europeu (PT-PT)
- Soluções práticas e directas — sem over-engineering
- Docker/Linux como plataforma alvo (sem launchd, osascript, paths macOS)
- SQLite como store de dados (não ficheiros planos após Phase 7)
- Upload manual via browser (não download automático E-REDES — fora de scope)

---

## Sources

### Primary (HIGH confidence)
- Código fonte do projecto (`src/db/schema.py`, `src/web/app.py`, `src/backend/eredes_to_monthly_csv.py`, `src/backend/cpe_routing.py`) — análise directa
- `requirements-docker.txt` — versões confirmadas por leitura directa
- `config/system.json` — estrutura de locais existente
- `.planning/phases/06-ui-design-ui-phase/06-UI-SPEC.md` — UI contract para Phase 7 (formulários de upload, copywriting, estados)
- `.planning/STATE.md` — decisões v2.0 documentadas (playwright excluído do Docker, SQLite como store)

### Secondary (MEDIUM confidence)
- FastAPI docs pattern para `UploadFile` + `BackgroundTasks` — padrões estáveis, verificados via conhecimento de treinamento (FastAPI >= 0.104)
- SQLAlchemy Core `sqlalchemy.dialects.sqlite.insert` com `on_conflict_do_nothing()` — padrão documentado

### Tertiary (LOW confidence)
- Estimativa de 30-180s para consulta tiagofelicia.pt — baseado na análise do código (4 segundos de timeout por simulação × N meses)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tudo já instalado, versões verificadas directamente
- Architecture: HIGH — baseado em código existente do projecto
- Pitfalls: HIGH (Pitfalls 1-5) / MEDIUM (Pitfall 6 — bug latente)
- Open Questions: identificadas como bloqueadores reais que precisam de decisão antes de planear

**Research date:** 2026-03-30
**Valid until:** 2026-06-30 (stack estável; bibliotecas em versões fixas em requirements)
