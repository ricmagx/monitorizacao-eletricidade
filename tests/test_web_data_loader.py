"""Testes para src/web/services/data_loader.py"""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.web.services.data_loader import (
    build_custo_chart_data,
    get_freshness_info,
    load_analysis_json,
    load_consumo_csv,
    load_locations,
    load_monthly_status,
)


# ---------------------------------------------------------------------------
# load_locations
# ---------------------------------------------------------------------------


def test_load_locations(sample_config_json):
    """load_locations retorna lista com 2 dicts, cada um com keys esperadas."""
    locations = load_locations(sample_config_json)
    assert len(locations) == 2
    for loc in locations:
        assert "id" in loc
        assert "name" in loc
        assert "current_contract" in loc
        assert "pipeline" in loc


def test_load_locations_missing(tmp_path):
    """load_locations retorna [] se config nao existe."""
    result = load_locations(tmp_path / "nao_existe.json")
    assert result == []


# ---------------------------------------------------------------------------
# load_consumo_csv
# ---------------------------------------------------------------------------


def test_load_consumo_csv(sample_csv):
    """load_consumo_csv retorna lista de dicts com valores float."""
    rows = load_consumo_csv(sample_csv)
    assert len(rows) == 3
    row = rows[0]
    assert "year_month" in row
    assert isinstance(row["total_kwh"], float)
    assert isinstance(row["vazio_kwh"], float)
    assert isinstance(row["fora_vazio_kwh"], float)
    assert row["year_month"] == "2025-01"
    assert row["total_kwh"] == pytest.approx(1429.0)


def test_load_consumo_csv_missing(tmp_path):
    """load_consumo_csv retorna [] se ficheiro nao existe."""
    result = load_consumo_csv(tmp_path / "nao_existe.csv")
    assert result == []


# ---------------------------------------------------------------------------
# load_analysis_json
# ---------------------------------------------------------------------------


def test_load_analysis_json(sample_analysis_json):
    """load_analysis_json retorna dict com keys esperadas."""
    result = load_analysis_json(sample_analysis_json)
    assert result is not None
    assert "history_summary" in result
    assert "history" in result
    assert "current_supplier" in result


def test_load_analysis_json_missing(tmp_path):
    """load_analysis_json retorna None se ficheiro nao existe."""
    result = load_analysis_json(tmp_path / "nao_existe.json")
    assert result is None


# ---------------------------------------------------------------------------
# get_freshness_info
# ---------------------------------------------------------------------------


def test_get_freshness_info_recent(sample_status_json):
    """Status recente: days_ago=1, is_stale=False."""
    # sample_status_json fixture cria status com generated_at de ontem
    result = get_freshness_info(sample_status_json)
    assert result["is_stale"] is False
    assert result["days_ago"] is not None
    assert result["days_ago"] <= 2  # ontem ou hoje
    assert result["generated_at"] is not None


def test_get_freshness_info_stale():
    """Status de 50 dias atras: is_stale=True."""
    stale_date = (datetime.now(timezone.utc) - timedelta(days=50)).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )
    status = {"status": "ok", "generated_at": stale_date}
    result = get_freshness_info(status)
    assert result["is_stale"] is True
    assert result["days_ago"] >= 50


def test_get_freshness_info_missing():
    """Status None: days_ago=None, is_stale=True, generated_at=None."""
    result = get_freshness_info(None)
    assert result["days_ago"] is None
    assert result["is_stale"] is True
    assert result["generated_at"] is None


def test_get_freshness_info_missing_generated_at():
    """Status sem generated_at: is_stale=True."""
    result = get_freshness_info({"status": "ok"})
    assert result["is_stale"] is True
    assert result["days_ago"] is None


# ---------------------------------------------------------------------------
# build_custo_chart_data
# ---------------------------------------------------------------------------


def test_build_custo_chart_data(sample_csv):
    """build_custo_chart_data retorna labels, estimativa_data e custo_real_data correctos."""
    consumo = [
        {"year_month": "2025-01", "total_kwh": 1429.0, "vazio_kwh": 571.6, "fora_vazio_kwh": 857.4},
        {"year_month": "2025-02", "total_kwh": 1556.0, "vazio_kwh": 622.4, "fora_vazio_kwh": 933.6},
        {"year_month": "2025-03", "total_kwh": 1100.0, "vazio_kwh": 440.0, "fora_vazio_kwh": 660.0},
    ]
    analysis = {
        "history": [
            {
                "year_month": "2025-01",
                "current_supplier_result": {"supplier": "Meo Energia", "total_eur": 263.12},
            },
            {
                "year_month": "2025-02",
                "current_supplier_result": {"supplier": "Meo Energia", "total_eur": 280.00},
            },
        ]
    }
    custos_reais = {"2025-01": 210.50}

    result = build_custo_chart_data(consumo, analysis, custos_reais)

    assert result["labels"] == ["2025-01", "2025-02", "2025-03"]
    assert result["estimativa_data"][0] == pytest.approx(263.12)
    assert result["estimativa_data"][1] == pytest.approx(280.00)
    assert result["estimativa_data"][2] is None  # sem dados no analysis

    # custo_real_data: so 2025-01 tem dado, os outros sao None
    assert result["custo_real_data"][0] == pytest.approx(210.50)
    assert result["custo_real_data"][1] is None
    assert result["custo_real_data"][2] is None


def test_build_custo_chart_data_no_analysis(sample_csv):
    """build_custo_chart_data com analysis=None retorna estimativa_data com Nones."""
    consumo = [
        {"year_month": "2025-01", "total_kwh": 1429.0, "vazio_kwh": 571.6, "fora_vazio_kwh": 857.4},
    ]
    result = build_custo_chart_data(consumo, None, {})

    assert result["labels"] == ["2025-01"]
    assert result["estimativa_data"] == [None]
    assert result["custo_real_data"] == [None]
