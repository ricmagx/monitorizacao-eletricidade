"""Routes da dashboard de monitorizacao de eletricidade.

GET /          — pagina principal com selector de local
GET /local/{local_id}/dashboard — fragmento HTMX para troca de local
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.web.services.data_loader import (
    build_analysis_from_sqlite,
    build_custo_chart_data,
    get_freshness_from_sqlite,
    get_freshness_info,
    load_analysis_json,
    load_consumo_csv,
    load_consumo_sqlite,
    load_custos_reais,
    load_custos_reais_sqlite,
    load_locations,
    load_monthly_status,
)
from src.web.services.rankings import build_recommendation, calculate_annual_ranking

router = APIRouter()


def _load_location_data(request: Request, location: dict) -> dict:
    """Carrega todos os dados para um local especifico.

    Usa SQLite como fonte primaria para todos os locais.
    Se SQLite nao tiver dados e o local tiver pipeline CSV, usa fallback CSV/JSON.
    """
    project_root = request.app.state.project_root
    engine = request.app.state.db_engine
    local_id = location["id"]
    pipeline = location.get("pipeline")

    # --- Consumo ---
    consumo_data = load_consumo_sqlite(local_id, engine)
    if not consumo_data and pipeline:
        consumo_data = load_consumo_csv(project_root / pipeline["processed_csv_path"])

    # --- Analise de comparacoes ---
    analysis = build_analysis_from_sqlite(local_id, engine)
    if analysis is None and pipeline:
        analysis = load_analysis_json(project_root / pipeline["analysis_json_path"])

    # --- Custos reais ---
    custos_dict = load_custos_reais_sqlite(local_id, engine)
    if not custos_dict and pipeline:
        custos_path = project_root / "data" / local_id / "custos_reais.json"
        custos_dict = load_custos_reais(custos_path)

    # --- Frescura ---
    freshness = get_freshness_from_sqlite(local_id, engine)
    if freshness["days_ago"] is None and pipeline:
        status = load_monthly_status(project_root / pipeline["status_path"])
        freshness = get_freshness_info(status)

    # --- Graficos ---
    consumo_chart = {
        "labels": [row["year_month"] for row in consumo_data],
        "vazio_data": [row["vazio_kwh"] for row in consumo_data],
        "fora_vazio_data": [row["fora_vazio_kwh"] for row in consumo_data],
    }
    custo_chart = build_custo_chart_data(consumo_data, analysis, custos_dict)

    # Suporta ambos os formatos: config.json (current_contract) e SQLite (current_supplier)
    current_supplier = (
        location.get("current_supplier")
        or location.get("current_contract", {}).get("supplier", "")
    )
    ranking = calculate_annual_ranking(analysis, current_supplier)
    recommendation = build_recommendation(analysis)

    return {
        "consumo_data": consumo_data,
        "analysis": analysis,
        "freshness": freshness,
        "custos_reais": custos_dict,
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
