# Project State

**Last updated:** 2026-03-28
**Current phase:** Not started (ready for Phase 1)

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-28)

**Core value:** Com o perfil mensal real de cada local, saber qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual após a configuração inicial.
**Current focus:** Phase 1 — Unblock & Validate End-to-End

## Milestone

**Pipeline funcional multi-local com dashboard**
Phases: 1 → 2 → 3 → 4

## Phase Status

| Phase | Name | Status | Plans |
|-------|------|--------|-------|
| 1 | Unblock & Validate End-to-End | ○ Pending | 0/0 |
| 2 | Resilience | ○ Pending | 0/0 |
| 3 | Multi-Location Refactor | ○ Pending | 0/0 |
| 4 | Web Dashboard MVP | ○ Pending | 0/0 |

## Critical Blockers (confirmed by research)

- launchd watcher quebrado — TCC permission error (Python path errado no plist)
- Sessão E-REDES expirada — JWT exp em `state/eredes_storage_state.json`
- `.gitignore` não exclui ficheiros de sessão/credenciais

## Notes

- Projecto brownfield: pipeline backend escrito mas nunca executado end-to-end
- Download E-REDES: `external_firefox` é o design final (headless inviável por reCAPTCHA)
- Multi-local: loop sequencial no orquestrador (sessão Playwright partilhada)
- 3 módulos já location-agnostic: `eredes_to_monthly_csv`, `energy_compare`, `tiagofelicia_compare`
