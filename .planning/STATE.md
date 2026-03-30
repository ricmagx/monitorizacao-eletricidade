---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Sistema Integrado
current_phase: Phase 5 — Docker + SQLite Foundation
status: executing
stopped_at: Completed 05-03 (FastAPI+DB integration + Docker smoke test verified on Unraid)
last_updated: "2026-03-30T12:24:48.226Z"
last_activity: 2026-03-30
progress:
  total_phases: 8
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
---

# Project State

**Last updated:** 2026-03-30
**Current phase:** Phase 5 — Docker + SQLite Foundation

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Com o perfil mensal real de cada local, saber qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual além do upload mensal.
**Current focus:** Milestone v2.0 — Sistema Integrado (Phase 5 of 8)

## Current Position

Phase: 5 of 12 total (1 of 8 in v2.0)
Plan: 3 of 3 in Phase 5 (05-01 + 05-02 + 05-03 complete — Phase 5 DONE)
Status: Phase 5 Complete
Last activity: 2026-03-30 — Plan 05-03 complete (FastAPI+DB integration + Docker smoke test on Unraid)

Progress v2.0: [██████████] 100% (Phase 5)

## Performance Metrics

**v1.0 velocity:**

- Total plans completed: 9 (de 10 planeados — Phase 1 plano 2 pendente)
- Phases complete: 3/4 (Phase 2, 3, 4 completas)

**v2.0:**

- Plans completed: 3 (05-01, 05-02, 05-03)
- Phases complete: 1/8 (Phase 5 complete)

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 05 | 01 | 4min | 2 | 11 |
| 05 | 02 | 144s | 2 | 11 |
| 05 | 03 | 45min | 2 | 2 |

*Updated after each plan completion*

## Accumulated Context

### Decisões v1.0 que se mantêm em v2.0

- Idempotência: evita reprocessar o mesmo XLSX
- SAVING_THRESHOLD_EUR = 50 como limiar anual para banner de recomendação
- Loop sequencial (sessão Playwright partilhada)
- 3 módulos já location-agnostic: eredes_to_monthly_csv, energy_compare, tiagofelicia_compare

### Decisões v2.0

- Plataforma: Docker/Linux — eliminar launchd, osascript, open -a Firefox
- Dados: SQLite em vez de ficheiros planos CSV/JSON
- Upload: XLSX manual via browser (sem download automático E-REDES)
- PDF: pdfplumber (Meo Energia + Endesa — texto estruturado, sem IA)
- Comparação: tiagofelicia.pt primário + cache SQLite como fallback
- Deploy: Unraid nginx :8090, homepage :3000, Tailscale activo
- UI: redesenhado via ui-phase (Phase 6) antes de qualquer frontend
- requirements-docker.txt exclui playwright — upload manual substituiu E-REDES download, poupa ~500MB
- osascript substituído por logger.info com markers TODO Phase 7 — ficheiros backend preservados para reutilização
- config/system.json: download_mode=disabled, watcher.enabled=false — Docker não tem filesystem watcher local
- metadata.create_all() em lifespan como safety net para dev local — Alembic é o caminho principal em Docker
- APP_ROOT env var para compatibilidade Docker — default é o path calculado, retrocompatível
- Smoke test em Unraid (ambiente alvo) em vez de Mac local — Docker não disponível localmente por design

### Infra Unraid

- Homepage: http://192.168.122.110:3000
- Nginx: http://192.168.122.110:8090
- Target energia: /hobbies/casa/energia/
- Deploy: rsync/SSH → unraid:/mnt/user/appdata/nginx/www/

### Locais

- Casa: CPE PT0002000084968079SX, Meo Energia, bi-horário, 10,35 kVA
- Apartamento: CPE PT000200003982208 2NT, Endesa, bi-horário, 3,45 kVA

### Bloqueadores/Notas

- Phase 6 é design-only (ui-phase) — não produz código, produz UI-SPEC.md
- Phase 9 depende de UI-SPEC de Phase 6 — não implementar frontend antes disso

## Session Continuity

Last session: 2026-03-30T12:24:48.215Z
Stopped at: Completed 05-03 (FastAPI+DB integration + Docker smoke test verified on Unraid)
Resume file: None
