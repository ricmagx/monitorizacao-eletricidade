---
title: Operação - Sistema Mensal de Eletricidade
tags:
  - hobbies/casa
  - energia
  - eletricidade
  - operacao
created: 2026-03-26
status: active
area: hobbies
---

# Operação

## Objetivo

Executar o sistema automaticamente no dia `1` de cada mes para:

- descarregar o Excel da E-REDES
- converter para agregados mensais
- correr a comparacao no `tiagofelicia.pt`
- guardar historico e relatorio

## Fluxo operacional

### 1. Bootstrap de sessao E-REDES

Executar manualmente:

```bash
zsh energia/monitorizacao-eletricidade/scripts/bootstrap_eredes_session.sh
```

O browser abre em modo visivel.

- fazer login no Balcao Digital
- navegar ate a pagina de onde costuma descarregar o Excel
- voltar ao terminal e carregar `Enter`

Isso guarda:

- `state/eredes_storage_state.json`
- `state/eredes_bootstrap_context.json`

## 2. Configuracao do download

Editar [system.json](/Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade/config/system.json):

- `eredes.download_url`
- `eredes.download_mode`
- `eredes.navigation_click_texts` se forem precisos cliques adicionais
- `eredes.download_button_candidates`

Modo recomendado:

- `external_firefox`

Neste modo, no dia `1`, o sistema abre a E-REDES no `Firefox`. Faz o download manual do Excel nesse browser e o sistema observa `Downloads` para importar o ficheiro assim que ele aparecer.

O download da E-REDES e observado em:

- `/Users/ricmag/Downloads`

Quando aparecer um novo `.xlsx`, o sistema copia-o para o historico do projeto e prossegue.

## 3. Teste manual do workflow

```bash
python3 energia/monitorizacao-eletricidade/src/backend/monthly_workflow.py \
  --config energia/monitorizacao-eletricidade/config/system.json \
  --input-xlsx /Users/ricmag/Downloads/Consumos_PT0002000084968079SX_2025-01-01_2025-11-26_20251126115627.xlsx
```

## 3A. Processar o ultimo download

Depois de descarregar manualmente o Excel no `Firefox`, usar:

```bash
zsh energia/monitorizacao-eletricidade/scripts/process_latest_download.sh
```

Isto apanha o `.xlsx` mais recente em `Downloads` e corre a analise completa.

## 4. Agendamento

O sistema foi desenhado para `launchd` no macOS.

- dia: `1`
- hora: `09:00`

No modo atual, o `launchd` faz apenas o lembrete:

- mostra uma notificação macOS
- abre a E-REDES no `Firefox`
- deixa o estado como `waiting_for_download`

Existe tambem um segundo `launchd` opcional para processamento automatico:

- observa `Downloads`
- quando aparece um novo `Consumos_*.xlsx`
- corre o processador do ultimo download automaticamente

Se esse segundo agente estiver ativo, depois do download manual normalmente nao precisa correr `process_latest_download.sh`.

O plist pode ser gerado com:

```bash
python3 energia/monitorizacao-eletricidade/src/backend/install_launch_agent.py \
  --config energia/monitorizacao-eletricidade/config/system.json \
  --output energia/monitorizacao-eletricidade/launchd/com.ricmag.monitorizacao-eletricidade.plist
```

## 5. Ficheiros de saida

- `data/raw/eredes/` para os XLSX descarregados
- `data/processed/consumo_mensal_atual.csv`
- `data/processed/analise_tiagofelicia_atual.json`
- `data/reports/` para relatorios Markdown
- `state/monthly_status.json`

## Limites atuais

- a sessao da E-REDES pode expirar
- o HTML do Balcao Digital pode mudar
- o fluxo de download automatico so fica totalmente fiavel depois de validarmos a pagina real autenticada
