"""FastAPI app de monitorizacao de eletricidade.

Entry point: uvicorn src.web.app:app
"""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text, select, insert, func

from src.db.engine import engine
from src.db.schema import metadata, locais

BASE_DIR = Path(__file__).resolve().parent
# Docker-compatible: APP_ROOT env var tem precedencia sobre calculo por path
PROJECT_ROOT = Path(os.environ.get("APP_ROOT", str(BASE_DIR.parent.parent)))


def _seed_locais_from_config(engine, config_path: Path) -> None:
    """Copia locais de config/system.json para SQLite se tabela estiver vazia.

    Idempotente: nao faz nada se ja existirem locais na tabela.
    """
    if not config_path.exists():
        return
    with engine.connect() as conn:
        count = conn.execute(select(func.count()).select_from(locais)).scalar()
    if count and count > 0:
        return
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    locations = config.get("locations", [])
    if not locations:
        return
    with engine.begin() as conn:
        for loc in locations:
            contract = loc.get("current_contract", {})
            conn.execute(insert(locais).values(
                id=loc["id"],
                name=loc["name"],
                cpe=loc.get("cpe", ""),
                current_supplier=contract.get("supplier"),
                current_plan_contains=contract.get("current_plan_contains"),
                power_label=contract.get("power_label"),
            ))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida da app.

    Chama metadata.create_all como safety net para dev local sem Docker.
    Em Docker, as tabelas sao criadas pelo Alembic via entrypoint.sh.
    """
    metadata.create_all(engine)
    app.state.db_engine = engine
    _seed_locais_from_config(engine, PROJECT_ROOT / "config" / "system.json")
    yield


app = FastAPI(title="Monitorizacao Eletricidade", lifespan=lifespan)

# Montar ficheiros estaticos
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Configurar templates Jinja2
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Disponibilizar project_root, config_path e templates como app.state
app.state.project_root = PROJECT_ROOT
app.state.config_path = PROJECT_ROOT / "config" / "system.json"
app.state.templates = templates


@app.get("/health")
def health():
    """Health check com verificacao de conectividade da base de dados."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "db": "connected"})
    except Exception as e:
        return JSONResponse({"status": "error", "db": str(e)}, status_code=503)


# Registar routers
from src.web.routes.dashboard import router as dashboard_router  # noqa: E402
from src.web.routes.custos_reais import router as custos_router  # noqa: E402
from src.web.routes.upload import router as upload_router  # noqa: E402
from src.web.routes.locais import router as locais_router  # noqa: E402

app.include_router(dashboard_router)
app.include_router(custos_router)
app.include_router(upload_router)
app.include_router(locais_router)
