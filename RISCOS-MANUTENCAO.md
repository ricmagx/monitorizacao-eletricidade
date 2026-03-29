---
title: Riscos e Manutenção - Monitorização de Eletricidade
tags:
  - hobbies/casa
  - energia
  - eletricidade
  - riscos
created: 2026-03-26
status: active
area: hobbies
---

# Riscos e Manutencao

## Riscos principais

### 1. Tarifarios mal interpretados

Muitos tarifarios incluem:

- descontos por debito direto
- desconto por fatura eletrónica
- campanhas temporarias
- componentes indexadas
- custos fixos pouco visiveis

Mitigacao:
- guardar a fonte original
- confirmar condicoes antes de recomendar mudanca

### 2. Scraping fragil

Os sites podem mudar HTML, nomes de classes ou estrutura.

Mitigacao:
- preferir PDFs, CSVs e simuladores oficiais
- isolar scraping em conectores separados
- aceitar atualizacao manual no MVP

### 3. Comparacao enganadora por dados incompletos

Se faltar um periodo ou um custo fixo, o ranking pode ficar errado.

Mitigacao:
- validar dados minimos obrigatorios
- marcar recomendacoes como `parciais` quando houver lacunas

### 4. Excesso de automacao cedo demais

Automatizar logo a recolha de todos os comercializadores aumenta muito a manutencao.

Mitigacao:
- comecar com poucos operadores
- crescer apenas depois de estabilizar o modelo de calculo

## Politica de recomendacao

Uma recomendacao deve incluir:

- fornecedor atual
- melhor alternativa encontrada
- poupanca mensal estimada
- poupanca anual estimada
- data de atualizacao dos precos
- nota de confianca
