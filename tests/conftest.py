import csv
import json
from datetime import datetime, timedelta, timezone
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


# ---------------------------------------------------------------------------
# Fixtures para Phase 04 — Web Dashboard MVP
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_analysis_json(tmp_path):
    """JSON mock de analise tiagofelicia com estrutura completa."""
    json_path = tmp_path / "analise.json"
    payload = {
        "generated_at": "2026-03-29",
        "current_supplier": "Meo Energia",
        "history_summary": {
            "months_analysed": 11,
            "latest_recommendation": "bihorario",
            "latest_top_3": [
                {"rank": 1, "supplier": "Luzboa", "plan": "Bi Base", "total_eur": 120.0},
                {"rank": 2, "supplier": "EDP", "plan": "Bi Eco", "total_eur": 125.0},
                {"rank": 3, "supplier": "Meo Energia", "plan": "Variavel", "total_eur": 166.54},
            ],
            "latest_current_supplier_result": {
                "supplier": "Meo Energia",
                "plan": "Variavel",
                "total_eur": 166.54,
            },
            "latest_saving_vs_current_eur": 46.54,
        },
        "history": [
            {
                "year_month": "2026-02",
                "total_kwh": 1200.0,
                "recommendation": "bihorario",
                "top_3": [],
            },
            {
                "year_month": "2026-01",
                "total_kwh": 1350.0,
                "recommendation": "bihorario",
                "top_3": [],
            },
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return json_path


@pytest.fixture
def sample_status_json():
    """monthly_status mock com generated_at de ontem."""
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )
    return {
        "status": "ok",
        "generated_at": yesterday,
        "report_path": "data/casa/reports/relatorio_eletricidade_2026-03-29.md",
        "latest_recommendation": "bihorario",
        "latest_saving_vs_current_eur": 46.54,
    }


@pytest.fixture
def sample_config_json(tmp_path, sample_tariffs, sample_contract):
    """system.json mock com 2 locations (casa, apartamento), paths relativos ao tmp_path."""
    config_path = tmp_path / "config" / "system.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Criar estrutura de diretorias para cada local
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
        },
    }
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


@pytest.fixture
def web_client(sample_config_json):
    """FastAPI TestClient com config mock via override de app.state.config_path."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from src.db.schema import metadata
    from src.web.app import app

    # Override config path to use the test config
    app.state.config_path = sample_config_json

    # Fornecer db_engine (necessario apos Phase 7)
    test_engine = create_engine("sqlite:///:memory:")
    metadata.create_all(test_engine)
    app.state.db_engine = test_engine

    client = TestClient(app)
    yield client
    test_engine.dispose()


@pytest.fixture
def db_engine_test():
    """SQLAlchemy engine para SQLite in-memory — tabelas Phase 7."""
    from sqlalchemy import create_engine
    from src.db.schema import metadata
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def web_client_sqlite(tmp_path, sample_tariffs, sample_contract):
    """FastAPI TestClient com local SQLite-only (sem pipeline CSV).

    Cria um local "teste-sqlite" apenas na BD SQLite — sem entrada no config.json.
    Inclui seed data de consumo, comparacoes e custos_reais.
    Usado para testar que o dashboard funciona para locais criados via UI (Phase 7).
    """
    import json as _json
    from datetime import datetime, timezone
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, insert
    from src.db.schema import metadata, locais, consumo_mensal, comparacoes, custos_reais
    from src.web.app import app

    # --- Engine SQLite in-memory com seed data ---
    test_engine = create_engine("sqlite:///:memory:")
    metadata.create_all(test_engine)

    top_3_data = [
        {"rank": 1, "supplier": "Luzboa", "plan": "Bi Base", "total_eur": 110.0},
        {"rank": 2, "supplier": "EDP", "plan": "Bi Eco", "total_eur": 120.0},
        {"rank": 3, "supplier": "Meo Energia", "plan": "Variavel", "total_eur": 155.0},
    ]
    csr_data = {"supplier": "Meo Energia", "plan": "Variavel", "total_eur": 155.0}
    cached_ts = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)

    with test_engine.begin() as conn:
        # Local SQLite-only — sem entrada em config.json
        conn.execute(insert(locais).values(
            id="teste-sqlite",
            name="Teste SQLite",
            cpe="PT0099999999999999XX",
            current_supplier="Meo Energia",
            current_plan_contains="Variavel",
            power_label="6.9 kVA",
        ))

        # Seed consumo_mensal (3 meses)
        for ym, total, vazio, fv in [
            ("2025-01", 1400.0, 560.0, 840.0),
            ("2025-02", 1550.0, 620.0, 930.0),
            ("2025-03", 1100.0, 440.0, 660.0),
        ]:
            conn.execute(insert(consumo_mensal).values(
                location_id="teste-sqlite",
                year_month=ym,
                total_kwh=total,
                vazio_kwh=vazio,
                fora_vazio_kwh=fv,
            ))

        # Seed comparacoes (2 meses)
        for ym in ("2025-02", "2025-03"):
            conn.execute(insert(comparacoes).values(
                location_id="teste-sqlite",
                year_month=ym,
                top_3_json=_json.dumps(top_3_data),
                current_supplier_result_json=_json.dumps(csr_data),
                generated_at="2026-03-01T10:00:00",
                cached_at=cached_ts,
            ))

        # Seed custos_reais (1 mes)
        conn.execute(insert(custos_reais).values(
            location_id="teste-sqlite",
            year_month="2025-01",
            custo_eur=145.50,
            source="pdf",
        ))

    # --- Config com locais CSV-pipeline + local SQLite-only nao incluido ---
    for location_id in ("casa", "apartamento"):
        (tmp_path / "data" / location_id / "raw" / "eredes").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / location_id / "processed").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / location_id / "reports").mkdir(parents=True, exist_ok=True)
        (tmp_path / "state" / location_id).mkdir(parents=True, exist_ok=True)

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
    config_path.write_text(_json.dumps(config_payload, indent=2), encoding="utf-8")

    # Override app state
    app.state.config_path = config_path
    app.state.project_root = tmp_path
    app.state.db_engine = test_engine

    yield TestClient(app)
    test_engine.dispose()
