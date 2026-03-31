"""Route para submissao de custo real da factura.

POST /local/{local_id}/custo-real — persiste custo real e retorna fragmento actualizado.
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from src.web.services.data_loader import (
    build_analysis_from_sqlite,
    build_custo_chart_data,
    load_analysis_json,
    load_consumo_csv,
    load_consumo_sqlite,
    load_custos_reais,
    load_locations,
    save_custo_real,
)

router = APIRouter()


@router.post("/local/{local_id}/custo-real", response_class=HTMLResponse)
async def post_custo_real(
    request: Request,
    local_id: str,
    year_month: str = Form(...),
    custo_eur: float = Form(...),
):
    """Persiste custo real da factura e retorna fragmento custo_section actualizado.

    Args:
        request: FastAPI Request.
        local_id: ID do local (ex: "casa").
        year_month: Mes no formato "YYYY-MM".
        custo_eur: Custo real da factura em EUR.

    Returns:
        Fragmento HTML com custo_chart + custo_form actualizados (para HTMX swap).
    """
    project_root = request.app.state.project_root
    custos_path = project_root / "data" / local_id / "custos_reais.json"
    save_custo_real(custos_path, year_month, custo_eur)

    # Retornar fragmento actualizado do grafico de custo
    locations = load_locations(request.app.state.config_path, engine=request.app.state.db_engine)
    location = next((loc for loc in locations if loc["id"] == local_id), None)
    if not location:
        return HTMLResponse(status_code=404, content="Local nao encontrado")

    if "pipeline" in location:
        consumo_data = load_consumo_csv(project_root / location["pipeline"]["processed_csv_path"])
        analysis = load_analysis_json(project_root / location["pipeline"]["analysis_json_path"])
    else:
        engine = request.app.state.db_engine
        consumo_data = load_consumo_sqlite(local_id, engine)
        analysis = build_analysis_from_sqlite(local_id, engine)
    custos_reais = load_custos_reais(custos_path)
    custo_chart = build_custo_chart_data(consumo_data, analysis, custos_reais)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request=request,
        name="partials/custo_section.html",
        context={
            "custo_chart": custo_chart,
            "custos_reais": custos_reais,
            "consumo_data": consumo_data,
            "selected_location": location,
        },
    )
