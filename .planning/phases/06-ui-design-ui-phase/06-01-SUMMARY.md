---
phase: 06-ui-design-ui-phase
plan: 01
subsystem: design
tags: [ui-spec, design-system, css-tokens, htmx, chart-js, jinja2, interaction-contract]

# Dependency graph
requires: []
provides:
  - 06-UI-SPEC.md com design system completo (tokens CSS, tipografia, paleta, spacing scale)
  - Component inventory: 7 componentes existentes (estado v2.0) + 5 novos componentes por fase
  - Layout structure: header → selector → banner → grid 2col → upload → ranking → footer
  - Interaction contract HTMX para selector de local, upload XLSX, upload PDF, formulário de local
  - Copywriting contract com 20+ strings de UI (CTAs, empty states, erros, confirmações)
  - Chart.js contract para gráfico de consumo (bar empilhado) e gráfico de custo (bar lado-a-lado)
affects:
  - Phase 7 (upload XLSX + configuração de locais — UI guiada por UI-SPEC)
  - Phase 8 (upload PDF — componente e copywriting definidos)
  - Phase 9 (dashboard redesign — layout e component inventory definidos)
  - Phase 10 (badge de frescura + comparação — badge spec definida)
  - Phase 11 (análise multi-ano — extensões Chart.js definidas)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vanilla CSS com custom properties :root — nenhum framework CSS adicionado"
    - "shadcn não aplicável: stack é FastAPI + Jinja2 + HTMX + Chart.js sem React"
    - "Tokens CSS explícitos (xs a 3xl) formalizados a partir de valores implícitos da v1.0"
    - "Accent (#0d6efd) reservado exclusivamente para 3 CTAs primários"
    - "HTMX hx-trigger='change' para selector de local sem reload de página"

key-files:
  created:
    - .planning/phases/06-ui-design-ui-phase/06-UI-SPEC.md
  modified: []

key-decisions:
  - "Manter vanilla CSS existente: stack FastAPI+Jinja2+HTMX não usa React/shadcn — tokens explicitados em :root"
  - "2 pesos tipográficos apenas (400 regular, 600 semi-bold): eliminar 500 e 700 reduz inconsistências"
  - "Accent reservado para CTAs: evitar diluição do foco do utilizador com accent decorativo"
  - "Banner de recomendação é o ponto focal visual: success green (#198754), maior destaque da página"
  - "Gás Endesa silenciosamente ignorado em upload PDF: não mostrar aviso — simplifica UX"
  - "Editar/eliminar local deferred para v3: sem acções destrutivas em Phase 7"

patterns-established:
  - "UI-SPEC como contrato — fases frontend 7-11 não implementam nada não especificado aqui"
  - "Copywriting contract completo: todas as strings definidas antes de qualquer template HTML"
  - "Component inventory por fase: cada componente novo está atribuído à fase que o implementa"
