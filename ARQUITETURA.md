---
title: Arquitetura - Monitorização de Eletricidade
tags:
  - hobbies/casa
  - energia
  - eletricidade
  - arquitetura
created: 2026-03-26
status: active
area: hobbies
---

# Arquitetura

## Decisao central

Para o objetivo deste projeto, o sistema deve comparar contratos com base em `totais mensais por periodo tarifario`, nao em series de alta frequencia.

## Fluxo de dados

```text
Home Assistant / Shelly -----------\
                                    -> normalizacao -> agregados mensais -> simulacao de custos -> alertas -> dashboard
E-REDES (dados oficiais) ----------/

Tarifarios comercializadores ------> catalogo tarifario versionado ------/
```

## Componentes

### 1. Ingestao de consumo

- `Home Assistant`: usado para observabilidade corrente e controlo operacional
- `E-REDES`: usado como referencia oficial para reconciliar consumo mensal e periodos tarifarios

Regra pratica:
- O MVP deve conseguir funcionar apenas com uma importacao mensal da E-REDES
- O Home Assistant entra como complemento, nao como dependencia dura

### 2. Normalizacao

Saida esperada por mes:

```text
ano_mes
energia_total_kwh
energia_vazio_kwh
energia_fora_vazio_kwh
energia_cheias_kwh   # opcional
energia_ponta_kwh    # opcional
fonte
```

### 3. Catalogo tarifario

Cada comercializador deve ser modelado com:

- nome
- tipo de tarifa
- preco energia por periodo
- potencia contratada
- custos fixos
- descontos condicionais
- data de inicio e fim de validade
- fonte e data de recolha

### 4. Motor de simulacao

Entrada:
- agregados mensais por periodo
- catalogo de tarifarios

Saida:
- custo mensal por comercializador
- diferenca face ao contrato atual
- poupanca anual estimada
- ranking

### 5. Alertas

Um alerta so deve disparar quando:

- existir poupanca recorrente acima de um limiar
- a comparacao usar dados tarifarios atuais
- a mudanca nao depender de uma condicao comercial mal confirmada

## Porque esta arquitetura

- reduz complexidade
- evita armazenar detalhe desnecessario
- aproxima-se mais da decisao contratual real
- baixa o custo de manutencao
