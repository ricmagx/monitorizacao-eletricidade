---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Sistema Integrado
current_phase: 09
status: executing
stopped_at: Completed 09-01-PLAN.md
last_updated: "2026-03-31T01:30:16.311Z"
last_activity: 2026-03-31
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 11
  completed_plans: 10
---

# Project State

**Last updated:** 2026-03-30
**Current phase:** 09

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Com o perfil mensal real de cada local, saber qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual além do upload mensal.
**Current focus:** Phase 09 — dashboard-ui

## Current Position

Phase: 09 (dashboard-ui) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-03-31

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
| Phase 07 P01 | 234 | 3 tasks | 11 files |
| Phase 07 P02 | 5 | 5 tasks | 11 files |
| Phase 08 P02 | 231 | 2 tasks | 4 files |
| Phase 09 P01 | 20 | 3 tasks | 6 files |

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

### Decisões Phase 07

- Seed de locais idempotente: count(*) antes de inserir para segurança em restarts de container
- UniqueConstraint em comparacoes adicionado na migration 002 para compatibilidade com DB existentes
- parse_xlsx_to_dict() extraida como função pública reutilizável; convert_xlsx_to_monthly_csv() mantida como wrapper backward-compatible
- ingerir_xlsx usa on_conflict_do_nothing (dialecto SQLite) para idempotência de ingestão
- Background task tiagofelicia usa BackgroundTasks sincrono em thread pool — nao async def
- load_locations() engine=None opcional para backward compatibility — merge SQLite transparente
- Locais sem pipeline retornam dados vazios em _load_location_data — Phase 9 migrara para SQLite

### Decisoes Phase 09 Plan 01

- SQLite-first com fallback CSV: tentar SQLite primeiro; se vazio e local tem pipeline, usar CSV/JSON. Preserva retrocompatibilidade total.
- StaticPool para engines SQLite in-memory em testes: garante todas as conexoes partilham a mesma BD (sem StaticPool, cada nova conexao cria BD vazia).
- Context manager TestClient para override pos-lifespan: lifespan sobrescreve db_engine; usar with TestClient() e sobrepor apos __enter__.

### Bloqueadores/Notas

- Phase 6 é design-only (ui-phase) — não produz código, produz UI-SPEC.md
- Phase 9 depende de UI-SPEC de Phase 6 — não implementar frontend antes disso

## Session Continuity

Last session: 2026-03-31T01:30:16.298Z
Stopped at: Completed 09-01-PLAN.md
Resume file: None
