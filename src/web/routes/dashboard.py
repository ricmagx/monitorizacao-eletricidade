"""Routes da dashboard de monitorizacao de eletricidade.

GET /          — pagina principal com selector de local
GET /local/{local_id}/dashboard — fragmento HTMX para troca de local
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from src.web.services.data_loader import (
    build_analysis_from_sqlite,
    build_comparacao_meses,
    build_consumo_multi_ano,
    build_custo_chart_data,
    build_resumo_anual,
    get_freshness_from_sqlite,
    get_freshness_info,
    load_analysis_json,
    load_consumo_csv,
    load_consumo_sqlite,
    load_custos_reais,
    load_custos_reais_sqlite,
    load_locations,
    load_monthly_status,
    load_ultimo_detalhe_sqlite,
)
from src.web.services.rankings import build_recommendation, calculate_annual_ranking
from src.web.services.comparar_service import comparar_com_tarifarios

router = APIRouter()


def _extract_current_prices(detalhe: dict | None) -> dict | None:
    """Extrai precos unitarios com e sem IVA do detalhe_json da ultima fatura."""
    if not detalhe:
        return None
    by_tipo = {l["tipo"]: l for l in detalhe.get("linhas", [])}

    def com_iva(linha: dict) -> float:
        return round(linha["preco_base"] * (1 + linha.get("iva_pct", 23) / 100), 4)

    def sem_iva(linha: dict) -> float:
        return round(linha["preco_base"], 4)

    result: dict = {}
    if "energia_fv" in by_tipo:
        result["preco_fv"] = com_iva(by_tipo["energia_fv"])
        result["preco_fv_base"] = sem_iva(by_tipo["energia_fv"])
    if "energia_vn" in by_tipo:
        result["preco_vn"] = com_iva(by_tipo["energia_vn"])
        result["preco_vn_base"] = sem_iva(by_tipo["energia_vn"])
    if "energia" in by_tipo and "preco_fv" not in result:
        result["preco_simples"] = com_iva(by_tipo["energia"])
        result["preco_simples_base"] = sem_iva(by_tipo["energia"])
    if "potencia" in by_tipo:
        result["potencia_dia"] = com_iva(by_tipo["potencia"])
        result["potencia_dia_base"] = sem_iva(by_tipo["potencia"])
    return result if result else None


def _build_tariff_prices_lookup(tarifarios_path: Path) -> dict:
    """Constroi lookup {(supplier, plan): precos} a partir de tarifarios.json."""
    try:
        data = json.loads(tarifarios_path.read_text(encoding="utf-8"))
        lookup = {}
        for t in data.get("tariffs", []):
            energy = t.get("energy", {})
            fixed = t.get("fixed_daily", {})
            prices: dict = {}
            if "vazio" in energy:
                prices["preco_vn"] = energy["vazio"]
                prices["preco_fv"] = energy.get("fora_vazio")
            elif "simples" in energy:
                prices["preco_simples"] = energy["simples"]
            if "power_contract" in fixed:
                prices["potencia_dia"] = fixed["power_contract"]
            lookup[(t["supplier"], t["plan"])] = prices
        return lookup
    except Exception:
        return {}


def _enrich_ranking_with_prices(
    ranking: list,
    tariff_lookup: dict,
    current_prices: dict | None,
) -> None:
    """Acrescenta precos unitarios a cada entrada do ranking (in-place)."""
    for entry in ranking:
        key = (entry["supplier"], entry["plan"])
        if key in tariff_lookup:
            entry.update(tariff_lookup[key])
        elif entry.get("from_custos_reais") and current_prices:
            entry.update(current_prices)


def _load_location_data(request: Request, location: dict) -> dict:
    """Carrega todos os dados para um local especifico.

    Usa SQLite como fonte primaria para todos os locais.
    Se SQLite nao tiver dados e o local tiver pipeline CSV, usa fallback CSV/JSON.
    """
    project_root = request.app.state.project_root
    engine = request.app.state.db_engine
    local_id = location["id"]
    pipeline = location.get("pipeline")

    # Suporta ambos os formatos: config.json (current_contract) e SQLite (current_supplier)
    current_supplier = (
        location.get("current_supplier")
        or location.get("current_contract", {}).get("supplier", "")
    )

    # --- Consumo ---
    consumo_data = load_consumo_sqlite(local_id, engine)
    if not consumo_data and pipeline:
        consumo_data = load_consumo_csv(project_root / pipeline["processed_csv_path"])

    # --- Analise de comparacoes ---
    analysis = build_analysis_from_sqlite(local_id, engine)
    if analysis is None and pipeline:
        analysis = load_analysis_json(project_root / pipeline["analysis_json_path"])

    # --- Auto-comparacao: recalcular se ha meses de consumo sem comparacao ---
    if consumo_data:
        compared_months = (
            {e["year_month"] for e in analysis["history"]}
            if analysis and "history" in analysis else set()
        )
        consumo_months = {r["year_month"] for r in consumo_data}
        if consumo_months - compared_months:
            tarifarios_path = project_root / "config" / "tarifarios.json"
            comparar_com_tarifarios(local_id, current_supplier, engine, tarifarios_path)
            analysis = build_analysis_from_sqlite(local_id, engine)

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

    current_plan = location.get("current_contract", {}).get("current_plan_contains", "")
    ultimo_detalhe = load_ultimo_detalhe_sqlite(local_id, engine)
    ranking = calculate_annual_ranking(
        analysis, current_supplier,
        consumo_data=consumo_data,
        ultimo_detalhe=ultimo_detalhe,
        custos_reais=custos_dict,
        current_plan=current_plan,
    )

    tarifarios_path = project_root / "config" / "tarifarios.json"
    current_prices = _extract_current_prices(ultimo_detalhe)
    tariff_lookup = _build_tariff_prices_lookup(tarifarios_path)
    _enrich_ranking_with_prices(ranking, tariff_lookup, current_prices)

    recommendation = build_recommendation(analysis)

    return {
        "consumo_data": consumo_data,
        "analysis": analysis,
        "freshness": freshness,
        "custos_reais": custos_dict,
        "consumo_chart": consumo_chart,
        "custo_chart": custo_chart,
        "ranking": ranking,
        "current_prices": current_prices,
        "recommendation": recommendation,
    }


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, local: str | None = None):
    """Pagina principal com selector de local e dashboard do local default.

    Query param opcional: local (ex: ?local=apartamento) para preservar
    o local seleccionado em refreshes e bookmarks.
    """
    config_path = request.app.state.config_path
    templates = request.app.state.templates

    locations = load_locations(config_path, engine=request.app.state.db_engine)

    # Usar local do query param se valido, caso contrario usar primeiro
    selected_location = (
        next((loc for loc in locations if loc["id"] == local), None)
        if local else None
    ) or (locations[0] if locations else {})
    location_data = _load_location_data(request, selected_location) if selected_location else {
        "consumo_data": [],
        "analysis": None,
        "freshness": get_freshness_info(None),
        "custos_reais": {},
        "consumo_chart": {"labels": [], "vazio_data": [], "fora_vazio_data": []},
        "custo_chart": {"labels": [], "estimativa_data": [], "custo_real_data": []},
        "ranking": [],
        "current_prices": None,
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
    response = templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )
    # Actualizar URL do browser para preservar local em refresh/bookmark
    root_path = request.scope.get("root_path", "")
    response.headers["HX-Push-Url"] = f"{root_path}/?local={local_id}"
    return response


@router.get("/local/{local_id}/multi-ano", response_class=HTMLResponse)
async def local_multi_ano(
    request: Request,
    local_id: str,
    ano1: str | None = None,
    ano2: str | None = None,
    mes: str | None = None,
):
    """Fragmento HTMX com grafico multi-ano e resumo anual para um local.

    Query params opcionais: ano1, ano2, mes (ex: ?ano1=2023&ano2=2024&mes=03).
    Retorna partials/multi_ano.html com consumo_multi_ano, resumo_anual e
    comparacao_meses (None se params ausentes).
    """
    config_path = request.app.state.config_path
    templates = request.app.state.templates
    engine = request.app.state.db_engine
    project_root = request.app.state.project_root

    locations = load_locations(config_path, engine=engine)
    location = next((loc for loc in locations if loc["id"] == local_id), None)
    if location is None:
        raise HTTPException(status_code=404, detail=f"Local '{local_id}' nao encontrado")

    pipeline = location.get("pipeline")

    # --- Carregar consumo (SQLite first, fallback CSV) ---
    consumo_data = load_consumo_sqlite(local_id, engine)
    if not consumo_data and pipeline:
        consumo_data = load_consumo_csv(project_root / pipeline["processed_csv_path"])

    # --- Carregar analise (SQLite first, fallback JSON) ---
    analysis = build_analysis_from_sqlite(local_id, engine)
    if analysis is None and pipeline:
        analysis = load_analysis_json(project_root / pipeline["analysis_json_path"])

    comparacoes_history = analysis["history"] if analysis and "history" in analysis else None

    # --- Calcular dados multi-ano ---
    consumo_multi_ano = build_consumo_multi_ano(consumo_data) if consumo_data else None
    resumo_anual = build_resumo_anual(consumo_data, comparacoes_history) if consumo_data else []

    # Anos disponiveis para os selects
    anos_disponiveis = sorted({row["year_month"][:4] for row in consumo_data}) if consumo_data else []

    # Comparacao mensal (apenas se os 3 params estao presentes)
    comparacao_meses = None
    if ano1 and ano2 and mes:
        comparacao_meses = build_comparacao_meses(
            consumo_data, comparacoes_history, ano1=ano1, ano2=ano2, mes=mes
        )

    context = {
        "local_id": local_id,
        "selected_location": location,
        "consumo_multi_ano": consumo_multi_ano,
        "resumo_anual": resumo_anual,
        "comparacao_meses": comparacao_meses,
        "anos_disponiveis": anos_disponiveis,
        "selected_ano1": ano1 or (anos_disponiveis[-2] if len(anos_disponiveis) >= 2 else None),
        "selected_ano2": ano2 or (anos_disponiveis[-1] if anos_disponiveis else None),
        "selected_mes": mes or "01",
    }
    return templates.TemplateResponse(
        request=request,
        name="partials/multi_ano.html",
        context=context,
    )


@router.post("/local/{local_id}/comparar", response_class=HTMLResponse)
async def comparar_local(request: Request, local_id: str):
    """Corre comparacao de tarifarios locais e retorna ranking actualizado."""
    config_path = request.app.state.config_path
    templates = request.app.state.templates
    engine = request.app.state.db_engine
    tarifarios_path = request.app.state.project_root / "config" / "tarifarios.json"

    locations = load_locations(config_path, engine=engine)
    location = next((loc for loc in locations if loc["id"] == local_id), None)
    if location is None:
        return HTMLResponse(status_code=404, content="Local nao encontrado")

    current_supplier = location.get("current_supplier") or location.get(
        "current_contract", {}
    ).get("supplier", "")

    resultado = comparar_com_tarifarios(local_id, current_supplier, engine, tarifarios_path)

    if "erro" in resultado:
        return templates.TemplateResponse(
            request=request,
            name="partials/ranking_table.html",
            context={"ranking": [], "comparar_erro": resultado["erro"], "selected_location": location},
        )

    analysis = build_analysis_from_sqlite(local_id, engine)
    consumo_data = load_consumo_sqlite(local_id, engine)
    custos_dict = load_custos_reais_sqlite(local_id, engine)
    ultimo_detalhe = load_ultimo_detalhe_sqlite(local_id, engine)
    current_plan = location.get("current_contract", {}).get("current_plan_contains", "")
    ranking = calculate_annual_ranking(
        analysis, current_supplier,
        consumo_data=consumo_data,
        ultimo_detalhe=ultimo_detalhe,
        custos_reais=custos_dict,
        current_plan=current_plan,
    )

    current_prices = _extract_current_prices(ultimo_detalhe)
    tariff_lookup = _build_tariff_prices_lookup(tarifarios_path)
    _enrich_ranking_with_prices(ranking, tariff_lookup, current_prices)

    return templates.TemplateResponse(
        request=request,
        name="partials/ranking_table.html",
        context={
            "ranking": ranking,
            "current_prices": current_prices,
            "comparar_ok": resultado["meses"],
            "selected_location": location,
        },
    )
