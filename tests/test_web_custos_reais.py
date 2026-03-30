"""Testes para custos reais: data_loader (load/save) e endpoint POST /local/{id}/custo-real."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixture: sample_custos_reais_json
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_custos_reais_json(tmp_path):
    """custos_reais.json com 2 entries."""
    custos_path = tmp_path / "custos_reais.json"
    payload = {
        "updated_at": "2026-03-30T00:00:00",
        "entries": {
            "2025-01": 210.50,
            "2025-02": 195.00,
        },
    }
    custos_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return custos_path


# ---------------------------------------------------------------------------
# Tests: load_custos_reais
# ---------------------------------------------------------------------------


def test_load_custos_reais_existing(sample_custos_reais_json):
    """load_custos_reais com ficheiro valido retorna entries dict."""
    from src.web.services.data_loader import load_custos_reais

    result = load_custos_reais(sample_custos_reais_json)
    assert result == {"2025-01": 210.50, "2025-02": 195.00}


def test_load_custos_reais_missing(tmp_path):
    """load_custos_reais com path inexistente retorna {} (dict vazio)."""
    from src.web.services.data_loader import load_custos_reais

    result = load_custos_reais(tmp_path / "nao_existe.json")
    assert result == {}


# ---------------------------------------------------------------------------
# Tests: save_custo_real
# ---------------------------------------------------------------------------


def test_save_custo_real(tmp_path):
    """save_custo_real cria custos_reais.json com entry correcta."""
    from src.web.services.data_loader import save_custo_real, load_custos_reais

    custos_path = tmp_path / "custos_reais.json"
    save_custo_real(custos_path, "2025-03", 180.00)

    result = load_custos_reais(custos_path)
    assert result["2025-03"] == pytest.approx(180.00)


def test_save_custo_real_preserves_existing(sample_custos_reais_json):
    """save_custo_real adiciona nova entry sem apagar entries anteriores."""
    from src.web.services.data_loader import save_custo_real, load_custos_reais

    save_custo_real(sample_custos_reais_json, "2025-03", 180.00)
    result = load_custos_reais(sample_custos_reais_json)

    assert result["2025-01"] == pytest.approx(210.50)
    assert result["2025-02"] == pytest.approx(195.00)
    assert result["2025-03"] == pytest.approx(180.00)


def test_save_custo_real_overwrite(sample_custos_reais_json):
    """save_custo_real actualiza entry existente para novo valor."""
    from src.web.services.data_loader import save_custo_real, load_custos_reais

    save_custo_real(sample_custos_reais_json, "2025-01", 215.00)
    result = load_custos_reais(sample_custos_reais_json)

    assert result["2025-01"] == pytest.approx(215.00)
    # Entry anterior nao alterada
    assert result["2025-02"] == pytest.approx(195.00)


# ---------------------------------------------------------------------------
# Tests: endpoint POST /local/{local_id}/custo-real
# ---------------------------------------------------------------------------


@pytest.fixture
def web_client_with_csv(tmp_path, sample_tariffs, sample_contract):
    """FastAPI TestClient com config mock incluindo CSV de consumo para casa."""
    import csv as csv_module
    from src.web.app import app

    # Criar estrutura de diretorias
    for location_id in ("casa", "apartamento"):
        (tmp_path / "data" / location_id / "raw" / "eredes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / location_id / "processed").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / location_id / "reports").mkdir(parents=True, exist_ok=True)
        (tmp_path / "state" / location_id).mkdir(parents=True, exist_ok=True)

    # Criar CSV de consumo para casa
    csv_path = tmp_path / "data" / "casa" / "processed" / "consumo_mensal_atual.csv"
    rows = [
        {"year_month": "2025-01", "total_kwh": "1429.000", "vazio_kwh": "571.600", "fora_vazio_kwh": "857.400"},
        {"year_month": "2025-02", "total_kwh": "1556.000", "vazio_kwh": "622.400", "fora_vazio_kwh": "933.600"},
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv_module.DictWriter(f, fieldnames=["year_month", "total_kwh", "vazio_kwh", "fora_vazio_kwh"])
        writer.writeheader()
        writer.writerows(rows)

    # Criar analysis JSON vazio (sem history)
    analysis_path = tmp_path / "data" / "casa" / "processed" / "analise_tiagofelicia_atual.json"
    analysis_path.write_text(json.dumps({"history": [], "history_summary": {}}), encoding="utf-8")

    config_payload = {
        "locations": [
            {
                "id": "casa",
                "name": "Casa",
                "cpe": "PT0002000084968079SX",
                "current_contract": {
                    "supplier": "Meo Energia",
                    "current_plan_contains": "Tarifa Variavel",
                    "power_label": "10.35 kVA",
                },
                "pipeline": {
                    "raw_dir": "data/casa/raw/eredes",
                    "processed_csv_path": "data/casa/processed/consumo_mensal_atual.csv",
                    "analysis_json_path": "data/casa/processed/analise_tiagofelicia_atual.json",
                    "report_dir": "data/casa/reports",
                    "status_path": "state/casa/monthly_status.json",
                    "last_processed_tracker_path": "state/casa/last_processed_download.json",
                    "drop_partial_last_month": True,
                    "notify_on_completion": False,
                    "months_limit": None,
                    "local_tariffs_path": str(sample_tariffs),
                    "local_contract_path": str(sample_contract),
                },
            },
        ],
        "eredes": {"download_dir_base": "data/{location_id}/raw/eredes"},
    }
    config_path = tmp_path / "config" / "system.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config_payload, indent=2), encoding="utf-8")

    app.state.config_path = config_path
    app.state.project_root = tmp_path

    # Fornecer db_engine para load_locations (necessario apos Phase 7)
    from sqlalchemy import create_engine
    from src.db.schema import metadata
    test_engine = create_engine("sqlite:///:memory:")
    metadata.create_all(test_engine)
    app.state.db_engine = test_engine

    return TestClient(app)


def test_post_custo_real_endpoint(web_client_with_csv):
    """POST /local/casa/custo-real retorna 200."""
    response = web_client_with_csv.post(
        "/local/casa/custo-real",
        data={"year_month": "2025-01", "custo_eur": "210.50"},
    )
    assert response.status_code == 200


def test_post_custo_real_persists(tmp_path, web_client_with_csv):
    """Apos POST, GET /local/casa/dashboard contem o custo real no HTML."""
    web_client_with_csv.post(
        "/local/casa/custo-real",
        data={"year_month": "2025-01", "custo_eur": "210.50"},
    )
    response = web_client_with_csv.get("/local/casa/dashboard")
    assert response.status_code == 200
    assert "210.5" in response.text
