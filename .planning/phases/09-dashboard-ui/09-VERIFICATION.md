---
phase: 09-dashboard-ui
verified: 2026-03-31T00:00:00Z
status: passed
score: 9/9 must-haves verified
gaps: []
human_verification:
  - test: "Abrir browser em http://localhost:8000 e seleccionar um local SQLite-only"
    expected: "Grafico de consumo aparece com barras vazio/fora_vazio; ranking mostra coluna Poupanca Potencial (EUR/ano); banner de recomendacao inclui nome do plano; botao Importar Fatura PDF visivel no layout"
    why_human: "Verificacao visual de cores Chart.js (azul/rosa UI-SPEC), espaçamento e tipografia nao testavel programaticamente"
---

# Phase 9: Dashboard UI — Verification Report

**Phase Goal:** Dashboard UI fully aligned with UI-SPEC — all locals (including SQLite-only) show consumption data, rankings with savings column, bar+bar cost chart, recommendation banner with plan name, PDF upload integrated in layout.
**Verified:** 2026-03-31
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Locais criados via UI (sem pipeline CSV) mostram dados de consumo no dashboard | VERIFIED | `_load_location_data` usa `load_consumo_sqlite` como fonte primaria; fixture `web_client_sqlite` com seed data real; `test_sqlite_only_local_shows_consumo` passa |
| 2 | Locais criados via UI mostram dados de comparacao/ranking no dashboard | VERIFIED | `build_analysis_from_sqlite` consulta tabela `comparacoes`; `test_sqlite_only_local_shows_ranking` verifica fornecedores Luzboa/EDP/Meo Energia no HTML |
| 3 | Locais criados via UI mostram custos reais de fatura no dashboard | VERIFIED | `load_custos_reais_sqlite` consulta tabela `custos_reais`; seed data inclui custo_eur=145.50 para "2025-01" |
| 4 | Frescura e calculada a partir de comparacoes SQLite quando monthly_status.json nao existe | VERIFIED | `get_freshness_from_sqlite` usa `SELECT MAX(cached_at)` da tabela comparacoes; retorna `is_stale=True` se sem dados |
| 5 | Locais com pipeline CSV continuam a funcionar (retrocompatibilidade) | VERIFIED | `_load_location_data` faz fallback para `load_consumo_csv` se SQLite vazio e `pipeline` presente; `test_pipeline_local_still_works` passa |
| 6 | Ranking de fornecedores mostra coluna de poupanca potencial em EUR/ano | VERIFIED | `calculate_annual_ranking` calcula `poupanca_potencial` para cada entry; `ranking_table.html` renderiza coluna com estilo success; `test_ranking_has_poupanca_column` passa |
| 7 | Grafico de custo usa dois datasets bar lado a lado (nao line chart para custo real) | VERIFIED | `custo_chart.html` tem dois datasets com `type: 'bar'`; cores UI-SPEC aplicadas (azul 54,162,235 e rosa 255,99,132); `test_custo_chart_uses_bar_type` verifica ausencia de `type: 'line'` |
| 8 | Banner de recomendacao mostra nome do plano alem do fornecedor | VERIFIED | `build_recommendation` retorna campo `plan`; `recomendacao_banner.html` usa `recommendation.plan` com conditional `{% if recommendation.plan %}`; mensagem segue formato UI-SPEC |
| 9 | Upload PDF integrado no layout do dashboard | VERIFIED | `dashboard_content.html` inclui `upload_pdf.html`; ficheiro existe (17 linhas, formulario HTMX funcional); custo_form.html removido do layout; `test_dashboard_has_upload_pdf` e `test_dashboard_no_custo_form` passam |

**Score:** 9/9 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/web/services/data_loader.py` | SQLite reader functions: `load_consumo_sqlite`, `build_analysis_from_sqlite`, `load_custos_reais_sqlite`, `get_freshness_from_sqlite` | VERIFIED | Todas as 4 funcoes presentes (linhas 251-420); usam SQLAlchemy Core `select()` com `row._mapping`; retornam formatos compatíveis com os consumidores existentes |
| `src/web/routes/dashboard.py` | `_load_location_data` reescrito para usar SQLite como fonte primaria | VERIFIED | SQLite-first com fallback CSV para todos os locais; sem bloco `if "pipeline" not in location: return vazios`; importa as 4 novas funcoes SQLite |
| `src/web/routes/custos_reais.py` | Bug `location["pipeline"]` KeyError corrigido para locais SQLite-only | VERIFIED | Bloco `if "pipeline" in location / else` com `load_consumo_sqlite` + `build_analysis_from_sqlite` para locais sem pipeline |
| `src/web/services/rankings.py` | `calculate_annual_ranking` com campo `poupanca_potencial`; `build_recommendation` com campo `plan` | VERIFIED | `poupanca_potencial` calculado em linhas 86-93; `build_recommendation` retorna `plan` e mensagem UI-SPEC "Mudando para X — plano Y, poupa cerca de Z EUR/ano" |
| `src/web/templates/partials/custo_chart.html` | Dois datasets `type: 'bar'` lado a lado (sem line chart) | VERIFIED | Ambos datasets com `type: 'bar'`; cores UI-SPEC; legenda `position: 'bottom'`; eixo Y "EUR" |
| `src/web/templates/partials/ranking_table.html` | Coluna `Poupanca Potencial (EUR/ano)` | VERIFIED | `<th>Poupanca Potencial (EUR/ano)</th>` no thead; logica de rendering com estilo success para poupanca positiva; "—" para fornecedor actual e poupanca nula/negativa |
| `src/web/templates/partials/recomendacao_banner.html` | Banner mostra plano via `recommendation.plan` | VERIFIED | Template inline com conditional para `recommendation.plan`; funciona mesmo com plan vazio |
| `src/web/templates/partials/dashboard_content.html` | Layout com upload_xlsx + upload_pdf, sem custo_form | VERIFIED | `custo_form.html` ausente; `upload_pdf.html` incluido; ordem: banner → graficos → upload_xlsx → upload_pdf → ranking |
| `tests/conftest.py` | Fixture `web_client_sqlite` com seed data SQLite real | VERIFIED | Fixture completa (linhas 362-488); StaticPool para engine in-memory; seed data de consumo (3 meses), comparacoes (2 meses com top_3_json e current_supplier_result_json) e custos_reais (1 mes) |
| `tests/test_web_dashboard.py` | Testes para locais SQLite-only e alinhamento UI-SPEC | VERIFIED | 9 testes no ficheiro; 4 testes SQLite-only + 4 testes UI-SPEC; todos passam |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/web/routes/dashboard.py` | `src/web/services/data_loader.py` | `load_consumo_sqlite`, `build_analysis_from_sqlite` | WIRED | Importados e chamados em `_load_location_data()` (linhas 9-20, 39-46) |
| `src/web/services/data_loader.py` | `src/db/schema.py` | `select(consumo_mensal_table)`, `select(comparacoes_table)`, `select(custos_reais_table)` | WIRED | Queries reais nas linhas 263, 297, 362; usa `row._mapping` para acesso seguro |
| `src/web/services/rankings.py` | `src/web/templates/partials/ranking_table.html` | campo `poupanca_potencial` no dict de ranking | WIRED | Campo calculado em rankings.py:91-93; renderizado em ranking_table.html:24-25 |
| `src/web/services/rankings.py` | `src/web/templates/partials/recomendacao_banner.html` | campo `plan` no dict de recommendation | WIRED | Campo retornado em rankings.py:135; acedido em banner via `recommendation.plan` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ranking_table.html` | `ranking` (list de dicts) | `calculate_annual_ranking` ← `build_analysis_from_sqlite` ← SQLite `comparacoes` | Sim — SELECT real com `row._mapping`; seed data com top_3_json e current_supplier_result_json | FLOWING |
| `custo_chart.html` | `custo_chart` (labels + datasets) | `build_custo_chart_data` ← `load_consumo_sqlite` + `load_custos_reais_sqlite` ← SQLite | Sim — ambas as funcoes fazem SELECT real; seed data com 3 meses consumo e 1 mes custo | FLOWING |
| `recomendacao_banner.html` | `recommendation` (dict) | `build_recommendation` ← `build_analysis_from_sqlite` ← SQLite `comparacoes` | Sim — derivado de history_summary calculado de dados reais SQLite | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 107 testes passam sem regressoes | `python3 -m pytest tests/ -q` | `107 passed, 14 skipped in 0.88s` | PASS |
| Testes UI-SPEC e SQLite-only passam | `python3 -m pytest tests/test_web_dashboard.py tests/test_web_data_loader.py tests/test_web_rankings.py -q` | `45 passed in 0.71s` | PASS |
| Suite completa sem crash | `python3 -m pytest tests/ -q` | 0 failures, 0 errors | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UI-02 | 09-01-PLAN.md | Selector de local no topo da dashboard | SATISFIED | Selector presente no homepage; `load_locations` merge config.json + SQLite; locais SQLite-only aparecem via `get_all_locais` |
| UI-03 | 09-01-PLAN.md, 09-02-PLAN.md | Ranking de fornecedores com poupanca potencial em EUR/ano | SATISFIED | `calculate_annual_ranking` calcula `poupanca_potencial`; coluna renderizada em `ranking_table.html` |
| UI-04 | 09-01-PLAN.md | Grafico de consumo mensal (vazio/fora_vazio empilhados) | SATISFIED | `consumo_chart.html` existente (Phase 4); `_load_location_data` popula `consumo_chart` com dados SQLite para todos os locais |
| UI-05 | 09-01-PLAN.md, 09-02-PLAN.md | Grafico de custo: estimativa vs custo real (bar+bar) | SATISFIED | `custo_chart.html` corrigido para dois datasets `type: 'bar'` com cores UI-SPEC; dados de SQLite e custos_reais |

Notas sobre requisitos no REQUIREMENTS.md vs ROADMAP.md:
- REQUIREMENTS.md marca UI-02, UI-03, UI-04, UI-05 como `[x]` (completos) — consistente com a implementacao verificada.
- ROADMAP.md Coverage table indica UI-02 a UI-05 como "Pending" — esta discrepancia e cosmética (o ROADMAP.md Coverage table e mais antigo que REQUIREMENTS.md); a implementacao real existe e foi verificada.

Sem orphaned requirements — UI-02, UI-03, UI-04, UI-05 estao todos mapeados nas PLANs da Phase 9.

---

## Anti-Patterns Found

Nenhum anti-pattern bloqueante encontrado. Notas:

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `custo_form.html` | Ficheiro existe mas nao e incluido em `dashboard_content.html` | Info | O endpoint POST /local/{id}/custo-real continua funcional; o formulario foi removido do layout conforme especificado no plano; custo_form.html e ficheiro orfao inerte |

---

## Human Verification Required

### 1. Verificacao Visual do Dashboard

**Test:** Arrancar o servidor (`uvicorn src.web.app:app --reload`), abrir http://localhost:8000, seleccionar um local que tenha dados em SQLite.
**Expected:** (a) Grafico de custo mostra duas barras lado a lado por mes — uma azul (estimativa) e uma rosa/vermelha (custo real); (b) Ranking mostra coluna "Poupanca Potencial" com valores a verde nos fornecedores mais baratos; (c) Banner de recomendacao (quando poupanca > 50 EUR/ano) inclui "— plano [nome]" na mensagem; (d) Secao "Importar Fatura PDF" visivel no layout, sem o formulario manual de custo.
**Why human:** Cores exactas do Chart.js (rgba), espacamento, tipografia e comportamento visual nao sao verificaveis por grep ou testes de resposta HTML.

---

## Gaps Summary

Sem gaps. Todos os 9 must-haves verificados. A implementacao cobre os requisitos UI-02, UI-03, UI-04 e UI-05 na totalidade.

O unico item que requer atencao humana e a verificacao visual das cores e layout no browser — nao e um gap de implementacao, e confirmacao de qualidade visual.

---

_Verified: 2026-03-31_
_Verifier: Claude (gsd-verifier)_
