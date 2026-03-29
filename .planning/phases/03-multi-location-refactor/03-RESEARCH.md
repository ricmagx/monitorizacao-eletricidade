# Phase 3: Multi-Location Refactor - Research

**Researched:** 2026-03-29
**Domain:** Python refactor — config schema, directory layout, CPE-based routing, launchd plists, macOS notifications
**Confidence:** HIGH (brownfield project — all code is directly inspectable)

---

## Summary

Esta fase é um refactor puramente interno a um projecto Python brownfield. Não há bibliotecas novas a introduzir: toda a stack (openpyxl, playwright, pytest, osascript, launchd) já existe e está validada. O trabalho consiste em (1) estender o schema de configuração, (2) reorganizar os caminhos de dados e estado, (3) parametrizar os cinco módulos afectados para receber um objecto `location` em vez de ler caminhos directamente da secção `pipeline`, e (4) actualizar os plists launchd para reflectir o novo comportamento multi-local.

O risco de maior incerteza é a selecção programática do CPE no portal E-REDES (MULTI-06). O código actual em `eredes_download.py` usa `external_firefox` como modo final, o que significa que o utilizador faz o download manualmente no browser — o sistema apenas detecta o ficheiro novo em `~/Downloads` por snapshot de directório. A selecção do CPE na UI do portal não é automatizável de forma fiável (CAPTCHA + JWT curto), e o próprio ROADMAP confirma que `external_firefox` é o design final. O planeador deve time-box a tentativa de selecção programática e aceitar graciosamente que, se falhar, o utilizador selecciona o CPE manualmente e o routing por CPE no nome do ficheiro faz o resto.

**Primary recommendation:** Introduzir uma dataclass ou dict `Location` como unidade de composição; passar esse objecto como único argumento novo a todas as funções refactorizadas — evita proliferação de parâmetros e mantém retrocompatibilidade nos testes existentes.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MULTI-01 | Estender `config/system.json` com schema `"locations": [...]` | Schema definido em Architecture Patterns |
| MULTI-02 | Migrar estrutura de directórios para nested (`data/casa/`, `data/apartamento/`, `state/casa/`, `state/apartamento/`) | Runtime State Inventory documenta o que existe e o que muda |
| MULTI-03 | Refactorizar `monthly_workflow.py` para iterar sobre locais (loop sequencial) | Padrão de loop + `--location` flag documentado em Architecture Patterns |
| MULTI-04 | Refactorizar `process_latest_download.py` para routing de XLSX por CPE | CPE confirmado no nome real dos ficheiros — ver Runtime State Inventory |
| MULTI-05 | Refactorizar `reminder_job.py` para enviar notificação por local | Padrão de notificação por local em Code Examples |
| MULTI-06 | Estender `eredes_download.py` para seleccionar CPE correcto no portal | Modo `external_firefox` é o design final; selecção manual é o fallback aceite |
</phase_requirements>

---

## Runtime State Inventory

Esta fase é de migração/refactor — inventário obrigatório.

| Categoria | Items encontrados | Acção necessária |
|-----------|-------------------|-----------------|
| Stored data | `state/last_processed_download.json` — regista o path/mtime/size do último XLSX processado. Actualmente aponta para `Consumos_PT0002000084968079SX_...`. Path encoded com CPE → válido para routing mas o ficheiro é single-location (raiz de `state/`). | Migrar para `state/casa/last_processed_download.json` após o refactor; o formato permanece igual |
| Stored data | `state/monthly_status.json` — status do último run do workflow. Actualmente em raiz de `state/`. | Migrar para `state/casa/monthly_status.json` |
| Stored data | `data/raw/eredes/` — 3 ficheiros XLSX com CPE `PT0002000084968079SX` (`casa`). Não há XLSX do apartamento. | Mover para `data/casa/raw/eredes/` como parte da migração de directórios |
| Stored data | `data/processed/consumo_mensal_atual.csv` e `data/processed/analise_tiagofelicia_atual.json` — gerados pelo pipeline. | Migrar para `data/casa/processed/` (ficheiros gerados, não em git, mas os paths são referenciados em `monthly_status.json`) |
| Stored data | `data/reports/relatorio_eletricidade_2026-03-29.md` — relatório gerado. | Migrar para `data/casa/reports/` |
| Live service config | `launchd/com.ricmag.monitorizacao-eletricidade.plist` — `reminder_job.py` com `--config config/system.json`. Actualmente único local; precisa de iterar sobre locais ou ser duplicado. | Actualizar plist: `reminder_job.py` passa a iterar sobre todos os locais ou recebe `--location`; unload/reload com `launchctl` |
| Live service config | `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` — `process_latest_download.py` com `--config config/system.json`. Detecta qualquer XLSX em `~/Downloads`; após refactor o routing é feito por CPE no nome do ficheiro (multi-location por design). | Não requer duplicação — um único watcher serve ambos os locais; actualizar plist se `--config` mudar |
| OS-registered state | Ambos os plists podem estar registados via `launchctl load ~/Library/LaunchAgents/com.ricmag.monitorizacao-eletricidade*.plist`. | Após editar os plists: `launchctl unload` + editar + `launchctl load` |
| Secrets/env vars | `state/eredes_storage_state.json` (excluído do git) — sessão Playwright partilhada. O ROADMAP confirma explicitamente que este ficheiro permanece partilhado na raiz de `state/`. | Nenhuma — permanece em `state/eredes_storage_state.json` sem mover |
| Secrets/env vars | `state/eredes_bootstrap_context.json` — contexto do bootstrap. Também partilhado (não é por CPE). | Nenhuma — permanece na raiz de `state/` |
| Build artifacts | `src/backend/__pycache__/` — bytecode compilado. Não há egg-info nem package instalado. `pytest.ini` usa `pythonpath = src/backend`. | Nenhuma acção; `__pycache__` auto-regenera |
| CPE apartamento | `PT000200XXXXXXXXXX` — placeholder no ROADMAP. CPE real desconhecido. | Confirmar CPE real no portal E-REDES antes de completar `config/system.json`; a fase não pode completar sem este valor |

**Ficheiros em `data/` e `state/` não estão em git** (`.gitignore` exclui `data/raw/`, `data/processed/`, `data/reports/`). A migração de caminhos é uma operação local, não requer commit de dados.

---

## Standard Stack

### Core (já presente no projecto)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.11 | Runtime | Confirmado no plist launchd e pytest |
| argparse | stdlib | CLI parsing | Já usado em todos os módulos |
| json / pathlib | stdlib | Config e paths | Padrão uniforme em todo o projecto |
| pytest | 7.4.3 | Testes | Já instalado e configurado em `pytest.ini` |

### Sem novas dependências

Esta fase não requer bibliotecas novas. Playwright, openpyxl e osascript já estão presentes e a funcionar.

**Installation:** nenhuma instalação adicional necessária.

---

## Architecture Patterns

### Estrutura de directórios após o refactor

```
data/
├── casa/
│   ├── raw/eredes/          # XLSX da E-REDES para casa
│   ├── processed/           # CSV mensal e JSON de análise
│   └── reports/             # Relatórios .md gerados
└── apartamento/
    ├── raw/eredes/
    ├── processed/
    └── reports/

state/
├── eredes_storage_state.json     # PARTILHADO — sessão Playwright
├── eredes_bootstrap_context.json # PARTILHADO — contexto de bootstrap
├── casa/
│   ├── monthly_status.json
│   └── last_processed_download.json
└── apartamento/
    ├── monthly_status.json
    └── last_processed_download.json
```

### Schema `config/system.json` com `"locations"` (MULTI-01)

```json
{
  "locations": [
    {
      "id": "casa",
      "name": "Casa",
      "cpe": "PT0002000084968079SX",
      "current_contract": {
        "supplier": "Meo Energia",
        "current_plan_contains": "Tarifa Variável",
        "power_label": "10.35 kVA"
      },
      "pipeline": {
        "raw_dir": "data/casa/raw/eredes",
        "processed_csv_path": "data/casa/processed/consumo_mensal_atual.csv",
        "analysis_json_path": "data/casa/processed/analise_tiagofelicia_atual.json",
        "report_dir": "data/casa/reports",
        "status_path": "state/casa/monthly_status.json",
        "last_processed_tracker_path": "state/casa/last_processed_download.json",
        "drop_partial_last_month": true,
        "notify_on_completion": true,
        "months_limit": null,
        "local_tariffs_path": "config/tarifarios.json",
        "local_contract_path": "config/fornecedor_atual.exemplo.json"
      }
    },
    {
      "id": "apartamento",
      "name": "Apartamento",
      "cpe": "PT000200XXXXXXXXXX",
      "current_contract": {
        "supplier": "...",
        "current_plan_contains": "...",
        "power_label": "..."
      },
      "pipeline": {
        "raw_dir": "data/apartamento/raw/eredes",
        "processed_csv_path": "data/apartamento/processed/consumo_mensal_atual.csv",
        "analysis_json_path": "data/apartamento/processed/analise_tiagofelicia_atual.json",
        "report_dir": "data/apartamento/reports",
        "status_path": "state/apartamento/monthly_status.json",
        "last_processed_tracker_path": "state/apartamento/last_processed_download.json",
        "drop_partial_last_month": true,
        "notify_on_completion": true,
        "months_limit": null,
        "local_tariffs_path": "config/tarifarios.json",
        "local_contract_path": "config/fornecedor_atual.exemplo.json"
      }
    }
  ],
  "eredes": {
    "home_url": "https://balcaodigital.e-redes.pt/home",
    "storage_state_path": "state/eredes_storage_state.json",
    "bootstrap_context_path": "state/eredes_bootstrap_context.json",
    "download_dir_base": "data/{location_id}/raw/eredes",
    "download_url": "https://balcaodigital.e-redes.pt/consumptions/history",
    "download_mode": "external_firefox",
    "browser_app": "Firefox",
    "interactive_wait_seconds": 900,
    "local_download_watch_dir": "/Users/ricmag/Downloads",
    "local_download_glob": "Consumos_*.xlsx",
    "download_button_candidates": ["Exportar excel", "Descarregar Excel", "Download Excel", "Exportar Excel", "Excel"],
    "download_timeout_seconds": 60
  },
  "schedule": {
    "day": 1,
    "hour": 9,
    "minute": 0,
    "timezone": "Europe/Lisbon"
  },
  "watcher": {
    "enabled": true,
    "watch_paths": ["/Users/ricmag/Downloads"]
  }
}
```

**Nota de compatibilidade:** As secções `current_contract` e `pipeline` globais (sem `locations`) podem ser mantidas como fallback legacy durante a transição, ou removidas completamente. Recomendação: remover — obriga a testar o novo schema end-to-end.

### Padrão 1: CPE routing em `process_latest_download.py` (MULTI-04)

**What:** Ao detectar um XLSX novo em `~/Downloads`, extrair o CPE do nome do ficheiro e fazer lookup no array `locations` para saber qual o local a processar.

**Formato do nome:** `Consumos_PT0002000084968079SX_2026-02-07_2026-03-26_20260326043814.xlsx`

**Extracção do CPE:**
```python
# Fonte: inspecção directa de ficheiros reais em data/raw/eredes/
import re
from pathlib import Path

CPE_PATTERN = re.compile(r"Consumos_(PT\w+?)_")

def extract_cpe_from_filename(filename: str) -> str | None:
    m = CPE_PATTERN.search(Path(filename).name)
    return m.group(1) if m else None

def find_location_by_cpe(locations: list[dict], cpe: str) -> dict | None:
    for loc in locations:
        if loc.get("cpe") == cpe:
            return loc
    return None
```

**Fallback quando CPE não reconhecido:** log de aviso + skip (não crashar). O utilizador poderá ter descarregado um ficheiro de um CPE não configurado.

### Padrão 2: Loop sequencial em `monthly_workflow.py` (MULTI-03)

**What:** `run_workflow` passa a aceitar um objecto `location` com todos os caminhos; `main()` itera sobre `config["locations"]`, filtrando por `--location` se fornecido.

```python
# Assinatura refactorizada
def run_workflow(config: dict, location: dict, project_root: Path, input_xlsx: Path | None = None) -> dict:
    ...

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config(Path(args.config))
    project_root = project_root_from_config(Path(args.config))
    locations = config["locations"]
    if args.location:
        locations = [loc for loc in locations if loc["id"] == args.location]
        if not locations:
            print(f"Local '{args.location}' nao encontrado em config.", file=sys.stderr)
            return 1
    results = []
    for loc in locations:
        result = run_workflow(config=config, location=loc, project_root=project_root,
                              input_xlsx=Path(args.input_xlsx) if args.input_xlsx else None)
        results.append(result)
    print(json.dumps(results, indent=2, ensure_ascii=True))
    return 0
```

**Argumento novo no parser:** `--location` (opcional, string com o `id` do local).

### Padrão 3: Notificação por local em `reminder_job.py` (MULTI-05)

```python
# Por cada local na config:
for loc in config["locations"]:
    location_name = loc.get("name", loc["id"])
    message = f"[{location_name}] Descarregue o mes anterior completo da E-REDES e depois processe o XLSX."
    notify_mac(f"Eletricidade — {location_name}", message)
    open_browser(browser_app, download_url)
    # Escrever status em state/{loc_id}/monthly_status.json
```

**Nota:** O `reminder_job.py` abre o browser uma vez por local. Se houver dois locais, abre o browser duas vezes consecutivamente. Isto é aceitável para uso pessoal.

### Padrão 4: `eredes_download.py` com CPE hint (MULTI-06)

No modo `external_firefox` o utilizador selecciona o CPE manualmente. O sistema apenas comunica qual o CPE esperado via notificação.

```python
# Adicionar ao notify_mac antes de abrir o browser:
cpe_hint = location.get("cpe", "desconhecido")
notify_mac(
    "E-REDES",
    f"CPE: {cpe_hint} — Abra o Firefox, seleccione o CPE correcto, descarregue o Excel."
)
```

**Se o portal tiver selector de CPE automatizável:** time-box de uma sessão de exploração. Se não for limpo, aceitar `external_firefox` como design final e confiar no routing por CPE no nome do ficheiro. O ROADMAP já documenta esta decisão.

### Anti-Patterns a Evitar

- **Paralelismo:** não introduzir `threading` ou `asyncio` — a sessão Playwright é partilhada e o ROADMAP exige execução sequencial.
- **Config duplicada:** não criar um `system_casa.json` e `system_apartamento.json` separados — o array `locations` num único `system.json` é a abordagem correcta.
- **Paths hardcoded com location_id:** usar sempre a secção `pipeline` do objecto `location` em vez de construir paths por string formatting — evita divergência entre config e código.
- **Alterar `eredes_storage_state.json` para ser por local:** o ROADMAP especifica explicitamente que este ficheiro permanece partilhado; não mover.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CPE extraction from filename | Parser manual frágil | `re.compile(r"Consumos_(PT\w+?)_")` | O formato E-REDES é consistente nos 3 ficheiros reais; regex simples é suficiente |
| CLI `--location` filter | Framework de CLI | `argparse` já presente | Projeto usa argparse uniformemente; não mudar |
| Directory creation | Verificações manuais `os.path.exists` | `Path.mkdir(parents=True, exist_ok=True)` | Já é o padrão usado em todo o projecto |
| Location object | Dataclass com validação | Plain `dict` com keys documentadas | Projecto usa dicts ao longo de todo o código; dataclass seria inconsistente |

---

## Common Pitfalls

### Pitfall 1: `project_root_from_config` em contexto multi-local

**What goes wrong:** `project_root_from_config` usa `config_path.resolve().parent.parent` — funciona porque `config/system.json` está sempre dois níveis abaixo da raiz. Mas se o caller passar o `location["pipeline"]` dict directamente sem o `config_path`, a resolução de paths relativos quebra.

**Why it happens:** Os paths em `location["pipeline"]` são relativos à raiz do projecto, não ao ficheiro de config. A função `resolve_path(project_root, relative_path)` já existe e está correcta — basta garantir que o `project_root` é sempre derivado do `config_path`, não de `__file__` ou cwd.

**How to avoid:** Passar sempre `project_root` como parâmetro explícito a `run_workflow`; nunca calcular `project_root` a partir do objecto `location`.

### Pitfall 2: `last_processed_tracker_path` por local vs. global

**What goes wrong:** O tracker em `state/last_processed_download.json` regista o último XLSX processado. Se for partilhado entre locais, um XLSX de `apartamento` pode ser ignorado porque o tracker já viu esse mtime/size (colisão improvável mas possível).

**Why it happens:** O tracker compara `{"path": ..., "mtime": ..., "size": ...}` — paths diferentes nunca colidem, mas se o mesmo ficheiro for processado por dois locais diferentes (cenário impossível com routing por CPE), haveria problema.

**How to avoid:** Mover o tracker para `state/{location_id}/last_processed_download.json` conforme o REQUIREMENTS define (MULTI-02). Cada local tem o seu tracker independente.

### Pitfall 3: `config["current_contract"]` hardcoded em `render_report`

**What goes wrong:** `render_report` em `monthly_workflow.py` lê `config["current_contract"]["supplier"]` directamente. Após o refactor, o `current_contract` está dentro de `location`, não na raiz de `config`.

**Why it happens:** A função `render_report` recebe `config` (o dict completo) e não o objecto `location`. Após o refactor, todas as referências a `config["current_contract"]` devem ser substituídas por `location["current_contract"]`.

**Warning signs:** `KeyError: 'current_contract'` em runtime após o refactor.

### Pitfall 4: launchd plist não actualizado após o refactor

**What goes wrong:** Os plists em `launchd/` apontam para `--config config/system.json` e executam sem `--location`. Após o refactor, o `reminder_job.py` iterar sobre locais, mas os plists podem continuar a passar o path antigo. Se o schema antigo for removido, o launchd job crasha silenciosamente.

**Why it happens:** Os plists são ficheiros estáticos em `launchd/` e em `~/Library/LaunchAgents/`. Editar o plist em `launchd/` não actualiza automaticamente o job registado.

**How to avoid:** Incluir explicitamente no plano: (1) editar os plists, (2) `launchctl unload`, (3) copiar para `~/Library/LaunchAgents/`, (4) `launchctl load`. Verificar com `launchctl list | grep ricmag`.

### Pitfall 5: `.gitignore` não cobre os novos caminhos nested

**What goes wrong:** Actualmente `.gitignore` exclui `data/raw/`, `data/processed/`, `data/reports/`. Após criar `data/casa/raw/` etc., estas regras continuam a funcionar porque são prefixos de directório — mas verificar explicitamente com `git status` após criar a nova estrutura.

**Why it happens:** As regras `data/raw/` com trailing slash excluem qualquer directório chamado `raw` dentro de `data/` em qualquer nível de profundidade no git mais recente, mas o comportamento pode variar. Verificar.

**How to avoid:** Testar com `git status` após criar `data/casa/` e `data/apartamento/`. Se aparecerem no staging, actualizar `.gitignore` para `data/*/raw/`, `data/*/processed/`, `data/*/reports/`.

---

## Code Examples

### Extracção de CPE do nome de ficheiro (verificado com ficheiros reais)

```python
# Fonte: inspecção directa de data/raw/eredes/ com 3 ficheiros reais:
# Consumos_PT0002000084968079SX_2025-01-01_2025-11-26_20251126115627.xlsx
# Consumos_PT0002000084968079SX_20260326042940.xlsx
# Consumos_PT0002000084968079SX_20260326043825.xlsx
import re
from pathlib import Path

CPE_PATTERN = re.compile(r"Consumos_(PT\w+?)_")

def extract_cpe_from_filename(filename: str) -> str | None:
    m = CPE_PATTERN.search(Path(filename).name)
    return m.group(1) if m else None
```

### Notificação macOS com nome do local (MULTI-05)

```python
# Fonte: reminder_job.py existente, padrão osascript
def notify_mac(title: str, message: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
        check=False,
        capture_output=True,
        text=True,
    )

# Uso por local:
notify_mac(f"Eletricidade — {location['name']}", f"[{location['name']}] Descarregue o mês anterior.")
```

### Loop sequencial sobre locais (MULTI-03)

```python
# Padrão para monthly_workflow.py:main()
parser.add_argument("--location", default=None, help="ID do local a processar (omitir = todos).")

locations = config["locations"]
if args.location:
    locations = [loc for loc in locations if loc["id"] == args.location]
    if not locations:
        print(f"Local '{args.location}' nao encontrado.", file=sys.stderr)
        return 1

results = []
for loc in locations:  # sequencial — sessao Playwright partilhada
    result = run_workflow(config=config, location=loc, project_root=project_root,
                          input_xlsx=Path(args.input_xlsx) if args.input_xlsx else None)
    results.append({"location": loc["id"], **result})
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Runtime | disponivel | 3.11.14 | — |
| pytest | Testes | disponivel | 7.4.3 | — |
| launchctl | plist reload | disponivel (macOS) | macOS 25.3.0 | — |
| CPE apartamento real | MULTI-01, MULTI-04 | indisponivel | — | Usar placeholder; fase não pode completar sem este valor |

**Missing dependencies com no fallback:**
- CPE real do apartamento (`PT000200XXXXXXXXXX` é placeholder) — requer confirmação manual no portal E-REDES antes de poder completar `config/system.json` e testar o routing de MULTI-04.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.4.3 |
| Config file | `pytest.ini` (raiz do projecto) |
| Quick run command | `cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && python3 -m pytest tests/ -x -q` |
| Full suite command | `cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && python3 -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MULTI-01 | Schema `locations` carregado correctamente | unit | `pytest tests/test_multi_location_config.py -x` | ❌ Wave 0 |
| MULTI-02 | Caminhos nested criados em `data/casa/` e `state/casa/` | unit | `pytest tests/test_multi_location_config.py::test_directory_structure -x` | ❌ Wave 0 |
| MULTI-03 | Loop sequencial processa todos os locais; `--location casa` processa só `casa` | unit | `pytest tests/test_multi_workflow.py -x` | ❌ Wave 0 |
| MULTI-04 | Routing por CPE: XLSX `PT0002000084968079SX` routed para `casa`, CPE desconhecido skipped | unit | `pytest tests/test_cpe_routing.py -x` | ❌ Wave 0 |
| MULTI-05 | Notificação inclui nome do local | unit | `pytest tests/test_multi_reminder.py -x` | ❌ Wave 0 |
| MULTI-06 | `eredes_download.py` inclui CPE hint na notificação | unit | incluído em `test_multi_workflow.py` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green antes de `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_multi_location_config.py` — cobre MULTI-01, MULTI-02
- [ ] `tests/test_multi_workflow.py` — cobre MULTI-03, MULTI-06
- [ ] `tests/test_cpe_routing.py` — cobre MULTI-04
- [ ] `tests/test_multi_reminder.py` — cobre MULTI-05
- [ ] `tests/conftest.py` — adicionar fixture `multi_location_config` com dois locais (casa + apartamento mock) em `tmp_path`

---

## Open Questions

1. **CPE real do apartamento**
   - What we know: é `PT000200XXXXXXXXXX` como placeholder
   - What's unclear: o valor real
   - Recommendation: confirmar no portal E-REDES antes de executar o plano; o planeador deve incluir esta verificação como pré-condição da fase

2. **Schema legacy vs. novo: manter retrocompatibilidade?**
   - What we know: `system.json` actual tem `"current_contract"` e `"pipeline"` na raiz; o novo schema move estes para dentro de cada `location`
   - What's unclear: se algum código externo ou script manual usa o schema antigo
   - Recommendation: remover o schema antigo e migrar completamente — projecto pessoal, sem consumidores externos. Manter os dois schemas em paralelo aumenta a complexidade sem benefício.

3. **Selector de CPE no portal E-REDES (MULTI-06)**
   - What we know: o portal usa JWT de curta duração e reCAPTCHA, e o modo `external_firefox` é o design final confirmado
   - What's unclear: se o portal tem um selector de CPE na UI (multi-CPE apenas existe se o utilizador tiver mais de um CPE registado)
   - Recommendation: time-box a 30 minutos de exploração interactiva; se não for automatizável de forma limpa, documentar que o utilizador selecciona o CPE manualmente e o routing por nome de ficheiro faz o resto

---

## Sources

### Primary (HIGH confidence)

- Inspecção directa de `src/backend/monthly_workflow.py` — assinatura actual de `run_workflow`, `render_report`, paths lidos de `config`
- Inspecção directa de `src/backend/process_latest_download.py` — lógica de tracker e routing
- Inspecção directa de `src/backend/reminder_job.py` — padrão de notificação osascript
- Inspecção directa de `src/backend/eredes_download.py` — modo `external_firefox`, snapshot de directório, copy2
- Inspecção directa de `config/system.json` — schema actual
- Inspecção directa de `state/last_processed_download.json` — formato actual com path real confirmando CPE `PT0002000084968079SX`
- Inspecção directa de `data/raw/eredes/` — 3 ficheiros XLSX com naming `Consumos_PT0002000084968079SX_...`
- Inspecção directa de `launchd/*.plist` — dois plists, ambos com `--config config/system.json`
- `.planning/ROADMAP.md` — confirma `external_firefox` como design final e loop sequencial obrigatório
- `.planning/STATE.md` — confirma 3 módulos já location-agnostic, sessão Playwright partilhada

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — descrição detalhada de cada MULTI-XX
- `tests/conftest.py` e testes existentes — padrão de fixture com `test_config` e `tmp_path`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — projecto brownfield com dependências conhecidas e verificadas
- Architecture: HIGH — código fonte lido directamente; schema proposto é evolução natural do existente
- Pitfalls: HIGH — derivados de análise estática do código; não de conjecturas
- CPE apartamento: LOW — placeholder confirmado, valor real desconhecido

**Research date:** 2026-03-29
**Valid until:** 2026-04-28 (schema E-REDES estável; portal pode mudar UI)
