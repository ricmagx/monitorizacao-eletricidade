---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: sistema-integrado
current_phase: 5
status: Ready to plan
stopped_at: Roadmap v2.0 criado — Phase 5 pronta para planning
last_updated: "2026-03-30"
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
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
Plan: 0 of ? in Phase 5
Status: Ready to plan
Last activity: 2026-03-30 — Roadmap v2.0 criado (8 fases, 28 requisitos mapeados)

Progress v2.0: [░░░░░░░░░░] 0%

## Performance Metrics

**v1.0 velocity:**
- Total plans completed: 9 (de 10 planeados — Phase 1 plano 2 pendente)
- Phases complete: 3/4 (Phase 2, 3, 4 completas)

**v2.0:**
- Plans completed: 0
- Phases complete: 0/8

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

Last session: 2026-03-30
Stopped at: Roadmap v2.0 definido, 28 requisitos mapeados em 8 fases (05-12)
Resume file: None
