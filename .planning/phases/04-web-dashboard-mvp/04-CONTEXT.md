# Phase 4: Web Dashboard MVP - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Dashboard web local em modo leitura que apresenta histórico de consumo por local, ranking de
fornecedores e recomendação de mudança, com indicadores de frescura e delta ano-a-ano.
Opera sobre os ficheiros de output do pipeline (CSV + JSON) — não gera dados, só os apresenta.
Sem autenticação (ferramenta local, utilizador único).

Requisitos em scope: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06.
Requisitos DASH-07 a DASH-09 (simulação retroactiva, comparação homólogo, frescura avançada)
— ver REQUIREMENTS.md para estado (alguns podem estar no success criteria do ROADMAP).
</domain>

<decisions>
## Implementation Decisions

### Stack & Infraestrutura
- **D-01:** FastAPI + HTMX + Jinja2 + Chart.js — stack confirmado. Chart.js e HTMX servidos como ficheiros estáticos locais (sem CDN, sem build step).
- **D-02:** Módulo web em `src/web/` — entry point `uvicorn src.web.app:app` (conforme success criteria do ROADMAP).
- **D-03:** Sem autenticação — ferramenta local, utilizador único.

### Arranque do Servidor
- **D-04:** LaunchAgent automático — novo plist launchd que arranca o uvicorn no login do sistema. A dashboard fica disponível em background.
- **D-05:** Browser manual — o utilizador navega para `http://localhost:8000` quando quiser consultar a dashboard. O script/plist não abre o browser automaticamente.

### Custo Real da Factura (DASH-04)
- **D-06:** Formulário inline na dashboard (HTMX + POST). O utilizador introduz o custo real da factura directamente na dashboard, mês a mês, por local. A dashboard persiste os valores num ficheiro JSON (ex: `data/{local}/custos_reais.json`).
- **D-07:** Quando não existe custo real para um mês, omitir a linha no gráfico DASH-03. Meses sem dado mostram apenas a estimativa calculada — sem indicador de "pendente".

### Ranking de Fornecedores (DASH-05)
- **D-08:** Top-5 fornecedores por custo anual estimado + fornecedor actual (mesmo que não esteja no top-5). O fornecedor actual destacado visualmente na tabela.

### Recomendação de Mudança (DASH-06)
- **D-09:** Banner colorido com poupança estimada: "Podes poupar ~X €/ano mudando para [Fornecedor]". Só aparece se a poupança estimada for significativa (limiar: > 50 €/ano — deixar ao planner se o valor deve ser configurável). Baseado nos dados do último relatório disponível.

### Claude's Discretion
- Layout geral da página (o utilizador não discutiu esta área) — organização dos widgets, selector de local, disposição dos gráficos e tabela ficam a cargo do planner/implementador.
- Versões específicas de HTMX e Chart.js a usar (ROADMAP menciona HTMX 2.0.x e Chart.js 4.4.x como referência).
- Schema exacto do ficheiro `custos_reais.json` — planner decide estrutura.
- Limiar exacto para exibir o banner de recomendação (> 50 €/ano é sugestão, não decisão locked).
- Indicador de confiança na recomendação (DASH-06) — planner decide se inclui e como.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requisitos da Dashboard
- `.planning/REQUIREMENTS.md` §Dashboard Web — definições DASH-01 a DASH-09, critérios de aceitação
- `.planning/ROADMAP.md` §Phase 4 — success criteria, key risks, dependências

### Contexto do Projecto
- `.planning/PROJECT.md` — Stack técnica, Out of Scope (incluindo INT-03: leitura PDF factura = fora de scope v1), princípios de design
- `.planning/codebase/ARCHITECTURE.md` — Padrão de módulos, data flow do pipeline, onde encaixar a camada web
- `.planning/codebase/STRUCTURE.md` — Estrutura de directórios, onde adicionar novo código (`src/web/`, `launchd/`)
- `.planning/codebase/STACK.md` — Stack confirmado, versões de dependências

### Dados de Output do Pipeline (input da dashboard)
- `data/processed/consumo_mensal_atual.csv` — CSV de consumo mensal (vazio / fora_vazio kWh) — formato actual após Phase 3
- `data/processed/analise_tiagofelicia_atual.json` — JSON de análise do motor de comparação — schema a confirmar após Phase 3
- `state/monthly_status.json` — estado do último run do pipeline (para indicador de frescura)
- `data/reports/` — relatórios Markdown históricos (para determinar data do último relatório)

### Agendamento
- `launchd/` — plists existentes como referência para criar o novo plist do servidor web
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/backend/monthly_workflow.py`: `run_workflow()` — lógica de pipeline que a dashboard consome passivamente (não invoca, lê os outputs)
- `src/backend/energy_compare.py`: `MonthlyConsumption` dataclass — pode ser útil para parsing do CSV de consumo nos routes FastAPI
- `config/system.json`: configuração de locais (schema `"locations": [...]` com id, nome, CPE, fornecedor actual) — a dashboard lê daqui os locais disponíveis
- `state/monthly_status.json`: status do último pipeline run — usado para o indicador de frescura

### Established Patterns
- Flat file data: todos os dados como CSV/JSON em directórios por local (`data/{local}/`) — a dashboard é mais um consumidor desta convenção
- Config via `system.json`: todos os scripts acedem config via `--config` flag; a dashboard deve ler o mesmo ficheiro
- `src/backend/` flat structure: cada módulo é CLI + importável; `src/web/` deve seguir convenção análoga
- launchd plists: padrão existente em `launchd/` com `WorkingDirectory` e paths absolutos — novo plist para uvicorn deve seguir este padrão

### Integration Points
- `src/web/` (a criar) conecta-se a `data/`, `state/` e `config/system.json` via leitura directa de ficheiros
- Novo plist launchd (`com.ricmag.monitorizacao-eletricidade.dashboard.plist`) integra no mesmo namespace dos plists existentes
- `data/{local}/custos_reais.json` (a criar) — novo ficheiro de estado gerido pela dashboard (POST via HTMX)
- Selector de local na dashboard consome `config/system.json → locations[].id/nome`
</code_context>

<specifics>
## Specific Ideas

- OCR de PDF de factura para extracção automática do custo real — mencionado pelo utilizador mas explicitamente fora de scope v1 (INT-03 em REQUIREMENTS.md Out of Scope). Registado em Deferred.
- O utilizador quer o banner de recomendação simples e directo ("Podes poupar ~X €/ano mudando para [Fornecedor]") — não um card elaborado com múltiplas métricas.
</specifics>

<deferred>
## Deferred Ideas

- **Importação de PDF da factura por OCR** — mencionado pelo utilizador como input preferido para o custo real. Está explicitamente fora de scope v1 (REQUIREMENTS.md Out of Scope: "Leitura automática de PDF de factura — deferred para v2, INT-03"). A implementar em v2.

### Reviewed Todos (not folded)
Nenhum todo relevante encontrado para esta fase.
</deferred>

---

*Phase: 04-web-dashboard-mvp*
*Context gathered: 2026-03-30*
