# Phase 4: Web Dashboard MVP - Research

**Researched:** 2026-03-30
**Domain:** FastAPI + HTMX + Jinja2 + Chart.js — local read-only dashboard consuming pipeline flat files
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** FastAPI + HTMX + Jinja2 + Chart.js — stack confirmado. Chart.js e HTMX servidos como ficheiros estáticos locais (sem CDN, sem build step).
- **D-02:** Módulo web em `src/web/` — entry point `uvicorn src.web.app:app` (conforme success criteria do ROADMAP).
- **D-03:** Sem autenticação — ferramenta local, utilizador único.
- **D-04:** LaunchAgent automático — novo plist launchd que arranca o uvicorn no login do sistema. A dashboard fica disponível em background.
- **D-05:** Browser manual — o utilizador navega para `http://localhost:8000` quando quiser. O plist não abre o browser automaticamente.
- **D-06:** Formulário inline na dashboard (HTMX + POST). O utilizador introduz o custo real da factura directamente na dashboard, mês a mês, por local. A dashboard persiste os valores num ficheiro JSON (`data/{local}/custos_reais.json`).
- **D-07:** Quando não existe custo real para um mês, omitir a linha no gráfico DASH-03. Meses sem dado mostram apenas a estimativa calculada — sem indicador de "pendente".
- **D-08:** Top-5 fornecedores por custo anual estimado + fornecedor actual (mesmo que não esteja no top-5). O fornecedor actual destacado visualmente na tabela.
- **D-09:** Banner colorido com poupança estimada: "Podes poupar ~X €/ano mudando para [Fornecedor]". Só aparece se a poupança estimada for significativa (limiar: > 50 €/ano — deixar ao planner se o valor deve ser configurável). Baseado nos dados do último relatório disponível.

### Claude's Discretion

- Layout geral da página (organização dos widgets, selector de local, disposição dos gráficos e tabela).
- Versões específicas de HTMX e Chart.js (ROADMAP menciona HTMX 2.0.x e Chart.js 4.4.x como referência).
- Schema exacto do ficheiro `custos_reais.json`.
- Limiar exacto para exibir o banner de recomendação (> 50 €/ano é sugestão, não decisão locked).
- Indicador de confiança na recomendação (DASH-06) — planner decide se inclui e como.

### Deferred Ideas (OUT OF SCOPE)

- **Importação de PDF da factura por OCR** — explicitamente fora de scope v1 (REQUIREMENTS.md Out of Scope: INT-03). A implementar em v2.
- DASH-07 (simulação retroactiva), DASH-08 (comparação homólogo via REQUIREMENTS.md), DASH-09 (frescura avançada) — podem ou não estar no scope desta fase (ver REQUIREMENTS.md traceability; estão marcados Phase 4 Pending mas o CONTEXT.md limita scope a DASH-01 a DASH-06 + sucesso criteria DASH-09 de frescura simples).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Setup FastAPI + Jinja2 + HTMX (ficheiro estático local) + Chart.js (ficheiro estático local) — sem build step | FastAPI 0.104.1 + uvicorn 0.41.0 + Jinja2 3.1.6 confirmados instalados; HTMX 2.0.8 e Chart.js 4.5.1 disponíveis para download como ficheiros estáticos |
| DASH-02 | Gráfico de consumo mensal (kWh, barras empilhadas vazio/fora_vazio) ao longo do tempo, por local | CSV schema confirmado: `year_month,total_kwh,vazio_kwh,fora_vazio_kwh`; Chart.js stacked bar chart é um padrão directo |
| DASH-03 | Gráfico €/mês: custo real da factura + estimativa calculada — sobrepostos no mesmo eixo temporal | Chart.js mixed/combo chart (bar + line); custos reais persistidos em `data/{local}/custos_reais.json` (D-06) |
| DASH-04 | Modelo de dados para custo real da factura: campo de entrada manual por mês via formulário na dashboard | HTMX hx-post para POST endpoint FastAPI; schema `custos_reais.json` a definir pelo planner |
| DASH-05 | Tabela de ranking de comercializadores por custo anual estimado | JSON de análise contém `history[].top_3` e `history[].current_supplier_result` com `total_eur` por mês; ranking por custo anual = soma de `total_eur` por fornecedor ao longo dos meses disponíveis |
| DASH-06 | Recomendação de mudança com poupança estimada e indicador de confiança | `monthly_status.json` contém `latest_saving_vs_current_eur` (46.54 €) e `latest_recommendation`; análise JSON contém `history_summary.latest_top_3` e `latest_current_supplier_result` |
</phase_requirements>

---

## Summary

A Phase 4 é puramente uma camada de apresentação sobre ficheiros planos já existentes. O pipeline (Phases 1-3) produz três artefactos que a dashboard consome em modo read-only: `data/{local}/processed/consumo_mensal_atual.csv` (consumo por mês), `data/{local}/processed/analise_tiagofelicia_atual.json` (ranking de fornecedores por mês histórico), e `state/{local}/monthly_status.json` (estado do último run). A única escrita que a dashboard faz é em `data/{local}/custos_reais.json` quando o utilizador introduz o custo real da factura.

O stack (FastAPI + HTMX + Jinja2 + Chart.js) está completamente confirmado e os pacotes Python necessários já estão instalados na máquina (FastAPI 0.104.1, uvicorn 0.41.0, Jinja2 3.1.6, httpx 0.28.1, python-multipart 0.0.22). HTMX 2.0.8 e Chart.js 4.5.1 são as versões mais recentes e os seus URLs de download estático foram verificados. O único risco técnico relevante é que o JSON de análise (`analise_tiagofelicia_atual.json`) não tem um campo `ranking` de topo — o ranking DASH-05 tem de ser calculado pela dashboard a partir de `history[].top_3` e `history[].current_supplier_result`.

A nota de risco sobre dados de duas épocas (DASH-06 delta ano-a-ano) é confirmada: o CSV de `casa` tem apenas 11 meses de dados (jan-nov 2025); não há dados de 2024 para comparação homóloga. O success criteria da fase menciona delta ano-a-ano (critério 6) mas o CONTEXT.md mapeia isso como DASH-06 com "apenas se poupança significativa" — o planner deve verificar se delta ano-a-ano está mesmo em scope ou pertence a DASH-08 (deferred).

**Primary recommendation:** Implementar `src/web/` como módulo FastAPI autónomo que lê ficheiros planos — sem acesso a módulos `src/backend/` em runtime. O selector de local é o único elemento HTMX dinâmico obrigatório; todos os dados de um local carregam de uma vez.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.104.1 (instalado) | Web framework, routes, JSON responses | Já no projecto; async nativo; serve ficheiros estáticos; StaticFiles + Jinja2 nativos |
| uvicorn | 0.41.0 (instalado) | ASGI server, entry point `uvicorn src.web.app:app` | Recomendado pela FastAPI; arranque simples; compatível com launchd |
| Jinja2 | 3.1.6 (instalado) | Templating HTML server-side | Integração nativa FastAPI via `Jinja2Templates` |
| HTMX | 2.0.8 (CDN verificado) | Swap parcial de HTML sem JS custom | Ficheiro estático local; selector de local + formulário custo real |
| Chart.js | 4.5.1 (CDN verificado) | Gráficos de barras e linha | Ficheiro estático local; sem dependências; stacked bar nativo |
| python-multipart | 0.0.22 (instalado) | Parse de `Form()` no FastAPI | Obrigatório para POST de formulários HTMX |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 (instalado) | TestClient para testes FastAPI | Testes de routes com `from fastapi.testclient import TestClient` |
| pytest | 7.4.3 (instalado) | Framework de testes | Já usado no projecto; testes de routes web |
| aiofiles | 25.1.0 (instalado) | Leitura assíncrona de ficheiros | Opcional — FastAPI aceita leitura síncrona em routes normais |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTMX (server-side swap) | Alpine.js / Vanilla JS | HTMX é lock decision (D-01); Alpine seria mais flexível mas viola D-01 |
| Chart.js estático local | Plotly / ApexCharts | Chart.js é lock decision; Plotly mais pesado, sem vantagem para este caso |
| Jinja2 server-side | React/Vue SPA | Sem build step é requisito (D-01); SPA viola princípio |

**Installation (pacotes em falta):**
```bash
# Todos os pacotes necessários já estão instalados.
# Verificar: pip3 show fastapi uvicorn jinja2 python-multipart httpx aiofiles
```

**Download ficheiros estáticos (a fazer na Wave 0):**
```bash
mkdir -p src/web/static/vendor
curl -o src/web/static/vendor/htmx.min.js \
  https://unpkg.com/htmx.org@2.0.8/dist/htmx.min.js
curl -o src/web/static/vendor/chart.umd.min.js \
  https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/web/
├── __init__.py
├── app.py              # FastAPI app, monta StaticFiles, Jinja2Templates, importa routes
├── routes/
│   ├── __init__.py
│   ├── dashboard.py    # GET / (página principal), GET /local/{id} (swap HTMX)
│   └── custos_reais.py # POST /local/{id}/custo-real (formulário HTMX)
├── services/
│   ├── __init__.py
│   ├── data_loader.py  # Lê CSV, JSON análise, status, custos_reais — sem deps em src/backend
│   └── rankings.py     # Calcula ranking anual a partir de history[].top_3
├── templates/
│   ├── base.html       # Layout base com HTMX e Chart.js incluídos
│   ├── dashboard.html  # Página principal com selector de local
│   ├── partials/
│   │   ├── consumo_chart.html   # Fragmento retornado pelo swap HTMX
│   │   ├── custo_chart.html
│   │   ├── ranking_table.html
│   │   ├── recomendacao_banner.html
│   │   └── frescura_badge.html
└── static/
    ├── vendor/
    │   ├── htmx.min.js      # Ficheiro estático local (D-01)
    │   └── chart.umd.min.js # Ficheiro estático local (D-01)
    └── style.css            # CSS minimalista

launchd/
└── com.ricmag.monitorizacao-eletricidade.dashboard.plist  # Novo plist uvicorn
```

### Pattern 1: FastAPI app com StaticFiles + Jinja2Templates

**What:** Montar StaticFiles para `/static` e criar instância `Jinja2Templates` apontando para `src/web/templates/`.
**When to use:** Setup inicial obrigatório em `app.py`.

```python
# src/web/app.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Importar routes após criar app para evitar circular imports
from src.web.routes import dashboard, custos_reais  # noqa: E402
app.include_router(dashboard.router)
app.include_router(custos_reais.router)
```

### Pattern 2: HTMX partial swap com fragmento HTML

**What:** Route retorna fragmento HTML (parcial) em vez de página completa. HTMX faz swap do `hx-target`.
**When to use:** Selector de local (DASH-01, critério 2) e formulário de custo real (DASH-04).

```html
<!-- No template base: selector de local -->
<select name="local_id"
        hx-get="/local/{id}/dashboard"
        hx-target="#dashboard-content"
        hx-swap="innerHTML"
        hx-trigger="change">
  {% for loc in locations %}
  <option value="{{ loc.id }}">{{ loc.name }}</option>
  {% endfor %}
</select>

<div id="dashboard-content">
  {# Conteúdo inicial renderizado server-side no GET / #}
</div>
```

```python
# src/web/routes/dashboard.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/local/{local_id}/dashboard", response_class=HTMLResponse)
async def local_dashboard(request: Request, local_id: str, templates=Depends(get_templates)):
    data = load_dashboard_data(local_id)
    return templates.TemplateResponse(
        "partials/dashboard_content.html",
        {"request": request, **data}
    )
```

### Pattern 3: Chart.js stacked bar (DASH-02)

**What:** Gráfico de barras empilhadas com dois datasets (vazio e fora_vazio).
**When to use:** Fragmento `consumo_chart.html`; dados injectados como JSON inline via Jinja2.

```html
<!-- partials/consumo_chart.html -->
<canvas id="consumoChart"></canvas>
<script>
const ctx = document.getElementById('consumoChart').getContext('2d');
new Chart(ctx, {
  type: 'bar',
  data: {
    labels: {{ labels | tojson }},
    datasets: [
      {
        label: 'Vazio (kWh)',
        data: {{ vazio_data | tojson }},
        backgroundColor: 'rgba(54, 162, 235, 0.8)',
        stack: 'consumo'
      },
      {
        label: 'Fora de Vazio (kWh)',
        data: {{ fora_vazio_data | tojson }},
        backgroundColor: 'rgba(255, 99, 132, 0.8)',
        stack: 'consumo'
      }
    ]
  },
  options: {
    scales: { x: { stacked: true }, y: { stacked: true } }
  }
});
</script>
```

### Pattern 4: Chart.js mixed bar+line para DASH-03

**What:** Dataset `bar` para estimativa calculada + dataset `line` para custo real (só meses com dado).
**When to use:** Fragmento `custo_chart.html`; custo real de `custos_reais.json` com `null` para meses sem entrada.

```javascript
datasets: [
  { type: 'bar', label: 'Estimativa (€)', data: estimativa_data },
  { type: 'line', label: 'Custo Real (€)', data: custo_real_data,
    spanGaps: false }  // null = sem linha entre pontos
]
```

### Pattern 5: POST HTMX para formulário de custo real (DASH-04)

**What:** Form inline com `hx-post` envia dados; FastAPI processa `Form()`, escreve `custos_reais.json`, retorna fragmento actualizado.
**When to use:** Linha de cada mês na tabela de custos reais.

```python
# src/web/routes/custos_reais.py
from fastapi import APIRouter, Form
router = APIRouter()

@router.post("/local/{local_id}/custo-real", response_class=HTMLResponse)
async def save_custo_real(
    local_id: str,
    year_month: str = Form(...),
    custo_eur: float = Form(...),
):
    _persist_custo_real(local_id, year_month, custo_eur)
    # Retorna fragmento actualizado da linha
    ...
```

### Pattern 6: launchd plist para uvicorn (D-04)

**What:** LaunchAgent que arranca `uvicorn src.web.app:app --host 127.0.0.1 --port 8000` no login.
**When to use:** Seguir exactamente o padrão dos plists existentes (Python path, WorkingDirectory, paths absolutos).

```xml
<!-- launchd/com.ricmag.monitorizacao-eletricidade.dashboard.plist -->
<key>Label</key>
<string>com.ricmag.monitorizacao-eletricidade.dashboard</string>
<key>ProgramArguments</key>
<array>
  <string>/usr/local/opt/python@3.11/libexec/bin/python3</string>
  <string>-m</string>
  <string>uvicorn</string>
  <string>src.web.app:app</string>
  <string>--host</string>
  <string>127.0.0.1</string>
  <string>--port</string>
  <string>8000</string>
</array>
<key>WorkingDirectory</key>
<string>/Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade</string>
<key>RunAtLoad</key>
<true/>
<key>StandardOutPath</key>
<string>/Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade/state/launchd.dashboard.stdout.log</string>
<key>StandardErrorPath</key>
<string>/Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade/state/launchd.dashboard.stderr.log</string>
```

### Anti-Patterns to Avoid

- **Importar `src/backend/` em runtime na dashboard:** A dashboard é read-only sobre ficheiros planos. Nunca chamar `run_workflow()` ou `energy_compare.py` a partir de routes. Usa `data_loader.py` dedicado.
- **CDN em runtime:** HTMX e Chart.js devem estar em `src/web/static/vendor/` como ficheiros descarregados. Nunca referenciar `unpkg.com` ou `cdn.jsdelivr.net` no HTML.
- **Calcular ranking em template:** O ranking anual (DASH-05) requer agregação de `history[].top_3` por fornecedor. Fazer esta lógica em `services/rankings.py`, não no template Jinja2.
- **uvicorn com `--reload` no plist:** `--reload` é para desenvolvimento. O plist de produção não deve ter `--reload`.
- **Porta 8000 bloqueada:** Se outra aplicação usar a porta 8000, uvicorn falha silenciosamente no launchd. Verificar antes de instalar o plist.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Servir ficheiros estáticos | Lógica manual de file serving | `app.mount("/static", StaticFiles(...))` do FastAPI | StaticFiles inclui ETag, Content-Type, range requests |
| Partial HTML swap | `fetch()` + `innerHTML` manual em JS | HTMX `hx-get`/`hx-post` com `hx-target` | Zero JS custom; funciona com Jinja2 fragmentos |
| Gráficos de barras empilhadas | Canvas API manual | Chart.js `type: 'bar'` com `stack` | Animações, tooltips, responsividade incluídos |
| Form submission assíncrona | `XMLHttpRequest` / `fetch` manual | HTMX `hx-post` com `hx-swap` | Zero JS custom para formulário de custo real |
| Rendering de templates | f-strings com HTML | Jinja2Templates | Escaping automático, herança de templates |

**Key insight:** A dashboard é intencionalmente simples — sem build step, sem bundler, sem framework JS. HTMX permite dinamismo mínimo sem abandonar o paradigma server-side.

---

## Data Schemas (confirmados por inspecção directa)

### CSV de consumo (`data/{local}/processed/consumo_mensal_atual.csv`)
```
year_month,total_kwh,vazio_kwh,fora_vazio_kwh
2025-01,1429.626,832.157,597.469
2025-02,1556.376,961.641,594.735
...
```
- 11 meses disponíveis para `casa` (jan-nov 2025)
- `year_month` no formato `YYYY-MM`

### JSON de análise (`data/{local}/processed/analise_tiagofelicia_atual.json`)
Campos de topo:
```json
{
  "generated_at": "2026-03-29",
  "source": "tiagofelicia.pt",
  "power_label": "10.35 kVA",
  "current_supplier": "Meo Energia",
  "current_plan_contains": "Tarifa Variável",
  "seasonality": { ... },
  "history_summary": {
    "months_analysed": 11,
    "simple_wins": 0,
    "bihorario_wins": 11,
    "latest_month": "...",
    "latest_recommendation": "bihorario",
    "latest_top_3": [...],
    "latest_current_supplier_result": {...},
    "latest_change_needed": true,
    "latest_saving_vs_current_eur": 46.54
  },
  "history": [
    {
      "year_month": "2025-01",
      "top_3": [
        { "supplier": "Ibelectra", "plan": "...", "total_eur": 188.32, ... },
        ...
      ],
      "current_supplier_result": { "supplier": "Meo Energia", "total_eur": 263.12, ... },
      "best_simple": { ... },
      "best_bihorario": { ... },
      "recommended_option": "bihorario",
      "saving_vs_current_eur": 74.8,
      "needs_change": true
    },
    ...
  ]
}
```

**Nota crítica:** Não existe campo `ranking` de topo no JSON. O ranking DASH-05 (top-5 fornecedores por custo anual estimado) tem de ser calculado por `services/rankings.py`:
1. Iterar `history[]`
2. Para cada mês, recolher todos os fornecedores únicos de `top_3` + `current_supplier_result`
3. Somar `total_eur` por fornecedor ao longo dos meses
4. Ordenar por custo anual total
5. Devolver top-5 + fornecedor actual (mesmo que fora do top-5)

### Estado do pipeline (`state/{local}/monthly_status.json`)

**Atenção:** O `state/monthly_status.json` na raiz é o schema antigo (Phase 1-2). Após Phase 3 (multi-local), o path correcto é `state/{local}/monthly_status.json`. Mas o estado actual da máquina ainda tem o ficheiro antigo na raiz. A dashboard deve usar o path do `config/system.json` → `locations[id].pipeline.status_path`.

```json
{
  "status": "ok",
  "generated_at": "2026-03-29T22:40:59.508976",
  "xlsx_path": "...",
  "processed_csv_path": "...",
  "analysis_json_path": "...",
  "report_path": "...",
  "latest_change_needed": true,
  "latest_recommendation": "bihorario",
  "latest_saving_vs_current_eur": 46.54
}
```

### Schema proposto para `custos_reais.json` (novo ficheiro gerido pela dashboard)

```json
{
  "updated_at": "2026-03-30T00:00:00",
  "entries": {
    "2025-01": 210.50,
    "2025-02": 195.00
  }
}
```
- Chave: `year_month` em formato `YYYY-MM`
- Valor: custo real da factura em euros (float)
- Path: `data/{local}/custos_reais.json` (relativo ao `project_root`)

### Frescura dos dados (DASH-09 / success criteria 5)

- Fonte: `report_path` do `monthly_status.json` → data do ficheiro do último relatório
- Alternativamente: `generated_at` do JSON de análise
- Limiar de aviso: > 40 dias desde a data do último relatório (conforme success criteria 5)
- Lógica: `(today - last_report_date).days > 40`

---

## Common Pitfalls

### Pitfall 1: `src.web.app` não é importável como módulo
**What goes wrong:** `uvicorn src.web.app:app` falha com `ModuleNotFoundError` se `src/web/__init__.py` não existir ou se o `WorkingDirectory` do plist não for o `project_root`.
**Why it happens:** Python precisa encontrar `src` no `sys.path`; uvicorn resolve o módulo relativo ao `cwd`.
**How to avoid:** Garantir `src/__init__.py` e `src/web/__init__.py` existem. O plist deve ter `WorkingDirectory` apontando para o `project_root`.
**Warning signs:** Log launchd.dashboard.stderr.log mostra `ModuleNotFoundError: No module named 'src'`.

### Pitfall 2: HTMX e Chart.js referenciados por CDN no HTML
**What goes wrong:** O success criteria 7 exige que nenhum pedido de rede externo seja feito. Se `<script src="https://unpkg.com/htmx.org">` estiver no HTML, o critério falha.
**Why it happens:** Desenvolvimento rápido com CDN, esquecendo o requisito de offline.
**How to avoid:** O template `base.html` referencia `/static/vendor/htmx.min.js` e `/static/vendor/chart.umd.min.js`. Verificar no Network tab das DevTools antes de marcar como completo.
**Warning signs:** DevTools Network tab mostra pedidos a `unpkg.com` ou `jsdelivr.net`.

### Pitfall 3: `python-multipart` não instalado causa erro silencioso em POST
**What goes wrong:** FastAPI retorna 422 ou 400 em posts de formulários HTMX sem mensagem clara.
**Why it happens:** FastAPI requer `python-multipart` para `Form()` mas não o inclui como dependência.
**How to avoid:** `python-multipart` já está instalado (0.0.22 confirmado). Verificar no `requirements.txt`.
**Warning signs:** `POST /local/{id}/custo-real` retorna 422 Unprocessable Entity.

### Pitfall 4: Ranking calculado no template em vez de no service
**What goes wrong:** Lógica de agregação de `history[].top_3` em Jinja2 é lenta, ilegível e não testável.
**Why it happens:** Tentação de usar filtros Jinja2 para agrupar listas.
**How to avoid:** `services/rankings.py` calcula o ranking antes de passar dados ao template. O template recebe lista já ordenada.

### Pitfall 5: Status file path desactualizado após Phase 3
**What goes wrong:** `state/monthly_status.json` na raiz é o ficheiro da Phase 1-2. Após Phase 3 (multi-local), o path correcto é `state/{local}/monthly_status.json`.
**Why it happens:** O ficheiro antigo existe na raiz e pode ser lido por engano.
**How to avoid:** A dashboard deve sempre resolver o path via `config/system.json → locations[id].pipeline.status_path`. Nunca hardcodar `state/monthly_status.json`.

### Pitfall 6: Delta ano-a-ano (success criteria 6) sem dados suficientes
**What goes wrong:** O CSV de `casa` tem apenas jan-nov 2025. Não há dados de 2024. Comparação com período homólogo é impossível para todos os meses.
**Why it happens:** O projecto começou em 2025 e só tem 1 ano de histórico.
**How to avoid:** O planner deve decidir se o delta ano-a-ano (success criteria 6) está em scope para esta fase ou pertence a DASH-08 (deferred). A lógica da dashboard deve mostrar delta apenas quando `year_month - 12 meses` existe no CSV; caso contrário, omitir silenciosamente.

### Pitfall 7: `RunAtLoad true` no plist sem garantir que a porta 8000 está livre
**What goes wrong:** uvicorn falha ao arrancar se a porta 8000 estiver ocupada; launchd marca o job como falhado mas não avisa.
**Why it happens:** `RunAtLoad: true` significa que o plist arranca imediatamente ao instalar com `launchctl load`.
**How to avoid:** Verificar `lsof -i :8000` antes de instalar o plist. Adicionar instrução de verificação ao script de instalação.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Toda a lógica web | ✓ | 3.11.14 | — |
| FastAPI | DASH-01, routes | ✓ | 0.104.1 | — |
| uvicorn | DASH-01, entry point | ✓ | 0.41.0 | — |
| Jinja2 | DASH-01, templating | ✓ | 3.1.6 | — |
| python-multipart | DASH-04, Form() | ✓ | 0.0.22 | — |
| httpx | Testes FastAPI | ✓ | 0.28.1 | — |
| aiofiles | Leitura async ficheiros | ✓ | 25.1.0 | Leitura síncrona em route normal |
| HTMX 2.0.8 | DASH-01 (ficheiro estático) | A descarregar | — | — |
| Chart.js 4.5.1 | DASH-02/03 (ficheiro estático) | A descarregar | — | — |
| pytest | Testes | ✓ | 7.4.3 | — |
| Port 8000 | uvicorn server | A verificar | — | `--port 8001` se ocupada |

**Missing dependencies com fallback:**
- HTMX e Chart.js: URLs de download verificados (`https://unpkg.com/htmx.org@2.0.8/dist/htmx.min.js`, `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js`) — Wave 0 deve descarregá-los para `src/web/static/vendor/`.

**Missing dependencies sem fallback:**
- Nenhum — todos os pacotes Python estão instalados.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 |
| Config file | `tests/conftest.py` (existente) |
| Quick run command | `pytest tests/test_web_*.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | `GET /` retorna 200 e HTML com selector de local | smoke | `pytest tests/test_web_dashboard.py::test_homepage_ok -x` | ❌ Wave 0 |
| DASH-01 | HTMX e Chart.js servidos como estáticos locais (sem CDN) | smoke | `pytest tests/test_web_dashboard.py::test_static_files_local -x` | ❌ Wave 0 |
| DASH-02 | Dados CSV carregados correctamente para o gráfico | unit | `pytest tests/test_web_data_loader.py::test_load_consumo_csv -x` | ❌ Wave 0 |
| DASH-02 | Swap HTMX do selector de local retorna fragmento com dados correctos | integration | `pytest tests/test_web_dashboard.py::test_local_selector_swap -x` | ❌ Wave 0 |
| DASH-04 | POST de custo real persiste em `custos_reais.json` | unit | `pytest tests/test_web_custos_reais.py::test_save_custo_real -x` | ❌ Wave 0 |
| DASH-05 | Ranking calculado correctamente a partir de `history[]` | unit | `pytest tests/test_web_rankings.py::test_ranking_calculation -x` | ❌ Wave 0 |
| DASH-06 | Banner aparece quando poupança > limiar; oculto quando abaixo | unit | `pytest tests/test_web_rankings.py::test_recomendacao_banner -x` | ❌ Wave 0 |
| DASH-09 (frescura) | Badge de aviso quando último relatório > 40 dias | unit | `pytest tests/test_web_data_loader.py::test_freshness_warning -x` | ❌ Wave 0 |

### Sampling Rate

- **Por task commit:** `pytest tests/test_web_*.py -x -q`
- **Por wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green antes de `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_web_dashboard.py` — cobre DASH-01, DASH-02 (smoke + swap HTMX)
- [ ] `tests/test_web_data_loader.py` — cobre DASH-02 (CSV parsing), DASH-09 (frescura)
- [ ] `tests/test_web_custos_reais.py` — cobre DASH-04 (POST + persistência)
- [ ] `tests/test_web_rankings.py` — cobre DASH-05 (ranking), DASH-06 (banner)
- [ ] `tests/conftest.py` — adicionar fixtures: `sample_analysis_json`, `sample_status_json`, `client` (FastAPI TestClient)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `src/frontend/README.md` (placeholder) | `src/web/` com FastAPI | Phase 4 | Nova estrutura de directórios; `src/frontend/` não é usado |
| `state/monthly_status.json` (raiz) | `state/{local}/monthly_status.json` | Phase 3 | Dashboard deve ler via `config/system.json`, nunca hardcodar path raiz |
| `data/processed/` (flat) | `data/{local}/processed/` | Phase 3 | Todos os paths de data são por local |

**Deprecated/outdated:**
- `state/monthly_status.json` na raiz: ficheiro da Phase 1-2, ainda existe na máquina. A dashboard ignora-o e usa `config/system.json` para resolver paths por local.
- `src/frontend/README.md`: placeholder que pode ser removido quando `src/web/` for criado.

---

## Open Questions

1. **Delta ano-a-ano (success criteria 6) vs. DASH-08 (deferred)**
   - What we know: Success criteria 6 menciona "delta ano-a-ano visível por mês"; DASH-08 está marcado como Phase 4 Pending em REQUIREMENTS.md; mas CONTEXT.md limita scope a DASH-01 a DASH-06.
   - What's unclear: O success criteria 6 pertence a DASH-06 (recomendação) ou a DASH-08 (comparação homóloga)? Com apenas 11 meses de dados (jan-nov 2025), comparação com período homólogo de 2024 é impossível.
   - Recommendation: O planner deve confirmar se delta ano-a-ano está em scope. Se sim, implementar com omissão silenciosa quando dados do ano anterior não existem (que é o caso actual para todos os meses). Se não, o success criteria 6 pode ser interpretado como "delta mês-a-mês" (vs. mês anterior) que é implementável com os dados existentes.

2. **`custos_reais.json` path por local após Phase 3**
   - What we know: CONTEXT.md define D-06 como `data/{local}/custos_reais.json`; Phase 3 criou estrutura `data/{local}/`.
   - What's unclear: Se o `config/system.json` deve ter um campo `custos_reais_path` por local (como os outros paths) ou se a dashboard hardcoda a convenção `data/{local}/custos_reais.json`.
   - Recommendation: Seguir a convenção existente sem adicionar ao `system.json` — construir o path programaticamente a partir de `location.id`.

3. **uvicorn `--app-dir` vs. `WorkingDirectory` no plist**
   - What we know: `uvicorn src.web.app:app` requer que `src` seja encontrável; o `WorkingDirectory` no plist resolve isto se apontar para o `project_root`.
   - What's unclear: Se o Python path do plist (`/usr/local/opt/python@3.11/libexec/bin/python3`) tem o mesmo ambiente que o pip3 do utilizador (onde FastAPI está instalado).
   - Recommendation: Verificar com `which python3` e comparar com o path no plist. Se diferente, usar o mesmo path do plist existente (confirmado como correcto pela Phase 1).

---

## Sources

### Primary (HIGH confidence)

- Inspecção directa de `config/system.json` — schema de locations e paths confirmados
- Inspecção directa de `data/processed/analise_tiagofelicia_atual.json` — schema JSON de análise confirmado (sem campo `ranking`; `history[].top_3` como fonte)
- Inspecção directa de `state/monthly_status.json` — schema do estado de pipeline confirmado
- Inspecção directa de `data/processed/consumo_mensal_atual.csv` — colunas CSV confirmadas
- `pip3 show fastapi uvicorn jinja2 python-multipart httpx aiofiles` — versões instaladas confirmadas
- `npm view htmx.org version` → 2.0.8; `npm view chart.js version` → 4.5.1
- Verificação HTTP de URLs de download estático: `unpkg.com/htmx.org@2.0.8` (HTTP 200), `cdn.jsdelivr.net/npm/chart.js@4.5.1` (HTTP 200)
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `STACK.md` — padrões existentes do projecto
- `.planning/phases/04-web-dashboard-mvp/04-CONTEXT.md` — decisões locked

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — mapeamento DASH-01 a DASH-09
- `.planning/STATE.md` — decisões de fases anteriores
- `launchd/com.ricmag.monitorizacao-eletricidade.plist` — padrão de plist existente confirmado

### Tertiary (LOW confidence)

- Nenhum — toda a informação relevante foi verificada por inspecção directa de ficheiros e comandos.

---

## Project Constraints (from CLAUDE.md)

Directivas do `CLAUDE.md` global (aplicável a todos os projectos):

- Responder sempre em português europeu (PT-PT)
- Soluções práticas e directas — sem over-engineering
- Commits pequenos e incrementais
- Não modificar código sem ler primeiro
- Não implementar sem planear em features médias/grandes

Directivas do `3-hobbies/CLAUDE.md`:
- Novos projectos/funcionalidades dentro de `3-hobbies/[nome-projecto]/`
- Sem restrições específicas de stack para este projecto

**Não existem directivas de projeto CLAUDE.md local** (ficheiro não encontrado em `monitorizacao-eletricidade/`).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pacotes verificados por `pip3 show`; versões HTMX/Chart.js verificadas via npm e HTTP
- Architecture: HIGH — padrões do projecto inspeccionados directamente; schemas de ficheiros confirmados
- Pitfalls: HIGH — baseados em código existente inspeccionado e padrões confirmados do projecto
- Data schemas: HIGH — JSON e CSV lidos directamente da máquina

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stack estável; risco se Phase 3 alterar schema do JSON de análise)
