# Phase 9: Dashboard UI - Research

**Researched:** 2026-03-31
**Domain:** FastAPI + Jinja2 + HTMX + Chart.js dashboard — SQLite data migration + UI-SPEC alignment
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-02 | Selector de local no topo da dashboard | Selector já existe em `dashboard.html`; HTMX pattern funcional via `hx-trigger="change"` — requer ajuste para SQLite-only data loading e link "Gerir locais" já presente |
| UI-03 | Ranking de fornecedores com poupança potencial em €/ano | `ranking_table.html` + `rankings.py` existem mas falta coluna de poupança potencial; `calculate_annual_ranking()` retorna `custo_anual_estimado` mas não `poupanca_vs_atual` |
| UI-04 | Gráfico de consumo mensal (vazio/fora vazio empilhados) | `consumo_chart.html` já implementado com stack e cores correctas per UI-SPEC; migração de source (CSV → SQLite) necessária para locais sem pipeline |
| UI-05 | Gráfico de custo: estimativa do fornecedor actual vs custo real da fatura | `custo_chart.html` existe mas usa line chart para custo real; UI-SPEC especifica dois datasets `bar` lado a lado — divergência a corrigir |

</phase_requirements>

---

## Summary

O dashboard de monitorização de eletricidade tem uma base sólida: o stack FastAPI + HTMX + Jinja2 + Chart.js está operacional, o selector de local com HTMX funciona, e os partials de gráfico e ranking existem e são funcionais. A Phase 9 não é uma implementação do zero — é uma **migração + alinhamento com a UI-SPEC**.

O problema central é que o dashboard actual lê dados de ficheiros CSV/JSON de pipeline (`config/system.json → pipeline`) e retorna dados vazios para locais criados via UI (Phase 7). Phase 9 deve migrar `_load_location_data()` para ler directamente do SQLite (tabelas `consumo_mensal`, `comparacoes`, `custos_reais`, `locais`) — tornando o dashboard funcional para todos os locais independentemente de haver pipeline CSV.

Há três divergências concretas entre o estado actual e a UI-SPEC aprovada: (1) o gráfico de custo usa `type: 'line'` para custo real em vez de `bar` lado a lado; (2) a tabela de ranking não tem coluna de poupança potencial em EUR/ano; (3) o `custo_form.html` (entrada manual de custo) deve ser substituído pelo upload PDF já implementado na Phase 8.

**Primary recommendation:** Migrar `_load_location_data()` para SQLite como primeira tarefa (desbloqueia todos os outros componentes), depois alinhar os 3 componentes com a UI-SPEC, e por último integrar o upload PDF no layout da dashboard.

---

## Standard Stack

### Core (já no projecto — nenhuma instalação adicional)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| FastAPI | instalado | API + routing | Operacional |
| Jinja2 | instalado | Templates HTML | Operacional |
| HTMX | vendored `static/vendor/htmx.min.js` | Interactividade sem JS | Operacional |
| Chart.js | vendored `static/vendor/chart.umd.min.js` | Gráficos | Operacional |
| SQLAlchemy (Core) | instalado | ORM/queries SQLite | Operacional |
| pdfplumber | 0.11.7 (adicionado Phase 8) | Extracção PDF | Operacional |

**Nenhuma dependência nova é necessária.** Phase 9 usa apenas o que já existe.

---

## Architecture Patterns

### Estrutura de ficheiros actual (relevante para Phase 9)

```
src/web/
├── routes/
│   ├── dashboard.py          # GET / e GET /local/{id}/dashboard — MODIFICAR
│   ├── custos_reais.py       # POST /local/{id}/custo-real — manter (pode ser deprecated mais tarde)
│   ├── upload.py             # POST /upload/xlsx + /upload/pdf — sem alteração
│   └── locais.py             # CRUD locais — sem alteração
├── services/
│   ├── data_loader.py        # Leitura CSV/JSON/status — ESTENDER com SQLite readers
│   ├── rankings.py           # calculate_annual_ranking + build_recommendation — ESTENDER
│   └── locais_service.py     # CRUD SQLite locais — reutilizar
├── templates/
│   ├── dashboard.html        # Layout principal — MODIFICAR (upload PDF)
│   ├── base.html             # Cabeçalho HTML — sem alteração
│   └── partials/
│       ├── dashboard_content.html   # Grid de componentes — sem alteração
│       ├── consumo_chart.html       # Chart.js consumo — sem alteração (já conforme UI-SPEC)
│       ├── custo_chart.html         # Chart.js custo — MODIFICAR (line → bar)
│       ├── custo_form.html          # Formulário manual — DEPRECAR/REMOVER
│       ├── custo_section.html       # Wrapper custo — sem alteração
│       ├── ranking_table.html       # Tabela ranking — MODIFICAR (coluna poupança)
│       ├── recomendacao_banner.html # Banner — MODIFICAR (mensagem UI-SPEC)
│       ├── frescura_badge.html      # Badge frescura — sem alteração (já conforme UI-SPEC)
│       ├── upload_xlsx.html         # Upload XLSX — sem alteração
│       └── upload_pdf.html          # Upload PDF (Phase 8) — INTEGRAR em dashboard.html
```

### Pattern 1: Migração de data source (CSV/JSON → SQLite)

**O problema actual:** `_load_location_data()` em `dashboard.py` bifurca-se: locais com `pipeline` lêem CSV/JSON; locais sem `pipeline` (criados via UI) retornam dados vazios. Comment explícito: `"Phase 9 migrará para leitura directa de SQLite"`.

**O que Phase 9 deve fazer:** Implementar leitores SQLite em `data_loader.py` e reescrever `_load_location_data()` para usar exclusivamente SQLite.

**Fontes de dados SQLite por componente:**

| Componente | Tabela SQLite | Campos relevantes |
|------------|--------------|-------------------|
| Gráfico consumo | `consumo_mensal` | `location_id`, `year_month`, `vazio_kwh`, `fora_vazio_kwh` |
| Gráfico custo (estimativa) | `comparacoes` | `location_id`, `year_month`, `current_supplier_result_json` |
| Gráfico custo (real) | `custos_reais` | `location_id`, `year_month`, `custo_eur` |
| Ranking | `comparacoes` | `location_id`, `year_month`, `top_3_json`, `current_supplier_result_json` |
| Frescura | `comparacoes` | `location_id`, `generated_at` (coluna mais recente) |
| Fornecedor actual | `locais` | `current_supplier`, `current_plan_contains` |

**Nota crítica sobre `comparacoes.top_3_json` e `current_supplier_result_json`:** Estes campos são TEXT (JSON serializado como string). Os leitores SQLite devem fazer `json.loads()` ao ler estes campos para reconstruir a estrutura de dicts que `rankings.py` e `build_custo_chart_data()` esperam. O schema de `analysis_json` usado pelo code actual pode não mapear 1:1 com o schema `comparacoes` — verificar antes de implementar.

```python
# Padrão de leitura SQLite (SQLAlchemy Core, sem ORM)
from sqlalchemy import select, Engine
from src.db.schema import consumo_mensal

def load_consumo_sqlite(location_id: str, engine: Engine) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(consumo_mensal)
            .where(consumo_mensal.c.location_id == location_id)
            .order_by(consumo_mensal.c.year_month)
        ).fetchall()
    return [dict(row._mapping) for row in rows]
```

### Pattern 2: Ranking com poupança potencial (UI-03)

`calculate_annual_ranking()` actualmente retorna:
```python
{"supplier": ..., "plan": ..., "custo_anual_estimado": ..., "is_current": ...}
```

UI-SPEC exige coluna de poupança potencial: diferença entre custo do fornecedor actual e custo do fornecedor na linha. Algoritmo:

1. Após ordenar o ranking, identificar `custo_anual_atual` (custo da linha com `is_current=True`)
2. Para cada linha: `poupanca_potencial = custo_anual_atual - custo_anual_estimado`
3. Para a linha do fornecedor actual: `poupanca_potencial = 0` (ou `-` no template)
4. Para linhas mais caras que o actual: `poupanca_potencial` negativa (ignorar ou mostrar como 0)

```python
# Extensão de calculate_annual_ranking() em rankings.py
# Após sort, calcular poupança:
current_cost = next((r["custo_anual_estimado"] for r in top5 if r["is_current"]), None)
for r in top5:
    r["poupanca_potencial"] = round(current_cost - r["custo_anual_estimado"], 2) if current_cost else None
```

### Pattern 3: Gráfico de custo — correcção para dois bars lado a lado (UI-05)

**Estado actual** (`custo_chart.html`): dataset 1 = `type: 'bar'`, dataset 2 = `type: 'line'` com `spanGaps: false`.

**UI-SPEC especifica**: dois datasets `bar` lado a lado (não empilhados). Cores:
- Dataset "Estimativa (EUR)": `rgba(54, 162, 235, 0.8)` — azul
- Dataset "Custo Real (EUR)": `rgba(255, 99, 132, 0.8)` — vermelho/rosa

**Correcção:**
```javascript
// Ambos os datasets devem ser type: 'bar' sem stack
// Remover 'type: line', 'tension', 'spanGaps', 'borderColor'
datasets: [
  {
    label: 'Estimativa (EUR)',
    data: custo_chart.estimativa_data,
    backgroundColor: 'rgba(54, 162, 235, 0.8)',
    // sem 'stack' — lado a lado por default
  },
  {
    label: 'Custo Real (EUR)',
    data: custo_chart.custo_real_data,
    backgroundColor: 'rgba(255, 99, 132, 0.8)',
  }
]
```

**Nota sobre valores null:** Chart.js com `bar` e valores `null` não desenha a barra — comportamento correcto para meses sem custo real. Não é necessário `spanGaps`.

### Pattern 4: Selector de local — integração HTMX existente

O selector já implementa `hx-trigger="change"` com o path construído dinamicamente via JavaScript:

```javascript
document.getElementById('local-selector').addEventListener('htmx:configRequest', function(evt) {
  evt.detail.path = '/local/' + this.value + '/dashboard';
});
```

Este padrão está correcto e em conformidade com a UI-SPEC. **Não necessita alteração.** O link "Gerir locais" também já existe em `dashboard.html`.

### Pattern 5: Integração do upload PDF no layout

`dashboard.html` actualmente inclui apenas `upload_xlsx.html`. Deve incluir também `upload_pdf.html` (criado na Phase 8):

```html
<!-- Seccao de Upload — Phase 7 + Phase 8 -->
{% include "partials/upload_xlsx.html" %}
{% include "partials/upload_pdf.html" %}
```

O `upload_pdf.html` já existe e implementa o contrato HTMX correcto (Phase 8 Plan 02).

### Anti-Patterns a Evitar

- **Não reescrever o sistema de ficheiros CSV/JSON:** A migração para SQLite é additive — os locais com `pipeline` (Casa, Apartamento) ainda têm dados nos ficheiros CSV. Mas a fonte primária para o dashboard deve ser SQLite. A abordagem correcta é: tentar SQLite primeiro; se sem dados, tentar CSV como fallback (retrocompatível).
- **Não chamar `analysis_json` directamente:** `comparacoes` tem um schema diferente do `analise_tiagofelicia_atual.json`. O código de construção do ranking deve adaptar-se ao schema de `comparacoes`, não assumir que é igual ao JSON de ficheiro.
- **Não duplicar `build_custo_chart_data()`:** A função existe e funciona. Apenas precisa de ser alimentada com dados SQLite em vez de dados CSV.
- **Não remover `custo_form.html` sem garantir backward compat:** O endpoint `POST /local/{id}/custo-real` ainda é válido (entrada manual pode coexistir com upload PDF). Remover o formulário manual é decisão do planner — a UI-SPEC diz "Migrar: entradas manuais substituídas por upload PDF" mas não diz explicitamente para remover o endpoint.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQLAlchemy select com JOIN | Query manual com string SQL | `select(tabela).where(...)` com `.fetchall()` | Pattern já estabelecido em `locais_service.py` e todos os outros serviços |
| JSON deserialização de `top_3_json` | Parser custom | `json.loads()` inline na função de leitura | Campo é TEXT com JSON serializado — standard Python |
| HTMX selector update | JavaScript manual | Padrão `htmx:configRequest` existente | Já funcional, não tocar |
| Chart.js destroy/recreate | Gestão manual de canvas | `window._consumoChart.destroy()` antes de `new Chart()` | Padrão já implementado em ambos os charts — evita memory leak ao trocar local |
| Empty state HTML | Componente custom | Texto simples com `var(--muted)` e cópia da UI-SPEC | Stack não tem componente library — HTML nativo |

---

## Common Pitfalls

### Pitfall 1: Schema mismatch entre `comparacoes` e `analysis_json`

**O que corre mal:** `build_custo_chart_data()` e `calculate_annual_ranking()` esperam um dict com estrutura `{"history": [...], "history_summary": {...}}`. A tabela `comparacoes` tem uma linha por `(location_id, year_month)` com `top_3_json` e `current_supplier_result_json` como strings JSON separadas.

**Porquê acontece:** Os dados foram migrados para SQLite por registos mensais individuais — não como documento JSON monolítico.

**Como evitar:** Criar uma função `build_analysis_from_sqlite(location_id, engine)` que:
1. Lê todas as linhas de `comparacoes` para o `location_id`
2. Deserializa `top_3_json` e `current_supplier_result_json` com `json.loads()`
3. Constrói um dict com estrutura compatível com `history[]` que as funções existentes consomem
4. Reutiliza `calculate_annual_ranking()` e `build_recommendation()` sem modificar as suas assinaturas

### Pitfall 2: Frescura calculada a partir de comparacoes vs. monthly_status.json

**O que corre mal:** `get_freshness_info()` actualmente lê `state/{local}/monthly_status.json`. Para locais SQLite-only, esse ficheiro não existe.

**Porquê acontece:** O ficheiro de status pertence ao pipeline antigo que não corre para locais criados via UI.

**Como evitar:** Para locais sem pipeline, calcular frescura a partir do `MAX(cached_at)` da tabela `comparacoes` para o `location_id`. Se não houver nenhuma comparação, retornar `{"days_ago": None, "is_stale": True, "generated_at": None}` (comportamento já implementado em `get_freshness_info(None)`).

### Pitfall 3: Chart.js destroy/recreate ao trocar local via HTMX

**O que corre mal:** Ao fazer HTMX swap do `#dashboard-content`, o novo HTML tem `<canvas>` com o mesmo `id`. Se `window._consumoChart` não for destruído antes, Chart.js lança erro "Canvas is already in use".

**Porquê acontece:** HTMX substitui o DOM mas a instância Chart.js anterior fica em memória.

**Como evitar:** O padrão já está implementado nos charts actuais:
```javascript
if (window._consumoChart) window._consumoChart.destroy();
```
Garantir que este padrão se mantém em qualquer modificação ao `custo_chart.html`.

### Pitfall 4: Locais do SQLite sem `current_supplier` para o ranking

**O que corre mal:** `calculate_annual_ranking()` recebe `current_supplier_name` para marcar `is_current=True`. Para locais SQLite, o supplier vem de `locais.current_supplier`. Se for `None` ou string vazia, nenhuma linha fica marcada como actual.

**Porquê acontece:** `update_fornecedor()` pode não ter sido chamado após criação do local.

**Como evitar:** Em `_load_location_data()`, garantir fallback: `current_supplier = location.get("current_supplier") or location.get("current_contract", {}).get("supplier", "")`.

### Pitfall 5: `custo_form.html` com referência a `pipeline` em `custos_reais.py`

**O que corre mal:** O endpoint `POST /local/{id}/custo-real` em `custos_reais.py` acede a `location["pipeline"]["processed_csv_path"]` — falha com `KeyError` para locais SQLite-only.

**Porquê acontece:** `custos_reais.py` não foi actualizado quando os locais SQLite foram adicionados na Phase 7.

**Como evitar:** Se o `custo_form.html` for mantido (não removido), o endpoint `custos_reais.py` deve ser corrigido para usar SQLite quando `pipeline` não existe. Se o formulário manual for removido (substituído por upload PDF), este pitfall não se aplica — mas o endpoint deve continuar a funcionar para não quebrar testes existentes.

---

## Code Examples

### Leitura de consumo_mensal do SQLite

```python
# Source: padrão estabelecido em locais_service.py
from sqlalchemy import select, Engine
from src.db.schema import consumo_mensal

def load_consumo_sqlite(location_id: str, engine: Engine) -> list[dict]:
    """Lê dados de consumo mensal do SQLite para um local."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(consumo_mensal)
            .where(consumo_mensal.c.location_id == location_id)
            .order_by(consumo_mensal.c.year_month)
        ).fetchall()
    return [dict(row._mapping) for row in rows]
```

### Construção de analysis dict a partir de comparacoes

```python
import json
from sqlalchemy import select, Engine
from src.db.schema import comparacoes

def build_analysis_from_sqlite(location_id: str, engine: Engine) -> dict | None:
    """Reconstrói dict 'analysis' compatível com rankings.py a partir da tabela comparacoes."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(comparacoes)
            .where(comparacoes.c.location_id == location_id)
            .order_by(comparacoes.c.year_month)
        ).fetchall()
    if not rows:
        return None

    history = []
    for row in rows:
        top_3 = json.loads(row.top_3_json) if row.top_3_json else []
        csr = json.loads(row.current_supplier_result_json) if row.current_supplier_result_json else {}
        history.append({
            "year_month": row.year_month,
            "top_3": top_3,
            "current_supplier_result": csr,
        })

    # history_summary: derivado do último mês
    last = history[-1] if history else {}
    latest_top3 = last.get("top_3", [])
    latest_csr = last.get("current_supplier_result", {})
    latest_saving = 0.0
    if latest_top3 and latest_csr:
        best_cost = latest_top3[0].get("total_eur", 0)
        current_cost = latest_csr.get("total_eur", 0)
        latest_saving = current_cost - best_cost

    return {
        "history": history,
        "history_summary": {
            "latest_top_3": latest_top3,
            "latest_current_supplier_result": latest_csr,
            "latest_saving_vs_current_eur": latest_saving,
        },
    }
```

### Coluna de poupança no ranking

```python
# Extensão de calculate_annual_ranking() em rankings.py
# Após calcular top5, adicionar poupanca_potencial:
current_annual = next(
    (r["custo_anual_estimado"] for r in top5 if r["is_current"]), None
)
for r in top5:
    if current_annual is not None:
        r["poupanca_potencial"] = round(current_annual - r["custo_anual_estimado"], 2)
    else:
        r["poupanca_potencial"] = None
```

### ranking_table.html com coluna poupança

```html
<thead>
  <tr>
    <th>#</th>
    <th>Fornecedor</th>
    <th>Plano</th>
    <th>Custo Anual Est. (EUR)</th>
    <th>Poupança Potencial (EUR/ano)</th>
  </tr>
</thead>
<tbody>
  {% for r in ranking %}
  <tr{% if r.is_current %} class="highlight"{% endif %}>
    <td>{{ loop.index }}</td>
    <td>{{ r.supplier }}{% if r.is_current %} (actual){% endif %}</td>
    <td>{{ r.plan }}</td>
    <td>{{ "%.2f" | format(r.custo_anual_estimado) }}</td>
    <td>
      {% if r.is_current %}—
      {% elif r.poupanca_potencial is not none and r.poupanca_potencial > 0 %}
        <span style="color: var(--success); font-weight: 600;">{{ "%.2f" | format(r.poupanca_potencial) }}</span>
      {% else %}—{% endif %}
    </td>
  </tr>
  {% endfor %}
</tbody>
```

### recomendacao_banner.html alinhado com UI-SPEC copywriting

```html
{% if recommendation.show %}
<div class="banner banner-success">
  Mudando para {{ recommendation.supplier }} — plano {{ recommendation.plan }}, poupa cerca de {{ recommendation.saving_eur | int }} EUR/ano
</div>
{% endif %}
```

Nota: `build_recommendation()` actualmente não retorna `plan`. A função deve ser extendida para incluir `plan` no dict de retorno.

---

## Gap Analysis: Phase 8 → Phase 9

| Componente | Estado após Phase 8 | Necessário para Phase 9 | Gap |
|------------|---------------------|------------------------|-----|
| `extrator_pdf.py` | Implementado e testado | Nenhuma alteração | Nenhum |
| `POST /upload/pdf` | Endpoint funcional | Nenhuma alteração | Nenhum |
| `upload_pdf.html` | Criado | Incluir em `dashboard.html` | Pequeno |
| `_load_location_data()` | Retorna vazio para locais UI | Ler de SQLite | Gap maior |
| `consumo_chart.html` | Conforme UI-SPEC (azul/laranja, stack) | Sem alteração | Nenhum |
| `custo_chart.html` | Line chart para custo real | Bar chart para ambos datasets | Gap médio |
| `ranking_table.html` | Sem coluna poupança | Adicionar coluna poupança potencial | Gap médio |
| `rankings.py` | Sem poupança_potencial no dict | Calcular e incluir | Gap médio |
| `recomendacao_banner.html` | Mensagem genérica | Mensagem UI-SPEC com plano | Gap pequeno |
| `build_recommendation()` | Não retorna `plan` | Incluir `plan` no retorno | Gap pequeno |
| CSS tokens | Conformes UI-SPEC | Sem alteração | Nenhum |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` ou `pyproject.toml` (verificar) |
| Quick run command | `python3 -m pytest tests/test_web_dashboard.py tests/test_web_rankings.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behaviour | Test Type | Automated Command | File Exists? |
|--------|-----------|-----------|-------------------|-------------|
| UI-02 | Selector troca local sem reload | integration | `pytest tests/test_web_dashboard.py::test_local_dashboard_swap -x` | Exists |
| UI-02 | Locais SQLite-only aparecem no selector | integration | `pytest tests/test_web_dashboard.py -x -k "selector"` | Wave 0 gap |
| UI-03 | Ranking tem coluna poupança potencial | integration | `pytest tests/test_web_rankings.py -x` | Exists (verificar cobertura) |
| UI-03 | Poupança calculada correctamente | unit | `pytest tests/test_web_rankings.py::test_annual_ranking_poupanca -x` | Wave 0 gap |
| UI-04 | Gráfico consumo tem dados SQLite | integration | `pytest tests/test_web_dashboard.py::test_consumo_chart_sqlite -x` | Wave 0 gap |
| UI-05 | Gráfico custo usa dois bar datasets | integration | `pytest tests/test_web_dashboard.py::test_custo_chart_two_bars -x` | Wave 0 gap |

### Testes existentes relevantes (não quebrar)

- `tests/test_web_dashboard.py` — 5 testes de dashboard (GET /, GET /local/{id}/dashboard, 404) — todos devem continuar a passar
- `tests/test_web_rankings.py` — testes de ranking (verificar se já cobre poupança potencial)
- `tests/test_web_data_loader.py` — testes de data_loader (funções que se vão estender)
- `tests/test_web_custos_reais.py` — testes de custos reais (não devem quebrar)

### Wave 0 Gaps

- [ ] `tests/test_web_dashboard.py` — adicionar testes para locais SQLite-only (consumo chart com dados SQLite)
- [ ] `tests/test_web_rankings.py` — adicionar `test_annual_ranking_poupanca` para verificar campo `poupanca_potencial`
- [ ] `tests/conftest.py` — verificar se fixture `web_client` funciona com locais SQLite (pode precisar de seed de dados na tabela `comparacoes` + `consumo_mensal`)

---

## Environment Availability

Step 2.6: SKIPPED — Phase 9 é puramente code/template changes. Todas as dependências (FastAPI, SQLite, pdfplumber, Chart.js, HTMX) já estão disponíveis e verificadas em phases anteriores.

---

## State of the Art

| Old Approach | Current Approach | Phase Changed | Impact |
|--------------|------------------|---------------|--------|
| CSV/JSON files como data source do dashboard | SQLite como data source primário | Phase 7/8 introduziu SQLite; Phase 9 migra o dashboard | Dashboard funciona para todos os locais |
| `custo_form.html` — entrada manual de custo | Upload PDF (Phase 8) | Phase 8 | Formulário manual pode ser removido ou mantido como fallback |
| Locais de `config/system.json` | Locais de SQLite (`locais` table) | Phase 7 | `load_locations()` já faz merge — Phase 9 completa a migração |

---

## Open Questions

1. **Manter ou remover `custo_form.html` e endpoint `POST /local/{id}/custo-real`?**
   - O que sabemos: A UI-SPEC diz "Migrar: entradas manuais substituídas por upload PDF". O endpoint de custo manual tem um bug latente (acesso a `pipeline` para locais SQLite-only).
   - O que está unclear: Se o utilizador quer poder continuar a inserir custos manualmente (para meses sem PDF).
   - Recomendação: Remover `custo_form.html` do `dashboard_content.html` mas manter o endpoint funcional (não o expor na UI principal). Corrigir o bug do endpoint para suportar locais SQLite-only.

2. **Fallback CSV → SQLite ou SQLite-only?**
   - O que sabemos: Os dois locais reais (Casa, Apartamento) têm dados históricos em CSV e provavelmente também em SQLite (ingestão Phase 7).
   - O que está unclear: Se há dados históricos anteriores à Phase 7 que só existem em CSV.
   - Recomendação: SQLite como fonte primária; se sem dados em SQLite, tentar CSV como fallback (retrocompatível). Planner decide se o fallback é necessário ou se a migração SQLite é completa.

3. **Schema de `comparacoes.top_3_json` — formato exacto?**
   - O que sabemos: Inserido pelo serviço `tiagofelicia_compare` da Phase 7. O código de `calculate_annual_ranking()` espera `top_3[]` com keys `supplier`, `plan`, `total_eur`.
   - O que está unclear: Se o JSON serializado em `top_3_json` usa exactamente estas keys ou tem variação.
   - Recomendação: Ler `tests/test_comparacao.py` ou inspecionar dados reais de `comparacoes` antes de implementar `build_analysis_from_sqlite()`.

---

## Sources

### Primary (HIGH confidence)

- Codebase lido directamente — `src/web/routes/dashboard.py`, `data_loader.py`, `rankings.py`, templates, `schema.py`, `style.css`
- `.planning/phases/06-ui-design-ui-phase/06-UI-SPEC.md` — contrato visual aprovado, lido na íntegra
- `.planning/phases/08-upload-pdf-extrac-o-de-faturas/08-01-PLAN.md` + `08-02-PLAN.md` — deliverables Phase 8 verificados
- `.planning/STATE.md` — decisões arquitecturais acumuladas

### Secondary (MEDIUM confidence)

- Padrão Chart.js `bar` com dois datasets sem stack — comportamento conhecido (values `null` omitem barra, sem necessidade de `spanGaps`)

---

## Metadata

**Confidence breakdown:**

- Standard Stack: HIGH — verificado directamente no codebase
- Architecture Patterns: HIGH — baseado em leitura completa do código actual + UI-SPEC
- Pitfalls: HIGH — identificados por análise do código existente (bugs latentes documentados)
- Gap Analysis: HIGH — comparação directa entre estado actual e UI-SPEC

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stack estável, sem dependências externas novas)
