"""Testes para servico de rankings e recomendacoes de fornecedores.

Cobre:
- calculate_annual_ranking: calculo de ranking anual a partir de history[].top_3 + current_supplier_result
- build_recommendation: banner de recomendacao (so aparece quando poupanca > 50 EUR/ano)
"""
import pytest


def make_analysis(months=3, saving=74.8, current_total=263.12):
    """Helper para criar mock de analysis JSON com N meses de history."""
    history = []
    for i in range(months):
        ym = f"2025-{i + 1:02d}"
        history.append({
            "year_month": ym,
            "top_3": [
                {"supplier": "Ibelectra", "plan": "Indexado Bi-Horario", "total_eur": 188.32},
                {"supplier": "Goldenergy", "plan": "Bi-Horario Gold", "total_eur": 192.45},
                {"supplier": "Luzboa", "plan": "Bi-Horario Verde", "total_eur": 195.10},
            ],
            "current_supplier_result": {
                "supplier": "Meo Energia",
                "plan": "Tarifa Variavel",
                "total_eur": current_total,
            },
            "saving_vs_current_eur": saving,
        })
    return {
        "current_supplier": "Meo Energia",
        "history_summary": {
            "months_analysed": months,
            "latest_top_3": history[-1]["top_3"] if history else [],
            "latest_current_supplier_result": history[-1]["current_supplier_result"] if history else {},
            "latest_saving_vs_current_eur": saving,
            "latest_change_needed": saving > 0,
        },
        "history": history,
    }


# ---------------------------------------------------------------------------
# calculate_annual_ranking
# ---------------------------------------------------------------------------


def test_calculate_annual_ranking_basic():
    """Com 3 meses, retorna lista ordenada por custo_anual_estimado (menor primeiro).
    Cada entry tem keys supplier, plan, custo_anual_estimado, is_current.
    """
    from src.web.services.rankings import calculate_annual_ranking

    analysis = make_analysis(months=3)
    result = calculate_annual_ranking(analysis, "Meo Energia")

    assert len(result) >= 4  # top-3 + current (nao esta no top-3)
    # Ordenado por custo_anual_estimado (menor primeiro)
    for i in range(len(result) - 1):
        assert result[i]["custo_anual_estimado"] <= result[i + 1]["custo_anual_estimado"]
    # Verificar keys obrigatorias
    for entry in result:
        assert "supplier" in entry
        assert "plan" in entry
        assert "custo_anual_estimado" in entry
        assert "is_current" in entry
    # Fornecedor actual marcado
    current_entries = [r for r in result if r["is_current"]]
    assert len(current_entries) == 1
    assert current_entries[0]["supplier"] == "Meo Energia"


def test_calculate_annual_ranking_top5():
    """Com history que tem 8 fornecedores distintos, retorna no maximo 6 entries (top-5 + actual)."""
    from src.web.services.rankings import calculate_annual_ranking

    # Criar analysis com 8 fornecedores distintos no top_3
    history_entry = {
        "year_month": "2025-01",
        "top_3": [
            {"supplier": "A", "plan": "Pa", "total_eur": 100.0},
            {"supplier": "B", "plan": "Pb", "total_eur": 110.0},
            {"supplier": "C", "plan": "Pc", "total_eur": 120.0},
            {"supplier": "D", "plan": "Pd", "total_eur": 130.0},
            {"supplier": "E", "plan": "Pe", "total_eur": 140.0},
            {"supplier": "F", "plan": "Pf", "total_eur": 150.0},
            {"supplier": "G", "plan": "Pg", "total_eur": 160.0},
            {"supplier": "H", "plan": "Ph", "total_eur": 170.0},
        ],
        "current_supplier_result": {
            "supplier": "Meo Energia",
            "plan": "Tarifa Variavel",
            "total_eur": 263.12,
        },
    }
    analysis = {
        "current_supplier": "Meo Energia",
        "history_summary": {
            "months_analysed": 1,
            "latest_top_3": history_entry["top_3"],
            "latest_current_supplier_result": history_entry["current_supplier_result"],
            "latest_saving_vs_current_eur": 163.12,
            "latest_change_needed": True,
        },
        "history": [history_entry],
    }
    result = calculate_annual_ranking(analysis, "Meo Energia")
    # Deve retornar top-5 + actual (actual nao esta no top-5)
    assert len(result) == 6
    # Actual deve estar no resultado
    assert any(r["is_current"] for r in result)


def test_calculate_annual_ranking_current_in_top5():
    """Se fornecedor actual esta no top-5, nao duplica — retorna exactamente 5 entries."""
    from src.web.services.rankings import calculate_annual_ranking

    # Meo Energia ja esta no top_3 → deve estar no top-5 → nao adicionar novamente
    history_entry = {
        "year_month": "2025-01",
        "top_3": [
            {"supplier": "Ibelectra", "plan": "Indexado", "total_eur": 100.0},
            {"supplier": "Goldenergy", "plan": "Gold", "total_eur": 110.0},
            {"supplier": "Meo Energia", "plan": "Tarifa Variavel", "total_eur": 120.0},
        ],
        "current_supplier_result": {
            "supplier": "Meo Energia",
            "plan": "Tarifa Variavel",
            "total_eur": 120.0,
        },
    }
    analysis = {
        "current_supplier": "Meo Energia",
        "history_summary": {},
        "history": [history_entry],
    }
    result = calculate_annual_ranking(analysis, "Meo Energia")
    # Apenas 3 fornecedores distintos (Meo ja esta no top_3 e em current_supplier_result)
    suppliers = [r["supplier"] for r in result]
    assert suppliers.count("Meo Energia") == 1  # Nao duplicado
    assert len(result) <= 5  # No maximo top-5


def test_calculate_annual_ranking_empty():
    """Com analysis=None ou history vazio, retorna lista vazia."""
    from src.web.services.rankings import calculate_annual_ranking

    assert calculate_annual_ranking(None, "Meo Energia") == []
    assert calculate_annual_ranking({}, "Meo Energia") == []
    assert calculate_annual_ranking({"history": []}, "Meo Energia") == []


# ---------------------------------------------------------------------------
# build_recommendation
# ---------------------------------------------------------------------------


def test_build_recommendation_significant():
    """Com poupanca > 50 EUR/ano, retorna show=True com supplier e saving_eur e message."""
    from src.web.services.rankings import build_recommendation

    # saving mensal 74.8 * 12 = 897.6 EUR/ano → significativo
    analysis = make_analysis(saving=74.8)
    result = build_recommendation(analysis)

    assert result["show"] is True
    assert result["supplier"] == "Ibelectra"
    assert result["saving_eur"] > 50
    assert "Podes poupar" in result["message"]
    assert "Ibelectra" in result["message"]
    assert "EUR/ano" in result["message"]


def test_build_recommendation_insignificant():
    """Com poupanca < 50 EUR/ano (anualisada), retorna {"show": False}."""
    from src.web.services.rankings import build_recommendation

    # saving mensal 3.0 * 12 = 36 EUR/ano → insignificante
    analysis = make_analysis(saving=3.0)
    result = build_recommendation(analysis)

    assert result == {"show": False}


def test_build_recommendation_no_data():
    """Com analysis=None, retorna {"show": False}."""
    from src.web.services.rankings import build_recommendation

    assert build_recommendation(None) == {"show": False}
    assert build_recommendation({}) == {"show": False}
