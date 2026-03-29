import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest


def _make_location_from_test_config(test_config: Path) -> tuple[dict, dict, Path]:
    """Constroi config, location e project_root a partir do test_config (schema legado).

    Retorna (config_dict, location_dict, project_root) para chamar run_workflow com a
    nova assinatura multi-location.
    """
    config = json.loads(test_config.read_text(encoding="utf-8"))
    project_root = test_config.resolve().parent.parent
    old_pipeline = config["pipeline"]
    # Adaptar schema legado para schema multi-location: adicionar raw_dir
    pipeline = {
        "raw_dir": config.get("eredes", {}).get("download_dir", "data/raw/eredes"),
        **old_pipeline,
    }
    location = {
        "id": "test",
        "name": "Test",
        "cpe": "PT_TEST",
        "current_contract": config["current_contract"],
        "pipeline": pipeline,
    }
    return config, location, project_root


def test_fallback_activated_on_network_error(test_config, sample_csv):
    """RES-01: Pipeline usa catalogo local quando tiagofelicia.pt inacessivel."""
    from monthly_workflow import run_workflow

    config, location, project_root = _make_location_from_test_config(test_config)

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        result = run_workflow(config=config, location=location, project_root=project_root, input_xlsx=sample_csv)
    assert result["source"] == "local_catalog"


def test_report_indicates_local_catalog(test_config, sample_csv):
    """RES-01: Relatorio indica explicitamente que usou catalogo local."""
    from monthly_workflow import run_workflow

    config, location, project_root = _make_location_from_test_config(test_config)

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        result = run_workflow(config=config, location=location, project_root=project_root, input_xlsx=sample_csv)
    report_text = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "catalogo local" in report_text.lower() or "catálogo local" in report_text.lower()


def test_fallback_reason_recorded(test_config, sample_csv):
    """RES-01: Resultado contem razao do fallback."""
    from monthly_workflow import run_workflow

    config, location, project_root = _make_location_from_test_config(test_config)

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.side_effect = Exception("net::ERR_NAME_NOT_RESOLVED")
        result = run_workflow(config=config, location=location, project_root=project_root, input_xlsx=sample_csv)
    assert "fallback_reason" in result
    assert "ERR_NAME_NOT_RESOLVED" in result["fallback_reason"]
