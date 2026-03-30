"""FastAPI app de monitorizacao de eletricidade.

Entry point: uvicorn src.web.app:app
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from src.db.engine import engine
from src.db.schema import metadata

BASE_DIR = Path(__file__).resolve().parent
# Docker-compatible: APP_ROOT env var tem precedencia sobre calculo por path
PROJECT_ROOT = Path(os.environ.get("APP_ROOT", str(BASE_DIR.parent.parent)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida da app.

    Chama metadata.create_all como safety net para dev local sem Docker.
    Em Docker, as tabelas sao criadas pelo Alembic via entrypoint.sh.
    """
    metadata.create_all(engine)
    app.state.db_engine = engine
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

app.include_router(dashboard_router)
app.include_router(custos_router)
