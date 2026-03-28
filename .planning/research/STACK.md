# Technology Stack — Dashboard & Multi-Location Layer

**Project:** Monitorização de Eletricidade
**Researched:** 2026-03-28
**Scope:** Additive stack for web dashboard and multi-location config. Does NOT replace the existing backend stack (Python 3.11, Playwright 1.58, openpyxl 3.1 — already documented in `.planning/codebase/STACK.md`).

---

## Recommended Stack — New Components Only

### Web Server

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | >=0.111, pin 0.115.x | HTTP server, route handler, static file serving | Already named in PROJECT.md; async by default; Jinja2 integration is first-class; StaticFiles mount eliminates need for a separate static server |
| uvicorn | >=0.29, pin 0.29.x | ASGI server to run FastAPI locally | Standard pairing; `uvicorn src.web.app:app --reload` for dev; zero config |

**Why FastAPI over Flask:** FastAPI's `Jinja2Templates` and `StaticFiles` are built-in with no extra adapter. Async routes mean the server does not block while reading JSON files from disk. Flask would work but adds no advantage here.

**Why not Starlette directly:** FastAPI wraps Starlette with less boilerplate. For a personal project with no team, FastAPI's auto-docs are a useful bonus.

### Templating

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Jinja2 | >=3.1, pin 3.1.x | Server-side HTML rendering | FastAPI's `Jinja2Templates` wrapper requires it; template inheritance (`{% extends %}`) keeps base layout DRY across pages |
| python-multipart | >=0.0.9 | Form body parsing (needed by FastAPI if any forms are used) | FastAPI requires it when processing form data; install even if forms are minimal |

**Template pattern confirmed by FastAPI docs (HIGH confidence):**
```python
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"locations": config.locations}
    )
```

### Frontend — No Build Step

| Technology | Version | How to load | Why |
|------------|---------|------------|-----|
| HTMX | 2.0.x | CDN via `<script src>` in base template | Partial HTML updates via `hx-get`/`hx-target` attributes; server returns HTML fragments; zero JS to write |
| Chart.js | 4.4.x | CDN via `<script src>` in base template | Bar/line charts from inline JSON data; no bundler needed; `new Chart(ctx, config)` is self-contained |

**CDN load pattern (no npm, no webpack, no node_modules):**
```html
<!-- In templates/base.html -->
<script src="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
```

Alternatively, download these two files once into `src/web/static/js/` and serve locally — eliminates external CDN dependency for a local-only tool. This is the recommended approach for a macOS-only personal project: no internet required to open the dashboard.

**HTMX interaction pattern for this project:**
```html
<!-- Location selector triggers partial update -->
<select hx-get="/partial/history" hx-target="#history-panel" name="location_id">
  <option value="cpe1">Casa Lisboa</option>
  <option value="cpe2">Casa Porto</option>
</select>

<!-- FastAPI returns an HTML fragment, not a full page -->
<div id="history-panel">
  <!-- injected by HTMX -->
</div>
```

**Why HTMX over Alpine.js or Vue:** The data is static (monthly aggregates from JSON files). There is no reactive state, no user input beyond a location selector, and no client-side business logic. HTMX's `hx-get` + server-rendered fragments is the right level of complexity. Alpine.js would add JS logic for something that is fundamentally a server problem.

**Why Chart.js over Plotly or ECharts:** Chart.js 4.x has the cleanest CDN-only UMD build. Plotly is 3 MB and overkill for bar/line charts. ECharts is well-maintained but less familiar. Chart.js is the de-facto standard for lightweight dashboard charts without a build step.

**Why NOT a JS framework (React, Vue, Svelte):** All require a build step (npm, vite, webpack). The constraint is explicit: no frontend build. A framework would also require a JSON API and client-side routing, doubling the surface area for what is a personal read-only display tool.

### Configuration — Multi-Location

| Pattern | Technology | Why |
|---------|-----------|-----|
| Single config file, array of location objects | `config/system.json` (existing) extended with `"locations": [...]` | Fewest files to manage; a single `json.load()` in app startup; each location is self-describing with its own `cpe_id`, `name`, `state_dir`, `csv_dir` |

**Recommended config structure:**
```json
{
  "locations": [
    {
      "id": "lisboa",
      "name": "Casa Lisboa",
      "cpe": "PT0002XXXXXXXXXX",
      "state_dir": "state/lisboa",
      "data_dir": "data/lisboa"
    },
    {
      "id": "porto",
      "name": "Casa Porto",
      "cpe": "PT0002YYYYYYYYYY",
      "state_dir": "state/porto",
      "data_dir": "data/porto"
    }
  ],
  "eredes": {
    "username": "...",
    "password_env": "EREDES_PASSWORD"
  }
}
```

**Why single file with array (not one file per location):**
- The existing codebase already uses `config/system.json` — extending it is zero-friction
- With 2 locations (and unlikely to exceed 5), a single file is simpler than a directory of files with a discovery mechanism
- No code needed to enumerate or merge config files
- The `id` field on each location doubles as the directory name and URL slug, keeping things consistent

**Why NOT pydantic-settings or dynaconf:** Both add a dependency and a learning curve for a project that already reads plain JSON. The config is not environment-driven (no staging/production split). pydantic-settings is valuable when config comes from env vars + files + secrets — overkill here. A dataclass loaded from JSON is enough.

**Recommended config loader pattern:**
```python
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class LocationConfig:
    id: str
    name: str
    cpe: str
    state_dir: Path
    data_dir: Path

@dataclass
class AppConfig:
    locations: list[LocationConfig]

def load_config(path: Path) -> AppConfig:
    raw = json.loads(path.read_text())
    locations = [
        LocationConfig(
            id=loc["id"],
            name=loc["name"],
            cpe=loc["cpe"],
            state_dir=Path(loc["state_dir"]),
            data_dir=Path(loc["data_dir"]),
        )
        for loc in raw["locations"]
    ]
    return AppConfig(locations=locations)
```

No extra library. Full type hints. Compatible with Python 3.11 standard library.

---

## Complete New Dependencies (pip install)

```bash
# Web dashboard additions only — backend deps already exist
pip install fastapi==0.115.* uvicorn==0.29.* jinja2==3.1.* python-multipart==0.0.*
```

No other Python packages needed. HTMX and Chart.js are loaded as static files (downloaded once, committed to `src/web/static/js/`).

---

## Directory Structure for New Components

```
src/
  web/
    app.py              # FastAPI app, routes
    templates/
      base.html         # Layout, CDN script tags
      index.html        # Dashboard overview
      partials/
        history.html    # HTMX fragment: monthly history table/chart
        ranking.html    # HTMX fragment: tariff ranking for a location
    static/
      js/
        htmx.min.js     # Downloaded from CDN, served locally
        chart.umd.min.js
      css/
        style.css       # Minimal custom CSS, no framework needed
config/
  system.json           # Extended with "locations" array
```

FastAPI mounts `src/web/static/` as `/static`:
```python
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web server | FastAPI | Flask | Flask needs flask-jinja2 adapter; no async; no auto-docs; no advantage |
| Web server | FastAPI | Django | Massive overkill; ORM, migrations, admin panel — none needed |
| Charts | Chart.js CDN | Plotly | 3 MB bundle; server-side fig generation needed for no-build use |
| Charts | Chart.js CDN | Matplotlib PNG | Static images; no interactivity; no zoom/hover |
| Partial updates | HTMX | Alpine.js | Alpine needs JS state management — not needed for static data |
| Partial updates | HTMX | Full page reload | Acceptable for 2 locations, but HTMX is barely more complex and feels better |
| Config | JSON array | One JSON per location | Requires file discovery logic; no benefit at N=2 |
| Config | JSON array | pydantic-settings | Adds dependency; overkill for static local config |
| Config | JSON array | TOML (tomllib) | tomllib is stdlib in 3.11+, but JSON is already the project standard |

---

## Integration with Existing Backend

The dashboard is a read-only view over data already produced by the pipeline:

```
Pipeline output                  Dashboard reads
─────────────────────────────────────────────────
data/{location}/YYYY-MM.csv  →  Monthly consumption history
reports/{location}/YYYY-MM.md →  Recommendation text (render as HTML)
data/{location}/comparison.json → Tariff ranking chart data
```

FastAPI reads these files directly from disk at request time. No database, no shared memory, no message queue. The pipeline writes files; the dashboard reads them. They never run simultaneously (pipeline runs at midnight on day 1; dashboard is accessed interactively during the day).

This means: **no IPC, no queue, no cache layer needed.** A simple `Path.read_text()` in each route is correct.

---

## Sources

- FastAPI Jinja2 templates documentation (fetched directly): https://fastapi.tiangolo.com/advanced/templates/ — HIGH confidence
- FastAPI StaticFiles pattern: official docs — HIGH confidence
- HTMX 2.0 CDN pattern and attributes: training knowledge (cutoff Aug 2025), release confirmed stable — MEDIUM confidence (version number may have moved to 2.0.x in late 2025)
- Chart.js 4.4.x CDN UMD build: training knowledge (cutoff Aug 2025) — MEDIUM confidence (4.4 branch was current; patch version may differ)
- Multi-location JSON config pattern: derived from existing project conventions + Python stdlib dataclass pattern — HIGH confidence (no external dependency, no version risk)
- pydantic-settings / dynaconf comparison: training knowledge — MEDIUM confidence

**Version note:** Version numbers for FastAPI (0.115.x), uvicorn (0.29.x), jinja2 (3.1.x), HTMX (2.0.x), and Chart.js (4.4.x) are the latest known stable releases as of August 2025 training cutoff. Verify with `pip install fastapi --dry-run` or PyPI before pinning in requirements.txt. The major versions (FastAPI 0.1xx, HTMX 2.x, Chart.js 4.x) are stable and the pattern recommendations are version-independent within those majors.
