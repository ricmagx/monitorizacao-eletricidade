# Roadmap — Monitorização de Eletricidade Multi-Local

**Milestone:** Pipeline funcional multi-local com dashboard
**Granularidade:** Coarse (4 fases)
**Cobertura:** 21/21 requisitos v1 mapeados

---

## Phases

- [ ] **Phase 1: Unblock & Validate End-to-End** — Corrigir os dois bloqueadores confirmados e validar que o pipeline corre com dados reais
- [ ] **Phase 2: Resilience** — Tornar o pipeline robusto antes de adicionar complexidade
- [ ] **Phase 3: Multi-Location Refactor** — Estender o pipeline validado para suportar N locais independentes
- [ ] **Phase 4: Web Dashboard MVP** — Dashboard web local em modo leitura sobre os ficheiros de output do pipeline

---

## Phase Details

### Phase 1: Unblock & Validate End-to-End

**Goal:** Corrigir os dois bloqueadores confirmados (launchd TCC e sessão E-REDES expirada) e verificar que o pipeline produz um relatório correcto a partir dos ficheiros XLSX reais disponíveis.

**Depends on:** Nada (fase inicial)

**Requirements:** FIX-01, FIX-02, FIX-03, FIX-04, VAL-01, VAL-02

**Success Criteria** (o que deve ser verdade quando a fase termina):
  1. Ao colocar um XLSX E-REDES em `~/Downloads`, o launchd deteta-o e o pipeline corre sem erros de TCC (`state/launchd.process.stderr.log` não regista `[Errno 1] Operation not permitted` após o fix)
  2. O pipeline produz um ficheiro `data/reports/relatorio_eletricidade_YYYY-MM-DD.md` com ranking de fornecedores e recomendação mono/bihorário a partir dos XLSX disponíveis
  3. O parser XLSX corre sem erros nos três ficheiros disponíveis em `data/raw/eredes/` (incluindo o formato de 2025 e o de 2026)
  4. `state/eredes_storage_state.json` está excluído do repositório git e não aparece em `git status`
  5. `pip install -r requirements.txt` instala todas as dependências sem erros num ambiente limpo

**Key Risks:**
- O fix do plist pode requerer concessão de Full Disk Access manual em System Settings > Privacy & Security — passo que não é automatizável e que requer intervenção do utilizador
- O parser XLSX usa detecção heurística de colunas (posicional, não por nome); se o formato dos ficheiros 2026 diferir do esperado, o parser pode produzir valores incorretos sem erro explícito — validar com os bounds check de 30-1000 kWh/mês
- A sessão E-REDES expira em ~90 minutos após bootstrap; o bootstrap tem de ser executado imediatamente antes do primeiro teste end-to-end

**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — Corrigir .gitignore, requirements.txt e path Python nos plists launchd
- [ ] 01-02-PLAN.md — Bootstrap sessao E-REDES, validar parser XLSX e pipeline end-to-end

---

### Phase 2: Resilience

**Goal:** O pipeline produz sempre um relatório utilizável, mesmo quando `tiagofelicia.pt` está indisponível ou devolve dados incorrectos.

**Depends on:** Phase 1

**Requirements:** RES-01, RES-02, RES-03

**Success Criteria** (o que deve ser verdade quando a fase termina):
  1. Com `tiagofelicia.pt` inacessível (simulado via bloqueio de rede ou hostname falso), o pipeline termina com sucesso e o relatório indica explicitamente que usou o catálogo local como fallback
  2. Se o nome do fornecedor actual não corresponder a nenhuma linha da tabela do simulador, o pipeline termina com sucesso (não crash) e o relatório assinala a ausência de correspondência com mensagem de aviso
  3. Ao fornecer um XLSX com valores fora dos limites plausíveis (por exemplo, 0 kWh ou 5000 kWh num mês), o pipeline aborta com uma mensagem de erro clara antes de escrever qualquer output

**Key Risks:**
- A verificação do fallback requer simular falha de rede; nos testes locais pode ser necessário editar `/etc/hosts` ou usar `unittest.mock` para substituir a chamada Playwright — definir a abordagem de teste antes de implementar
- O selector-based DOM wait para substituir `wait_for_timeout(4000)` depende de conhecer o sinal DOM exato de "tabela actualizada" no site; pode requerer inspeção da página ao vivo antes de codificar

**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — Corrigir .gitignore, requirements.txt e path Python nos plists launchd
- [ ] 01-02-PLAN.md — Bootstrap sessao E-REDES, validar parser XLSX e pipeline end-to-end

---

### Phase 3: Multi-Location Refactor

**Goal:** Ambos os locais (`casa` e `apartamento`) correm o pipeline completo de forma independente, com routing de XLSX por CPE no nome do ficheiro e estado separado por local.

**Depends on:** Phase 2

**Requirements:** MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05, MULTI-06

**Success Criteria** (o que deve ser verdade quando a fase termina):
  1. Ao colocar em `~/Downloads` um XLSX com o CPE de `casa` (`PT0002000084968079SX`), o pipeline escreve o relatório em `data/casa/reports/` e não toca em `data/apartamento/`
  2. `python3 src/backend/monthly_workflow.py --config config/system.json` (sem `--location`) produz relatórios para todos os locais configurados, executados sequencialmente
  3. `python3 src/backend/monthly_workflow.py --config config/system.json --location casa` processa apenas `casa`
  4. `state/casa/` e `state/apartamento/` existem com os ficheiros de estado independentes; `state/eredes_storage_state.json` permanece partilhado na raiz de `state/`
  5. A notificação macOS do dia 1 identifica explicitamente o local a que se refere (não envia uma notificação genérica para todos os locais em simultâneo)

**Key Risks:**
- A selecção do CPE correcto no portal E-REDES (`eredes_download.py` MULTI-06) é a parte com menor certeza de todo o refactor: o comportamento exacto da UI multi-CPE do portal não está documentado e requer exploração interactiva da sessão ao vivo; time-box a uma sessão — se não for automatizável de forma limpa, `external_firefox` trata o caso graciosamente (utilizador selecciona o CPE manualmente e o routing por CPE no nome do ficheiro faz o resto
- O CPE do `apartamento` é um placeholder (`PT000200XXXXXXXXXX`) — deve ser confirmado no portal E-REDES antes de completar a configuração e os testes desta fase
- A execução sequencial é obrigatória (sessão Playwright partilhada); não introduzir paralelismo nesta fase

**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — Corrigir .gitignore, requirements.txt e path Python nos plists launchd
- [ ] 01-02-PLAN.md — Bootstrap sessao E-REDES, validar parser XLSX e pipeline end-to-end

---

### Phase 4: Web Dashboard MVP

**Goal:** Dashboard web local em modo leitura que apresenta histórico de consumo por local, ranking de fornecedores e recomendação de mudança, com indicadores de frescura e delta ano-a-ano.

**Depends on:** Phase 3

**Requirements:** DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06

**Success Criteria** (o que deve ser verdade quando a fase termina):
  1. `uvicorn src.web.app:app` arranca sem erros e a página principal abre em `http://localhost:8000` num browser local
  2. O selector de local actualiza o gráfico e a tabela por HTMX sem recarregar a página inteira, e mostra dados corretos para cada local configurado
  3. O gráfico de barras empilhadas mostra o consumo mensal (vazio / fora de vazio) para todos os meses disponíveis no CSV processado do local seleccionado
  4. A tabela de ranking lista os fornecedores por custo anual estimado; a linha do fornecedor actual está assinalada; a recomendação mostra a poupança estimada em euros/ano
  5. O indicador de frescura mostra a data do último relatório gerado; se o último relatório tiver mais de 40 dias, o indicador aparece em estado de aviso
  6. O delta ano-a-ano está visível por mês (comparação com o período homólogo); meses sem dados do ano anterior não mostram delta
  7. Nenhum pedido de rede externo é efectuado pelo browser (Chart.js e HTMX são servidos como ficheiros estáticos locais — verificável no Network tab das DevTools)

**Key Risks:**
- O formato dos ficheiros JSON de análise (`analise_tiagofelicia_atual.json`) pode sofrer alterações durante a Phase 3 que tornem os routes FastAPI desta fase inconsistentes; definir e estabilizar o schema de output da Phase 3 antes de codificar os routes
- HTMX e Chart.js devem ser descarregados e fixados como ficheiros estáticos locais antes de qualquer trabalho de UI — verificar versões disponíveis (HTMX 2.0.x, Chart.js 4.4.x) e confirmar que o UMD build do Chart.js não requer bundler
- O ano-a-ano (DASH-06) depende de ter pelo menos 2 anos de dados para `casa`; para `apartamento` provavelmente não existe histórico suficiente na primeira iteração — a UI deve mostrar o estado "sem dados para comparação" de forma elegante e não como erro

**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — Corrigir .gitignore, requirements.txt e path Python nos plists launchd
- [ ] 01-02-PLAN.md — Bootstrap sessao E-REDES, validar parser XLSX e pipeline end-to-end

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Unblock & Validate | 0/2 | Planning complete | - |
| 2. Resilience | 0/? | Not started | - |
| 3. Multi-Location Refactor | 0/? | Not started | - |
| 4. Web Dashboard MVP | 0/? | Not started | - |

---

## Milestone

**Pipeline funcional multi-local com dashboard**
Completo quando todas as 4 fases estiverem concluídas.

Definição de concluído para o milestone:
- O pipeline corre automaticamente via launchd para os dois locais após download de XLSX
- Cada local tem relatório mensal independente com ranking de fornecedores e recomendação
- A dashboard apresenta histórico, ranking e recomendação para ambos os locais
- Nenhum requisito v1 está em estado pendente

---

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 1 | Pending |
| FIX-02 | Phase 1 | Pending |
| FIX-03 | Phase 1 | Pending |
| FIX-04 | Phase 1 | Pending |
| VAL-01 | Phase 1 | Pending |
| VAL-02 | Phase 1 | Pending |
| RES-01 | Phase 2 | Pending |
| RES-02 | Phase 2 | Pending |
| RES-03 | Phase 2 | Pending |
| MULTI-01 | Phase 3 | Pending |
| MULTI-02 | Phase 3 | Pending |
| MULTI-03 | Phase 3 | Pending |
| MULTI-04 | Phase 3 | Pending |
| MULTI-05 | Phase 3 | Pending |
| MULTI-06 | Phase 3 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |
| DASH-05 | Phase 4 | Pending |
| DASH-06 | Phase 4 | Pending |

**Total v1:** 21 requisitos mapeados em 4 fases. Sem orphans.

---

*Roadmap criado: 2026-03-28*
