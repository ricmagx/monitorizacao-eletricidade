# Monitorização de Eletricidade — Multi-Local

## What This Is

Serviço web em Docker (Unraid) para monitorizar o consumo elétrico de dois imóveis, comparar tarifários de comercializadores com base no consumo real e recomendar quando compensa mudar de fornecedor. O utilizador faz upload do XLSX da E-REDES e das faturas PDF — o sistema processa, armazena histórico multi-ano e apresenta dashboard com ranking e análise comparativa.

## Core Value

Com o perfil mensal real de cada local, saber hoje qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual além do upload mensal.

## Current Milestone: v2.0 Sistema Integrado

**Goal:** Transformar o sistema de monitorização num serviço autónomo em Docker (Unraid), com upload de ficheiros via browser, extracção automática de faturas PDF, histórico multi-ano e UI redesenhado.

**Target features:**
- Docker container no Unraid — eliminar dependência macOS (launchd, osascript)
- Upload XLSX E-REDES via browser (Casa + Apartamento)
- Upload PDF fatura → extracção automática de valores (Meo Energia + Endesa)
- SQLite para histórico multi-ano (3+ anos, 2 locais)
- tiagofelicia.pt como fonte principal + cache quando indisponível
- Locais editáveis no UI (nome livre + CPE associado)
- UI redesenhado (ui-phase antes de qualquer frontend)
- Comparações temporais: mesmo mês em anos diferentes, evolução anual

## Requirements

### Validated

- ✓ Normalização E-REDES: converte XLSX de 15 em 15 minutos em CSV mensal (vazio/fora_vazio) — existing
- ✓ Motor de comparação local: calcula custo por tarifário com catálogo JSON, produz ranking e recomendação mono/bihorário — existing
- ✓ Motor de comparação via tiagofelicia.pt: scraping Playwright do simulador oficial, extrai tabela de resultados — existing
- ✓ Idempotência: evita reprocessar o mesmo XLSX — existing
- ✓ Dashboard web MVP: FastAPI + HTMX + Chart.js, gráficos consumo/custo, ranking top-5, banner recomendação — Validated in Phase 04

### Active

- [ ] Docker container no Unraid com reverse proxy nginx
- [ ] Upload XLSX via browser para cada local
- [ ] Extracção automática de PDF de fatura (Meo Energia + Endesa)
- [ ] SQLite para histórico multi-ano
- [ ] Cache tiagofelicia.pt com fallback transparente
- [ ] Locais editáveis no UI (nome + CPE)
- [ ] UI redesenhado com ui-phase
- [ ] Comparações temporais multi-ano

### Out of Scope

- Download automático da E-REDES (scraping do portal) — frágil, upload manual é suficiente
- Gás — apenas electricidade neste milestone
- Mudança automática de fornecedor — risco contratual
- Captura ao minuto (Shelly) — agregados mensais chegam para decisão tarifária
- Integração Home Assistant — deferred v3
- Otimização por aparelho individual — fora do âmbito do comparador tarifário

## Context

**v1.0 entregou** o pipeline backend completo e dashboard MVP. Nunca correu em produção com dados reais contínuos.

**v2.0 muda a plataforma:** de macOS (launchd) para Docker no Unraid do utilizador. O Unraid já corre nginx em :8090 e homepage em :3000 com Tailscale para acesso remoto.

**Dois imóveis:** Casa (Meo Energia, bi-horário, 10,35 kVA, CPE PT0002000084968079SX) e Apartamento (Endesa, bi-horário, 3,45 kVA, CPE PT00020000398220 82NT). Faturas em formatos PDF distintos mas com texto estruturado — extracção via pdfplumber sem IA.

**Stack técnica v2.0:**
- Python 3.11, FastAPI, SQLite, pdfplumber, openpyxl
- HTMX + Chart.js (sem CDN)
- Docker + docker-compose (Unraid)
- tiagofelicia.pt scraping com cache em SQLite

## Constraints

- **Plataforma**: Docker/Linux — eliminar toda dependência macOS (launchd, osascript, open -a Firefox)
- **Unraid infra**: nginx :8090, homepage :3000, Tailscale, deploy via rsync/SSH para `unraid:/mnt/user/appdata/`
- **Apenas electricidade**: gás excluído mesmo que presente nas faturas (Endesa)
- **tiagofelicia.pt**: scraping frágil — cache obrigatória, nunca bloquear o utilizador se o site estiver em baixo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agregados mensais em vez de dados ao minuto | Suficiente para decisão tarifária | ✓ Good |
| SQLite em vez de ficheiros planos | 3+ anos × 2 locais requerem queries temporais | ✓ Good |
| tiagofelicia.pt + cache (Opção B) | Preços sempre actuais, sistema nunca bloqueia | ✓ Good |
| Upload manual XLSX (não download automático) | Robusto, sem dependência do portal E-REDES | ✓ Good |
| Docker no Unraid | Servidor 24/7 do utilizador, Tailscale já activo | ✓ Good |
| pdfplumber para PDF (sem IA) | Ambos os formatos têm texto estruturado | — Pending |
| UI redesenhado via ui-phase | v1 UI reconhecidamente fraco | — Pending |

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
*Last updated: 2026-03-30 — Milestone v2.0 iniciado (Sistema Integrado)*
