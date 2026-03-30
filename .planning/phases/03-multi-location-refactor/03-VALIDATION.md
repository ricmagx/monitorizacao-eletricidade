---
phase: 3
slug: multi-location-refactor
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.4.3 |
| **Config file** | `pytest.ini` (raiz do projecto) |
| **Quick run command** | `cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && python3 -m pytest tests/ -x -q` |
| **Full suite command** | `cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && python3 -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/ -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-W0-01 | 01 | 0 | MULTI-01, MULTI-02 | unit | `pytest tests/test_multi_location_config.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-02 | 01 | 0 | MULTI-03 | unit | `pytest tests/test_multi_workflow.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-03 | 01 | 0 | MULTI-04 | unit | `pytest tests/test_cpe_routing.py -x` | ❌ W0 | ⬜ pending |
| 3-W0-04 | 01 | 0 | MULTI-05 | unit | `pytest tests/test_multi_reminder.py -x` | ❌ W0 | ⬜ pending |
| 3-01-01 | 01 | 1 | MULTI-01 | unit | `pytest tests/test_multi_location_config.py -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | MULTI-02 | unit | `pytest tests/test_multi_location_config.py::test_directory_structure -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | MULTI-03 | unit | `pytest tests/test_multi_workflow.py -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 2 | MULTI-04 | unit | `pytest tests/test_cpe_routing.py -x` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 3 | MULTI-05 | unit | `pytest tests/test_multi_reminder.py -x` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 4 | MULTI-06 | unit | `pytest tests/test_multi_workflow.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_multi_location_config.py` — stubs para MULTI-01, MULTI-02
- [ ] `tests/test_multi_workflow.py` — stubs para MULTI-03, MULTI-06
- [ ] `tests/test_cpe_routing.py` — stubs para MULTI-04
- [ ] `tests/test_multi_reminder.py` — stubs para MULTI-05
- [ ] `tests/conftest.py` — fixture `multi_location_config` com dois locais (casa + apartamento mock) em `tmp_path`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Confirmar CPE real do apartamento no portal E-REDES | MULTI-01, MULTI-06 | Requer login interactivo ao portal E-REDES | Aceder ao portal E-REDES, ver contratos/CPEs associados, substituir placeholder `PT000200XXXXXXXXXX` em `config/system.json` |
| Selector de CPE no portal (modo external_firefox) | MULTI-06 | Depende do comportamento real da UI do portal E-REDES | Correr `eredes_download.py` com dois CPEs; verificar se o portal pede selecção ou redireciona automaticamente; time-box 30 min |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
