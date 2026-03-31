# Requirements: Monitorização de Eletricidade

**Defined:** 2026-03-30
**Core Value:** Com o perfil mensal real de cada local, saber qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual além do upload mensal.

## v2 Requirements

### Infraestrutura (Docker/Unraid)

- [x] **INFRA-01**: Sistema corre como container Docker no Unraid
- [ ] **INFRA-02**: App exposta via reverse proxy nginx em `/hobbies/casa/energia/`
- [x] **INFRA-03**: Dados persistem em volume Docker (SQLite)
- [ ] **INFRA-04**: App aparece como tile no Homepage do Unraid
- [ ] **INFRA-05**: App acessível via Tailscale fora da rede local

### Dados (SQLite)

- [x] **DADOS-01**: Histórico de consumo mensal por local em SQLite (vazio/fora_vazio kWh)
- [x] **DADOS-02**: Histórico de comparações tiagofelicia.pt em SQLite (por mês, por local)
- [x] **DADOS-03**: Custos reais de faturas em SQLite (por mês, por local)
- [x] **DADOS-04**: Cache de resultados tiagofelicia.pt com timestamp

### Upload e Ingestão

- [x] **UPLD-01**: Utilizador faz upload de XLSX da E-REDES via browser
- [x] **UPLD-02**: Sistema normaliza XLSX e armazena consumo em SQLite automaticamente
- [x] **UPLD-03**: Utilizador faz upload de PDF de fatura via browser
- [x] **UPLD-04**: Sistema extrai total pago e período do PDF (formatos Meo Energia + Endesa)
- [x] **UPLD-05**: Sistema detecta o local correcto via CPE presente no ficheiro

### Configuração de Locais

- [x] **CONF-01**: Utilizador pode criar e editar locais no UI (nome livre + CPE)
- [x] **CONF-02**: Utilizador pode definir fornecedor actual por local

### Comparação de Tarifários

- [x] **COMP-01**: Sistema consulta tiagofelicia.pt após cada upload de XLSX
- [x] **COMP-02**: Resultado guardado em cache SQLite com data
- [x] **COMP-03**: Dashboard usa cache quando tiagofelicia.pt está indisponível
- [x] **COMP-04**: Badge indica se dados são frescos ou do cache (com data)

### UI e Dashboard

- [ ] **UI-01**: Design definido via ui-phase antes de qualquer implementação frontend
- [x] **UI-02**: Selector de local no topo da dashboard
- [x] **UI-03**: Ranking de fornecedores com poupança potencial em €/ano
- [x] **UI-04**: Gráfico de consumo mensal (vazio/fora vazio empilhados)
- [x] **UI-05**: Gráfico de custo: estimativa do fornecedor actual vs custo real da fatura

### Análise Multi-ano

- [x] **ANAL-01**: Histórico com 3+ anos de dados visível em gráficos
- [x] **ANAL-02**: Comparação do mesmo mês em anos diferentes
- [x] **ANAL-03**: Resumo anual: custo total, consumo total por ano

## v3 Requirements (deferred)

### Notificações
- **NOTF-01**: Notificação push/email quando pipeline completa
- **NOTF-02**: Alerta quando poupança potencial ultrapassa limiar configurável

### Integrações
- **INT-01**: Integração Home Assistant (Lovelace card)
- **INT-02**: Download automático E-REDES (se portal estabilizar)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Gás | Apenas electricidade neste milestone |
| Download automático E-REDES | Frágil (portal muda, reCAPTCHA) — upload manual suficiente |
| Mudança automática de fornecedor | Risco contratual — recomendação é suficiente |
| Captura ao minuto (Shelly) | Agregados mensais chegam para decisão tarifária |
| Otimização por aparelho individual | Fora do âmbito do comparador tarifário |
| Extracção PDF via IA | pdfplumber suficiente para os dois formatos conhecidos |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 5 | Complete |
| INFRA-02 | Phase 12 | Pending |
| INFRA-03 | Phase 5 | Complete |
| INFRA-04 | Phase 12 | Pending |
| INFRA-05 | Phase 12 | Pending |
| DADOS-01 | Phase 5 | Complete |
| DADOS-02 | Phase 5 | Complete |
| DADOS-03 | Phase 5 | Complete |
| DADOS-04 | Phase 5 | Complete |
| UPLD-01 | Phase 7 | Complete |
| UPLD-02 | Phase 7 | Complete |
| UPLD-03 | Phase 8 | Complete |
| UPLD-04 | Phase 8 | Complete |
| UPLD-05 | Phase 7 | Complete |
| CONF-01 | Phase 7 | Complete |
| CONF-02 | Phase 7 | Complete |
| COMP-01 | Phase 7 | Complete |
| COMP-02 | Phase 7 | Complete |
| COMP-03 | Phase 10 | Complete |
| COMP-04 | Phase 10 | Complete |
| UI-01 | Phase 6 | Pending |
| UI-02 | Phase 9 | Complete |
| UI-03 | Phase 9 | Complete |
| UI-04 | Phase 9 | Complete |
| UI-05 | Phase 9 | Complete |
| ANAL-01 | Phase 11 | Complete |
| ANAL-02 | Phase 11 | Complete |
| ANAL-03 | Phase 11 | Complete |

**Coverage:**
- v2 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 — INFRA-02 moved from Phase 5 to Phase 12 (nginx reverse proxy belongs to deploy phase)*
