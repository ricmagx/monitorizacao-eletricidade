import shutil
import pytest


def test_compare_month_marks_supplier_not_found():
    """RES-03: compare_month inclui supplier_not_found quando fornecedor sem match."""
    from tiagofelicia_compare import compare_month
    from energy_compare import MonthlyConsumption
    from unittest.mock import MagicMock, patch
    import tiagofelicia_compare

    fake_results = [
        {
            "supplier": "Luzboa",
            "plan": "Mono",
            "product_type": "",
            "cycle": "Simples",
            "year_month": "2025-01",
            "total_eur": 150.0,
            "energy_rate": "0.16",
            "power_rate": "0.30",
        },
    ]
    mock_page = MagicMock()
    with patch.object(tiagofelicia_compare, "run_simple_simulation", return_value=fake_results), \
         patch.object(tiagofelicia_compare, "run_bi_simulation", return_value=fake_results):
        result = compare_month(
            page=mock_page,
            month_row=MonthlyConsumption("2025-01", 1429.0, 571.6, 857.4),
            power_label="10.35 kVA",
            current_supplier="Fornecedor Inexistente XYZ",
            current_plan_contains=None,
        )
    assert result["supplier_not_found"] is True
    assert result["current_supplier_result"] is None


def test_report_warns_when_supplier_not_found(test_config, sample_csv):
    """RES-03: Relatorio contem aviso quando fornecedor sem match no simulador."""
    from monthly_workflow import run_workflow
    from unittest.mock import patch

    fake_analysis = {
        "generated_at": "2026-03-29",
        "source": "tiagofelicia.pt",
        "power_label": "10.35 kVA",
        "current_supplier": "Fornecedor Inexistente",
        "current_plan_contains": None,
        "seasonality": {
            "avg_monthly_total_kwh": 1362.0,
            "avg_vazio_ratio": 0.4,
            "winter_avg_kwh": 1492.0,
            "summer_avg_kwh": None,
            "monthly_profile": [],
        },
        "history_summary": {
            "months_analysed": 1,
            "simple_wins": 1,
            "bihorario_wins": 0,
            "latest_month": "2025-01",
            "latest_recommendation": "simples",
            "latest_top_3": [
                {
                    "supplier": "Luzboa",
                    "plan": "Mono",
                    "cycle": "Simples",
                    "year_month": "2025-01",
                    "total_eur": 150.0,
                    "energy_rate": "0.16",
                    "power_rate": "0.30",
                }
            ],
            "latest_current_supplier_result": None,
            "latest_change_needed": False,
            "latest_saving_vs_current_eur": None,
            "supplier_not_found": True,
        },
        "history": [
            {
                "year_month": "2025-01",
                "top_3": [
                    {
                        "supplier": "Luzboa",
                        "plan": "Mono",
                        "cycle": "Simples",
                        "year_month": "2025-01",
                        "total_eur": 150.0,
                        "energy_rate": "0.16",
                        "power_rate": "0.30",
                    }
                ],
                "current_supplier_result": None,
                "supplier_not_found": True,
                "best_simple": {"supplier": "Luzboa", "total_eur": 150.0},
                "best_bihorario": {"supplier": "Luzboa", "total_eur": 150.0},
                "recommended_option": "simples",
                "difference_simple_vs_bi_eur": 0.0,
                "needs_change": False,
                "saving_vs_current_eur": None,
            }
        ],
    }
    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago", return_value=fake_analysis):
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        result = run_workflow(config_path=test_config, input_xlsx=sample_csv)
    report_text = open(result["report_path"], encoding="utf-8").read()
    assert "nao foi encontrado" in report_text.lower() or "não foi encontrado" in report_text.lower()


def test_pipeline_does_not_crash_on_missing_supplier(test_config, sample_csv):
    """RES-03: Pipeline termina sem excepcao quando fornecedor sem match."""
    from monthly_workflow import run_workflow
    from unittest.mock import patch

    fake_analysis = {
        "generated_at": "2026-03-29",
        "source": "tiagofelicia.pt",
        "power_label": "10.35 kVA",
        "current_supplier": "Fornecedor Inexistente",
        "current_plan_contains": None,
        "seasonality": {
            "avg_monthly_total_kwh": 1362.0,
            "avg_vazio_ratio": 0.4,
            "winter_avg_kwh": 1492.0,
            "summer_avg_kwh": None,
            "monthly_profile": [],
        },
        "history_summary": {
            "months_analysed": 1,
            "simple_wins": 1,
            "bihorario_wins": 0,
            "latest_month": "2025-01",
            "latest_recommendation": "simples",
            "latest_top_3": [
                {
                    "supplier": "Luzboa",
                    "plan": "Mono",
                    "cycle": "Simples",
                    "year_month": "2025-01",
                    "total_eur": 150.0,
                    "energy_rate": "0.16",
                    "power_rate": "0.30",
                }
            ],
            "latest_current_supplier_result": None,
            "latest_change_needed": False,
            "latest_saving_vs_current_eur": None,
            "supplier_not_found": True,
        },
        "history": [
            {
                "year_month": "2025-01",
                "top_3": [
                    {
                        "supplier": "Luzboa",
                        "plan": "Mono",
                        "cycle": "Simples",
                        "year_month": "2025-01",
                        "total_eur": 150.0,
                        "energy_rate": "0.16",
                        "power_rate": "0.30",
                    }
                ],
                "current_supplier_result": None,
                "supplier_not_found": True,
                "best_simple": {"supplier": "Luzboa", "total_eur": 150.0},
                "best_bihorario": {"supplier": "Luzboa", "total_eur": 150.0},
                "recommended_option": "simples",
                "difference_simple_vs_bi_eur": 0.0,
                "needs_change": False,
                "saving_vs_current_eur": None,
            }
        ],
    }
    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago", return_value=fake_analysis):
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        result = run_workflow(config_path=test_config, input_xlsx=sample_csv)
    assert result["status"] == "ok"
