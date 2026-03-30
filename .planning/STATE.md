---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 04
status: Milestone complete
stopped_at: Completed 04-03-PLAN.md (ranking de fornecedores + LaunchAgent plist)
last_updated: "2026-03-30T01:02:57.973Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 10
  completed_plans: 10
---

# Project State

**Last updated:** 2026-03-28
**Current phase:** 04

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Com o perfil mensal real de cada local, saber qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual após a configuração inicial.
**Current focus:** Phase 04 — web-dashboard-mvp

## Milestone

**Pipeline funcional multi-local com dashboard**
Phases: 1 → 2 → 3 → 4

## Phase Status

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Unblock & Validate End-to-End | ◑ In Progress | 1/2 |
| 2 | Resilience | ○ Pending | 0/0 |
| 3 | Multi-Location Refactor | ○ Pending | 0/0 |
| 4 | Web Dashboard MVP | ○ Pending | 0/0 |

## Critical Blockers (confirmed by research)

- ~~launchd watcher quebrado — TCC permission error (Python path errado no plist)~~ RESOLVIDO (01-01)
- Sessão E-REDES expirada — JWT exp em `state/eredes_storage_state.json` (FIX-03 — requer acção manual)
- ~~`.gitignore` não exclui ficheiros de sessão/credenciais~~ RESOLVIDO (01-01)

## Decisions

- Homebrew Python (`/usr/local/opt/python@3.11/libexec/bin/python3`) usado nos plists launchd — confirmado como path correcto que já correu o pipeline com sucesso (2026-03-26)
- `data/raw/`, `data/processed/` e `data/reports/` excluidos do git — CPE do imóvel exposto e ficheiros gerados pelo pipeline
- [Phase 02-resilience]: render_report refactorizada com dual-path (tiagofelicia vs local_catalog) porque estruturas de analise sao incompativeis
- [Phase 02-resilience]: Bounds check inserido antes de output_path.parent.mkdir para garantir validate-before-write no parser XLSX (RES-02)
- [Phase 03]: location dict passed as explicit parameter to run_workflow — avoids config root access for contract/pipeline data
- [Phase 03]: process_latest_download routing fully automatic by CPE in filename — no --location flag needed
- [Phase 03]: Launchd plists require no content changes — reminder_job now handles multi-location internally via config['locations'] iteration
- [Phase 04-web-dashboard-mvp]: FastAPI upgradeado para 0.135.2 para compatibilidade com Starlette 1.0.0; TemplateResponse usa API request= kwarg
- [Phase 04-web-dashboard-mvp]: app.state.config_path permite override em testes sem monkeypatch complexo — padrao para todos os planos da fase 04
- [Phase 04-web-dashboard-mvp]: custo_section.html como wrapper unico para swap HTMX — permite actualizar grafico + formulario num unico hx-swap
- [Phase 04-web-dashboard-mvp]: custos_reais.json em data/{local_id}/ — input do utilizador, nao estado do pipeline; None para meses sem custo real serializa para null (Chart.js gap)
- [Phase 04]: SAVING_THRESHOLD_EUR = 50 como limiar anual — banner so aparece quando poupanca > 50 EUR/ano
- [Phase 04]: LaunchAgent nao instalado automaticamente — utilizador instala manualmente com cp + launchctl load

## Notes

- Projecto brownfield: pipeline backend escrito mas nunca executado end-to-end
- Download E-REDES: `external_firefox` é o design final (headless inviável por reCAPTCHA)
- Multi-local: loop sequencial no orquestrador (sessão Playwright partilhada)
- 3 módulos já location-agnostic: `eredes_to_monthly_csv`, `energy_compare`, `tiagofelicia_compare`
- Plists launchd corrigidos e agents activos — watcher pronto para testar com trigger manual em ~/Downloads
- Próximo passo: FIX-03 (re-bootstrap sessão E-REDES) requer acção manual do utilizador

## Last session

**Stopped at:** Completed 04-03-PLAN.md (ranking de fornecedores + LaunchAgent plist)
**Session date:** 2026-03-28T23:05:00Z
