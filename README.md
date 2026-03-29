---
title: Monitorização de Eletricidade e Comparação de Comercializadores
description: Projeto pessoal para acompanhar consumo elétrico, comparar tarifários e recomendar mudança de fornecedor com base no perfil real da casa
tags:
  - hobbies/casa
  - casa
  - energia
  - eletricidade
  - home-assistant
  - comercializadores
aliases:
  - Projeto Eletricidade
  - Comparador de Comercializadores
created: 2026-03-26
status: active
area: hobbies
---

# Monitorização de Eletricidade e Comparação de Comercializadores

Projeto pessoal para acompanhar o consumo de eletricidade da casa e recomendar quando compensa mudar de fornecedor.

> [!note] Decisão de scope
> O MVP nao vai guardar consumo ao minuto. Para comparar `tarifa simples` vs `bihorario` e avaliar comercializadores, basta trabalhar com agregados `mensais` por periodo tarifario, em especial `vazio` e `fora de vazio`.

## Objetivo

- Medir o perfil mensal de consumo por periodo tarifario
- Calcular o custo desse perfil em varios comercializadores
- Atualizar a comparacao quando os precos mudarem
- Gerar alertas quando mudar de fornecedor passar a compensar
- Expor o resultado no Home Assistant e, se fizer sentido, numa dashboard web

## Arquitetura recomendada

- `Fonte operacional`: Home Assistant + Shelly
- `Fonte oficial`: E-REDES
- `Motor de calculo`: regras tarifarias e simulacao mensal por comercializador
- `Camada de alertas`: limiar minimo de poupanca para evitar ruido
- `Interface`: dashboard simples para ranking, poupanca estimada e historico

Ver:
- [[3-hobbies/Casa/energia/monitorizacao-eletricidade/ARQUITETURA|Arquitetura]]
- [[3-hobbies/Casa/energia/monitorizacao-eletricidade/MVP|MVP]]
- [[3-hobbies/Casa/energia/monitorizacao-eletricidade/FONTES-DADOS|Fontes de Dados]]
- [[3-hobbies/Casa/energia/monitorizacao-eletricidade/RISCOS-MANUTENCAO|Riscos e Manutencao]]
- [[3-hobbies/Casa/energia/monitorizacao-eletricidade/ROADMAP|Roadmap]]
- [[3-hobbies/Casa/energia/monitorizacao-eletricidade/OPERACAO|Operação]]

## Stack escolhida

- `Python` para importacao, normalizacao e regras tarifarias
- `FastAPI` para API e tarefas agendadas simples
- `SQLite` ou `DuckDB` para guardar agregados mensais e simulacoes
- `HTMX + Jinja + Chart.js` para uma dashboard leve

## Ferramenta inicial pronta

Existe ja um comparador em linha de comando em:

- `src/backend/energy_compare.py`
- `src/backend/tiagofelicia_compare.py`

Entrada esperada:

- `CSV` com consumo mensal por `vazio` e `fora_vazio`
- `JSON` com catalogo de tarifarios
- `JSON` com o fornecedor atual

Saida:

- `top 3` comercializadores por custo anual estimado
- comparacao com o contrato atual
- recomendacao `mono-horario` vs `bihorario`
- resumo de sazonalidade com base no historico

## Motor principal do mercado

Existe tambem uma integracao com `tiagofelicia.pt` pensada para ser o motor principal de comparacao:

- [[3-hobbies/Casa/energia/monitorizacao-eletricidade/integracoes/tiago-felicia/README|Integração Tiago Felícia]]

## Sistema mensal

O projeto inclui agora um workflow mensal completo em:

- `src/backend/monthly_workflow.py`
- `src/backend/reminder_job.py`
- `src/backend/process_latest_download.py`
- `src/backend/eredes_download.py`
- `src/backend/eredes_bootstrap_session.py`
- `src/backend/install_launch_agent.py`

Config real:

- `config/system.json`

Objetivo:

- correr no dia `1` de cada mes
- lembrar o download do Excel da E-REDES
- atualizar o historico
- recalcular o melhor fornecedor
- guardar relatorio e estado

Exemplo de uso:

```bash
python3 energia/monitorizacao-eletricidade/src/backend/tiagofelicia_compare.py \
  --consumption energia/monitorizacao-eletricidade/data/processed/consumo_mensal.exemplo.csv \
  --power "6.90 kVA" \
  --current-supplier Goldenergy \
  --current-plan-contains "Indexado" \
  --months-limit 2
```

Exemplo de uso:

```bash
python3 energia/monitorizacao-eletricidade/src/backend/energy_compare.py \
  --consumption energia/monitorizacao-eletricidade/data/processed/consumo_mensal.exemplo.csv \
  --tariffs energia/monitorizacao-eletricidade/config/tarifarios.exemplo.json \
  --contract energia/monitorizacao-eletricidade/config/fornecedor_atual.exemplo.json \
  --alerts energia/monitorizacao-eletricidade/config/alertas.exemplo.json
```

## Estrutura

```text
monitorizacao-eletricidade/
├── README.md
├── ARQUITETURA.md
├── MVP.md
├── FONTES-DADOS.md
├── RISCOS-MANUTENCAO.md
├── ROADMAP.md
├── config/
├── data/
├── integracoes/
└── src/
```

## Principios do projeto

- Preferir dados oficiais para decisoes contratuais
- Guardar apenas o nivel de detalhe necessario para o caso de uso
- Evitar scraping fragil quando existir PDF, CSV ou simulador oficial
- Gerar recomendacoes conservadoras, nao mudancas automaticas

## Notas relacionadas

- [[3-hobbies/Casa/HA/ha-config-project/README|Projeto HomeAssistant]]
- [[3-hobbies/Casa/energia/dados-vento-arcozelo-2025|Dados do vento - Arcozelo 2025]]
- [[3-hobbies/Casa/README|Hub Casa]]
