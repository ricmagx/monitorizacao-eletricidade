# Monitorização de Eletricidade — Multi-Local

## What This Is

Ferramenta pessoal macOS para monitorizar o consumo elétrico de dois imóveis (mesma conta E-REDES, CPEs distintos), comparar tarifários de vários comercializadores com base no perfil de consumo real, e recomendar quando compensa mudar de fornecedor. O resultado é um relatório mensal independente por local e uma dashboard web com histórico e ranking.

## Core Value

Com o perfil mensal real de cada local, saber hoje qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual após a configuração inicial.

## Requirements

### Validated

<!-- O que o codebase já faz com certeza -->

- ✓ Normalização E-REDES: converte XLSX de 15 em 15 minutos em CSV mensal (vazio/fora_vazio) — existing
- ✓ Motor de comparação local: calcula custo por tarifário com catálogo JSON, produz ranking e recomendação mono/bihorário — existing
- ✓ Motor de comparação via tiagofelicia.pt: scraping Playwright do simulador oficial, extrai tabela de resultados — existing
- ✓ Workflow mensal orquestrado: `run_workflow()` encadeia download → normalização → comparação → relatório Markdown → notificação macOS — existing
- ✓ Agendamento launchd: reminder no dia 1 às 09:00 + watcher `~/Downloads` para disparar pipeline automaticamente — existing
- ✓ Gestão de sessão E-REDES: bootstrap com Firefox, sessão Playwright persistida em `state/` para downloads automáticos — existing
- ✓ Idempotência: `process_latest_download.py` evita reprocessar o mesmo XLSX — existing

### Active

<!-- O que falta construir -->

- [ ] Validação end-to-end com XLSX real: correr o pipeline completo com os ficheiros XLSX já disponíveis e confirmar que tudo funciona
- [ ] Suporte multi-local: refactorizar config/state/workflow para suportar N locais independentes (cada local com CPE, config e estado próprios)
- [ ] Download multi-CPE: seleccionar o CPE correcto no portal E-REDES durante o download automático (mesma conta, múltiplos contadores)
- [ ] Dashboard web: FastAPI + HTMX + Jinja + Chart.js com histórico mensal por local, ranking de comercializadores e recomendação actual
- [ ] requirements.txt: formalizar dependências (playwright, openpyxl, fastapi, uvicorn, jinja2)

### Out of Scope

- Mudança automática de fornecedor — risco contratual, recomendação conservadora é suficiente
- Captura ao minuto (integração Shelly granular) — agregados mensais chegam para decisão tarifária
- Integração Home Assistant com sensores Lovelace — deferred para v2
- Otimização por aparelho individual — fora do âmbito do comparador tarifário
- Suporte multi-plataforma (Linux/Windows) — macOS-only por design (launchd, osascript)

## Context

**Codebase existente mas nunca executado em produção.** Todo o pipeline backend foi escrito mas ainda não foi validado end-to-end com dados reais. O utilizador tem ficheiros XLSX da E-REDES disponíveis para o primeiro teste.

**Dois imóveis, mesma conta E-REDES:** a mesma sessão Playwright serve os dois locais, mas é preciso seleccionar o CPE correcto no portal antes do download. A arquitectura actual assume um único local.

**Stack técnica:**
- Python 3.11, Playwright 1.58, openpyxl 3.1
- FastAPI + HTMX + Jinja2 + Chart.js (a implementar para a dashboard)
- macOS: launchd, osascript, open -a Firefox
- Dados como ficheiros planos (CSV, JSON, Markdown) — sem base de dados

**Dependência externa crítica:** `tiagofelicia.pt` é o motor principal de comparação. Qualquer alteração ao layout do site quebra o scraping.

## Constraints

- **Plataforma**: macOS only — launchd e osascript não existem noutros sistemas
- **Conta E-REDES**: um único login para ambos os locais — o download multi-CPE tem de usar a mesma sessão
- **Dependência tiagofelicia.pt**: scraping frágil — preferir fallback para catálogo local se o site estiver indisponível
- **Sem lockfile**: não existe `requirements.txt` — qualquer novo programador não consegue instalar as dependências sem documentação

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agregados mensais em vez de dados ao minuto | Suficiente para decisão tarifária; evita storage complexo e Shelly como dependência obrigatória | ✓ Good |
| Ficheiros planos em vez de base de dados | Simplicidade; consultas são sempre sobre todos os meses de um local | — Pending |
| tiagofelicia.pt como motor principal | Preços sempre actualizados sem manutenção de catálogo | ⚠️ Revisit (frágil) |
| macOS-only | Utilizador corre no Mac Mini M4 Pro; launchd é o scheduler natural | ✓ Good |
| Multi-local desde o início | Evita refactorização posterior dolorosa | — Pending |

## Evolution

Este documento evolui em cada transição de fase e milestone.

**Após cada fase** (via `/gsd:transition`):
1. Requirements invalidados? → Mover para Out of Scope com razão
2. Requirements validados? → Mover para Validated com referência à fase
3. Novos requirements? → Adicionar em Active
4. Decisões a registar? → Adicionar em Key Decisions
5. "What This Is" ainda preciso? → Actualizar se derivou

**Após cada milestone** (via `/gsd:complete-milestone`):
1. Revisão completa de todas as secções
2. Core Value check — ainda é a prioridade certa?
3. Auditoria de Out of Scope — razões ainda válidas?
4. Actualizar Context com estado actual

---
*Last updated: 2026-03-28 after initialization*
