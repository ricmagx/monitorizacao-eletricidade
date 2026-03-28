# Requirements: Monitorização de Eletricidade — Multi-Local

**Defined:** 2026-03-28
**Core Value:** Com o perfil mensal real de cada local, saber hoje qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual após a configuração inicial.

## v1 Requirements

### Correções Críticas (Bloqueadores)

- [x] **FIX-01**: Corrigir caminho Python no plist launchd (TCC permission error — watcher quebrado, 21 erros confirmados no log)
- [x] **FIX-02**: Corrigir `.gitignore` para excluir `state/eredes_storage_state.json` e outros ficheiros com credenciais/sessões
- [ ] **FIX-03**: Re-fazer bootstrap da sessão E-REDES (JWT expirado em `state/eredes_storage_state.json`)
- [x] **FIX-04**: Criar `requirements.txt` com todas as dependências do projecto

### Validação End-to-End

- [ ] **VAL-01**: Correr pipeline completo com XLSX real (um local) e verificar relatório gerado
- [ ] **VAL-02**: Validar parser XLSX contra os ficheiros E-REDES disponíveis (incluindo variação de formato entre anos)

### Resiliência

- [ ] **RES-01**: Implementar fallback de `tiagofelicia_compare.py` para catálogo local quando o site estiver indisponível ou devolver erro
- [ ] **RES-02**: Adicionar verificação de sanidade ao parser XLSX (limites plausíveis de consumo, colunas esperadas)
- [ ] **RES-03**: Tratar nome de fornecedor sem correspondência em `tiagofelicia_compare.py` (actualmente retorna `None` em silêncio)

### Multi-Local

- [ ] **MULTI-01**: Estender `config/system.json` com schema `"locations": [...]` (id, nome, CPE, potência, fornecedor actual, caminhos de dados)
- [ ] **MULTI-02**: Migrar estrutura de directórios para nested (`data/casa/`, `data/apartamento/`, `state/casa/`, `state/apartamento/`)
- [ ] **MULTI-03**: Refactorizar `monthly_workflow.py` para iterar sobre locais (loop sequencial — sessão Playwright partilhada)
- [ ] **MULTI-04**: Refactorizar `process_latest_download.py` para fazer routing de XLSX por CPE no nome do ficheiro
- [ ] **MULTI-05**: Refactorizar `reminder_job.py` para enviar notificação por local
- [ ] **MULTI-06**: Estender `eredes_download.py` para seleccionar CPE correcto no portal (modo `external_firefox` — o utilizador selecciona manualmente)

### Dashboard Web

- [ ] **DASH-01**: Setup FastAPI + Jinja2 + HTMX (ficheiro estático local) + Chart.js (ficheiro estático local) — sem build step
- [ ] **DASH-02**: Gráfico de consumo mensal (kWh, barras empilhadas vazio/fora_vazio) ao longo do tempo, por local
- [ ] **DASH-03**: Gráfico de custo €/mês: custo real da factura + estimativa calculada pelo contrato — sobrepostos no mesmo eixo temporal
- [ ] **DASH-04**: Modelo de dados para custo real da factura: campo de entrada manual por mês (CSV ou formulário na dashboard)
- [ ] **DASH-05**: Tabela de ranking de comercializadores por custo anual estimado (recomendação mensal actual)
- [ ] **DASH-06**: Recomendação de mudança com poupança estimada e indicador de confiança
- [ ] **DASH-07**: Vista histórica: simulação retroactiva de quem teria sido o mais barato em cada mês passado
- [ ] **DASH-08**: Comparação com período homólogo (este mês vs mesmo mês do ano anterior) para consumo e custo
- [ ] **DASH-09**: Indicador de frescura dos dados (data do último relatório gerado)

## v2 Requirements

### Comparação Multi-Local

- **COMP-01**: Vista lado-a-lado dos dois locais (consumo e custo) — requer MULTI-06 validado end-to-end
- **COMP-02**: Sumário consolidado: custo total dos dois locais por mês

### Integrações

- **INT-01**: Sensores Home Assistant (melhor fornecedor, poupança potencial) via MQTT ou REST sensor
- **INT-02**: Second comparison engine via `simulador.erse.pt` como alternativa ao tiagofelicia.pt
- **INT-03**: Leitura de PDF de factura do fornecedor para extracção automática do custo real mensal
- **INT-04**: Ligação ao portal do fornecedor para obter preços/facturas actualizados automaticamente

### Qualidade

- **QUAL-01**: Testes automatizados para o parser XLSX e motor de comparação local
- **QUAL-02**: Logging estruturado (substituir `print()` por `logging` com níveis)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Download headless E-REDES | reCAPTCHA + JWT de curta duração tornam headless inviável; `external_firefox` é o design final |
| Mudança automática de fornecedor | Risco contratual; recomendação conservadora é suficiente |
| Captura ao minuto (Shelly) | Agregados mensais chegam para decisão tarifária |
| Previsão de consumo / ML | Fora do âmbito do comparador tarifário pessoal |
| Notificações push / email | Anti-feature para ferramenta pessoal; notificação macOS é suficiente |
| Autenticação na dashboard | Ferramenta local, utilizador único |
| Deploy cloud | macOS-only por design; Mac Mini M4 Pro é o servidor |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 1 | Complete |
| FIX-02 | Phase 1 | Complete |
| FIX-03 | Phase 1 | Pending |
| FIX-04 | Phase 1 | Complete |
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
| DASH-07 | Phase 4 | Pending |
| DASH-08 | Phase 4 | Pending |
| DASH-09 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after initialization*
