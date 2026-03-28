---
phase: 01-unblock-validate-end-to-end
plan: 01
subsystem: infra
tags: [launchd, python, gitignore, requirements, macos, tcc]

# Dependency graph
requires: []
provides:
  - .gitignore excluindo credenciais E-REDES, dados raw/processed e logs launchd
  - requirements.txt com 4 dependencias pinadas (playwright, openpyxl, tf-playwright-stealth, requests)
  - Ambos os plists launchd com path absoluto Homebrew Python 3.11
  - Agents launchd recarregados e activos
affects: [02-resilience, 03-multi-location, 04-web-dashboard]

# Tech tracking
tech-stack:
  added: [playwright==1.58.0, openpyxl==3.1.5, tf-playwright-stealth==1.2.0, requests==2.32.5]
  patterns: [launchd-absolute-python-path, gitignore-credentials-exclusion]

key-files:
  created:
    - .gitignore
    - requirements.txt
  modified:
    - launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist
    - launchd/com.ricmag.monitorizacao-eletricidade.plist

key-decisions:
  - "Path Python nos plists: /usr/local/opt/python@3.11/libexec/bin/python3 (Homebrew, nao Command Line Tools)"
  - "data/raw/, data/processed/ e data/reports/ excluidos do git (dados com CPE exposto e ficheiros gerados)"

patterns-established:
  - "Plists launchd devem sempre usar path absoluto do interpretador Python — nunca python3 bare"
  - "Reload launchd: unload + cp para ~/Library/LaunchAgents/ + load"

requirements-completed: [FIX-01, FIX-02, FIX-04]

# Metrics
duration: 1min
completed: 2026-03-28
---

# Phase 01 Plan 01: Unblock Config Blockers Summary

**.gitignore e requirements.txt criados, path Python corrigido em ambos os plists launchd com Homebrew Python 3.11 e agents recarregados**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-28T23:03:39Z
- **Completed:** 2026-03-28T23:04:36Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `.gitignore` criado com exclusao de credenciais E-REDES (`state/eredes_storage_state.json`, `state/eredes_bootstrap_context.json`), dados raw/processed/reports e logs launchd — ficheiros sensiveis ja nao aparecem em `git status`
- `requirements.txt` criado com 4 dependencias pinadas: `playwright==1.58.0`, `openpyxl==3.1.5`, `tf-playwright-stealth==1.2.0`, `requests==2.32.5`
- Ambos os plists launchd (`watcher` e `reminder`) corrigidos de `python3` bare para `/usr/local/opt/python@3.11/libexec/bin/python3` (Homebrew), copiados para `~/Library/LaunchAgents/` e agents recarregados com sucesso

## Task Commits

1. **Task 1: Criar .gitignore e requirements.txt** - `bc1ecc9` (chore)
2. **Task 2: Corrigir path Python nos plists launchd** - `5b690c2` (fix)

**Plan metadata:** (docs commit — criado a seguir)

## Files Created/Modified

- `.gitignore` — Exclui credenciais, dados gerados e logs do controlo de versao
- `requirements.txt` — Declara 4 dependencias de producao com versoes fixas
- `launchd/com.ricmag.monitorizacao-eletricidade.process-latest.plist` — Watcher ~/Downloads com Python path corrigido
- `launchd/com.ricmag.monitorizacao-eletricidade.plist` — Reminder dia 1 com Python path corrigido

## Decisions Made

- Homebrew Python (`/usr/local/opt/python@3.11/libexec/bin/python3`) escolhido para os plists — e o path confirmado na research como `which python3` quando Homebrew esta activo, e o mesmo Python que ja correu o pipeline com sucesso a 2026-03-26
- `data/raw/`, `data/processed/` e `data/reports/` excluidos inteiramente do git — contem CPE do imóvel (identificador unico do contador) e ficheiros gerados pelo pipeline que nao devem ser versionados

## Deviations from Plan

None - plano executado exactamente como escrito.

## Issues Encountered

None.

## User Setup Required

**Nota sobre TCC (Full Disk Access):** Se apos o fix do path Python o watcher launchd continuar a produzir `[Errno 1] Operation not permitted` nos logs, sera necessario conceder Full Disk Access ao binario Homebrew Python em Definicoes do Sistema > Privacidade e Seguranca > Acesso Total ao Disco > adicionar `/usr/local/opt/python@3.11/libexec/bin/python3`. Este passo nao e automatizavel. Ver `.planning/phases/01-unblock-validate-end-to-end/01-RESEARCH.md` (Pitfall 6) para detalhes.

## Next Phase Readiness

- Proxima tarefa desta fase: FIX-03 (re-bootstrap da sessao E-REDES — JWT expirado desde 2026-03-22) — requer intervencao manual do utilizador
- Apos FIX-03: VAL-01 e VAL-02 (validacao end-to-end com XLSX reais)
- Watcher launchd activo e pronto para testar com trigger manual em ~/Downloads

---
*Phase: 01-unblock-validate-end-to-end*
*Completed: 2026-03-28*
