---
phase: 8
slug: upload-pdf-extrac-o-de-faturas
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini / pyproject.toml |
| **Quick run command** | `pytest tests/test_extrator_pdf.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_extrator_pdf.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 0 | UPLD-03 | infra | `grep pdfplumber requirements-docker.txt` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 0 | UPLD-03 | stub | `pytest tests/test_extrator_pdf.py --collect-only` | ❌ W0 | ⬜ pending |
| 8-02-01 | 02 | 1 | UPLD-03 | unit | `pytest tests/test_extrator_pdf.py::test_meo_extractor -v` | ❌ W0 | ⬜ pending |
| 8-02-02 | 02 | 1 | UPLD-04 | unit | `pytest tests/test_extrator_pdf.py::test_endesa_extractor -v` | ❌ W0 | ⬜ pending |
| 8-02-03 | 02 | 1 | UPLD-03 | unit | `pytest tests/test_extrator_pdf.py::test_unknown_format -v` | ❌ W0 | ⬜ pending |
| 8-03-01 | 03 | 1 | UPLD-03 | integration | `pytest tests/test_upload_endpoint.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_extrator_pdf.py` — stubs para UPLD-03, UPLD-04 (Meo, Endesa, formato desconhecido)
- [ ] `tests/test_upload_endpoint.py` — stubs para endpoint de upload
- [ ] `pdfplumber==0.11.7` adicionado a `requirements-docker.txt`

*Infraestrutura pytest existente cobre fixtures partilhadas.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF Meo Energia real extrai total correcto | UPLD-03 | Sem PDF real no repositório | Fazer upload de fatura Meo via browser; confirmar total € e período no dashboard |
| PDF Endesa real extrai electricidade (sem gás) | UPLD-04 | Sem PDF real no repositório | Fazer upload de fatura Endesa via browser; confirmar que só electricidade é importada |
| CPE com espaço detecta local correcto | UPLD-03 | Dependente de CPE real | Verificar com fatura cujo CPE tenha espaço (ex: PT000200003982208 2NT) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
