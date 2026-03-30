---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: sistema-integrado
current_phase: not-started
status: Defining requirements
stopped_at: Milestone v2.0 iniciado — a definir requirements
last_updated: "2026-03-30"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

**Last updated:** 2026-03-30
**Current phase:** Not started (defining requirements)

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-30)

**Core value:** Com o perfil mensal real de cada local, saber qual seria o comercializador mais barato e quando compensa mudar — sem esforço manual além do upload mensal.
**Current focus:** Milestone v2.0 — Sistema Integrado

## Milestone

**v2.0 — Sistema Integrado**
Docker (Unraid) + Upload XLSX/PDF + SQLite multi-ano + UI redesenhado

## Phase Status

*(A definir após roadmap)*

## Accumulated Context

### Decisões v1.0 que se mantêm
- Homebrew Python path confirmado: `/usr/local/opt/python@3.11/libexec/bin/python3`
- `data/raw/`, `data/processed/`, `data/reports/` excluídos do git (CPE exposto)
- Multi-local: loop sequencial no orquestrador (sessão Playwright partilhada)
- 3 módulos já location-agnostic: `eredes_to_monthly_csv`, `energy_compare`, `tiagofelicia_compare`
- SAVING_THRESHOLD_EUR = 50 como limiar anual para banner de recomendação

### Decisões v2.0 (novas)
- Plataforma: Docker/Linux — eliminar launchd, osascript, open -a Firefox
- Dados: SQLite em vez de ficheiros planos CSV/JSON
- Upload: XLSX manual via browser (sem download automático do portal E-REDES)
- PDF: pdfplumber para extracção (Meo Energia + Endesa — texto estruturado)
- Comparação: tiagofelicia.pt primário + cache SQLite como fallback
- Deploy: Unraid nginx :8090, homepage :3000, Tailscale activo
- UI: redesenhado via ui-phase antes de qualquer frontend

### Infra Unraid
- Homepage: `http://192.168.122.110:3000`
- Nginx: `http://192.168.122.110:8090`
- Deploy script: `/Users/ricmag/Documents/AI/3-hobbies/Casa/deploy-dashboard.sh energia`
- Target energia: `/hobbies/casa/energia/`

### Locais conhecidos
- Casa: CPE PT0002000084968079SX, Meo Energia, bi-horário, 10,35 kVA
- Apartamento: CPE PT000200003982208 2NT, Endesa, bi-horário, 3,45 kVA

## Notes

- v1.0 entregou pipeline backend + dashboard MVP (4 fases, 10 planos)
- Dashboard v1 reconhecidamente fraca — redesign obrigatório em v2
- FIX-03 (re-bootstrap sessão E-REDES) torna-se irrelevante em v2 (upload manual)
- pdfplumber consegue extrair texto dos dois formatos de fatura sem IA
