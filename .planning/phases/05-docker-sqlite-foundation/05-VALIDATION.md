---
phase: 5
slug: docker-sqlite-foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-30
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `docker compose run --rm app pytest tests/ -x -q` |
| **Full suite command** | `docker compose run --rm app pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose run --rm app pytest tests/ -x -q`
- **After every plan wave:** Run `docker compose run --rm app pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | INFRA-01 | manual | `docker compose up --build -d` | n/a | pending |
| 5-01-02 | 01 | 1 | INFRA-01 | manual | `grep -r "osascript" src/ config/` returns 0 | n/a | pending |
| 5-02-01 | 02 | 1 | DADOS-01 | unit | `pytest tests/test_db_schema.py -q` | W0 | pending |
| 5-02-02 | 02 | 1 | DADOS-02 | unit | `pytest tests/test_db_schema.py::test_comparacoes_columns -q` | W0 | pending |
| 5-02-03 | 02 | 1 | DADOS-03 | unit | `pytest tests/test_db_schema.py::test_custos_reais_columns -q` | W0 | pending |
| 5-02-04 | 02 | 1 | DADOS-04 | unit | `pytest tests/test_db_schema.py::test_comparacoes_columns -q` | W0 | pending |
| 5-02-05 | 02 | 1 | INFRA-03 | unit | `pytest tests/test_db_migrations.py -q` | W0 | pending |
| 5-03-01 | 03 | 2 | INFRA-01 | integration | `docker compose up --build -d && curl -f http://localhost:8000/health` | n/a | pending |
| 5-03-02 | 03 | 2 | INFRA-03 | integration | `docker compose down && docker compose up -d` + verify data | n/a | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_db_schema.py` — stubs for DADOS-01 through DADOS-04 (tables, persistence, schema, cached_at)
- [ ] `tests/test_db_migrations.py` — stubs for INFRA-03 (Alembic migration runs, idempotent)
- [ ] `tests/conftest.py` — shared fixtures (SQLite in-memory or temp file)
- [ ] `pytest` — install in requirements-docker.txt if not present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Container starts with `docker compose up` without errors | INFRA-01 | Requires Docker runtime | `docker compose up --build -d && docker compose ps` — all services "Up" |
| Data persists across `docker compose down && docker compose up` | INFRA-03 | Requires Docker volume | Write record, down, up, verify record exists |
| App responds at http://localhost:8000 inside container | INFRA-01 | Network access required | `curl http://localhost:8000` returns 200 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
