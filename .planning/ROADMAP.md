# Roadmap — Monitorização de Eletricidade Multi-Local

## Milestones

- ✅ **v1.0 Pipeline MVP** — Phases 1-4 (shipped 2026-03-30)
- 🚧 **v2.0 Sistema Integrado** — Phases 5-12 (in progress)

## Phases

<details>
<summary>✅ v1.0 Pipeline MVP (Phases 1-4) — SHIPPED 2026-03-30</summary>

### Phase 1: Unblock & Validate End-to-End
**Goal**: Corrigir os dois bloqueadores confirmados (launchd TCC e sessão E-REDES expirada) e verificar que o pipeline produz um relatório correcto a partir dos ficheiros XLSX reais disponíveis.
**Depends on**: Nada (fase inicial)
**Requirements**: FIX-01, FIX-02, FIX-03, FIX-04, VAL-01, VAL-02
**Success Criteria** (what must be TRUE):
  1. Ao colocar um XLSX E-REDES em ~/Downloads, o launchd detecta-o e o pipeline corre sem erros de TCC
  2. O pipeline produz um ficheiro relatorio_eletricidade_YYYY-MM-DD.md com ranking e recomendação
  3. O parser XLSX corre sem erros nos ficheiros disponíveis em data/raw/eredes/
  4. state/eredes_storage_state.json está excluído do repositório git
  5. pip install -r requirements.txt instala todas as dependências sem erros num ambiente limpo
**Plans**: 1/2 plans executed

Plans:
- [x] 01-01-PLAN.md — Corrigir .gitignore, requirements.txt e path Python nos plists launchd
- [ ] 01-02-PLAN.md — Bootstrap sessao E-REDES, validar parser XLSX e pipeline end-to-end

### Phase 2: Resilience
**Goal**: O pipeline produz sempre um relatório utilizável, mesmo quando tiagofelicia.pt está indisponível ou devolve dados incorrectos.
**Depends on**: Phase 1
**Requirements**: RES-01, RES-02, RES-03
**Success Criteria** (what must be TRUE):
  1. Com tiagofelicia.pt inacessível, o pipeline termina com sucesso e o relatório indica que usou catálogo local como fallback
  2. Se o fornecedor actual não corresponder a nenhuma linha da tabela, o pipeline termina sem crash e assinala a ausência com aviso
  3. XLSX com valores fora dos limites plausíveis aborta com mensagem de erro clara antes de escrever qualquer output
**Plans**: 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md — Fallback tiagofelicia.pt para catalogo local + fornecedor sem match + infraestrutura pytest
- [x] 02-02-PLAN.md — Bounds check no parser XLSX

### Phase 3: Multi-Location Refactor
**Goal**: Ambos os locais (casa e apartamento) correm o pipeline completo de forma independente, com routing de XLSX por CPE no nome do ficheiro e estado separado por local.
**Depends on**: Phase 2
**Requirements**: MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05, MULTI-06
**Success Criteria** (what must be TRUE):
  1. XLSX com CPE de casa escreve relatório em data/casa/reports/ e não toca em data/apartamento/
  2. monthly_workflow.py sem --location produz relatórios para todos os locais sequencialmente
  3. monthly_workflow.py --location casa processa apenas casa
  4. state/casa/ e state/apartamento/ existem com ficheiros de estado independentes
  5. A notificação macOS identifica explicitamente o local a que se refere
**Plans**: 3/3 plans complete

Plans:
- [x] 03-01-PLAN.md — Config schema locations array + CPE routing module + test infrastructure
- [x] 03-02-PLAN.md — Refactor monthly_workflow.py + process_latest_download.py + eredes_download.py
- [x] 03-03-PLAN.md — Refactor reminder_job.py para notificacoes per-location + verificacao launchd

### Phase 4: Web Dashboard MVP
**Goal**: Dashboard web local em modo leitura que apresenta histórico de consumo por local, ranking de fornecedores e recomendação de mudança, com indicadores de frescura.
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. uvicorn src.web.app:app arranca sem erros e a página principal abre em http://localhost:8000
  2. O selector de local actualiza gráfico e tabela por HTMX sem recarregar a página inteira
  3. O gráfico de barras empilhadas mostra consumo mensal (vazio/fora de vazio) para todos os meses disponíveis
  4. A tabela de ranking lista fornecedores por custo anual estimado com recomendação e poupança em €/ano
  5. O indicador de frescura mostra data do último relatório; se >40 dias aparece em estado de aviso
  6. Nenhum pedido de rede externo é efectuado pelo browser (Chart.js e HTMX servidos como ficheiros estáticos locais)
**Plans**: 3/3 plans complete

Plans:
- [x] 04-01-PLAN.md — FastAPI app + data loader + templates base + ficheiros estáticos
- [x] 04-02-PLAN.md — Gráficos de consumo e custo + formulário de custo real da factura
- [x] 04-03-PLAN.md — Ranking de fornecedores + banner de recomendação + LaunchAgent plist

</details>

---

### 🚧 v2.0 Sistema Integrado (In Progress)

**Milestone Goal:** Transformar o sistema num serviço autónomo em Docker (Unraid), com upload de ficheiros via browser, extracção automática de faturas PDF, histórico multi-ano em SQLite e UI redesenhado.

---

## Phase Details

### Phase 5: Docker + SQLite Foundation
**Goal**: A aplicação corre como container Docker no Unraid com dados persistentes em SQLite, eliminando toda dependência macOS (launchd, osascript, open -a Firefox).
**Depends on**: Phase 4
**Requirements**: INFRA-01, INFRA-03, DADOS-01, DADOS-02, DADOS-03, DADOS-04
**Success Criteria** (what must be TRUE):
  1. docker-compose up arranca a aplicação sem erros e a app responde em http://localhost:8000 dentro do container
  2. A base SQLite é criada automaticamente no arranque com as tabelas de consumo, comparações e custos de fatura
  3. Dados escritos na sessão anterior persistem após docker-compose down && docker-compose up (volume montado)
  4. O código não contém referências a launchd, osascript, open -a Firefox ou paths macOS
  5. O container aplica as migrações de schema sem intervenção manual ao arrancar
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — Docker infrastructure (Dockerfile, compose, entrypoint) + remoção código macOS
- [x] 05-02-PLAN.md — SQLite schema (SQLAlchemy Core) + Alembic migrations + testes
- [x] 05-03-PLAN.md — Integração FastAPI+DB + health endpoint + Docker smoke test
**UI hint**: no

### Phase 6: UI Design (ui-phase)
**Goal**: Especificação visual completa do sistema v2 definida e aprovada antes de qualquer implementação frontend — esta é uma fase de design, não de código.
**Depends on**: Phase 5
**Requirements**: UI-01
**Success Criteria** (what must be TRUE):
  1. UI-SPEC.md existe em .planning/ com wireframes e decisões de layout aprovados pelo utilizador
  2. A spec define o layout do selector de local, ranking, gráficos de consumo/custo e badge de frescura
  3. A spec define o comportamento de estado vazio (sem dados ainda carregados) e estado de erro
**Plans**: TBD
**UI hint**: yes

### Phase 7: Upload XLSX + Ingestão de Dados
**Goal**: O utilizador faz upload de XLSX E-REDES via browser e o sistema normaliza e armazena o consumo mensal em SQLite, com detecção automática de local por CPE e gestão de locais no UI.
**Depends on**: Phase 6
**Requirements**: UPLD-01, UPLD-02, UPLD-05, CONF-01, CONF-02, COMP-01, COMP-02
**Success Criteria** (what must be TRUE):
  1. O utilizador faz upload de um XLSX via formulário web e recebe confirmação com o período importado e o local detectado (CPE)
  2. O consumo mensal (vazio/fora_vazio kWh) fica gravado em SQLite e visível no dashboard após upload
  3. Fazer upload do mesmo XLSX duas vezes não duplica os dados (idempotência mantida)
  4. O utilizador pode criar um novo local com nome livre e CPE via formulário no UI, e pode editar o fornecedor actual do local
  5. Após upload de XLSX, o sistema consulta tiagofelicia.pt e guarda o resultado em SQLite com timestamp
**Plans**: TBD
**UI hint**: yes

### Phase 8: Upload PDF + Extracção de Faturas
**Goal**: O utilizador faz upload de PDF de fatura via browser e o sistema extrai automaticamente o total pago e período, detectando o local pelo CPE presente no documento, para os formatos Meo Energia e Endesa.
**Depends on**: Phase 7
**Requirements**: UPLD-03, UPLD-04
**Success Criteria** (what must be TRUE):
  1. Upload de um PDF Meo Energia extrai o total pago em € e o período correcto, visíveis no dashboard
  2. Upload de um PDF Endesa extrai o total pago em € e o período correcto, visíveis no dashboard
  3. Se o PDF não for reconhecido como nenhum dos formatos conhecidos, o sistema mostra mensagem de erro clara sem crash
  4. O gás, mesmo que presente na fatura Endesa, não é importado
**Plans**: 2 plans
**UI hint**: no

Plans:
- [x] 08-01-PLAN.md — pdfplumber dependency + extrator PDF (Meo Energia + Endesa) com testes
- [x] 08-02-PLAN.md — Endpoint POST /upload/pdf + templates HTML

### Phase 9: Dashboard UI
**Goal**: Dashboard completo implementado conforme UI-SPEC produzida na Phase 6, com selector de local, ranking de fornecedores, gráficos de consumo e custo.
**Depends on**: Phase 8
**Requirements**: UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. O selector de local no topo do dashboard muda todos os dados visíveis sem recarregar a página
  2. O ranking de fornecedores mostra custo anual estimado e poupança potencial em €/ano para o perfil de consumo do local seleccionado
  3. O gráfico de consumo mensal mostra barras empilhadas vazio/fora_vazio para todos os meses disponíveis
  4. O gráfico de custo mostra a estimativa do fornecedor actual lado a lado com o custo real da fatura para os meses com PDF importado
  5. O layout segue a UI-SPEC aprovada (cores, tipografia, espaçamento)
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [ ] 09-01-PLAN.md — Migracao data source CSV/JSON para SQLite + retrocompatibilidade
- [ ] 09-02-PLAN.md — Alinhamento UI com UI-SPEC (custo chart, ranking, banner, layout)

### Phase 10: Cache tiagofelicia.pt + Integração Comparação
**Goal**: O dashboard usa sempre dados de comparação actuais quando tiagofelicia.pt está disponível e recorre ao cache de forma transparente quando o site está em baixo, com indicação visível do estado dos dados.
**Depends on**: Phase 9
**Requirements**: COMP-03, COMP-04
**Success Criteria** (what must be TRUE):
  1. Com tiagofelicia.pt inacessível, o dashboard continua a mostrar o ranking usando os dados do cache SQLite
  2. Um badge visível indica se os dados de comparação são frescos (data da última consulta bem-sucedida) ou provêm do cache
  3. O utilizador nunca fica bloqueado ou vê uma página de erro devido à indisponibilidade de tiagofelicia.pt
**Plans**: TBD
**UI hint**: yes

### Phase 11: Análise Multi-ano
**Goal**: O utilizador pode comparar o consumo e custo do mesmo mês em anos diferentes e ver resumos anuais, com 3+ anos de histórico visíveis nos gráficos.
**Depends on**: Phase 10
**Requirements**: ANAL-01, ANAL-02, ANAL-03
**Success Criteria** (what must be TRUE):
  1. O gráfico de consumo mensal mostra dados de 3+ anos quando existentes, com anos distinguíveis visualmente
  2. O utilizador pode seleccionar dois anos e ver o mesmo mês comparado (consumo kWh e custo €) lado a lado
  3. Um painel de resumo anual mostra custo total e consumo total por ano para o local seleccionado
**Plans**: TBD
**UI hint**: yes

### Phase 12: Deploy Unraid + Homepage + Tailscale
**Goal**: A aplicação está em produção no Unraid, acessível via Homepage tile e via Tailscale fora da rede local, com deploy documentado via rsync/SSH.
**Depends on**: Phase 11
**Requirements**: INFRA-02, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. A aplicação está acessível em http://192.168.122.110:8090/hobbies/casa/energia/ a partir da rede local
  2. Um tile "Energia" aparece no Homepage do Unraid e abre a aplicação ao clicar
  3. A aplicação está acessível via Tailscale fora da rede local (URL Tailscale funcional)
  4. O comando de deploy (rsync/SSH) está documentado e um deploy a partir do Mac actualiza a aplicação em produção
**Plans**: TBD
**UI hint**: no

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Unblock & Validate | v1.0 | 1/2 | In progress | — |
| 2. Resilience | v1.0 | 2/2 | Complete | 2026-03-29 |
| 3. Multi-Location Refactor | v1.0 | 3/3 | Complete | 2026-03-29 |
| 4. Web Dashboard MVP | v1.0 | 3/3 | Complete | 2026-03-30 |
| 5. Docker + SQLite Foundation | v2.0 | 3/3 | Complete   | 2026-03-30 |
| 6. UI Design (ui-phase) | v2.0 | 0/? | Not started | — |
| 7. Upload XLSX + Ingestão | v2.0 | 3/3 | Complete   | 2026-03-30 |
| 8. Upload PDF + Extracção | v2.0 | 2/2 | Complete   | 2026-03-31 |
| 9. Dashboard UI | v2.0 | 0/2 | Not started | — |
| 10. Cache + Comparação | v2.0 | 0/? | Not started | — |
| 11. Análise Multi-ano | v2.0 | 0/? | Not started | — |
| 12. Deploy Unraid + Homepage | v2.0 | 0/? | Not started | — |

---

## Coverage

### v1.0 (Phases 1-4)

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 1 | Pending |
| FIX-02 | Phase 1 | Pending |
| FIX-03 | Phase 1 | Pending |
| FIX-04 | Phase 1 | Pending |
| VAL-01 | Phase 1 | Pending |
| VAL-02 | Phase 1 | Pending |
| RES-01 | Phase 2 | Complete |
| RES-02 | Phase 2 | Complete |
| RES-03 | Phase 2 | Complete |
| MULTI-01 | Phase 3 | Complete |
| MULTI-02 | Phase 3 | Complete |
| MULTI-03 | Phase 3 | Complete |
| MULTI-04 | Phase 3 | Complete |
| MULTI-05 | Phase 3 | Complete |
| MULTI-06 | Phase 3 | Complete |
| DASH-01 | Phase 4 | Complete |
| DASH-02 | Phase 4 | Complete |
| DASH-03 | Phase 4 | Complete |
| DASH-04 | Phase 4 | Complete |
| DASH-05 | Phase 4 | Complete |
| DASH-06 | Phase 4 | Complete |

### v2.0 (Phases 5-12)

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 5 | Pending |
| INFRA-02 | Phase 12 | Pending |
| INFRA-03 | Phase 5 | Pending |
| DADOS-01 | Phase 5 | Pending |
| DADOS-02 | Phase 5 | Pending |
| DADOS-03 | Phase 5 | Pending |
| DADOS-04 | Phase 5 | Pending |
| UI-01 | Phase 6 | Pending |
| UPLD-01 | Phase 7 | Pending |
| UPLD-02 | Phase 7 | Pending |
| UPLD-05 | Phase 7 | Pending |
| CONF-01 | Phase 7 | Pending |
| CONF-02 | Phase 7 | Pending |
| COMP-01 | Phase 7 | Pending |
| COMP-02 | Phase 7 | Pending |
| UPLD-03 | Phase 8 | Pending |
| UPLD-04 | Phase 8 | Pending |
| UI-02 | Phase 9 | Pending |
| UI-03 | Phase 9 | Pending |
| UI-04 | Phase 9 | Pending |
| UI-05 | Phase 9 | Pending |
| COMP-03 | Phase 10 | Pending |
| COMP-04 | Phase 10 | Pending |
| ANAL-01 | Phase 11 | Pending |
| ANAL-02 | Phase 11 | Pending |
| ANAL-03 | Phase 11 | Pending |
| INFRA-04 | Phase 12 | Pending |
| INFRA-05 | Phase 12 | Pending |

**Total v2.0:** 28 requisitos mapeados em 8 fases. Sem orphans.

---

*Roadmap v1.0 criado: 2026-03-28*
*Roadmap v2.0 criado: 2026-03-30*
