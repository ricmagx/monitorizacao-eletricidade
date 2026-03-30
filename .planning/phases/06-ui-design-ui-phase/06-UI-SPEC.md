---
phase: 6
slug: ui-design
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-30
---

# Phase 6 — UI Design Contract

> Visual and interaction contract para fases frontend (Phase 7, 8, 9, 10, 11).
> Gerado por gsd-ui-researcher. Verificado por gsd-ui-checker.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none — CSS custom properties + vanilla CSS |
| Preset | not applicable |
| Component library | none — HTML nativo + Jinja2 partials |
| Icon library | none (texto/badges em substituição de ícones) |
| Font | system-ui, -apple-system, sans-serif |

**Fonte:** `src/web/static/style.css` existente — tokens CSS já definidos como `:root` custom properties.
**shadcn não aplicável:** stack é FastAPI + Jinja2 + HTMX + Chart.js. Não existe React/Next.js/Vite.
**Decisão:** Manter a abordagem vanilla CSS existente e formalizar os tokens detectados.

---

## Spacing Scale

Declared values (multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, separadores inline, `padding: 0.25rem` em badges |
| sm | 8px | Padding compacto — botões inline, inputs, células de tabela (`padding: 0.5rem 0.75rem`) |
| md | 16px | Espaçamento entre elementos dentro de card, padding de formulário inline |
| lg | 20px | Padding interno de card (`padding: 1.25rem`) |
| xl | 24px | Margem entre cards (`margin-bottom: 1.25rem`) |
| 2xl | 32px | Padding lateral de página (`padding: 1rem 2rem`) |
| 3xl | 48px | Separação de secções principais no layout |

Exceptions:
- Touch targets em mobile: mínimo 44px de altura para botões e selects
- Header bottom padding: `padding-bottom: 1rem` (16px) com `border-bottom`

**Fonte:** `style.css` existente — escala implícita convertida para tokens explícitos.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px (1rem) | 400 (regular) | 1.5 |
| Label / Small | 13.6px (0.85rem) | 500 (medium) | 1.4 |
| Heading (h2) | 19.2px (1.2rem) | 400 (regular) | 1.3 |
| Display (h1) | 24px (1.5rem) | 400 (regular) | 1.2 |

Regras:
- Cabeçalhos de tabela (`th`): 13.6px, weight 600, uppercase, cor `--muted`
- Texto muted (legendas, estado vazio): 16px, weight 400, cor `#6c757d`
- Valores monetários destacados: weight 700 em contexto de ranking (fornecedor recomendado)

**Fonte:** `style.css` existente + extensão para v2.0.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#f8f9fa` | Background de página (`--bg`) |
| Secondary (30%) | `#ffffff` | Fundo de cards, tabelas, formulários (`--card-bg`) |
| Accent (10%) | `#0d6efd` | Botão primário "Guardar", link activo no selector de local, indicador de comparação actualizado |
| Success | `#198754` | Badge "dados frescos", banner de recomendação de mudança, linha de fornecedor mais barato |
| Warning | `#ffc107` / `#856404` | Badge "dados desactualizados" (>40 dias), linha de fornecedor actual em ranking quando não é o mais barato |
| Danger | `#dc3545` | Mensagens de erro de upload (PDF/XLSX inválido ou não reconhecido) |
| Border | `#dee2e6` | Separadores de tabela, bordas de card, bordas de input |
| Text primary | `#212529` | Corpo de texto |
| Text muted | `#6c757d` | Labels secundários, estados vazios, texto de apoio |

Accent (`#0d6efd`) reservado especificamente para:
1. Botão "Guardar" no formulário de custo real
2. Botão de submit no formulário de upload XLSX/PDF
3. Botão "Criar local" no formulário de configuração de locais

Accent NÃO é usado em: links de texto, ícones decorativos, bordas de card, texto de ranking.

**Fonte:** `style.css` existente — tokens `:root` detectados e classificados por papel.

---

## Component Inventory

Os seguintes componentes existem na v1.0 e são preservados/estendidos em v2.0:

| Componente | Ficheiro | Estado v2.0 |
|------------|----------|-------------|
| Badge de frescura | `partials/frescura_badge.html` | Estender: mostrar data da consulta tiagofelicia.pt separada |
| Banner de recomendação | `partials/recomendacao_banner.html` | Preservar — adicionar valor de poupança em EUR/ano |
| Tabela de ranking | `partials/ranking_table.html` | Estender: coluna de poupança potencial (EUR/ano vs actual) |
| Gráfico de consumo | `partials/consumo_chart.html` | Estender: suporte multi-ano com cores distintas por ano |
| Gráfico de custo | `partials/custo_chart.html` | Preservar — estimativa vs custo real de fatura |
| Formulário custo real | `partials/custo_form.html` | Migrar: entradas manuais substituídas por upload PDF |
| Selector de local | `dashboard.html` | Preservar padrão HTMX — adicionar link "Editar locais" |

Novos componentes a criar em v2.0:

| Componente | Fase | Descrição |
|------------|------|-----------|
| Upload XLSX | Phase 7 | Drop zone + botão + feedback de confirmação com período importado |
| Upload PDF | Phase 8 | Drop zone + botão + feedback de extracção (valor + período detectados) |
| Formulário de local | Phase 7 | Nome livre + CPE — criar e editar |
| Badge de fonte comparação | Phase 10 | "Dados frescos" vs "Cache de YYYY-MM-DD" |
| Painel de resumo anual | Phase 11 | Custo total + consumo total por ano |

---

## Layout

### Estrutura de página (container único)

```
[HEADER]
  - Título "Monitorização de Electricidade"
  - Badge de frescura (dados)

[SELECTOR BAR]
  - Label "Local:" + <select> com HTMX
  - Link "Gerir locais" (nova funcionalidade v2.0)

[BANNER DE RECOMENDAÇÃO] — condicional, só se poupança > 50 EUR/ano

[GRID 2 COLUNAS — desktop / 1 coluna mobile]
  - Gráfico de consumo mensal (vazio/fora vazio empilhados)
  - Gráfico de custo (estimativa vs real)

[SECÇÃO DE UPLOAD] — nova em v2.0
  - Upload XLSX E-REDES
  - Upload PDF Fatura

[TABELA DE RANKING]
  - Fornecedores por custo anual estimado
  - Linha do fornecedor actual destacada

[FOOTER / STATUS] — opcional
```

### Breakpoints

| Breakpoint | Comportamento |
|------------|---------------|
| >= 769px | Grid 2 colunas para gráficos |
| <= 768px | Grid 1 coluna, tudo em stack vertical |

**Fonte:** `@media (max-width: 768px)` existente em `style.css`.

### max-width

Container: `max-width: 1200px`, centrado com `margin: 0 auto`.

---

## Interaction Contract

### Selector de local

- Comportamento: `hx-trigger="change"` → HTMX GET para `/local/{id}/dashboard` → substitui `#dashboard-content`
- Loading state: `htmx-indicator` class durante pedido (actualmente escondido via CSS — a manter)
- Sem reload de página completa

### Upload XLSX (Phase 7)

- Formulário com `enctype="multipart/form-data"`
- Submit via HTMX POST
- Resposta: partial HTML com confirmação — "Importados X meses de [local] (CPE: XXXX)"
- Erro: partial HTML com mensagem de erro em vermelho (`--danger`) — "Ficheiro não reconhecido como XLSX E-REDES válido"
- Idempotência: se dados já existem → "Dados já importados para este período. Nenhuma alteração efectuada."

### Upload PDF (Phase 8)

- Formulário com `enctype="multipart/form-data"`
- Submit via HTMX POST
- Resposta: "Fatura [mês/ano] de [fornecedor]: EUR XX.XX registado"
- Erro: "PDF não reconhecido como fatura Meo Energia ou Endesa. Verificar ficheiro."
- Gás (Endesa): silenciosamente ignorado — não mostrar aviso

### Formulário de local (Phase 7)

- Campos: Nome (text, obrigatório) + CPE (text, obrigatório, formato PT000...)
- Submit via HTMX POST
- Resposta: actualiza lista de locais no selector
- Sem confirmação destrutiva — editar local não apaga dados históricos

### Banner de recomendação

- Aparece apenas quando `poupanca_anual >= 50 EUR`
- Cópia: "Mudando para [fornecedor] — plano [plano], poupa cerca de [X] EUR/ano"
- Não aparece quando dados de comparação estão a mais de 60 dias (badge stale activo)

---

## Copywriting Contract

| Elemento | Cópia |
|----------|-------|
| Primary CTA (upload XLSX) | "Importar XLSX" |
| Primary CTA (upload PDF) | "Importar Fatura PDF" |
| Primary CTA (guardar custo) | "Guardar" |
| Primary CTA (criar local) | "Criar Local" |
| Empty state — sem dados de consumo | "Sem dados de consumo. Faça upload do XLSX da E-REDES para este local." |
| Empty state — sem ranking | "Sem dados de comparação disponíveis. Importe um XLSX para gerar o ranking." |
| Empty state — sem locais | "Nenhum local configurado. Crie um local com o CPE da E-REDES." |
| Error — XLSX inválido | "Ficheiro não reconhecido como exportação E-REDES. Verifique o formato e tente novamente." |
| Error — PDF não reconhecido | "PDF não identificado como fatura Meo Energia ou Endesa. Verifique o ficheiro." |
| Error — CPE não encontrado no ficheiro | "CPE não detectado no ficheiro. Associe o ficheiro ao local manualmente." |
| Error — servidor indisponível | "Erro de servidor. Tente novamente em alguns instantes." |
| Frescura — dados ok | "Última actualização: [data] (há [N] dias)" |
| Frescura — dados stale | "Dados desactualizados — Última actualização: [data]" |
| Comparação — dados frescos | "Tarifários actualizados em [data]" |
| Comparação — dados de cache | "Tarifários do cache — tiagofelicia.pt indisponível (última consulta: [data])" |
| Recomendação activa | "Mudando para [fornecedor] — plano [plano], poupa cerca de [X] EUR/ano" |
| Recomendação sem mudança | "O seu fornecedor actual já está entre os mais baratos para o seu perfil de consumo." |
| Upload idempotente XLSX | "Dados já importados para [mês/ano]. Nenhuma alteração efectuada." |
| Confirmação upload XLSX | "Importados [N] meses para [local] (CPE: [CPE]). Período: [mês início] a [mês fim]." |
| Confirmação upload PDF | "Fatura [fornecedor] — [mês/ano]: EUR [valor] registado." |

Acções destrutivas nesta fase: nenhuma. Editar/eliminar local é deferred (não há eliminação de dados em Phase 7).

---

## Chart.js Contract

### Gráfico de consumo mensal (vazio/fora vazio)

- Tipo: `bar` empilhado (`stack: 'consumo'`)
- Dataset "Vazio (kWh)": `rgba(54, 162, 235, 0.8)` — azul
- Dataset "Fora de Vazio (kWh)": `rgba(255, 159, 64, 0.8)` — laranja
- Legenda: `position: 'bottom'`
- Eixo Y: título "kWh"
- Multi-ano (Phase 11): cada ano com opacidade diferente na mesma paleta (0.9 → ano mais recente, 0.5 → mais antigo)

### Gráfico de custo (estimativa vs real)

- Tipo: `bar` com dois datasets lado a lado (não empilhados)
- Dataset "Estimativa (EUR)": `rgba(54, 162, 235, 0.8)` — azul
- Dataset "Custo Real (EUR)": `rgba(255, 99, 132, 0.8)` — vermelho/rosa
- Legenda: `position: 'bottom'`
- Eixo Y: título "EUR"

**Fonte:** `partials/consumo_chart.html` existente — cores e configuração preservadas.

---

## States Inventory

Para cada componente principal, os estados que o executor deve implementar:

### Dashboard completo

| Estado | Trigger | Visualização |
|--------|---------|--------------|
| Loaded | Dados existem | Layout normal com gráficos e ranking |
| Empty | Sem XLSX importado para este local | Empty state cards com mensagem + CTA de upload |
| Loading | HTMX request em curso | `htmx-indicator` visível (spinner ou texto) |
| Stale | Dados > 40 dias | Badge amarelo no header |

### Upload XLSX/PDF

| Estado | Trigger | Visualização |
|--------|---------|--------------|
| Idle | Sem ficheiro seleccionado | Botão desactivado ou placeholder |
| Selected | Ficheiro escolhido | Nome do ficheiro visível |
| Uploading | POST em curso | Botão desactivado + indicador |
| Success | Processamento ok | Mensagem verde com detalhe do período importado |
| Error | Ficheiro inválido / erro servidor | Mensagem vermelha com instrução de recuperação |
| Duplicate | XLSX já importado | Mensagem neutra (não erro) — "já importado" |

### Badge de frescura

| Estado | Trigger | Classe CSS |
|--------|---------|------------|
| Fresh | dias_desde_relatorio <= 40 | `badge-ok` (fundo verde claro) |
| Stale | dias_desde_relatorio > 40 | `badge-stale` (fundo amarelo) |
| No data | Sem relatório ainda | `badge-stale` + texto "Sem dados" |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable — shadcn not initialized |
| npm/CDN Chart.js | `chart.umd.min.js` (vendored) | already vendored in static/vendor/ — no external requests |
| npm/CDN HTMX | `htmx.min.js` (vendored) | already vendored in static/vendor/ — no external requests |

Nota: todos os assets JS estão em `src/web/static/vendor/` — sem pedidos externos em runtime (DASH-06 satisfeito).

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
