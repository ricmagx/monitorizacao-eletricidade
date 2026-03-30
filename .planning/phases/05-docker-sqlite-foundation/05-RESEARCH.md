# Phase 5: Docker + SQLite Foundation — Research

**Researched:** 2026-03-30
**Domain:** Docker containerization (Python/FastAPI), SQLite + Alembic migrations, macOS dependency elimination
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Sistema corre como container Docker no Unraid | Dockerfile + docker-compose.yml com python:3.11-slim; uvicorn como entrypoint |
| INFRA-02 | App exposta via reverse proxy nginx em `/hobbies/casa/energia/` | `root_path="/hobbies/casa/energia"` no FastAPI + HTMX basepath — INFRA-02 is **Phase 12** scope; Phase 5 only needs `localhost:8000` working |
| INFRA-03 | Dados persistem em volume Docker (SQLite) | Named volume → `/app/data/energia.db`; WAL mode; never bind-mount to NFS |
| DADOS-01 | Histórico de consumo mensal por local em SQLite | Table `consumo_mensal(id, location_id, year_month, total_kwh, vazio_kwh, fora_vazio_kwh)` |
| DADOS-02 | Histórico de comparações tiagofelicia.pt em SQLite | Table `comparacoes(id, location_id, year_month, top_3_json, current_supplier_result_json, generated_at)` |
| DADOS-03 | Custos reais de faturas em SQLite | Table `custos_reais(id, location_id, year_month, custo_eur, source, created_at)` |
| DADOS-04 | Cache de resultados tiagofelicia.pt com timestamp | Subsumed into `comparacoes` table + `cached_at` column; or separate `cache_tiagofelicia` table |
</phase_requirements>

---

## Summary

Phase 5 is a platform migration, not a feature build. The existing FastAPI + Python codebase (v1.0) is functionally complete but tied to macOS: launchd plists, `osascript` calls, `/Users/ricmag/Downloads` paths, and flat CSV/JSON files for data storage. This phase replaces the platform substrate without changing observable app behaviour.

There are three work streams: (1) write a Dockerfile + docker-compose.yml so the app starts inside a Linux container; (2) create a SQLite schema with Alembic migrations and a `db.py` layer that replaces the current `data_loader.py` file I/O; (3) surgically remove all macOS-specific code — eight affected files were identified. The existing web app (`src/web/`) remains unchanged in this phase.

The critical constraint: **Phase 5 success criteria only require the app to answer on `localhost:8000` inside Docker with data persisting across restarts.** Reverse proxy path-prefix (`/hobbies/casa/energia/`) is Phase 12 scope.

**Primary recommendation:** Use `python:3.11-slim`, SQLAlchemy 2.x Core (not ORM) for schema + queries, Alembic for migrations invoked automatically in the container entrypoint, and a named Docker volume at `/app/data/`. Remove macOS-specific code but do not delete the backend scripts — they will be repurposed in Phase 7.

---

## Project Constraints (from CLAUDE.md)

No project-level CLAUDE.md exists. Global CLAUDE.md directives that apply:

- Respostas e código comentado em **português europeu (PT-PT)**
- Soluções práticas e directas — sem over-engineering
- Commits atómicos, features pequenas e incrementais

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python | 3.11-slim (Docker base image) | Runtime | Matches existing codebase; slim = smaller image |
| sqlalchemy | 2.0.48 (latest) | SQL toolkit + schema definition | Industry standard; Core API sufficient for this use case |
| alembic | 1.18.4 (latest) | Schema migrations | Official SQLAlchemy companion; auto-generates migration scripts |
| fastapi | 0.135.2 (latest) | Web framework | Already in use; no change |
| uvicorn | 0.42.0 (latest) | ASGI server | Already in use; no change |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 | stdlib (3.51.3 on host) | Python SQLite driver | Built-in; zero install cost |
| python-dotenv | latest | Environment variable config | Container config via `.env` file |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLAlchemy Core | SQLAlchemy ORM | ORM adds model classes = more code; Core sufficient for 3 simple tables |
| Alembic | Manual migration scripts | Manual scripts don't track state; Alembic is the standard companion |
| python:3.11-slim | python:3.11-alpine | Alpine has musl libc — can cause issues with compiled wheels (openpyxl, Playwright); slim is safer |
| Named volume | Bind mount (`./data:/app/data`) | Bind mounts on Unraid (often NFS/XFS) cause SQLite WAL locking issues; named volume is safer |

**Installation (requirements.txt additions):**
```bash
sqlalchemy>=2.0.0
alembic>=1.18.0
python-dotenv>=1.0.0
```

**Version verification:** Confirmed against PyPI on 2026-03-30:
- sqlalchemy: 2.0.48
- alembic: 1.18.4
- fastapi: 0.135.2
- uvicorn: 0.42.0

---

## Architecture Patterns

### Recommended Project Structure (additions to existing)

```
monitorizacao-eletricidade/
├── Dockerfile                  # NEW — Python 3.11-slim, copies src/, runs alembic then uvicorn
├── docker-compose.yml          # NEW — service + named volume
├── .env.example                # NEW — DB_PATH, APP_PORT
├── src/
│   ├── db/                     # NEW — SQLite layer
│   │   ├── __init__.py
│   │   ├── engine.py           # create_engine(), get_db() dependency
│   │   ├── schema.py           # Table definitions (SQLAlchemy Core metadata)
│   │   └── migrations/         # Alembic env + versions/
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   │           └── 001_initial_schema.py
│   ├── web/                    # UNCHANGED (Phase 5 leaves web layer intact)
│   └── backend/                # MODIFIED — remove macOS calls, keep logic
└── data/                       # .gitignored — SQLite DB lives here in dev
```

### Pattern 1: Alembic Auto-run on Container Start

**What:** Entrypoint script runs `alembic upgrade head` then starts uvicorn. Migrations are idempotent — safe to run on every restart.

**When to use:** Always in Docker deployments; avoids manual migration steps.

**Example:**
```bash
# entrypoint.sh
#!/bin/sh
set -e
cd /app
alembic upgrade head
exec uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
```

### Pattern 2: SQLAlchemy Core — Schema Definition

**What:** Define tables with `MetaData` + `Table` objects. No ORM models. Queries use `conn.execute(select(...))`.

**When to use:** Small number of tables with simple queries — this project's case exactly.

**Example:**
```python
# Source: SQLAlchemy 2.x Core docs
from sqlalchemy import MetaData, Table, Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone

metadata = MetaData()

consumo_mensal = Table(
    "consumo_mensal", metadata,
    Column("id", Integer, primary_key=True),
    Column("location_id", String(64), nullable=False),
    Column("year_month", String(7), nullable=False),  # "YYYY-MM"
    Column("total_kwh", Float, nullable=False),
    Column("vazio_kwh", Float, nullable=False),
    Column("fora_vazio_kwh", Float, nullable=False),
    # UNIQUE prevents duplicate import (idempotency)
)

comparacoes = Table(
    "comparacoes", metadata,
    Column("id", Integer, primary_key=True),
    Column("location_id", String(64), nullable=False),
    Column("year_month", String(7), nullable=False),
    Column("top_3_json", Text),           # JSON blob
    Column("current_supplier_result_json", Text),  # JSON blob
    Column("generated_at", String(32)),
    Column("cached_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)

custos_reais = Table(
    "custos_reais", metadata,
    Column("id", Integer, primary_key=True),
    Column("location_id", String(64), nullable=False),
    Column("year_month", String(7), nullable=False),
    Column("custo_eur", Float, nullable=False),
    Column("source", String(64)),         # "upload_pdf", "manual", etc.
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)
```

### Pattern 3: Named Volume in docker-compose

**What:** Declare a named volume; mount it at `/app/data` inside the container. Unraid stores it in `/var/lib/docker/volumes/`.

**When to use:** Always for SQLite in Docker — avoids NFS/bind-mount WAL locking issues.

**Example:**
```yaml
# docker-compose.yml
services:
  energia:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - energia_data:/app/data
    environment:
      - DB_PATH=/app/data/energia.db
    restart: unless-stopped

volumes:
  energia_data:
```

### Pattern 4: UNIQUE Constraint for Idempotency

**What:** Add `UniqueConstraint("location_id", "year_month")` on `consumo_mensal` and `custos_reais`. Use `INSERT OR REPLACE` / `ON CONFLICT DO UPDATE` for upsert.

**When to use:** Every table that can receive duplicate imports. Existing codebase already enforces idempotency in the pipeline — this moves the guarantee to the database layer.

```python
# SQLAlchemy Core upsert (SQLite dialect)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

stmt = sqlite_insert(consumo_mensal).values(...)
stmt = stmt.on_conflict_do_update(
    index_elements=["location_id", "year_month"],
    set_={"total_kwh": stmt.excluded.total_kwh, ...}
)
conn.execute(stmt)
```

### Anti-Patterns to Avoid

- **WAL mode not enabled:** Default SQLite journal mode can cause locking under concurrent FastAPI workers. Enable WAL: `PRAGMA journal_mode=WAL` on first connect. (On a single-worker uvicorn this is low risk but good hygiene.)
- **Bind-mounting to Unraid share path:** `/mnt/user/appdata/...` on Unraid is often NFS or a user share — SQLite WAL does not work reliably on NFS. Use a named volume (Docker manages the storage on local disk).
- **Running migrations outside entrypoint:** If migrations run only at image build time (`RUN alembic upgrade head`), they cannot apply to the persistent volume mounted at runtime. Must run at container start.
- **Deleting backend scripts in this phase:** `src/backend/` scripts are still needed by Phase 7 (upload pipeline). Only remove macOS-specific calls, do not delete files.
- **Hardcoded paths inside `src/web/app.py`:** `PROJECT_ROOT` is computed at import time. In Docker, `/app` is the working directory. Paths like `PROJECT_ROOT / "config" / "system.json"` will break if computed relative to `__file__` in a different directory. Use env var `DB_PATH` for the database, and keep `config/system.json` in the image or in a volume.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migrations | Custom SQL upgrade scripts | Alembic | Tracks migration state; handles upgrades and rollbacks; generates scripts from model diff |
| SQLite connection management | Manual `sqlite3.connect()` pool | SQLAlchemy `create_engine` with `pool_pre_ping=True` | Handles reconnect, thread safety, WAL mode setup |
| Upsert (insert-or-update) | Try/except IntegrityError loop | `sqlite_insert().on_conflict_do_update()` | Atomic; SQLite-dialect-aware |
| Container healthcheck | External probe script | Docker `HEALTHCHECK` directive | Native; Unraid and docker-compose both understand it |

**Key insight:** SQLite's threading model is "one writer at a time" — SQLAlchemy's connection pool with `check_same_thread=False` (SQLite-specific) and WAL mode handles this correctly without custom locking.

---

## Runtime State Inventory

> Included because this phase involves a rename/migration of data storage from flat files to SQLite.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `data/casa/processed/consumo_mensal_atual.csv` — 1 row (2026-02). `data/casa/processed/analise_tiagofelicia_atual.json` — 1 history entry. `state/casa/monthly_status.json` — last run metadata. `state/last_processed_download.json` — processed XLSX tracker. | Data migration script (optional, Wave 0) — import CSV rows into SQLite on first run. Can also start fresh: v1.0 had only 1 month of real data. |
| Live service config | macOS launchd: 3 plists in `launchd/` directory (dashboard, monthly, process-watch). These are registered on the Mac at `~/Library/LaunchAgents/`. | Unload from Mac after Docker is running. Not a blocking step for Phase 5. |
| OS-registered state | launchd agents registered on macOS host (not verifiable from here). Log files at `state/launchd.*.log`. | Unload launchd agents after Docker working. Log files safe to delete. |
| Secrets/env vars | No secrets in repo. `DB_PATH` will be introduced as env var. | Add `.env.example`; add `.env` to `.gitignore`. |
| Build artifacts | None — Python source, no compiled artefacts. | None. |

**Note on data migration:** With only 1 month of real data in v1.0, starting the SQLite DB fresh (empty tables) is acceptable. The planner should decide: (a) skip migration — user re-imports XLSX via Phase 7 upload, or (b) include a one-off migration script. Recommendation: skip migration in Phase 5 (no blocking data), document as known gap.

---

## Common Pitfalls

### Pitfall 1: SQLite WAL on NFS/Unraid User Share
**What goes wrong:** App starts, writes work locally, then on Unraid the SQLite database corrupts or hangs on write.
**Why it happens:** WAL mode uses memory-mapped files and file locking that NFS does not honour correctly. Unraid user shares (`/mnt/user/`) are SMB/NFS over the internal virtual filesystem.
**How to avoid:** Use a Docker named volume (`volumes: energia_data:`). Docker stores named volumes on the local Unraid disk (not a user share), bypassing NFS.
**Warning signs:** `database is locked` errors in logs; database file size stays at 0 bytes after writes.

### Pitfall 2: Alembic Migration Not Finding the Database at Runtime
**What goes wrong:** `alembic upgrade head` runs at build time (in `RUN` step), not at container start. The volume is mounted after build — the upgrade runs against a temporary file that disappears.
**Why it happens:** Confusing `RUN` (build time) with `CMD`/entrypoint (runtime).
**How to avoid:** Put `alembic upgrade head` in `entrypoint.sh`, which runs as the container's `CMD`.
**Warning signs:** Tables missing after `docker-compose up`; no error during build.

### Pitfall 3: `PROJECT_ROOT` Computed Relative to Source File
**What goes wrong:** `app.py` computes `PROJECT_ROOT = Path(__file__).resolve().parent.parent` — inside Docker this gives `/app/src`, not `/app`. Paths like `PROJECT_ROOT / "config" / "system.json"` break.
**Why it happens:** Mac dev path is `/Users/ricmag/.../monitorizacao-eletricidade/src/web/app.py` — going up two levels gives the project root. In Docker with `WORKDIR /app` and `COPY . .`, the same relative logic works **only if** the working directory matches. Verify: `WORKDIR /app` + `COPY . /app/` means `__file__` = `/app/src/web/app.py` → parent.parent = `/app/src` ≠ `/app`.
**How to avoid:** Use `Path(__file__).resolve().parents[2]` (3 levels up from `app.py` gives `/app`) or use `os.environ.get("APP_ROOT", "/app")`.
**Warning signs:** `FileNotFoundError: config/system.json` on startup inside Docker even though the file exists.

### Pitfall 4: `osascript`/`launchd` Calls Crashing the Container
**What goes wrong:** Code in `monthly_workflow.py`, `reminder_job.py`, `eredes_download.py` calls `subprocess.run(["osascript", ...])` — `osascript` does not exist on Linux; subprocess raises `FileNotFoundError`.
**Why it happens:** macOS notification calls were not conditioned on platform.
**How to avoid:** Replace `osascript` notify calls with a no-op or `logging.info()` stub. Keep the function signature; just change the body. Mark with `# TODO Phase 7: substituir por notificação web`.
**Warning signs:** Container starts then immediately exits; `docker logs` shows `FileNotFoundError: [Errno 2] No such file or directory: 'osascript'`.

### Pitfall 5: Playwright Installed in Image But Not Needed for Phase 5
**What goes wrong:** `pip install playwright` pulls ~200MB of dependencies; then `playwright install chromium` adds ~300MB. Image becomes 700MB+.
**Why it happens:** Playwright is in `requirements.txt` but Phase 5 does not use the tiagofelicia.pt scraping.
**How to avoid:** Create a `requirements-docker.txt` that excludes `playwright` and `tf-playwright-stealth`. Phase 5 Docker image only needs FastAPI + SQLAlchemy + Alembic. Playwright stays in the full `requirements.txt` for local dev.
**Warning signs:** `docker build` takes 10+ minutes; image size > 500MB.

---

## Code Examples

### Alembic env.py for SQLite
```python
# Source: Alembic docs — https://alembic.sqlalchemy.org/en/latest/tutorial.html
# alembic/env.py (critical section)
import os
from sqlalchemy import engine_from_config, pool
from alembic import context
from src.db.schema import metadata

config = context.config

# Override sqlalchemy.url from environment variable
db_path = os.environ.get("DB_PATH", "data/energia.db")
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

target_metadata = metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.config_ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

### SQLAlchemy engine with WAL mode
```python
# src/db/engine.py
import os
from sqlalchemy import create_engine, event, text

DB_PATH = os.environ.get("DB_PATH", "data/energia.db")

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_conn, connection_record):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
```

### FastAPI lifespan + DB init
```python
# src/web/app.py — adicionar lifespan
from contextlib import asynccontextmanager
from src.db.engine import engine
from src.db.schema import metadata

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Alembic já cria as tabelas via entrypoint.sh
    # Este create_all é apenas safety net para dev local sem Docker
    metadata.create_all(engine)
    yield

app = FastAPI(title="Monitorizacao Eletricidade", lifespan=lifespan)
```

---

## macOS Code to Remove — Inventory

Files with macOS-specific code that must be cleaned in Phase 5:

| File | What to Remove | What to Keep |
|------|---------------|--------------|
| `src/backend/monthly_workflow.py:172` | `osascript` notify call | All pipeline logic |
| `src/backend/reminder_job.py:25` | `osascript` notify call | Reminder scheduling logic |
| `src/backend/eredes_download.py:48,99,122,168` | `osascript` calls + `/Users/ricmag/Downloads` hardcoded paths | Download logic (reused in Phase 7) |
| `src/backend/process_latest_download.py:55` | `local_download_watch_dir` → `Path.home() / "Downloads"` fallback | Processing logic |
| `src/backend/install_launch_agent.py` | Entire file (launchd generator) | Nothing — file becomes obsolete |
| `src/backend/install_process_watch_agent.py` | Entire file (launchd generator) | Nothing — file becomes obsolete |
| `launchd/` directory | All 3 `.plist` files | Nothing — entire directory obsolete |
| `config/system.json` | `eredes.local_download_watch_dir`, `eredes.download_mode: external_firefox`, `watcher.watch_paths` macOS paths | All other config |

**Strategy:** Replace `osascript` calls with `logging.info("Notificacao: %s", message)`. Do not delete `eredes_download.py` or `process_latest_download.py` — they contain XLSX processing logic needed in Phase 7.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docker-compose` (v1 CLI) | `docker compose` (v2, built into Docker) | Docker 20.10+ | Use `docker compose` not `docker-compose` |
| SQLAlchemy 1.x `Session` + ORM | SQLAlchemy 2.x `with engine.connect() as conn` | SQLAlchemy 2.0 (Jan 2023) | New connection style; `conn.execute()` returns `CursorResult` |
| Alembic `op.create_table` manually | Alembic `--autogenerate` from metadata | Always available | Auto-generates migration from schema diff |

**Deprecated/outdated:**
- `docker-compose.yml` version field (`version: "3.8"`): Docker Compose v2 ignores `version` key — omit it or leave it (harmless but misleading).
- SQLAlchemy `engine.execute()`: Removed in 2.0 — use `with engine.connect() as conn: conn.execute(...)`.

---

## Open Questions

1. **Data migration from v1.0 CSV to SQLite**
   - What we know: Only 1 real month of data exists (`consumo_mensal_atual.csv` → 2026-02).
   - What's unclear: Should Phase 5 include a one-off import script, or should the user re-import via Phase 7 upload?
   - Recommendation: Skip migration in Phase 5. Document that existing data will be re-imported via Phase 7 XLSX upload. Add a note in the plan.

2. **`config/system.json` in Docker**
   - What we know: App currently reads `system.json` for location config (CPE, paths, etc.).
   - What's unclear: Should `system.json` be in the Docker image (baked in) or mounted as a volume?
   - Recommendation: Bake `config/system.json` into the image for Phase 5 (simpler). Phase 7 will move location config to SQLite (`locations` table) — making this moot.

3. **`requirements-docker.txt` vs single requirements.txt**
   - What we know: Playwright adds ~500MB to the image but is unused in Phase 5.
   - What's unclear: How much does image size matter for Unraid deployment?
   - Recommendation: Create `requirements-docker.txt` excluding playwright/playwright-stealth. Reference it in Dockerfile. Keeps base image lean (~150MB vs ~700MB).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Build + run container | ✓ | 28.3.2 | — |
| docker compose (v2) | `docker compose up` | ✓ | v2.38.2 | — |
| Python 3.11 | Runtime in container | ✓ | 3.11.14 (host) | — |
| SQLAlchemy | DB layer | ✓ (installed) | 2.0.23 (host pip) | — |
| Alembic | Migrations | ✓ (installed) | 1.12.1 (host pip) | Upgrade to 1.18.4 |
| sqlite3 | DB engine | ✓ (stdlib) | 3.51.3 | — |
| Unraid server | Production deploy | ✗ (not reachable from dev Mac) | — | Develop + test locally; deploy manually to Unraid after Phase 5 passes locally |

**Missing dependencies with no fallback:** None that block Phase 5.

**Missing dependencies with fallback:**
- Unraid server: not reachable from dev Mac — all Phase 5 testing runs locally with `docker compose up`. Deploy to Unraid is a manual step at the end.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` (exists: `testpaths = tests`, `pythonpath = . src/backend`) |
| Quick run command | `pytest tests/test_db*.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `docker compose up` arranca sem erros | smoke | `docker compose up -d && curl -f http://localhost:8000/health` | ❌ Wave 0 |
| INFRA-03 | Dados persistem após restart | smoke | `docker compose down && docker compose up -d && curl http://localhost:8000/api/consumo` | ❌ Wave 0 |
| DADOS-01 | Tabela `consumo_mensal` criada + UNIQUE funciona | unit | `pytest tests/test_db_schema.py::test_consumo_mensal_table -x` | ❌ Wave 0 |
| DADOS-02 | Tabela `comparacoes` criada com timestamp | unit | `pytest tests/test_db_schema.py::test_comparacoes_table -x` | ❌ Wave 0 |
| DADOS-03 | Tabela `custos_reais` criada + upsert | unit | `pytest tests/test_db_schema.py::test_custos_reais_upsert -x` | ❌ Wave 0 |
| DADOS-04 | Cache tiagofelicia — `cached_at` coluna presente | unit | `pytest tests/test_db_schema.py::test_cache_timestamp -x` | ❌ Wave 0 |
| — | Código sem `osascript`/`launchd` refs | lint | `grep -r "osascript\|launchd\|open -a Firefox" src/ && exit 1 \|\| exit 0` | ❌ Wave 0 |
| — | Migrações aplicadas automaticamente no startup | integration | Docker smoke test covers this | — |

### Sampling Rate
- **Per task commit:** `pytest tests/test_db_schema.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green + Docker smoke test before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_db_schema.py` — cobre DADOS-01 a DADOS-04 (tabelas, constraints, upsert, WAL)
- [ ] `tests/test_db_migrations.py` — verifica que `alembic upgrade head` cria todas as tabelas
- [ ] `src/db/__init__.py`, `src/db/engine.py`, `src/db/schema.py` — módulo DB inexistente
- [ ] `src/db/migrations/` — directório Alembic inexistente
- [ ] `Dockerfile` — não existe
- [ ] `docker-compose.yml` — não existe
- [ ] `entrypoint.sh` — não existe

---

## Sources

### Primary (HIGH confidence)
- SQLAlchemy 2.x Core docs (official) — schema definition, connection patterns, WAL setup
- Alembic docs (official) — env.py pattern, `upgrade head` at runtime
- Docker docs (official) — named volumes, HEALTHCHECK, entrypoint patterns
- Local codebase inspection (definitive) — macOS file inventory, existing schema, test infrastructure

### Secondary (MEDIUM confidence)
- Docker best practices for Python apps — slim base image, non-root user, layer caching
- SQLite WAL mode on NFS — well-documented known issue (multiple SQLite docs references)

### Tertiary (LOW confidence)
- Unraid Docker volume storage location (`/var/lib/docker/volumes/`) — standard Docker behaviour, not Unraid-specific documentation verified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI on 2026-03-30
- Architecture: HIGH — Docker + Alembic + SQLAlchemy Core patterns are stable and well-documented
- Pitfalls: HIGH — SQLite WAL/NFS and Alembic migration timing are known documented issues; macOS refs found by direct code inspection
- macOS code inventory: HIGH — found by direct grep of codebase

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable ecosystem — 30 days)
