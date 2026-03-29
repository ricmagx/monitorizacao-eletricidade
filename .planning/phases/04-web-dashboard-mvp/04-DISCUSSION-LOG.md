# Phase 4: Web Dashboard MVP - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — este log preserva o registo da discussão.

**Date:** 2026-03-30
**Phase:** 04-web-dashboard-mvp
**Mode:** discuss
**Areas analyzed:** Custo real da factura, Arranque do servidor, Ranking & recomendação

## Gray Areas Presented

| Área | Descrita como |
|------|--------------|
| Layout & navegação | Scroll único vs tabs vs sidebar; organização dos widgets |
| Custo real da factura | CSV manual vs formulário inline na dashboard |
| Arranque do servidor | uvicorn manual vs LaunchAgent automático |
| Ranking & recomendação | Todos os fornecedores ou top-N; formato da recomendação |

## Áreas Seleccionadas pelo Utilizador

Custo real da factura, Arranque do servidor, Ranking & recomendação.
(Layout & navegação não seleccionado → Claude's Discretion)

## Questões e Respostas

### Custo real da factura

| Questão | Opções | Resposta |
|---------|--------|----------|
| Como introduzir o custo real da factura? | CSV manual / Formulário inline / Tu decides | OCR de PDF da factura (se não for possível, formulário) |
| Quando não existe custo real para um mês? | Omitir a linha / Mostrar como pendente / Tu decides | Omitir a linha |

**Nota:** OCR de PDF foi identificado como scope creep — já em Out of Scope v1 (INT-03). Decisão locked: formulário inline na dashboard.

### Arranque do servidor

| Questão | Opções | Resposta |
|---------|--------|----------|
| Como arrancar o servidor? | Script manual / LaunchAgent automático / Tu decides | LaunchAgent automático |
| Browser abre automaticamente? | Abre automaticamente / Navegas manualmente / Tu decides | Navegas manualmente |

### Ranking & recomendação

| Questão | Opções | Resposta |
|---------|--------|----------|
| Quantos fornecedores no ranking? | Todos / Top-5 + actual / Tu decides | Top-5 + actual |
| Como apresentar a recomendação? | Banner com poupança / Card detalhado / Tu decides | Banner com poupança |

## Scope Creep Registado

- **OCR de PDF da factura** — mencionado pelo utilizador como input preferido para custo real. Redirected para Deferred (INT-03 já em REQUIREMENTS.md Out of Scope v1).

## Auto-Resolved

Nenhum (modo interactivo sem --auto).
