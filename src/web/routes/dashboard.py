"""Routes da dashboard de monitorizacao de eletricidade.

GET /          — pagina principal com selector de local
GET /local/{local_id}/dashboard — fragmento HTMX para troca de local
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.web.services.data_loader import (
    build_custo_chart_data,
    get_freshness_info,
    load_analysis_json,
    load_consumo_csv,
    load_custos_reais,
    load_locations,
    load_monthly_status,
)
from src.web.services.rankings import build_recommendation, calculate_annual_ranking

router = APIRouter()


def _load_location_data(request: Request, location: dict) -> dict:
    """Carrega todos os dados para um local especifico."""
    project_root = request.app.state.project_root
    local_id = location["id"]

    # Local criado via UI (Phase 7) — sem dados de pipeline CSV
    # Retornar dados vazios — Phase 9 migrara para leitura directa de SQLite
    if "pipeline" not in location:
        return {
            "consumo_data": [],
            "analysis": None,
            "freshness": get_freshness_info(None),
            "custos_reais": {},
            "consumo_chart": {"labels": [], "vazio_data": [], "fora_vazio_data": []},
            "custo_chart": {"labels": [], "estimativa_data": [], "custo_real_data": []},
            "ranking": [],
            "recommendation": {"show": False},
        }

    pipeline = location["pipeline"]

    consumo_data = load_consumo_csv(project_root / pipeline["processed_csv_path"])
    analysis = load_analysis_json(project_root / pipeline["analysis_json_path"])
    status = load_monthly_status(project_root / pipeline["status_path"])
    freshness = get_freshness_info(status)

    custos_path = project_root / "data" / local_id / "custos_reais.json"
    custos_reais = load_custos_reais(custos_path)

    consumo_chart = {
        "labels": [row["year_month"] for row in consumo_data],
        "vazio_data": [row["vazio_kwh"] for row in consumo_data],
        "fora_vazio_data": [row["fora_vazio_kwh"] for row in consumo_data],
    }
    custo_chart = build_custo_chart_data(consumo_data, analysis, custos_reais)

    current_supplier = location.get("current_contract", {}).get("supplier", "")
    ranking = calculate_annual_ranking(analysis, current_supplier)
    recommendation = build_recommendation(analysis)

    return {
        "consumo_data": consumo_data,
        "analysis": analysis,
        "freshness": freshness,
        "custos_reais": custos_reais,
        "consumo_chart": consumo_chart,
        "custo_chart": custo_chart,
        "ranking": ranking,
        "recommendation": recommendation,
    }


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Pagina principal com selector de local e dashboard do local default."""
    config_path = request.app.state.config_path
    templates = request.app.state.templates

    locations = load_locations(config_path, engine=request.app.state.db_engine)

    # Usar primeiro local como default
    selected_location = locations[0] if locations else {}
    location_data = _load_location_data(request, selected_location) if selected_location else {
        "consumo_data": [],
        "analysis": None,
        "freshness": get_freshness_info(None),
        "custos_reais": {},
        "consumo_chart": {"labels": [], "vazio_data": [], "fora_vazio_data": []},
        "custo_chart": {"labels": [], "estimativa_data": [], "custo_real_data": []},
        "ranking": [],
        "recommendation": {"show": False},
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

    locations = load_locations(config_path, engine=request.app.state.db_engine)

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
