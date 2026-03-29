from unittest.mock import patch
from pathlib import Path
import shutil
import pytest


def _copy_csv_to_processed(test_config, sample_csv):
    """Copia sample_csv para o processed_csv_path esperado pelo workflow."""
    import json
    config = json.loads(test_config.read_text(encoding="utf-8"))
    project_root = test_config.resolve().parent.parent
    processed_path = project_root / config["pipeline"]["processed_csv_path"]
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(sample_csv, processed_path)


def test_fallback_activated_on_network_error(test_config, sample_csv):
    """RES-01: Pipeline usa catalogo local quando tiagofelicia.pt inacessivel."""
    from monthly_workflow import run_workflow

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        result = run_workflow(config_path=test_config, input_xlsx=sample_csv)
    assert result["source"] == "local_catalog"


def test_report_indicates_local_catalog(test_config, sample_csv):
    """RES-01: Relatorio indica explicitamente que usou catalogo local."""
    from monthly_workflow import run_workflow

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        result = run_workflow(config_path=test_config, input_xlsx=sample_csv)
    report_text = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "catalogo local" in report_text.lower() or "catálogo local" in report_text.lower()


def test_fallback_reason_recorded(test_config, sample_csv):
    """RES-01: Resultado contem razao do fallback."""
    from monthly_workflow import run_workflow

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        result = run_workflow(config_path=test_config, input_xlsx=sample_csv)
    assert "fallback_reason" in result
    assert "ERR_NAME_NOT_RESOLVED" in result["fallback_reason"]
