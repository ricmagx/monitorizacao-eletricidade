---
phase: 10
slug: cache-tiagofelicia-pt-integra-o-compara-o
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini / pyproject.toml |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | COMP-03 | unit | `pytest tests/test_web_data_loader.py -x -q` | ✅ | ⬜ pending |
| 10-01-02 | 01 | 1 | COMP-03 | unit | `pytest tests/test_web_data_loader.py -x -q` | ✅ | ⬜ pending |
| 10-02-01 | 02 | 2 | COMP-04 | unit | `pytest tests/test_web_dashboard.py -x -q` | ✅ | ⬜ pending |
| 10-02-02 | 02 | 2 | COMP-04 | integration | `pytest tests/ -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — test files já existem.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Badge visual frescos vs cache | COMP-04 | Verificação visual do UI | Abrir dashboard com site disponível → confirmar badge verde; simular site em baixo → confirmar badge laranja/amarelo |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
