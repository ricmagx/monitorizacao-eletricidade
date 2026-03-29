# Phase 2: Resilience — Research

**Researched:** 2026-03-29
**Domain:** Python error handling, Playwright network fallback, XLSX input validation, unittest.mock
**Confidence:** HIGH — all findings derived directly from reading the existing codebase; no speculation

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RES-01 | Implementar fallback de `tiagofelicia_compare.py` para catálogo local quando o site estiver indisponível ou devolver erro | `analyse_with_tiago()` cria um browser Playwright headless e chama `page.goto(SITE_URL)` — qualquer falha de rede lança `playwright._impl._errors.Error` ou `TimeoutError`. O fallback deve envolver esta chamada num try/except, devolver o resultado do `energy_compare.py` (já existe catálogo local em `config/tarifarios.exemplo.json`) e assinalar `"source": "local_catalog"` no JSON de análise. |
| RES-02 | Adicionar verificação de sanidade ao parser XLSX (limites plausíveis de consumo, colunas esperadas) | `eredes_to_monthly_csv.py` já valida colunas (`detect_data_start_row` lança `ValueError` se não encontrar header). Falta: validação de limites de consumo por mês (0 kWh ou > 5000 kWh são impossíveis). O ponto de inserção é após a agregação de `monthly` mas antes de escrever o CSV — loop que verifica `total_kwh` de cada mês e lança `ValueError` com mensagem clara se fora dos limites. |
| RES-03 | Tratar nome de fornecedor sem correspondência em `tiagofelicia_compare.py` (actualmente retorna `None` em silêncio) | `pick_current_result()` retorna `None` quando o nome do fornecedor não bate com nenhuma linha. `render_report()` em `monthly_workflow.py` acede `latest['latest_saving_vs_current_eur']` que é `None` sem aviso. O report deve assinalar explicitamente quando `current_supplier_result` é `None`, com mensagem "fornecedor não encontrado no simulador". |
</phase_requirements>

---

## Summary

A Phase 2 é estritamente defensiva: não acrescenta funcionalidade ao pipeline, apenas garante que ele não crasha silenciosamente face a três categorias de falha — rede indisponível, dados de input absurdos, e nome de fornecedor sem match.

O código existente tem uma fragilidade importante: `analyse_with_tiago()` em `tiagofelicia_compare.py` lança excepções não capturadas quando a rede falha, e `pick_current_result()` retorna `None` em silêncio quando o fornecedor não tem correspondência — o que depois provoca `TypeError` ou output enganoso no relatório. O parser XLSX `eredes_to_monthly_csv.py` já tem detecção de header (`ValueError` explícito) mas não valida os valores numéricos agregados.

O catálogo local já existe (`config/tarifarios.exemplo.json`) e `energy_compare.py` já tem toda a lógica para calcular custos a partir desse catálogo — o fallback RES-01 não precisa de novo código de cálculo, apenas de orquestração no `monthly_workflow.py`. A abordagem de teste mais limpa para RES-01 é `unittest.mock.patch` na chamada Playwright (evita manipulação de `/etc/hosts`).

**Primary recommendation:** Implementar os três requisitos como alterações cirúrgicas em três ficheiros (`eredes_to_monthly_csv.py` para RES-02, `tiagofelicia_compare.py` para RES-01 e RES-03, `monthly_workflow.py` para orquestrar o fallback). Escrever testes `pytest` com `unittest.mock` para cada cenário.

---

## Standard Stack

### Core (inalterado — já instalado)

| Package | Versão | Propósito | Nota |
|---------|--------|-----------|------|
| Python | 3.11.14 | Runtime | Homebrew em `/usr/local/opt/python@3.11/libexec/bin/python3` |
| playwright | 1.58.0 | Browser headless para tiagofelicia.pt | Mock via `unittest.mock.patch` nos testes |
| openpyxl | 3.1.5 | Parse XLSX E-REDES | |
| pytest | 7.4.3 | Framework de testes | Já instalado no sistema |
| unittest.mock | stdlib | Mock de chamadas de rede/Playwright | Parte da stdlib Python — zero dependências novas |

### Novas dependências para esta fase

Nenhuma. Todos os mecanismos necessários (try/except, ValueError, unittest.mock.patch, pytest) são stdlib ou já instalados.

**Installation:** nenhuma.

---

## Architecture Patterns

### Recommended Project Structure (adições desta fase)

```
src/backend/
  tiagofelicia_compare.py    # RES-01: fallback + RES-03: missing supplier warning
  eredes_to_monthly_csv.py   # RES-02: bounds check antes de escrever CSV
  monthly_workflow.py        # Orquestra fallback: chama analyse_with_tiago, em caso
                              # de falha chama energy_compare.analyse()
config/
  tarifarios.json            # Catálogo local real (cópia editada de tarifarios.exemplo.json)
tests/
  test_tiagofelicia_fallback.py   # RES-01: mock de falha de rede
  test_xlsx_validation.py         # RES-02: bounds check
  test_supplier_missing.py        # RES-03: fornecedor sem correspondência
```

### Pattern 1: Fallback de rede com try/except + mock nos testes (RES-01)

**What:** `analyse_with_tiago()` é envolvida num try/except que captura `Exception` de Playwright. Em caso de falha, `monthly_workflow.py` chama `energy_compare.analyse()` com o catálogo local e assinala `"source": "local_catalog"` no resultado.

**When to use:** Sempre que o site estiver inacessível (timeout, DNS fail, HTTP 5xx, Playwright error).

**Estrutura em `monthly_workflow.py`:**
```python
# Source: análise directa do código existente
try:
    analysis = analyse_with_tiago(
        consumption_path=processed_csv_path,
        power_label=config["current_contract"]["power_label"],
        current_supplier=config["current_contract"]["supplier"],
        current_plan_contains=config["current_contract"].get("current_plan_contains"),
        months_limit=config["pipeline"].get("months_limit"),
    )
    analysis["source"] = "tiagofelicia.pt"
except Exception as exc:
    # fallback para catálogo local
    tariffs_path = resolve_path(project_root, config["pipeline"]["local_tariffs_path"])
    analysis = energy_compare.analyse(
        consumption_path=processed_csv_path,
        tariffs_path=tariffs_path,
        contract_path=...,
    )
    analysis["source"] = "local_catalog"
    analysis["fallback_reason"] = str(exc)
```

**Padrão de mock nos testes (RES-01):**
```python
# Source: Python docs + uso standard em projectos Playwright
from unittest.mock import patch, MagicMock

def test_fallback_when_site_unavailable(tmp_path):
    with patch("tiagofelicia_compare.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        # chamar monthly_workflow.run_workflow(config_path, input_xlsx=...)
        # verificar que result["source"] == "local_catalog"
        # verificar que relatório contém "catálogo local"
```

**Alternativa descartada — editar `/etc/hosts`:** Requer `sudo`, não é reversível automaticamente se o teste crashar, e polui o ambiente. `unittest.mock.patch` é a abordagem correcta para testes unitários de integração com serviços externos.

### Pattern 2: Bounds check no parser XLSX (RES-02)

**What:** Após a agregação do `monthly` dict em `eredes_to_monthly_csv.py`, antes de escrever o CSV, verificar que cada linha tem `total_kwh` dentro de limites plausíveis.

**Limites plausíveis (baseados nos dados reais do projecto):**
- Mínimo: 30 kWh/mês (valor conservador; consumo real em Jan 2025 foi 1429 kWh)
- Máximo: 5000 kWh/mês (limite de RES-03 no ROADMAP)
- `total_kwh == 0` é claramente inválido (ficheiro XLSX corrompido ou vazio)

**Ponto de inserção em `convert_xlsx_to_monthly_csv()`:**
```python
# Após o loop de agregação, antes do output_path.open(...)
for ym, totals in monthly.items():
    if not (30 <= totals["total_kwh"] <= 5000):
        raise ValueError(
            f"Consumo fora dos limites plausíveis para {ym}: "
            f"{totals['total_kwh']:.1f} kWh (esperado 30–5000 kWh/mês)"
        )
```

**Nota crítica:** O `raise` deve acontecer ANTES de qualquer escrita em disco. A função já tem `output_path.parent.mkdir()` e depois `output_path.open("w", ...)` — o bounds check entra antes desse bloco. Isto garante o critério de sucesso "pipeline aborta com mensagem de erro clara antes de escrever qualquer output".

**Teste (RES-02):**
```python
def test_bounds_check_rejects_zero_kwh(tmp_path):
    # Criar XLSX com uma linha de consumo 0
    # Verificar que convert_xlsx_to_monthly_csv() lança ValueError
    # Verificar que o ficheiro CSV de output NÃO foi criado

def test_bounds_check_rejects_5000_kwh(tmp_path):
    # Similar com valor > 5000
```

### Pattern 3: Fornecedor sem correspondência — warning em vez de crash (RES-03)

**What:** `pick_current_result()` já retorna `None` quando o nome não bate. O problema é que `render_report()` acede `latest['latest_saving_vs_current_eur']` que pode ser `None`, e o relatório mostra `None EUR` sem explicação.

**Fix em `tiagofelicia_compare.py`:** `compare_month()` deve incluir no dict resultado um campo `"supplier_not_found": True` quando `current` é `None`, e `summarise_history()` deve propagar isso.

**Fix em `monthly_workflow.py` / `render_report()`:** Se `latest_current_supplier_result` é `None`, incluir uma linha de aviso explícita no relatório:
```
> Aviso: fornecedor atual "Meo Energia" não foi encontrado na tabela do simulador.
> O ranking é apresentado sem comparação com o contrato atual.
```

**Anti-Pattern a Evitar:**
- **Silenciar o `None`:** `saving_vs_current_eur or 0` — esconde o problema e produz resultados enganosos.
- **Crash sem mensagem:** `current["total_eur"]` quando `current is None` — este é o estado actual, que esta fase deve corrigir.

### Anti-Patterns to Avoid

- **Capturar `Exception` genérico em `eredes_to_monthly_csv.py`:** O bounds check deve lançar `ValueError` e propagar — não silenciar. Quem chama (`monthly_workflow.run_workflow`) já tem um try/except de último recurso que escreve o erro no status file.
- **Fallback parcial:** Se `analyse_with_tiago` falha a meio (por exemplo, processou 3 meses e falhou no 4.º), não há resultado parcial recuperável. O fallback deve ser all-or-nothing: qualquer excepção de Playwright → usar catálogo local para todos os meses.
- **Limites hardcoded em múltiplos sítios:** Os limites de bounds check (30 / 5000 kWh) devem ser constantes nomeadas (`MIN_MONTHLY_KWH = 30`, `MAX_MONTHLY_KWH = 5000`) no topo de `eredes_to_monthly_csv.py` — não repetidos inline.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Simular falha de rede em testes | Script que edita `/etc/hosts` | `unittest.mock.patch("tiagofelicia_compare.sync_playwright")` | Reversível, sem root, sem efeitos colaterais no ambiente |
| Catálogo de tarifários de fallback | Scraping de outro site como backup | `energy_compare.analyse()` com `config/tarifarios.json` | Já existe; energia_compare.py já implementa toda a lógica de ranking |
| Logging estruturado de erros | Substituir `print()` por `logging` agora | Deixar para v2 (QUAL-02) | QUAL-02 está explicitamente em v2 — não misturar com Phase 2 |
| Validação de schema do config JSON | Pydantic ou jsonschema | Verificações simples com `if "key" not in config: raise ValueError(...)` | Já é o padrão do projecto; adicionar pydantic seria over-engineering para este projecto pessoal |

**Key insight:** O fallback de RES-01 não precisa de novo motor de cálculo — `energy_compare.py` já existe e já faz exactamente o cálculo de custos com catálogo local. A única tarefa é ligar os dois caminhos no orquestrador.

---

## Common Pitfalls

### Pitfall 1: Capturar excepções Playwright demasiado cedo
**What goes wrong:** Envolver apenas `page.goto()` no try/except, mas `parse_results_table()` pode lançar `RuntimeError("Nao foi possivel extrair resultados da tabela do simulador.")` mesmo com a página carregada (site devolveu HTML diferente do esperado).
**Why it happens:** O site `tiagofelicia.pt` pode estar acessível mas com layout alterado, produzindo uma tabela vazia.
**How to avoid:** O try/except deve envolver a função `analyse_with_tiago()` completa (incluindo o bloco `with sync_playwright()`) — não apenas a chamada `goto`.
**Warning signs:** Teste de fallback passa mas teste de integração com site alterado crasha.

### Pitfall 2: Bounds check com limites demasiado apertados
**What goes wrong:** Limites como `100 <= total_kwh <= 2000` rejeitam meses de inverno reais (Jan 2025 = 1429 kWh) ou verões de baixo consumo.
**Why it happens:** Os dados reais do projecto mostram variação de 644 kWh (Jun 2025) a 1556 kWh (Fev 2025). Um limite superior de 2000 seria arriscado para anos de consumo elevado.
**How to avoid:** Usar limites conservadores (30 / 5000) que apenas capturam valores claramente errados (XLSX corrompido, colunas erradas) sem rejeitar consumos legítimos altos.
**Warning signs:** Pipeline começa a rejeitar ficheiros XLSX reais após actualização do contrato.

### Pitfall 3: `wait_for_timeout(4000)` não substituído causa testes lentos
**What goes wrong:** `run_simple_simulation()` e `run_bi_simulation()` têm `page.wait_for_timeout(4000)` — 4 segundos cada. Com mock, estes timeouts ainda são chamados se o mock não cobrir correctamente a sessão Playwright.
**Why it happens:** O mock deve substituir `sync_playwright` completo — se o mock não implementar correctamente o context manager, o código real pode ser invocado.
**How to avoid:** No mock de `sync_playwright`, garantir que `__enter__` retorna um objeto com `chromium.launch()` que retorna um browser mock cujo `new_page()` retorna uma page mock. Todos os métodos da page mock devem retornar valores aceitáveis (listas vazias, strings vazias) para evitar erros de atributo.
**Warning signs:** Testes de fallback demoram > 10 segundos.

### Pitfall 4: `config/tarifarios.json` não existe em produção
**What goes wrong:** O fallback RES-01 referencia `config/tarifarios.json` mas o repositório só tem `config/tarifarios.exemplo.json`.
**Why it happens:** O `.gitignore` ou a convenção do projecto pode não incluir o ficheiro real.
**How to avoid:** O catálogo local de fallback deve ser `config/tarifarios.json` (não `.exemplo.json`), criado a partir do exemplo, e NÃO excluído do git (não contém dados pessoais — apenas tarifas públicas de fornecedores). Verificar que `config/tarifarios.json` existe antes do pipeline correr, e lançar erro informativo se não existir.
**Warning signs:** Fallback activa mas lança `FileNotFoundError` em vez de produzir relatório.

### Pitfall 5: O relatório não indica claramente o modo fallback
**What goes wrong:** O relatório gerado em modo fallback parece idêntico ao normal, o utilizador não sabe que os dados são do catálogo local (potencialmente desactualizado).
**Why it happens:** `render_report()` não verifica `analysis["source"]`.
**How to avoid:** `render_report()` deve incluir uma secção ou linha de cabeçalho explícita quando `source == "local_catalog"`:
```
> Fonte: catálogo local (tiagofelicia.pt indisponível — dados podem estar desactualizados)
```
**Warning signs:** Critério de sucesso 1 da fase não verificado: "o relatório indica explicitamente que usou o catálogo local como fallback".

---

## Code Examples

### RES-01: Mock de Playwright para teste de fallback

```python
# Source: Python stdlib docs + padrão standard em projectos com Playwright
from unittest.mock import patch, MagicMock
import pytest

def test_fallback_activated_on_network_error(tmp_path, config_with_local_tariffs):
    """Pipeline usa catálogo local quando tiagofelicia.pt inacessível."""
    with patch("monthly_workflow.analyse_with_tiago") as mock_analyse:
        mock_analyse.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        result = run_workflow(
            config_path=config_with_local_tariffs,
            input_xlsx=sample_xlsx_path,
        )
    assert result["source"] == "local_catalog"
    assert "catálogo local" in Path(result["report_path"]).read_text()
```

### RES-02: Teste de bounds check

```python
# Source: padrão pytest com tmp_path fixture
def test_bounds_check_rejects_zero_month(tmp_path):
    """XLSX com mês de consumo 0 kWh deve levantar ValueError antes de escrever CSV."""
    xlsx = build_xlsx_with_zero_month(tmp_path)  # fixture que cria XLSX de teste
    output_csv = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="fora dos limites plausíveis"):
        convert_xlsx_to_monthly_csv(xlsx, output_csv)
    assert not output_csv.exists(), "CSV não deve ser criado quando bounds check falha"
```

### RES-03: Teste de fornecedor sem match

```python
# Source: análise directa de pick_current_result() + compare_month()
def test_report_warns_when_supplier_not_found():
    """Relatório deve assinalar ausência de correspondência do fornecedor actual."""
    result = compare_month(
        page=mock_page_with_results(),
        month_row=sample_month_row,
        power_label="6.90 kVA",
        current_supplier="Fornecedor Inexistente XYZ",
        current_plan_contains=None,
    )
    assert result["current_supplier_result"] is None
    # O render_report deve converter isto num aviso, não num crash
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 |
| Config file | none — Wave 0 deve criar `pytest.ini` ou secção `[tool.pytest.ini_options]` em `pyproject.toml` |
| Quick run command | `cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RES-01 | Pipeline usa catálogo local quando tiagofelicia.pt inacessível | unit (mock) | `python -m pytest tests/test_tiagofelicia_fallback.py -x` | Wave 0 |
| RES-01 | Relatório indica explicitamente "catálogo local" | unit | incluído no mesmo ficheiro | Wave 0 |
| RES-02 | Bounds check rejeita 0 kWh antes de escrever CSV | unit | `python -m pytest tests/test_xlsx_validation.py -x` | Wave 0 |
| RES-02 | Bounds check rejeita > 5000 kWh antes de escrever CSV | unit | incluído no mesmo ficheiro | Wave 0 |
| RES-03 | Pipeline não crasha quando fornecedor sem match | unit | `python -m pytest tests/test_supplier_missing.py -x` | Wave 0 |
| RES-03 | Relatório contém mensagem de aviso quando fornecedor sem match | unit | incluído no mesmo ficheiro | Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green antes de `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — torna `tests/` um package Python
- [ ] `tests/conftest.py` — fixtures partilhadas (sample XLSX, sample CSV, config de teste com catálogo local, mock da page Playwright)
- [ ] `tests/test_tiagofelicia_fallback.py` — cobre RES-01 (mock de falha de rede + verificação de relatório)
- [ ] `tests/test_xlsx_validation.py` — cobre RES-02 (bounds check: 0 kWh, > 5000 kWh, valores normais)
- [ ] `tests/test_supplier_missing.py` — cobre RES-03 (None result + warning no relatório)
- [ ] `pytest.ini` ou `[tool.pytest.ini_options]` em `pyproject.toml` — define `testpaths = ["tests"]` e `pythonpath = ["src/backend"]`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Runtime | ✓ | 3.11.14 | — |
| pytest | Test runner | ✓ | 7.4.3 | — |
| unittest.mock | Mock Playwright | ✓ | stdlib | — |
| playwright | Código de produção (mock nos testes) | ✓ | 1.58.0 | — |
| openpyxl | Parser XLSX (tests com XLSX fixtures) | ✓ | 3.1.5 | — |

**Missing dependencies with no fallback:** Nenhuma.

**Nota:** `tiagofelicia.pt` é necessário para testes de integração ao vivo, mas esta fase usa exclusivamente mocks — não é necessário acesso à internet para correr a suite de testes.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `wait_for_timeout(4000)` hardcoded | DOM selector wait (futuro — fora do escopo desta fase) | N/A — fase 2 não altera | O ROADMAP menciona este risco mas o fix é opcional para Phase 2 |
| Nenhum fallback | `energy_compare.analyse()` com catálogo local | Esta fase | Pipeline robusto face a indisponibilidade |
| `None` silencioso | Warning explícito no relatório | Esta fase | Utilizador informado quando fornecedor não tem match |

**Deprecated/outdated:**
- `page.wait_for_timeout(4000)` em `run_simple_simulation()` e `run_bi_simulation()`: tecnicamente funciona mas é frágil; o ROADMAP identifica a substituição por DOM selector wait como risco para Phase 2, mas não é bloqueante — pode ficar para Phase 3 se o sinal DOM exacto não for identificável sem inspeção ao vivo.

---

## Open Questions

1. **Qual é o path correcto para `config/tarifarios.json` no fallback?**
   - What we know: `config/tarifarios.exemplo.json` existe com estrutura correcta; `energy_compare.load_tariffs()` lê qualquer JSON nesse formato
   - What's unclear: O ficheiro real de produção com tarifas actualizadas ainda não existe (apenas o exemplo)
   - Recommendation: Wave 0 deve criar `config/tarifarios.json` a partir do exemplo, com tarifas reais actualizadas. O planner deve incluir esta tarefa como dependência de RES-01.

2. **Substituir `wait_for_timeout(4000)` por DOM selector wait?**
   - What we know: O ROADMAP identifica isto como risco para Phase 2; requer inspeção da página ao vivo
   - What's unclear: Qual é o sinal DOM exacto de "tabela actualizada" (classe CSS, atributo, novo elemento)
   - Recommendation: Deixar para Phase 2 como tarefa opcional (nice-to-have); o fallback RES-01 funciona independentemente. Se o utilizador tiver acesso ao site ao vivo durante a implementação, resolver. Caso contrário, deferir para Phase 3.

3. **`current_plan_contains` no config atual é "Tarifa Variável" — corresponde a alguma linha do simulador?**
   - What we know: `pick_current_result()` faz matching por `supplier.lower() == current_supplier.lower()`; o supplier actual é "Meo Energia"
   - What's unclear: Se "Meo Energia" aparece no simulador tiagofelicia.pt com esse nome exacto
   - Recommendation: RES-03 trata este caso graciosamente independentemente da resposta; o teste deve cobrir ambos os cenários (com e sem match).

---

## Project Constraints (from CLAUDE.md global)

Directivas relevantes do `CLAUDE.md` global:

- **Respostas em PT-PT** — código comentado em português, naming em português
- **Soluções práticas e directas — sem over-engineering** — esta fase não deve introduzir pydantic, logging estruturado (QUAL-02 é v2), ou abstrações desnecessárias
- **Commits atómicos** — cada requisito (RES-01, RES-02, RES-03) deve resultar num commit separado

Sem `CLAUDE.md` local no projecto.

---

## Sources

### Primary (HIGH confidence)
- Leitura directa de `src/backend/tiagofelicia_compare.py` — lógica de `analyse_with_tiago()`, `pick_current_result()`, `run_simple_simulation()`
- Leitura directa de `src/backend/eredes_to_monthly_csv.py` — lógica de `convert_xlsx_to_monthly_csv()`, `detect_data_start_row()`
- Leitura directa de `src/backend/monthly_workflow.py` — lógica de `run_workflow()`, `render_report()`
- Leitura directa de `src/backend/energy_compare.py` — confirma que `analyse()` aceita `tariffs_path` e produz ranking local
- Leitura directa de `data/processed/consumo_mensal_atual.csv` — dados reais: 644–1556 kWh/mês (calibra limites do bounds check)
- Leitura directa de `config/tarifarios.exemplo.json` — schema do catálogo local de fallback
- Leitura directa de `config/system.json` — paths de configuração actuais
- Python stdlib `unittest.mock` — disponível em Python 3.11 stdlib, sem dependências externas (HIGH confidence)
- pytest 7.4.3 — instalado e verificado no sistema

### Secondary (MEDIUM confidence)
- Padrão de mock de Playwright via `unittest.mock.patch("module.sync_playwright")` — padrão standard em testes Python para qualquer context manager; não verificado em docs oficiais Playwright mas é idiomático Python

### Tertiary (LOW confidence)
- Comportamento exacto de `tiagofelicia.pt` quando indisponível (qual excepção Playwright específica) — não verificável sem simular falha real; o try/except genérico (`Exception`) é mais robusto do que tentar capturar excepções específicas

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verificado directamente do sistema e do código existente
- Architecture: HIGH — derivado directamente da leitura do código; sem inferências
- Pitfalls: HIGH — baseados em análise do código actual (problemas RES-01/03 já existem no código)
- Test patterns: MEDIUM — padrão unittest.mock é idiomático Python mas não verificado contra docs Playwright especificamente

**Research date:** 2026-03-29
**Valid until:** 2026-06-29 (stack estável; sem versões em fast-moving)

---

## RESEARCH COMPLETE
