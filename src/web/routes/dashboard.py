"""Routes da dashboard de monitorizacao de eletricidade.

GET /          — pagina principal com selector de local
GET /local/{local_id}/dashboard — fragmento HTMX para troca de local
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.web.services.data_loader import (
    get_freshness_info,
    load_analysis_json,
    load_consumo_csv,
    load_locations,
    load_monthly_status,
)

router = APIRouter()


def _load_location_data(request: Request, location: dict) -> dict:
    """Carrega todos os dados para um local especifico."""
    project_root = request.app.state.project_root
    pipeline = location["pipeline"]

    consumo_data = load_consumo_csv(project_root / pipeline["processed_csv_path"])
    analysis = load_analysis_json(project_root / pipeline["analysis_json_path"])
    status = load_monthly_status(project_root / pipeline["status_path"])
    freshness = get_freshness_info(status)

    return {
        "consumo_data": consumo_data,
        "analysis": analysis,
        "freshness": freshness,
    }


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Pagina principal com selector de local e dashboard do local default."""
    config_path = request.app.state.config_path
    templates = request.app.state.templates

    locations = load_locations(config_path)

    # Usar primeiro local como default
    selected_location = locations[0] if locations else {}
    location_data = _load_location_data(request, selected_location) if selected_location else {
        "consumo_data": [],
        "analysis": None,
        "freshness": get_freshness_info(None),
    }

    context = {
        "locations": locations,
        "selected_location": selected_location,
        **location_data,
    }
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=context,
    )


@router.get("/local/{local_id}/dashboard", response_class=HTMLResponse)
async def local_dashboard(request: Request, local_id: str):
    """Fragmento HTMX para troca de local via selector."""
    config_path = request.app.state.config_path
    templates = request.app.state.templates

    locations = load_locations(config_path)

    # Validar que local_id existe
    location = next((loc for loc in locations if loc["id"] == local_id), None)
    if location is None:
        raise HTTPException(status_code=404, detail=f"Local '{local_id}' nao encontrado")

    location_data = _load_location_data(request, location)

    context = {
        "selected_location": location,
        **location_data,
    }
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )
