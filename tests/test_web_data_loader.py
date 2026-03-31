"""Testes para src/web/services/data_loader.py"""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.web.services.data_loader import (
    build_consumo_multi_ano,
    build_custo_chart_data,
    build_resumo_anual,
    build_comparacao_meses,
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


# ---------------------------------------------------------------------------
# Testes para funcoes SQLite (Phase 9)
# ---------------------------------------------------------------------------


def test_load_consumo_sqlite(db_engine_test):
    """load_consumo_sqlite retorna lista de dicts ordenada por year_month."""
    from sqlalchemy import insert
    from src.db.schema import consumo_mensal
    from src.web.services.data_loader import load_consumo_sqlite

    with db_engine_test.begin() as conn:
        for ym, total, vazio, fv in [
            ("2025-02", 1550.0, 620.0, 930.0),
            ("2025-01", 1400.0, 560.0, 840.0),
        ]:
            conn.execute(insert(consumo_mensal).values(
                location_id="teste",
                year_month=ym,
                total_kwh=total,
                vazio_kwh=vazio,
                fora_vazio_kwh=fv,
            ))

    rows = load_consumo_sqlite("teste", db_engine_test)
    assert len(rows) == 2
    assert rows[0]["year_month"] == "2025-01"
    assert rows[1]["year_month"] == "2025-02"
    assert "vazio_kwh" in rows[0]
    assert "fora_vazio_kwh" in rows[0]
    assert rows[0]["total_kwh"] == pytest.approx(1400.0)


def test_build_analysis_from_sqlite(db_engine_test):
    """build_analysis_from_sqlite retorna dict compativel com calculate_annual_ranking."""
    import json as _json
    from datetime import datetime, timezone
    from sqlalchemy import insert
    from src.db.schema import comparacoes
    from src.web.services.data_loader import build_analysis_from_sqlite

    top_3 = [
        {"rank": 1, "supplier": "Luzboa", "plan": "Bi Base", "total_eur": 110.0},
        {"rank": 2, "supplier": "EDP", "plan": "Bi Eco", "total_eur": 120.0},
        {"rank": 3, "supplier": "Meo Energia", "plan": "Variavel", "total_eur": 155.0},
    ]
    csr = {"supplier": "Meo Energia", "plan": "Variavel", "total_eur": 155.0}

    with db_engine_test.begin() as conn:
        for ym in ("2025-02", "2025-03"):
            conn.execute(insert(comparacoes).values(
                location_id="teste",
                year_month=ym,
                top_3_json=_json.dumps(top_3),
                current_supplier_result_json=_json.dumps(csr),
                generated_at="2026-03-01T10:00:00",
                cached_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ))

    result = build_analysis_from_sqlite("teste", db_engine_test)
    assert result is not None
    assert "history" in result
    assert "history_summary" in result
    assert len(result["history"]) == 2
    # Deve ter latest_top_3 em history_summary
    assert "latest_top_3" in result["history_summary"]
    assert "latest_saving_vs_current_eur" in result["history_summary"]


def test_build_analysis_from_sqlite_empty(db_engine_test):
    """build_analysis_from_sqlite retorna None se sem dados."""
    from src.web.services.data_loader import build_analysis_from_sqlite

    result = build_analysis_from_sqlite("local-inexistente", db_engine_test)
    assert result is None


def test_get_freshness_from_sqlite(db_engine_test):
    """get_freshness_from_sqlite calcula frescura a partir de MAX(cached_at) de comparacoes."""
    import json as _json
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import insert
    from src.db.schema import comparacoes
    from src.web.services.data_loader import get_freshness_from_sqlite

    recent_ts = datetime.now(timezone.utc) - timedelta(days=5)
    with db_engine_test.begin() as conn:
        conn.execute(insert(comparacoes).values(
            location_id="teste",
            year_month="2025-03",
            top_3_json=_json.dumps([]),
            current_supplier_result_json=_json.dumps({}),
            generated_at="2026-03-01T10:00:00",
            cached_at=recent_ts,
        ))

    result = get_freshness_from_sqlite("teste", db_engine_test)
    assert result["days_ago"] is not None
    assert result["days_ago"] <= 6  # 5 dias atras, margem de 1 dia
    assert result["is_stale"] is False


def test_freshness_source_fresh(db_engine_test):
    """cached_at recente (<48h) -> source='fresh'."""
    import json as _json
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import insert
    from src.db.schema import comparacoes
    from src.web.services.data_loader import get_freshness_from_sqlite

    recent_ts = datetime.now(timezone.utc) - timedelta(hours=1)
    with db_engine_test.begin() as conn:
        conn.execute(insert(comparacoes).values(
            location_id="teste-fresh",
            year_month="2025-03",
            top_3_json=_json.dumps([]),
            current_supplier_result_json=_json.dumps({}),
            generated_at="2026-03-01T10:00:00",
            cached_at=recent_ts,
        ))

    result = get_freshness_from_sqlite("teste-fresh", db_engine_test)
    assert result["source"] == "fresh"
    assert result["is_stale"] is False


def test_freshness_source_cache(db_engine_test):
    """cached_at antigo (>48h) -> source='cache'."""
    import json as _json
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import insert
    from src.db.schema import comparacoes
    from src.web.services.data_loader import get_freshness_from_sqlite

    old_ts = datetime.now(timezone.utc) - timedelta(hours=72)
    with db_engine_test.begin() as conn:
        conn.execute(insert(comparacoes).values(
            location_id="teste-cache",
            year_month="2025-03",
            top_3_json=_json.dumps([]),
            current_supplier_result_json=_json.dumps({}),
            generated_at="2026-03-01T10:00:00",
            cached_at=old_ts,
        ))

    result = get_freshness_from_sqlite("teste-cache", db_engine_test)
    assert result["source"] == "cache"
    assert result["is_stale"] is False


def test_freshness_source_none(db_engine_test):
    """Sem comparacoes -> source='none'."""
    from src.web.services.data_loader import get_freshness_from_sqlite
    result = get_freshness_from_sqlite("local-inexistente", db_engine_test)
    assert result["source"] == "none"


def test_freshness_source_stale_is_cache(db_engine_test):
    """cached_at de 50 dias -> source='cache' e is_stale=True."""
    import json as _json
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import insert
    from src.db.schema import comparacoes
    from src.web.services.data_loader import get_freshness_from_sqlite

    stale_ts = datetime.now(timezone.utc) - timedelta(days=50)
    with db_engine_test.begin() as conn:
        conn.execute(insert(comparacoes).values(
            location_id="teste-stale",
            year_month="2025-03",
            top_3_json=_json.dumps([]),
            current_supplier_result_json=_json.dumps({}),
            generated_at="2026-03-01T10:00:00",
            cached_at=stale_ts,
        ))

    result = get_freshness_from_sqlite("teste-stale", db_engine_test)
    assert result["source"] == "cache"
    assert result["is_stale"] is True


# ---------------------------------------------------------------------------
# Testes para funcoes multi-ano (Phase 11)
# ---------------------------------------------------------------------------


class TestMultiAno:
    """Testes para build_consumo_multi_ano, build_resumo_anual, build_comparacao_meses."""

    CONSUMO_3_ANOS = [
        # 2023
        {"year_month": "2023-01", "total_kwh": 1400.0, "vazio_kwh": 560.0, "fora_vazio_kwh": 840.0},
        {"year_month": "2023-06", "total_kwh": 800.0, "vazio_kwh": 320.0, "fora_vazio_kwh": 480.0},
        {"year_month": "2023-12", "total_kwh": 1300.0, "vazio_kwh": 520.0, "fora_vazio_kwh": 780.0},
        # 2024
        {"year_month": "2024-01", "total_kwh": 1450.0, "vazio_kwh": 580.0, "fora_vazio_kwh": 870.0},
        {"year_month": "2024-03", "total_kwh": 1100.0, "vazio_kwh": 440.0, "fora_vazio_kwh": 660.0},
        # 2025
        {"year_month": "2025-01", "total_kwh": 1500.0, "vazio_kwh": 600.0, "fora_vazio_kwh": 900.0},
        {"year_month": "2025-03", "total_kwh": 1050.0, "vazio_kwh": 420.0, "fora_vazio_kwh": 630.0},
    ]

    COMPARACOES_HISTORY = [
        {"year_month": "2023-01", "current_supplier_result": {"supplier": "Meo", "total_eur": 200.0}},
        {"year_month": "2024-01", "current_supplier_result": {"supplier": "Meo", "total_eur": 210.0}},
        {"year_month": "2024-03", "current_supplier_result": {"supplier": "Meo", "total_eur": 180.0}},
        {"year_month": "2025-01", "current_supplier_result": {"supplier": "Meo", "total_eur": 215.0}},
    ]

    def test_consumo_multi_ano_3_anos(self):
        """build_consumo_multi_ano retorna 3 anos com datasets correctos."""
        result = build_consumo_multi_ano(self.CONSUMO_3_ANOS)
        assert sorted(result["anos"]) == ["2023", "2024", "2025"]
        assert result["meses"] == ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                                    "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        assert len(result["datasets"]) == 3
        # Verificar dataset 2023 — indice 0 = Jan, indice 5 = Jun
        ds_2023 = next(d for d in result["datasets"] if d["ano"] == "2023")
        assert ds_2023["vazio"][0] == pytest.approx(560.0)   # Jan
        assert ds_2023["fora_vazio"][0] == pytest.approx(840.0)  # Jan
        assert ds_2023["vazio"][5] == pytest.approx(320.0)   # Jun
        assert ds_2023["vazio"][11] == pytest.approx(520.0)  # Dez

    def test_consumo_multi_ano_meses_em_falta(self):
        """build_consumo_multi_ano preenche None para meses sem dados."""
        result = build_consumo_multi_ano(self.CONSUMO_3_ANOS)
        ds_2024 = next(d for d in result["datasets"] if d["ano"] == "2024")
        # 2024 so tem Jan e Mar — Feb (indice 1) deve ser None
        assert ds_2024["vazio"][1] is None
        assert ds_2024["fora_vazio"][1] is None
        # Jan (indice 0) deve ter valor
        assert ds_2024["vazio"][0] == pytest.approx(580.0)

    def test_resumo_anual_sem_comparacoes(self):
        """build_resumo_anual com comparacoes_history=None retorna custo_total_eur=None."""
        result = build_resumo_anual(self.CONSUMO_3_ANOS, None)
        assert len(result) == 3
        anos = {r["ano"] for r in result}
        assert anos == {"2023", "2024", "2025"}
        for r in result:
            assert r["custo_total_eur"] is None
            assert r["consumo_total_kwh"] > 0

    def test_comparacao_meses_basica(self):
        """build_comparacao_meses retorna consumo e custo correctos para mes existente."""
        result = build_comparacao_meses(
            self.CONSUMO_3_ANOS,
            self.COMPARACOES_HISTORY,
            ano1="2024",
            ano2="2025",
            mes="01",
        )
        assert result["mes"] == "01"
        assert result["ano1"] == "2024"
        assert result["ano2"] == "2025"
        assert result["consumo_ano1"] == pytest.approx(1450.0)
        assert result["consumo_ano2"] == pytest.approx(1500.0)
        assert result["custo_ano1"] == pytest.approx(210.0)
        assert result["custo_ano2"] == pytest.approx(215.0)
