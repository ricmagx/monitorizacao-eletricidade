import csv
import json
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def sample_csv(tmp_path):
    """CSV de consumo mensal com 3 meses de dados reais plausíveis."""
    csv_path = tmp_path / "consumo_mensal.csv"
    rows = [
        {"year_month": "2025-01", "total_kwh": "1429.000", "vazio_kwh": "571.600", "fora_vazio_kwh": "857.400"},
        {"year_month": "2025-02", "total_kwh": "1556.000", "vazio_kwh": "622.400", "fora_vazio_kwh": "933.600"},
        {"year_month": "2025-03", "total_kwh": "1100.000", "vazio_kwh": "440.000", "fora_vazio_kwh": "660.000"},
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year_month", "total_kwh", "vazio_kwh", "fora_vazio_kwh"])
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


@pytest.fixture
def sample_tariffs(tmp_path):
    """Catalogo local de tarifarios minimo para testes."""
    tariffs_path = tmp_path / "tarifarios.json"
    payload = {
        "metadata": {"currency": "EUR", "country": "PT", "updated_at": "2026-03-26"},
        "tariffs": [
            {
                "id": "luzboa-mono-base",
                "supplier": "Luzboa",
                "plan": "Mono Base",
                "type": "simples",
                "valid_from": "2026-03-01",
                "valid_to": None,
                "energy": {"simples": 0.1619},
                "fixed_daily": {"power_contract": 0.305},
                "source_url": "https://example.com/luzboa-mono",
            },
            {
                "id": "luzboa-bi-base",
                "supplier": "Luzboa",
                "plan": "Bi Base",
                "type": "bihorario",
                "valid_from": "2026-03-01",
                "valid_to": None,
                "energy": {"vazio": 0.108, "fora_vazio": 0.1905},
                "fixed_daily": {"power_contract": 0.305},
                "source_url": "https://example.com/luzboa-bi",
            },
        ],
    }
    tariffs_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return tariffs_path


@pytest.fixture
def sample_contract(tmp_path):
    """Contrato actual para testes (aponta para luzboa-mono-base)."""
    contract_path = tmp_path / "fornecedor_atual.json"
    payload = {
        "supplier": "Luzboa",
        "plan": "Mono Base",
        "current_tariff_id": "luzboa-mono-base",
    }
    contract_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return contract_path


@pytest.fixture
def test_config(tmp_path, sample_csv, sample_tariffs, sample_contract):
    """Config system.json minima para testes de workflow."""
    config_path = tmp_path / "config" / "system.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Criar dirs esperados pelo workflow
    (tmp_path / "data" / "processed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "raw" / "eredes").mkdir(parents=True, exist_ok=True)

    payload = {
        "current_contract": {
            "supplier": "Meo Energia",
            "current_plan_contains": "Tarifa Variavel",
            "power_label": "10.35 kVA",
        },
        "eredes": {
            "download_dir": "data/raw/eredes",
        },
        "pipeline": {
            "processed_csv_path": "data/processed/consumo_mensal_atual.csv",
            "analysis_json_path": "data/processed/analise_tiagofelicia_atual.json",
            "report_dir": "data/reports",
            "status_path": "state/monthly_status.json",
            "drop_partial_last_month": True,
            "notify_on_completion": False,
            "months_limit": None,
            "local_tariffs_path": str(sample_tariffs),
            "local_contract_path": str(sample_contract),
        },
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


@pytest.fixture
def multi_location_config(tmp_path, sample_tariffs, sample_contract):
    """Config system.json com schema multi-location para testes de fase 03.

    Cria config/system.json em tmp_path com dois locations (casa + apartamento)
    e todas as diretorias nested esperadas pelo pipeline.
    """
    config_path = tmp_path / "config" / "system.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Criar estrutura de diretorias nested para cada local
    for location_id in ("casa", "apartamento"):
        (tmp_path / "data" / location_id / "raw" / "eredes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / location_id / "processed").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / location_id / "reports").mkdir(parents=True, exist_ok=True)
        (tmp_path / "state" / location_id).mkdir(parents=True, exist_ok=True)

    payload = {
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
            {
                "id": "apartamento",
                "name": "Apartamento",
                "cpe": "PT000200XXXXXXXXXX",
                "current_contract": {
                    "supplier": "Fornecedor Mock",
                    "current_plan_contains": "Tarifa Mock",
                    "power_label": "6.9 kVA",
                },
                "pipeline": {
                    "raw_dir": "data/apartamento/raw/eredes",
                    "processed_csv_path": "data/apartamento/processed/consumo_mensal_atual.csv",
                    "analysis_json_path": "data/apartamento/processed/analise_tiagofelicia_atual.json",
                    "report_dir": "data/apartamento/reports",
                    "status_path": "state/apartamento/monthly_status.json",
                    "last_processed_tracker_path": "state/apartamento/last_processed_download.json",
                    "drop_partial_last_month": True,
                    "notify_on_completion": False,
                    "months_limit": None,
                    "local_tariffs_path": str(sample_tariffs),
                    "local_contract_path": str(sample_contract),
                },
            },
        ],
        "eredes": {
            "download_dir_base": "data/{location_id}/raw/eredes",
            "download_url": "https://balcaodigital.e-redes.pt/consumptions/history",
            "browser_app": "Firefox",
        },
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path
