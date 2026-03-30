"""FastAPI app de monitorizacao de eletricidade.

Entry point: uvicorn src.web.app:app
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent  # monitorizacao-eletricidade/

app = FastAPI(title="Monitorizacao Eletricidade")

# Montar ficheiros estaticos
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Configurar templates Jinja2
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Disponibilizar project_root, config_path e templates como app.state
app.state.project_root = PROJECT_ROOT
app.state.config_path = PROJECT_ROOT / "config" / "system.json"
app.state.templates = templates

# Registar routers
from src.web.routes.dashboard import router as dashboard_router  # noqa: E402
from src.web.routes.custos_reais import router as custos_router  # noqa: E402

app.include_router(dashboard_router)
app.include_router(custos_router)
