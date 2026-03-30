---
phase: 04-web-dashboard-mvp
verified: 2026-03-30T02:15:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Abrir http://localhost:8000 no browser e trocar o selector de local"
    expected: "O fragmento de dashboard muda sem recarregar a pagina inteira (verificavel no Network tab das DevTools — apenas o partial html e devolvido, nao DOCTYPE)"
    why_human: "HTMX swap e comportamento DOM — nao observavel via pytest/TestClient"
  - test: "Carregar a pagina com dados reais (apos gerar data/casa/processed/ com pipeline)"
    expected: "Graficos de barras empilhadas mostram consumo real; ranking mostra fornecedores reais; banner de recomendacao aparece se poupanca > 50 EUR/ano"
    why_human: "data/casa/processed/ nao existe ainda (pipeline nao correu com dados reais na estrutura multi-local — depende de FIX-03 que esta Pending em Phase 1)"
  - test: "Verificar que Chart.js e HTMX carregam de /static/vendor/ e nao de CDN externo"
    expected: "DevTools Network tab mostra htmx.min.js e chart.umd.min.js servidos de localhost:8000/static/vendor/ — nenhum pedido a unpkg/jsdelivr/cdnjs"
    why_human: "Verificacao de Network tab requer browser real"
---

# Phase 4: Web Dashboard MVP — Verification Report

**Phase Goal:** Dashboard web local em modo leitura que apresenta historico de consumo por local, ranking de fornecedores e recomendacao de mudanca, com indicadores de frescura.
**Verified:** 2026-03-30T02:15:00Z
**Status:** PASSED
**Re-verification:** No — verificacao inicial

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                      | Status     | Evidence                                                                                      |
|----|--------------------------------------------------------------------------------------------|------------|-----------------------------------------------------------------------------------------------|
| 1  | uvicorn src.web.app:app arranca sem erros e GET / retorna 200 com selector de local        | VERIFIED   | TestClient: GET / -> 200, HTML contem `<select` e `htmx.min.js`                               |
| 2  | O selector de local lista os locais de config/system.json (casa, apartamento)              | VERIFIED   | dashboard.html itera `locations` via Jinja2; load_locations le config/system.json            |
| 3  | HTMX e Chart.js sao servidos de /static/vendor/ — nenhum pedido a CDN externo             | VERIFIED   | base.html usa `url_for('static', path='vendor/...')` apenas; grep CDN: zero matches          |
| 4  | GET /local/{id}/dashboard retorna fragmento HTML parcial (HTMX swap)                      | VERIFIED   | TestClient: GET /local/casa/dashboard -> 200, sem DOCTYPE, tem `consumo-chart`               |
| 5  | Indicador de frescura mostra data do ultimo relatorio e estado de aviso se > 40 dias       | VERIFIED   | frescura_badge.html com badge-ok/badge-stale; get_freshness_info com limiar 40 dias testado  |
| 6  | Tabela de ranking mostra top-5 fornecedores + fornecedor actual destacado                  | VERIFIED   | rankings.py: calculate_annual_ranking com top5 logic; ranking_table.html com class=highlight |
| 7  | Banner de recomendacao aparece quando poupanca > 50 EUR/ano                               | VERIFIED   | build_recommendation com SAVING_THRESHOLD_EUR=50; recomendacao_banner.html com banner-success |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact                                          | Expected                                           | Status     | Details                                                    |
|---------------------------------------------------|----------------------------------------------------|------------|------------------------------------------------------------|
| `src/web/app.py`                                  | FastAPI app com StaticFiles e Jinja2Templates      | VERIFIED   | app=FastAPI, mount /static, Jinja2Templates, include_router para dashboard e custos         |
| `src/web/services/data_loader.py`                 | load_locations, load_consumo_csv, load_analysis_json, load_monthly_status, get_freshness_info, load_custos_reais, save_custo_real, build_custo_chart_data | VERIFIED   | Todas as 8 funcoes presentes, substantivas e com testes    |
| `src/web/services/rankings.py`                    | calculate_annual_ranking, build_recommendation     | VERIFIED   | Ambas as funcoes presentes; SAVING_THRESHOLD_EUR=50; top5 logic com is_current              |
| `src/web/routes/dashboard.py`                     | GET / e GET /local/{id}/dashboard                  | VERIFIED   | Ambas as routes presentes com 404 para local invalido; importa data_loader e rankings        |
| `src/web/routes/custos_reais.py`                  | POST /local/{id}/custo-real                        | VERIFIED   | Endpoint presente com Form(...), save_custo_real, re-render custo_section.html              |
| `src/web/static/vendor/htmx.min.js`              | HTMX 2.0.8 ficheiro estatico local (>10KB)         | VERIFIED   | 51250 bytes                                                |
| `src/web/static/vendor/chart.umd.min.js`         | Chart.js 4.5.1 ficheiro estatico local (>10KB)     | VERIFIED   | 208522 bytes                                               |
| `src/web/templates/base.html`                     | Template base sem CDN externo                      | VERIFIED   | Usa url_for para vendor/; zero refs a unpkg/jsdelivr/cdnjs |
| `src/web/templates/dashboard.html`                | Selector de local com hx-get e hx-target           | VERIFIED   | local-selector com hx-target="#dashboard-content"          |
| `src/web/templates/partials/dashboard_content.html` | Includes de todos os partials reais              | VERIFIED   | Inclui recomendacao_banner, consumo_chart, custo_section, custo_form, ranking_table — sem placeholders |
| `src/web/templates/partials/consumo_chart.html`   | Chart.js stacked bar com tojson                    | VERIFIED   | new Chart, type:'bar', stack:'consumo', tojson para labels/vazio_data/fora_vazio_data        |
| `src/web/templates/partials/custo_chart.html`     | Chart.js mixed bar+line com spanGaps:false         | VERIFIED   | type:'bar' + type:'line', spanGaps:false, tojson para estimativa_data/custo_real_data        |
| `src/web/templates/partials/frescura_badge.html`  | badge-ok e badge-stale condicionais                | VERIFIED   | Condicional is_stale; mostra days_ago e data; badge-stale quando sem dados                  |
| `src/web/templates/partials/ranking_table.html`   | Tabela com highlight no fornecedor actual           | VERIFIED   | class="highlight" em tr; label "(actual)" no fornecedor atual                                |
| `src/web/templates/partials/recomendacao_banner.html` | Banner condicional banner-success              | VERIFIED   | {% if recommendation.show %} com banner-success                                              |
| `launchd/com.ricmag.monitorizacao-eletricidade.dashboard.plist` | LaunchAgent com RunAtLoad e KeepAlive | VERIFIED   | Label correcto, uvicorn + src.web.app:app, 127.0.0.1:8000, RunAtLoad=true, KeepAlive=true, sem --reload |

---

### Key Link Verification

| From                                  | To                                    | Via                                          | Status  | Details                                                     |
|---------------------------------------|---------------------------------------|----------------------------------------------|---------|-------------------------------------------------------------|
| `src/web/routes/dashboard.py`         | `src/web/services/data_loader.py`     | from src.web.services.data_loader import ... | WIRED   | Importa load_locations, load_consumo_csv, load_analysis_json, load_monthly_status, get_freshness_info, load_custos_reais, build_custo_chart_data |
| `src/web/routes/dashboard.py`         | `src/web/services/rankings.py`        | from src.web.services.rankings import ...    | WIRED   | Importa calculate_annual_ranking, build_recommendation; usadas em _load_location_data |
| `src/web/app.py`                      | `src/web/routes/dashboard.py`         | app.include_router(dashboard_router)         | WIRED   | include_router presente e funcional (TestClient 200)        |
| `src/web/app.py`                      | `src/web/routes/custos_reais.py`      | app.include_router(custos_router)            | WIRED   | include_router presente; app.state.templates exposto        |
| `src/web/services/data_loader.py`     | `config/system.json`                  | json.load; config["locations"]               | WIRED   | load_locations le config/system.json; 2 locais carregados em teste |
| `src/web/templates/consumo_chart.html` | `src/web/routes/dashboard.py`        | Jinja2 context: consumo_chart.labels/vazio_data/fora_vazio_data via tojson | WIRED | dashboard.py constroi consumo_chart dict e passa ao contexto; template usa {{ consumo_chart.labels \| tojson }} |
| `src/web/templates/custo_chart.html`  | `src/web/routes/dashboard.py`         | Jinja2 context: custo_chart via tojson; spanGaps:false | WIRED   | build_custo_chart_data retorna labels/estimativa_data/custo_real_data; spanGaps:false presente |

---

### Data-Flow Trace (Level 4)

| Artifact                              | Data Variable              | Source                                      | Produces Real Data | Status      |
|---------------------------------------|----------------------------|---------------------------------------------|--------------------|-------------|
| `consumo_chart.html`                  | consumo_chart.labels       | load_consumo_csv(data/casa/processed/consumo_mensal_atual.csv) | Condicional: ficheiro NAO existe ainda em data/casa/processed/ — retorna [] graciosamente | HOLLOW (dados nao gerados ainda — dependencia externa: pipeline multi-local nao correu) |
| `ranking_table.html`                  | ranking                    | calculate_annual_ranking(load_analysis_json(...)) | Condicional: analysis_json nao existe em data/casa/processed/ | HOLLOW (mesma causa: FIX-03 Pending) |
| `frescura_badge.html`                 | freshness                  | get_freshness_info(load_monthly_status(...)) | Condicional: state/casa/monthly_status.json nao existe | HOLLOW (mesma causa) |

**Nota critica:** A data-flow trace revela que `data/casa/processed/` nao existe. Os dados historicos estao em `data/processed/` (estrutura pre-Phase-3). O dashboard apresentara graficos vazios ate que o pipeline corra pela primeira vez na estrutura multi-local. Isto nao e um bug de codigo — e uma dependencia de dados (FIX-03 Pending em Phase 1: bootstrap da sessao E-REDES). O codigo lida graciosamente com ficheiros ausentes (retorna []/None, nao crash). O objetivo da fase (dashboard web funcional com logica correcta) esta atingido; falta apenas dados reais para validacao visual completa.

---

### Behavioral Spot-Checks

| Behavior                                     | Command                                                          | Result                                         | Status  |
|----------------------------------------------|------------------------------------------------------------------|------------------------------------------------|---------|
| GET / retorna 200 com selector e HTMX        | TestClient GET /                                                 | 200, `<select` presente, `htmx.min.js` presente | PASS    |
| GET /local/casa/dashboard retorna partial    | TestClient GET /local/casa/dashboard                             | 200, sem DOCTYPE, `consumo-chart` presente      | PASS    |
| GET /local/inexistente/dashboard retorna 404 | TestClient GET /local/inexistente/dashboard                      | 404                                            | PASS    |
| Suite de testes completa                     | pytest tests/ -x -q                                              | 69 passed in 0.48s                             | PASS    |
| Ficheiros estaticos nao conteem CDN          | grep CDN em src/web/templates/                                   | Zero matches                                   | PASS    |
| Plist valido com uvicorn e RunAtLoad         | plistlib.load                                                    | Label, uvicorn, src.web.app:app, RunAtLoad=True, KeepAlive=True, sem --reload | PASS    |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                 | Status           | Evidence                                                              |
|-------------|-------------|-----------------------------------------------------------------------------|------------------|-----------------------------------------------------------------------|
| DASH-01     | 04-01       | Setup FastAPI + Jinja2 + HTMX + Chart.js (ficheiros estaticos)             | SATISFIED        | app.py com StaticFiles; htmx.min.js 51KB e chart.umd.min.js 208KB locais |
| DASH-02     | 04-01, 04-02 | Grafico de consumo mensal (kWh, barras empilhadas vazio/fora_vazio)        | SATISFIED        | consumo_chart.html com Chart.js stacked bar e tojson; GET /local/{id}/dashboard contem consumo-chart |
| DASH-03     | 04-02       | Grafico de custo EUR/mes: custo real + estimativa sobrepostos               | SATISFIED        | custo_chart.html com mixed bar+line, spanGaps:false para meses sem custo real |
| DASH-04     | 04-02       | Custo real da factura: formulario manual por mes                            | SATISFIED        | custo_form.html com hx-post; POST /local/{id}/custo-real com save_custo_real e persistencia JSON |
| DASH-05     | 04-03       | Tabela de ranking de comercializadores por custo anual estimado             | SATISFIED        | calculate_annual_ranking: top-5 + atual; ranking_table.html com highlight e label (actual) |
| DASH-06     | 04-03       | Recomendacao de mudanca com poupanca estimada                               | SATISFIED        | build_recommendation com SAVING_THRESHOLD_EUR=50; banner banner-success condicional |
| DASH-09     | 04-01       | Indicador de frescura dos dados (data do ultimo relatorio gerado)           | SATISFIED (*)    | get_freshness_info com limiar 40 dias; frescura_badge.html com badge-ok/badge-stale; REQUIREMENTS.md marca como Pending — inconsistencia de documentacao |

(*) DASH-09 esta implementado mas marcado como Pending no REQUIREMENTS.md. Nao e um gap de codigo — e uma inconsistencia de rastreabilidade documental. Nao bloqueia o objetivo da fase.

**Requisitos fora de scope desta fase confirmados:**
- DASH-07 (simulacao retroactiva) — Pending, fora de scope Phase 4
- DASH-08 (comparacao homologa / delta ano-a-ano) — Pending, fora de scope Phase 4. O ROADMAP Success Criterion 6 ("delta ano-a-ano") foi identificado em RESEARCH.md como correspondente a DASH-08, nao DASH-06. Os planos interpretaram DASH-06 como "recomendacao de mudanca com poupanca" — decisao do planner documentada em CONTEXT.md D-09.

---

### Anti-Patterns Found

| File                                          | Line | Pattern               | Severity  | Impact                                                    |
|-----------------------------------------------|------|-----------------------|-----------|-----------------------------------------------------------|
| `src/web/templates/dashboard_content.html`    | —    | Nenhum placeholder    | —         | Todos os placeholders do Plan 01/02 foram substituidos por includes reais no Plan 03 |

Nenhum anti-pattern bloqueante encontrado. Sem TODO/FIXME, sem `return null`, sem handlers vazios, sem props hardcoded com valores vazios nos templates finais.

---

### Human Verification Required

#### 1. HTMX Swap Sem Recarga de Pagina

**Test:** Abrir http://localhost:8000 no browser, abrir DevTools > Network tab, trocar o selector de local
**Expected:** Apenas o fragmento HTML e carregado (sem DOCTYPE, sem a pagina completa); o grafico e a tabela actualizam sem reload
**Why human:** Comportamento DOM/HTMX nao e observavel via pytest TestClient

#### 2. Graficos com Dados Reais

**Test:** Apos correr o pipeline (FIX-03 — bootstrap sessao E-REDES) que gere data/casa/processed/, navegar para http://localhost:8000
**Expected:** Grafico de barras empilhadas mostra 11 meses de consumo (jan-nov 2025); ranking lista fornecedores reais com Meo Energia destacado; banner de recomendacao aparece se poupanca > 50 EUR/ano
**Why human:** Requer execucao do pipeline end-to-end (FIX-03 Pending em Phase 1)

#### 3. Verificacao de No-CDN no Browser

**Test:** Abrir http://localhost:8000, DevTools > Network tab, confirmar que htmx.min.js e chart.umd.min.js carregam de localhost:8000/static/vendor/
**Expected:** Nenhum pedido a unpkg.com, jsdelivr.net ou cdnjs.cloudflare.com
**Why human:** Verificacao de Network tab requer browser real (o codigo ja garante isso via grep, mas confirmar em browser e boa pratica)

---

### Gaps Summary

Nenhum gap bloqueante. A fase atingiu o seu objetivo.

A unica observacao de data-flow e que `data/casa/processed/` nao existe porque o pipeline multi-local ainda nao correu (FIX-03 Pending). O dashboard apresenta estado vazio de forma graciosamente (sem crash, sem erro) ate que os dados existam. Isto e uma dependencia de dados externa ao scope desta fase, nao um defeito de codigo.

A inconsistencia de rastreabilidade (DASH-09 implementado mas marcado Pending no REQUIREMENTS.md) e apenas documental — nao afeta o funcionamento.

---

*Verified: 2026-03-30T02:15:00Z*
*Verifier: Claude (gsd-verifier)*
