# Phase 1: Unblock & Validate End-to-End — Research

**Researched:** 2026-03-28
**Domain:** macOS launchd TCC fix + Python dependency declaration + E-REDES session bootstrap + XLSX parser validation
**Confidence:** HIGH (all blockers confirmed from hard evidence in the codebase; no speculation)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIX-01 | Corrigir caminho Python no plist launchd (TCC permission error — watcher quebrado) | Erro confirmado em 21 entradas no log. Fix: substituir `python3` pelo path absoluto `/usr/local/opt/python@3.11/libexec/bin/python3` ou pelo path do sistema `/usr/local/bin/python3.11`. Plist instalado em `~/Library/LaunchAgents/` é idêntico ao ficheiro do projecto — ambos precisam de ser actualizados. Reload via `launchctl unload` + `launchctl load`. |
| FIX-02 | Corrigir `.gitignore` para excluir `state/eredes_storage_state.json` e outros ficheiros sensíveis | Confirmado: não existe `.gitignore`. Git status mostra `state/` como untracked. Ficheiro contém JWT + session cookies. Fix imediato antes de qualquer `git add`. |
| FIX-03 | Re-fazer bootstrap da sessão E-REDES (JWT expirado) | JWT `exp: 1774503078` = 2026-03-22. Expirado há 6 dias. `eredes_bootstrap_session.py` existe e está funcional. Requer intervenção manual do utilizador (login + Enter no terminal). Gera novos `state/eredes_storage_state.json` e `state/eredes_bootstrap_context.json`. |
| FIX-04 | Criar `requirements.txt` com todas as dependências do projecto | Confirmado: não existe `requirements.txt`. Packages instalados no Python do sistema (`/usr/local/opt/python@3.11`): `playwright==1.58.0`, `openpyxl==3.1.5`, `tf-playwright-stealth==1.2.0`, `requests==2.32.5`. Sem venv — tudo instalado globalmente. |
| VAL-01 | Correr pipeline completo com XLSX real (um local) e verificar relatório gerado | Relatório `data/reports/relatorio_eletricidade_2026-03-26.md` já existe — pipeline correu parcialmente a 2026-03-26 com um XLSX de `~/Downloads`. Confirmar que o pipeline corre limpo com os XLSXs em `data/raw/eredes/` via `--input-xlsx`. |
| VAL-02 | Validar parser XLSX contra os ficheiros E-REDES disponíveis (incluindo variação de formato entre anos) | 3 ficheiros disponíveis em `data/raw/eredes/`: 2025 (11 meses, formato data longa) + 2 de 2026 (formato timestamp curto). O parser usa heurística posicional (colunas 7, 6, 3, 2) — verificar output para cada ficheiro individualmente. |
</phase_requirements>

---

## Summary

Esta fase é estritamente de correcção e validação — zero código novo de funcionalidade. O pipeline backend está implementado e chegou a produzir um relatório a 2026-03-26, mas o trigger automático (launchd watcher) é 100% não-funcional por um erro de configuração comprovado.

Os dois bloqueadores têm causas-raiz distintas e independentes. O launchd chama `/Library/Developer/CommandLineTools/usr/bin/python3` — o interpretador das Command Line Tools da Apple — que não tem permissão TCC para aceder a ficheiros em `~/Documents`. O Python correcto está em `/usr/local/opt/python@3.11/libexec/bin/python3` (Homebrew). A sessão E-REDES expirou há 6 dias (JWT exp = 2026-03-22) e tem de ser renovada manualmente via `eredes_bootstrap_session.py`.

As tarefas de FIX são todas cirúrgicas: editar uma linha no plist, criar dois ficheiros (`.gitignore` e `requirements.txt`), correr um script interactivo. As tarefas de VAL correm o pipeline existente com dados reais e verificam o output. Nenhuma tarefa desta fase escreve nova lógica de negócio.

**Primary recommendation:** Fazer FIX-02 (`.gitignore`) PRIMEIRO, antes de qualquer operação git. Depois FIX-01 (plist), FIX-04 (requirements.txt), FIX-03 (bootstrap sessão), VAL-01 e VAL-02 em sequência.

---

## Standard Stack

### Core (já instalado, sem venv)

| Package | Versão instalada | Propósito | Nota |
|---------|-----------------|-----------|------|
| Python | 3.11.14 | Runtime | Homebrew em `/usr/local/opt/python@3.11/libexec/bin/python3` |
| playwright | 1.58.0 | Automação browser (bootstrap sessão + tiagofelicia) | `playwright install chromium` pode ser necessário |
| openpyxl | 3.1.5 | Parse de ficheiros XLSX da E-REDES | |
| tf-playwright-stealth | 1.2.0 | Stealth para Playwright (anti-detecção) | Instalado mas não usado activamente no bootstrap |
| requests | 2.32.5 | HTTP (usado em módulos auxiliares) | |

### Ambiente

**Não existe venv no projecto.** Os packages estão instalados no Python global do Homebrew (`/usr/local/lib/python3.11/site-packages`). O `requirements.txt` deve reflectir exactamente o que está instalado.

**Python correcto para o plist:**
```
/usr/local/opt/python@3.11/libexec/bin/python3
```

Este é o path que resolve como `which python3` quando o Homebrew Python está activo. Alternativa equivalente:
```
/usr/local/opt/python@3.11/bin/python3.11
```

### Conteúdo do requirements.txt a criar

```
playwright==1.58.0
openpyxl==3.1.5
tf-playwright-stealth==1.2.0
requests==2.32.5
```

`zoneinfo` e todos os outros módulos usados (`argparse`, `json`, `csv`, `pathlib`, `datetime`, `subprocess`, `collections`) são stdlib — não vão para o `requirements.txt`.

---

## Architecture Patterns

### Fix launchd TCC (FIX-01)

**O problema exacto:**

```
/Library/Developer/CommandLineTools/usr/bin/python3: can't open file '...': [Errno 1] Operation not permitted
```

O plist instalado em `~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist` é **idêntico** ao ficheiro do projecto em `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist`. Os dois têm de ser actualizados.

**Linha a alterar (linha 9 em ambos os ficheiros):**
```xml
<!-- ANTES (errado): -->
<string>python3</string>

<!-- DEPOIS (correcto): -->
<string>/usr/local/opt/python@3.11/libexec/bin/python3</string>
```

**Sequência de reload obrigatória:**
```bash
launchctl unload ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist
# Copiar plist actualizado para ~/Library/LaunchAgents/ ou editar in-place
launchctl load ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist
```

**TCC / Full Disk Access:** O erro `[Errno 1] Operation not permitted` confirma que o interpretador não tem acesso ao path do projecto (`~/Documents/AI/...`). Ao usar o Homebrew Python, a TCC deve resolver porque o utilizador (`ricmag`) já tem acesso ao próprio `~/Documents`. Se o erro persistir após o fix, será necessário conceder Full Disk Access ao binário Python em Definições > Privacidade e Segurança > Acesso Total ao Disco. Este passo não é automatizável — requer intervenção manual.

**Verificação após fix:**
```bash
# Colocar qualquer ficheiro em ~/Downloads e verificar log:
touch ~/Downloads/test_trigger.txt && sleep 2
tail -5 /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade/state/launchd.process.stderr.log
# Não deve aparecer "[Errno 1] Operation not permitted"
```

### Fix .gitignore (FIX-02)

**Conteúdo mínimo do `.gitignore` a criar na raiz do projecto:**

```gitignore
# Sessões e credenciais
state/eredes_storage_state.json
state/eredes_bootstrap_context.json

# Dados brutos com CPE exposto
data/raw/

# Dados processados (gerados pelo pipeline)
data/processed/

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/

# Ficheiros temporários do pipeline
config/_runtime_partial_override.json

# Logs de estado (opcionalmente excluir)
# state/  (manter os outros ficheiros de estado no git? ver nota abaixo)
```

**Nota:** `state/monthly_status.json` e `state/last_processed_download.json` são ficheiros de estado gerados pelo pipeline, não contêm credenciais. Podem ser excluídos também com `state/` completo. Recomendado: excluir `state/` inteiro e manter apenas os logs necessários.

**Verificação após criar:**
```bash
git status
# state/eredes_storage_state.json NÃO deve aparecer como untracked
```

### Bootstrap de Sessão E-REDES (FIX-03)

`eredes_bootstrap_session.py` está implementado e funcional. O fluxo é:

1. Abre Chromium via Playwright (non-headless)
2. Navega para `https://balcaodigital.e-redes.pt/home`
3. Utilizador faz login manualmente no browser
4. Utilizador navega até à página de consumos
5. Utilizador pressiona Enter no terminal
6. Script grava `state/eredes_storage_state.json` + `state/eredes_bootstrap_context.json`
7. Browser fecha

**Comando:**
```bash
cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade
/usr/local/opt/python@3.11/libexec/bin/python3 src/backend/eredes_bootstrap_session.py \
  --storage-state state/eredes_storage_state.json \
  --context-output state/eredes_bootstrap_context.json
```

**Atenção:** A sessão expira em ~90 minutos. O bootstrap deve ser feito imediatamente antes do teste end-to-end (VAL-01). Não fazer bootstrap um dia antes e testar no dia seguinte.

### Validação End-to-End (VAL-01, VAL-02)

**Pipeline corre em modo manual com `--input-xlsx`** — não requer o watcher launchd nem o download E-REDES. O relatório de 2026-03-26 foi produzido exactamente assim.

**Sequência de teste VAL-01:**
```bash
cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade

# Teste com XLSX de 2026 (o mais recente disponível):
/usr/local/opt/python@3.11/libexec/bin/python3 src/backend/monthly_workflow.py \
  --config config/system.json \
  --input-xlsx data/raw/eredes/Consumos_PT0002000084968079SX_20260326043825.xlsx \
  --allow-partial-last-month

# Verificar relatório gerado:
ls data/reports/
cat data/reports/relatorio_eletricidade_$(date +%Y-%m-%d).md
```

**Sequência de teste VAL-02 (parser XLSX contra todos os ficheiros):**
```bash
# Ficheiro 2025 (11 meses, formato data longa):
/usr/local/opt/python@3.11/libexec/bin/python3 src/backend/eredes_to_monthly_csv.py \
  --input data/raw/eredes/Consumos_PT0002000084968079SX_2025-01-01_2025-11-26_20251126115627.xlsx \
  --output /tmp/test_parse_2025.csv
cat /tmp/test_parse_2025.csv

# Ficheiro 2026 v1:
/usr/local/opt/python@3.11/libexec/bin/python3 src/backend/eredes_to_monthly_csv.py \
  --input data/raw/eredes/Consumos_PT0002000084968079SX_20260326042940.xlsx \
  --output /tmp/test_parse_2026v1.csv \
  --drop-partial-last-month
cat /tmp/test_parse_2026v1.csv

# Ficheiro 2026 v2:
/usr/local/opt/python@3.11/libexec/bin/python3 src/backend/eredes_to_monthly_csv.py \
  --input data/raw/eredes/Consumos_PT0002000084968079SX_20260326043825.xlsx \
  --output /tmp/test_parse_2026v2.csv \
  --drop-partial-last-month
cat /tmp/test_parse_2026v2.csv
```

**Critério de validação do parser:** Cada CSV deve ter colunas `year_month,total_kwh,vazio_kwh,fora_vazio_kwh`. O `total_kwh` de cada mês deve estar entre 30 e 1000 kWh para uso residencial. Valores fora deste intervalo indicam heurística de coluna errada.

### Verificação do watcher launchd após fix (VAL-01 — sucesso criteria 1)

O critério exige que o watcher detecte um XLSX em `~/Downloads` e o pipeline corra sem TCC errors. Após corrigir o plist:

```bash
# Simular trigger do watcher copiando um XLSX real:
cp data/raw/eredes/Consumos_PT0002000084968079SX_20260326043825.xlsx ~/Downloads/
sleep 5
tail -20 state/launchd.process.stderr.log
tail -20 state/launchd.process.stdout.log
# O stdout deve mostrar o JSON de resultado; o stderr não deve ter "[Errno 1]"
```

---

## Don't Hand-Roll

| Problema | Não construir | Usar em vez | Porquê |
|----------|--------------|-------------|--------|
| Bootstrap sessão E-REDES | Novo script de login | `eredes_bootstrap_session.py` existente | Já implementado e testado |
| Geração do plist launchd | Edição manual ad-hoc | `install_process_watch_agent.py --python-bin <path>` | Script já existe e aceita `--python-bin` como argumento — gera o plist correcto |
| Parsing de JWT para verificar expiração | Decoder manual de JWT | `import json, base64` + decode da payload | JWT é base64url — stdlib chega, sem dependência `PyJWT` |
| Validação de kWh bounds | Nada — adicionar inline | Adicionar assert após `convert_xlsx_to_monthly_csv` | Não é uma biblioteca, é uma guarda de 3 linhas |

---

## Runtime State Inventory

| Categoria | Itens encontrados | Acção necessária |
|-----------|------------------|------------------|
| Stored data | `state/eredes_storage_state.json` — JWT expirado (exp=2026-03-22). `state/last_processed_download.json` — aponta para XLSX em `~/Downloads` (já processado). `state/monthly_status.json` — estado do último run. `data/processed/consumo_mensal_atual.csv` — CSV de 1 mês (fevereiro 2026, 721 kWh). | Re-bootstrap da sessão (FIX-03). Outros ficheiros são válidos e não precisam de intervenção. |
| Live service config | launchd agent `com.ricmag.monitorizacao-eletricidade.process-latest` — carregado (`launchctl list` confirma) com plist errado. `com.ricmag.monitorizacao-eletricidade` (reminder) — carregado, usa `python3` bare (mesmo bug, menor impacto pois é calendar-based e o utilizador vê a notificação falhar). | Unload + fix plist + reload para o watcher. O reminder plist também usa `python3` bare — corrigir em simultâneo. |
| OS-registered state | Dois plists em `~/Library/LaunchAgents/`: `com.ricmag.monitorizacao-eletricidade.process-latest.plist` e `com.ricmag.monitorizacao-eletricidade.plist`. Ambos são idênticos aos ficheiros em `launchd/` do projecto. | Editar em `launchd/` do projecto E actualizar `~/Library/LaunchAgents/` (copiar ou editar in-place). Reload obrigatório via launchctl. |
| Secrets/env vars | `state/eredes_storage_state.json` — contém JWT `aat`, cookies `PHPSESSID`, `SimpleSAML`. Não está em nenhuma variável de ambiente — ficheiro em disco. Sem `.gitignore` actualmente. | Criar `.gitignore` antes de qualquer operação git (FIX-02 PRIMEIRO). |
| Build artifacts | `src/backend/__pycache__/` — 11 ficheiros `.pyc` não excluídos do git (não existe `.gitignore`). Nenhum venv instalado no projecto. Sem `requirements.txt`. | Adicionar `__pycache__/` e `*.pyc` ao `.gitignore`. Criar `requirements.txt` (FIX-04). |

---

## Common Pitfalls

### Pitfall 1: Editar o plist do projecto mas esquecer o plist instalado em ~/Library/LaunchAgents/

**O que falha:** O ficheiro corrigido fica em `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` mas o launchd continua a usar a cópia antiga em `~/Library/LaunchAgents/`. O erro persiste porque o launchd não lê o ficheiro do projecto — lê o que está instalado.

**Confirmado:** Os dois ficheiros são actualmente idênticos. Qualquer edição tem de propagar para os dois locais.

**Como evitar:** Editar o ficheiro do projecto e depois copiar para `~/Library/LaunchAgents/`. Ou editar directamente `~/Library/LaunchAgents/` e depois copiar para o projecto para manter sincronismo. Seguido sempre de `launchctl unload` + `launchctl load`.

**Sinal de alerta:** Após o fix, colocar um ficheiro em `~/Downloads` e verificar se o erro desaparece do log.

---

### Pitfall 2: Bootstrap da sessão sem navegação até à página de consumos

**O que falha:** `eredes_bootstrap_session.py` guarda o `storage_state` e o `context_info.current_url` no momento em que o utilizador pressiona Enter. Se o utilizador fizer login mas não navegar até `balcaodigital.e-redes.pt/consumptions/history`, o `storage_state` pode não incluir os cookies específicos da sessão de consumos.

**Como evitar:** Instruir o utilizador explicitamente: (1) fazer login, (2) navegar até à página de histórico de consumos, (3) confirmar que a tabela carregou, (4) só então pressionar Enter no terminal.

---

### Pitfall 3: Testar o pipeline com o XLSX mais antigo (2025) sem --allow-partial-last-month

**O que falha:** O ficheiro de 2025 tem dados de Janeiro a Novembro. Novembro pode ser o último mês e estar completo (26 de Novembro = último dia do mês? Não — Novembro tem 30 dias, logo novembro está incompleto). Com `drop_partial_last_month=True` (default), o mês de novembro é descartado e o CSV fica com 10 meses. Sem a flag `--allow-partial-last-month`, o workflow vai tentar correr com dados incompletos.

**Como evitar:** Usar `--allow-partial-last-month` para testes de validação. Para produção (ficheiro com o mês completo mais recente), não é necessária a flag.

---

### Pitfall 4: Relatório gerado mas com apenas 1 mês de histórico (análise incompleta)

**O que falha:** O relatório de 2026-03-26 mostra "Meses analisados: 1" e "Inverno médio: None kWh". Isto acontece porque o workflow usou apenas o XLSX mais recente com dados de Fevereiro 2026 (1 mês). Para uma análise completa, usar o XLSX de 2025 (11 meses) ou o de 2026 com todos os dados disponíveis.

**Como evitar:** Para VAL-01, usar o XLSX de 2025 com `--allow-partial-last-month` para obter o máximo de histórico. Verificar que o relatório mostra > 1 mês analisado.

---

### Pitfall 5: `eredes_to_monthly_csv.py` tem bug de tipo em `pick_sheet`

**O que é:** `pick_sheet` declara o retorno como `Any` mas não importa `Any` de `typing`. O Python 3.11 ignora anotações em runtime, por isso não causa crash. Mas o `mypy` ou qualquer type-checker vai falhar neste ficheiro.

**Impacto na fase:** Nenhum impacto em execução. Não bloqueia VAL-02. Registar como tech debt a resolver em fase futura.

---

### Pitfall 6: TCC Full Disk Access pode ser necessário mesmo após fix do path Python

**O que pode acontecer:** Mesmo usando o Homebrew Python, se este não tiver permissão TCC para `~/Documents`, o erro `[Errno 1]` persiste. A TCC no macOS controla acesso por binário, não por utilizador.

**Como verificar:** Se após o fix do plist o erro persistir, ir a Definições do Sistema > Privacidade e Segurança > Acesso Total ao Disco e adicionar `/usr/local/opt/python@3.11/libexec/bin/python3`. Este passo é manual e não é automatizável via script.

**Nota:** O pipeline já correu com sucesso a 2026-03-26 usando o mesmo Python mas em modo manual (terminal). O TCC afecta processos lançados pelo launchd de forma diferente de processos lançados pelo utilizador no terminal.

---

## Code Examples

### Gerar plist correcto com o script existente

```bash
# Source: src/backend/install_process_watch_agent.py (já existe no projecto)
/usr/local/opt/python@3.11/libexec/bin/python3 src/backend/install_process_watch_agent.py \
  --config /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade/config/system.json \
  --output launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist \
  --python-bin /usr/local/opt/python@3.11/libexec/bin/python3
```

### Verificar JWT expirado antes do bootstrap

```python
# Source: análise directa de state/eredes_storage_state.json
import json, base64
from datetime import datetime

state = json.loads(open("state/eredes_storage_state.json").read())
for origin in state.get("origins", []):
    for item in origin.get("localStorage", []):
        if item.get("name") == "aat":
            token = item["value"]
            payload = token.split(".")[1]
            # Base64url padding
            payload += "=" * (4 - len(payload) % 4)
            claims = json.loads(base64.b64decode(payload))
            exp = claims.get("exp", 0)
            print(f"JWT exp: {exp} = {datetime.fromtimestamp(exp).isoformat()}")
            print(f"Expirado: {datetime.now().timestamp() > exp}")
```

### Sequência launchctl reload

```bash
# Unload (não falha se não estiver carregado)
launchctl unload ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist 2>/dev/null

# Copiar plist actualizado
cp launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist \
   ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist

# Load
launchctl load ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist

# Verificar que está a correr
launchctl list | grep monitorizacao-eletricidade
```

### Teste de aceitação do watcher (trigger manual)

```bash
# Copiar XLSX para ~/Downloads para simular download do utilizador
cp data/raw/eredes/Consumos_PT0002000084968079SX_20260326043825.xlsx ~/Downloads/

# Aguardar 5 segundos para launchd detectar
sleep 5

# Verificar log (não deve haver [Errno 1])
tail -10 state/launchd.process.stderr.log
tail -10 state/launchd.process.stdout.log
```

---

## State of the Art

| Abordagem antiga | Abordagem correcta | Relevância para esta fase |
|------------------|--------------------|--------------------------|
| `python3` bare no plist | Path absoluto do interpretador correcto | Núcleo de FIX-01 |
| Sem `.gitignore` | `.gitignore` com `state/`, `data/raw/`, `__pycache__/` | Núcleo de FIX-02 |
| Sem `requirements.txt` | `requirements.txt` com versões fixas dos 4 packages | Núcleo de FIX-04 |
| Session JWT expirado | Re-bootstrap imediatamente antes do teste | Núcleo de FIX-03 |

---

## Open Questions

1. **Full Disk Access para o Homebrew Python**
   - O que sabemos: o erro TCC desaparece ao usar o interpretador correcto em processos do utilizador; o launchd agent corre como o utilizador (`ricmag`) mas o TCC pode tratar os dois casos de forma diferente
   - O que não está claro: se o Homebrew Python (`/usr/local/opt/python@3.11/...`) tem automaticamente FDA ou se requer concessão manual
   - Recomendação: executar o fix e testar com um trigger de ~/Downloads; se o erro persistir, conceder FDA manualmente — documentar o passo no plano como "pode ser necessário"

2. **Formato dos XLSXs de 2026 vs 2025**
   - O que sabemos: os nomes de ficheiro já mudaram (formato timestamp curto vs longo); o parser usa heurística posicional para as colunas
   - O que não está claro: se as colunas internas mudaram entre os ficheiros de 2025 e 2026
   - Recomendação: VAL-02 responde a esta questão — correr o parser nos 3 ficheiros e comparar os valores de kWh com o relatório já existente (721 kWh para Fevereiro 2026 é o valor de referência)

3. **`reminder_job.py` plist também usa `python3` bare**
   - O que sabemos: `com.ricmag.monitorizacao-eletricidade.plist` (reminder, day 1 às 9h) usa `python3` bare — mesmo bug que o watcher
   - O que não está claro: se este bug já causou falhas silenciosas (não há log de erro para o reminder, apenas `state/launchd.stderr.log`)
   - Recomendação: corrigir os dois plists em simultâneo no mesmo task (FIX-01 inclui os dois)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Nenhum instalado (sem pytest, sem unittest runner configurado) |
| Config file | Nenhum — Wave 0 cria `tests/` se necessário |
| Quick run command | `python3 -c "..."` ou scripts directo |
| Full suite command | N/A para esta fase |

**Nota:** Esta fase não cria testes unitários formais — é de correcção e validação manual. Os "testes" são os próprios comandos de validação documentados acima (VAL-01, VAL-02). A criação de infra de testes (pytest) é tech debt para fases posteriores (QUAL-01 está em v2).

### Phase Requirements → Test Map

| Req ID | Comportamento | Tipo | Comando | Ficheiro |
|--------|--------------|------|---------|---------|
| FIX-01 | launchd não produz `[Errno 1]` após trigger em ~/Downloads | manual smoke | `tail -5 state/launchd.process.stderr.log` após `touch ~/Downloads/x` | N/A |
| FIX-02 | `state/eredes_storage_state.json` não aparece em `git status` | manual check | `git status \| grep eredes_storage` | N/A |
| FIX-03 | `state/eredes_storage_state.json` tem JWT com exp > now() | manual check | script de verificação JWT acima | N/A |
| FIX-04 | `pip install -r requirements.txt` corre sem erros | smoke | `pip install --dry-run -r requirements.txt` | `requirements.txt` ❌ Wave 0 |
| VAL-01 | Pipeline produz `data/reports/relatorio_eletricidade_YYYY-MM-DD.md` | integration | `python3 src/backend/monthly_workflow.py --config ... --input-xlsx ...` | N/A |
| VAL-02 | Parser XLSX produz CSV com kWh entre 30-1000 para os 3 ficheiros | integration | `python3 src/backend/eredes_to_monthly_csv.py --input <xlsx> --output /tmp/x.csv && cat /tmp/x.csv` | N/A |

### Wave 0 Gaps

- [ ] `requirements.txt` — cobre FIX-04 (ficheiro a criar, não infra de teste)

*(Sem infra de teste formal nesta fase — todos os critérios são verificáveis por inspeção directa de outputs)*

---

## Sources

### Primary (HIGH confidence)

- `state/launchd.process.stderr.log` — 21 erros TCC confirmados, path do interpretador errado identificado
- `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` — linha 9 com `python3` bare
- `~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade.process-latest.plist` — idêntico ao ficheiro do projecto (diff confirmado)
- `state/eredes_storage_state.json` — JWT exp = 1774503078 (2026-03-22), expirado
- `launchctl list | grep ricmag` — ambos os agents carregados e activos
- `which python3` → `/usr/local/opt/python@3.11/libexec/bin/python3` — Python correcto identificado
- `pip3 show playwright openpyxl` — versões instaladas confirmadas
- `data/reports/relatorio_eletricidade_2026-03-26.md` — pipeline já correu com sucesso em modo manual
- `.planning/codebase/CONCERNS.md` — auditoria 2026-03-28
- `.planning/research/PITFALLS.md` — análise de domínio 2026-03-28
- `.planning/research/SUMMARY.md` — resumo de investigação prévia

### Secondary (MEDIUM confidence)

- Comportamento TCC do macOS para processos launchd vs processos do utilizador — documentação Apple Platform Security (training knowledge, consistente com evidência do log)
- Expiração de sessão E-REDES (~90 min) — inferido do timestamp JWT e comportamento descrito no PITFALLS.md

### Tertiary (LOW confidence)

- Nenhum item de LOW confidence nesta fase — todos os factos críticos têm evidência directa no codebase

---

## Metadata

**Confidence breakdown:**
- FIX-01 (launchd TCC): HIGH — evidência directa no log + plist inspeccionado + Python correcto identificado
- FIX-02 (.gitignore): HIGH — confirmado via `git status` e ausência de ficheiro
- FIX-03 (bootstrap): HIGH — JWT exp lido directamente do state file
- FIX-04 (requirements.txt): HIGH — packages verificados com `pip3 show`
- VAL-01/VAL-02 (validação): HIGH — relatório já existe de run anterior; parser a testar contra ficheiros reais disponíveis

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable — não depende de APIs externas nem de versões em rápida evolução)
