---
title: Fontes de Dados - Monitorização de Eletricidade
tags:
  - hobbies/casa
  - energia
  - eletricidade
  - dados
created: 2026-03-26
status: active
area: hobbies
---

# Fontes de Dados

## Ordem de confianca

### 1. E-REDES

Uso:
- referencia oficial para consumo e periodos
- ideal para alimentar a comparacao mensal

Papel no projeto:
- fonte primaria para decisao contratual

### 2. Sites e PDFs dos comercializadores

Uso:
- energia por periodo
- potencia contratada
- condicoes comerciais
- datas de vigencia

Papel no projeto:
- fonte primaria para precos

### 3. ERSE

Uso:
- validacao cruzada de precos e estrutura de simulacao

Papel no projeto:
- fonte secundaria de controlo

### 4. Home Assistant + Shelly

Uso:
- observabilidade corrente
- detecao de tendencias intra-mes
- exposicao de sensores e alertas

Papel no projeto:
- fonte operacional complementar

### 5. tiagofelicia.pt

Uso:
- referencia funcional
- benchmark para verificar se o calculo faz sentido

Papel no projeto:
- nao deve ser a unica fonte de decisao

## Politica recomendada

- Preferir importacao manual ou semi-manual de precos no MVP
- Guardar sempre a `fonte` e a `data de recolha`
- So usar scraping se nao existir alternativa mais estavel
- Assumir que a autenticacao na E-REDES e pessoal, logo a recolha automatica direta depende de credenciais do utilizador ou de um export fornecido manualmente

## Campos minimos a recolher

- nome do comercializador
- nome do tarifario
- tipo de tarifa
- precos por periodo
- custos fixos
- descontos
- fonte
- data de recolha
- validade
