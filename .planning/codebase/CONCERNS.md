# Codebase Concerns

**Analysis Date:** 2026-03-28

## Tech Debt

**Dependência exclusiva de scraping de site externo (tiagofelicia.pt):**
- Issue: Todo o motor de comparação de tarifários depende de um simulador web de terceiro sem API pública. O scraping usa seletores de texto (`button:has-text("📝 Simulação Completa")`), IDs de campos (`#potencia`, `#ciclo`, `#kwh_S`, `#kwh_V`, `#kwh_F`) e estrutura de tabela HTML — qualquer redesign do site quebra o pipeline.
- Files: `src/backend/tiagofelicia_compare.py` (linhas 57–86)
- Impact: O workflow mensal falha silenciosamente ou retorna dados errados se o site mudar. Não há fallback.
- Fix approach: Adicionar validação explícita dos resultados extraídos (ex: verificar se `total_eur > 0` e se `supplier` não está vazio). Considerar cache do resultado mais recente como fallback.

**Duplicação do padrão `load_config / project_root_from_config / resolve_path`:**
- Issue: As funções `load_config`, `project_root_from_config` e `resolve_path` estão copiadas identicamente em `monthly_workflow.py`, `process_latest_download.py`, `reminder_job.py` e `eredes_download.py`.
- Files: `src/backend/monthly_workflow.py`, `src/backend/process_latest_download.py`, `src/backend/reminder_job.py`, `src/backend/eredes_download.py`
- Impact: Qualquer alteração à lógica de resolução de caminhos tem de ser replicada manualmente em 4 ficheiros.
- Fix approach: Extrair para um módulo `src/backend/config_utils.py` e importar em todos os ficheiros.

**Duplicação de `notify_mac`:**
- Issue: A função `notify_mac` está copiada em `monthly_workflow.py`, `eredes_download.py` e `reminder_job.py`.
- Files: `src/backend/monthly_workflow.py` (linha 102), `src/backend/eredes_download.py` (linha 46), `src/backend/reminder_job.py` (linha 23)
- Impact: Mudança de comportamento (ex: adicionar logging) exige edição em 3 lugares.
- Fix approach: Mover para o mesmo módulo `config_utils.py` ou `utils.py`.

**Ficheiros `__pycache__` comprometidos no repositório:**
- Issue: O diretório `src/backend/__pycache__/` com bytecode compilado (`.pyc`) está presente no repositório — não existe `.gitignore` no projeto.
- Files: `src/backend/__pycache__/` (11 ficheiros `.pyc`)
- Impact: Commits desnecessários, potencial inconsistência entre bytecode e fonte, risco de expor informação de ambiente.
- Fix approach: Criar `.gitignore` com `__pycache__/`, `*.pyc`, `state/`, `data/raw/`, `data/processed/`.

**Ausência de `requirements.txt` ou `pyproject.toml`:**
- Issue: As dependências Python (`playwright`, `openpyxl`) não estão declaradas em nenhum ficheiro de gestão de dependências.
- Files: (ficheiro inexistente)
- Impact: Instalar o projeto noutro sistema requer inspeção manual do código para identificar dependências.
- Fix approach: Criar `requirements.txt` com `playwright`, `openpyxl`, e versões fixas.

## Known Bugs

**`pick_sheet` usa `Any` sem import:**
- Symptoms: `eredes_to_monthly_csv.py` define `pick_sheet` com retorno de tipo `Any` mas não importa `Any` de `typing`.
- Files: `src/backend/eredes_to_monthly_csv.py` (linha 34)
- Trigger: Qualquer ferramenta de type-checking (mypy, pyright) falha neste ficheiro.
- Workaround: Não impede execução em Python (anotação ignorada em runtime), mas impede type-checking correto.

**`launchd` do watcher usa o `python3` do sistema (CLI tools) — sem permissão:**
- Symptoms: `state/launchd.process.stderr.log` mostra 21 erros `[Errno 1] Operation not permitted` consecutivos — o launchd usa `/Library/Developer/CommandLineTools/usr/bin/python3` sem acesso ao ficheiro Python do projeto.
- Files: `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` (linha 9), `state/launchd.process.stderr.log`
- Trigger: Cada mudança em `/Users/ricmag/Downloads` (qualquer ficheiro) aciona o launchd, que falha sistematicamente.
- Workaround: O workflow funciona quando executado manualmente com o Python correto. O launchd watcher está efetivamente inoperacional.

**Tracker de deduplicação baseado em `mtime` + `size`:**
- Symptoms: `process_latest_download.py` usa a assinatura `{path, mtime, size}` para detetar se um ficheiro já foi processado. Um novo download com o mesmo tamanho e timestamp coincidente seria ignorado (improvável mas possível). Mais crítico: o tracker guarda o caminho absoluto em `~/Downloads`, que aponta para o ficheiro original fora do projeto.
- Files: `src/backend/process_latest_download.py` (linhas 31–38, 61–68), `state/last_processed_download.json`
- Trigger: Ficheiro copiado que preserve mtime e tamanho idênticos ao anterior.
- Workaround: Raro em prática dado que os nomes dos XLSX da E-REDES incluem timestamp.

## Security Considerations

**Sessão E-REDES com cookies de autenticação guardados em texto simples:**
- Risk: `state/eredes_storage_state.json` contém cookies de sessão da E-REDES incluindo tokens JWT e cookies de sessão HTTP (`aat`, `PHPSESSID`, `SimpleSAML`). O ficheiro está no repositório e exposto ao git se não existir `.gitignore`.
- Files: `state/eredes_storage_state.json`
- Current mitigation: Não há `.gitignore` — o ficheiro pode ser comprometido num commit inadvertido.
- Recommendations: Adicionar `state/eredes_storage_state.json` ao `.gitignore` imediatamente. Confirmar que o ficheiro não está já na história do git.

**PT NIF/número de instalação exposto em nomes de ficheiro e dados:**
- Risk: O CPE/EAN da instalação (`PT0002000084968079SX`) aparece nos nomes dos ficheiros XLSX em `data/raw/eredes/` e no `state/last_processed_download.json`. Se o repositório for alguma vez público, este identificador fica exposto.
- Files: `data/raw/eredes/Consumos_PT0002000084968079SX_*.xlsx`, `state/last_processed_download.json`
- Current mitigation: Repositório privado/local.
- Recommendations: Adicionar `data/raw/` ao `.gitignore`. Considerar ofuscação do EAN em logs.

**Injeção de shell via f-string em `notify_mac`:**
- Risk: A mensagem passada a `osascript` via f-string `f'display notification "{message}"...'` não tem escape de caracteres especiais. Se `message` contiver `"` ou carateres de controlo AppleScript, pode causar erro ou comportamento inesperado.
- Files: `src/backend/eredes_download.py` (linha 48), `src/backend/monthly_workflow.py` (linha 104), `src/backend/reminder_job.py` (linha 25)
- Current mitigation: As mensagens são strings literais definidas no código — risco baixo em prática.
- Recommendations: Escapar `"` para `\"` na mensagem antes de injetar na f-string AppleScript.

## Performance Bottlenecks

**Playwright abre um browser por cada análise completa:**
- Problem: `tiagofelicia_compare.py` abre um browser Chromium headless, carrega o site com `wait_until="networkidle"` e depois executa N simulações sequenciais (uma por mês no histórico). Com 11 meses de histórico, são 22 interações com formulário + esperas de 4 segundos cada.
- Files: `src/backend/tiagofelicia_compare.py` (linhas 172–189)
- Cause: Sem paralelismo — cada mês é processado sequencialmente na mesma página. Os `wait_for_timeout(4000)` são hardcoded como tempo de espera pela atualização da tabela.
- Improvement path: Reduzir os timeouts se a tabela carregar mais rápido (validar com `page.wait_for_selector`). Para muitos meses, considerar processamento em paralelo com múltiplas páginas.

**`openpyxl` carrega o XLSX inteiro em memória:**
- Problem: `eredes_to_monthly_csv.py` usa `load_workbook(..., read_only=True)` — correto para ficheiros grandes — mas itera todas as linhas sem limite. Um XLSX com dados de vários anos cresce linearmente.
- Files: `src/backend/eredes_to_monthly_csv.py` (linha 93)
- Cause: Ficheiros E-REDES com dados de 15 minutos para um ano têm ~35.000 linhas. Aceitável hoje, mas sem proteção para ficheiros maiores.
- Improvement path: Sem ação urgente para os volumes atuais. Adicionar logging do número de linhas processadas para detetar crescimento.

## Fragile Areas

**Parsing do XLSX da E-REDES com deteção heurística de colunas:**
- Files: `src/backend/eredes_to_monthly_csv.py` (funções `pick_sheet`, `detect_data_start_row`, `extract_date_time_and_kwh`)
- Why fragile: O código tenta detetar a linha de cabeçalho procurando "Data" e "Hora" nas primeiras 40 linhas, e usa listas de candidatos de colunas por índice numérico (ex: colunas 7, 6, 3, 2 como candidatos a potência). Um novo formato de export da E-REDES (nova coluna, nova folha, novo nome de folha) pode silenciosamente produzir kWh errados ou falhar com erro genérico.
- Safe modification: Qualquer alteração à lógica de deteção deve ser testada contra todos os XLSX existentes em `data/raw/eredes/`. Validar que `total_kwh` por mês é positivo e dentro de intervalos razoáveis (ex: 50–500 kWh/mês para habitação).
- Test coverage: Zero — não existem testes automatizados.

**Comparação do fornecedor atual por correspondência de string:**
- Files: `src/backend/tiagofelicia_compare.py` (função `pick_current_result`, linhas 89–101)
- Why fragile: A identificação do fornecedor atual na tabela de resultados usa `.lower()` para comparar o nome do fornecedor. Se o simulador tiagofelicia.pt mudar o nome de apresentação (ex: "MEO" vs "Meo Energia"), a comparação falha silenciosamente e `current_supplier_result` fica `None`.
- Safe modification: Sempre fornecer `current_plan_contains` no `system.json` para ter um segundo critério de identificação.
- Test coverage: Zero.

**`launchd` watcher dispara com qualquer mudança em `~/Downloads`:**
- Files: `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` (chave `WatchPaths`)
- Why fragile: O launchd watcher monitoriza toda a pasta `~/Downloads`. Qualquer download (PDF, imagem, etc.) aciona `process_latest_download.py`, que procura o XLSX mais recente. Se um XLSX não relacionado existir em Downloads e for mais recente que o tracker, será processado erroneamente.
- Safe modification: O filtro `Consumos_*.xlsx` em `local_download_glob` mitiga parcialmente — mas o launchd aciona o script independentemente do tipo de ficheiro descarregado.
- Test coverage: Zero.

## Missing Critical Features

**Ausência de testes automatizados:**
- Problem: Não existe nenhum ficheiro de teste no projeto (zero ficheiros `test_*.py` ou `*.test.py`).
- Blocks: Impossível verificar regressões ao alterar a lógica de parsing XLSX, cálculo de kWh ou comparação de fornecedores.
- Files impactadas sem cobertura: `src/backend/eredes_to_monthly_csv.py`, `src/backend/energy_compare.py`, `src/backend/tiagofelicia_compare.py`

**Home Assistant não implementado:**
- Problem: O Roadmap (Passo 5) e `integracoes/home-assistant/README.md` preveem publicação de resultados no Home Assistant, mas a integração não existe.
- Blocks: Não há visibilidade automática dos resultados — o utilizador tem de consultar manualmente `state/monthly_status.json` ou os relatórios em `data/reports/`.
- Files: `integracoes/home-assistant/README.md` (placeholder vazio), `src/frontend/` (pasta vazia)

**Frontend não implementado:**
- Problem: A pasta `src/frontend/` existe mas está vazia (apenas `README.md`). Não há dashboard ou interface de consulta.
- Blocks: Acesso aos resultados requer leitura direta de JSON ou Markdown.
- Files: `src/frontend/README.md`

## Test Coverage Gaps

**Pipeline de parsing XLSX sem testes:**
- What's not tested: Deteção de cabeçalho, seleção de folha, extração de kWh, cálculo de vazio/fora-de-vazio, drop de mês parcial.
- Files: `src/backend/eredes_to_monthly_csv.py`
- Risk: Uma mudança no formato E-REDES ou na lógica de parsing produz totais mensais errados sem qualquer alerta.
- Priority: High

**Lógica de comparação de tarifários sem testes:**
- What's not tested: Cálculo de custo mensal/anual, ranking, identificação do fornecedor atual, cálculo de poupança.
- Files: `src/backend/energy_compare.py`, `src/backend/tiagofelicia_compare.py`
- Risk: Bug no cálculo pode levar a uma recomendação de mudança de fornecedor errada com impacto financeiro real.
- Priority: High

**Lógica de deduplicação do tracker sem testes:**
- What's not tested: Comportamento quando tracker não existe, quando ficheiro já foi processado, quando mtime coincide.
- Files: `src/backend/process_latest_download.py`
- Risk: Re-processamento ou salto de ficheiro novo.
- Priority: Medium

---

*Concerns audit: 2026-03-28*
