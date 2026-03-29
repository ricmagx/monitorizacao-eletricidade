---
title: Integração Tiago Felícia - Monitorização de Eletricidade
tags:
  - hobbies/casa
  - energia
  - eletricidade
  - tiago-felicia
created: 2026-03-26
status: active
area: hobbies
---

# Integração Tiago Felícia

Esta integração usa o simulador do `tiagofelicia.pt` como motor principal para:

- obter o `top 3` de comercializadores
- comparar com o fornecedor atual
- avaliar `simples` vs `bihorario`

## Estado atual

- `Simulação Completa`: validada via browser automation
- extração da tabela: validada
- `Análise Avançada (E-REDES)`: ainda por adaptar ao formato real do ficheiro exportado

## Script

- `src/backend/tiagofelicia_compare.py`

## Limitação atual

Sem o ficheiro real da E-REDES, a integração usa os agregados mensais para preencher o simulador em modo `Simulação Completa`. Isso já permite automatizar:

- ranking de fornecedores
- comparação de opção horária
- histórico mensal e sazonalidade

## Nota sobre o contrato atual

Para comparar com o seu contrato atual sem ambiguidades, o ideal é fornecer:

- nome do fornecedor
- parte do nome do plano atual

Se indicar apenas o fornecedor, o script escolhe o resultado mais barato desse fornecedor dentro da tabela simulada, o que pode nao coincidir exatamente com o contrato contratado.
