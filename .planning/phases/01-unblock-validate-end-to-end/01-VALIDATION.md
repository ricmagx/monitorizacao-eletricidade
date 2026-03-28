---
phase: 1
slug: unblock-validate-end-to-end
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (já instalado via Homebrew Python) |
| **Config file** | none — testes inline via CLI |
| **Quick run command** | `python3 pipeline/eredes_parser.py --input-xlsx data/raw/eredes/<ficheiro>.xlsx` |
| **Full suite command** | `python3 pipeline/eredes_parser.py --input-xlsx data/raw/eredes/*.xlsx && python3 pipeline/run_pipeline.py` |
| **Estimated runtime** | ~30 segundos |

---

## Sampling Rate

- **After every task commit:** Run quick parser check no XLSX mais recente
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-FIX-02 | 01 | 1 | FIX-02 | manual | `git status \| grep eredes_storage_state` | ✅ | ⬜ pending |
| 1-FIX-01 | 01 | 1 | FIX-01 | manual | `grep python .planning/phases/01-unblock-validate-end-to-end/../../../com.ricmag.eredes_watcher.plist 2>/dev/null` | ✅ | ⬜ pending |
| 1-FIX-04 | 01 | 1 | FIX-04 | automated | `pip install -r requirements.txt 2>&1 \| tail -1` | ❌ W0 | ⬜ pending |
| 1-FIX-03 | 01 | 2 | FIX-03 | manual | `python3 eredes_bootstrap_session.py` | ✅ | ⬜ pending |
| 1-VAL-02 | 01 | 2 | VAL-02 | automated | `python3 pipeline/eredes_parser.py --input-xlsx data/raw/eredes/` | ✅ | ⬜ pending |
| 1-VAL-01 | 01 | 2 | VAL-01 | automated | `python3 pipeline/run_pipeline.py && ls data/reports/relatorio_*.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `requirements.txt` — criar com as 4 dependências confirmadas (FIX-04)

*Restante infraestrutura já existe no projecto.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| launchd TCC sem erros após fix | FIX-01 | Requer reiniciar o plist e observar o log em tempo real | `launchctl unload ~/Library/LaunchAgents/com.ricmag.eredes_watcher.plist && launchctl load ... && tail -f state/launchd.process.stderr.log` |
| Full Disk Access em System Settings | FIX-01 | Não automatizável — requer acção do utilizador em macOS UI | Verificar System Settings > Privacy & Security > Full Disk Access |
| Bootstrap sessão E-REDES | FIX-03 | Requer login interactivo (2FA / captcha possível) | `python3 eredes_bootstrap_session.py` e verificar `state/eredes_storage_state.json` actualizado |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
