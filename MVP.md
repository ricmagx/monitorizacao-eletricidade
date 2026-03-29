---
title: MVP - Monitorização de Eletricidade
tags:
  - hobbies/casa
  - energia
  - eletricidade
  - mvp
created: 2026-03-26
status: active
area: hobbies
---

# MVP

## Objetivo do MVP

Responder a uma pergunta simples:

> Com o meu perfil mensal real, qual seria hoje o comercializador mais barato e quando compensa mudar?

## O que entra no MVP

- Importacao manual mensal de consumo oficial
- Estrutura para guardar `vazio` e `fora de vazio`
- Cadastro inicial de comercializadores prioritarios
- Simulacao mensal e anual
- Ranking de fornecedores
- Regra de alerta simples

## O que fica fora do MVP

- Captura ao minuto
- Automatizacao completa de scraping
- Mudanca automatica de fornecedor
- Otimizacao por aparelho individual
- Integracao complexa com faturacao

## Entregaveis

### Fase 1

- modelo de dados mensal
- catalogo tarifario base
- calculadora de custo

### Fase 2

- importador E-REDES
- dashboard simples
- comparacao contrato atual vs alternativas

### Fase 3

- integracao Home Assistant
- sensor com melhor fornecedor atual
- alerta de poupanca potencial

## Criterios de sucesso

- conseguir comparar pelo menos `3 a 5` comercializadores
- obter custo mensal estimado para o contrato atual
- produzir uma recomendacao clara e verificavel
- atualizar facilmente os precos sem retrabalho grande
