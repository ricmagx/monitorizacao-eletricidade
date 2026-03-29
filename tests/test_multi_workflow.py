"""Tests for multi-location workflow (MULTI-03, MULTI-06) and CPE routing integration (MULTI-04)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper — minimal analysis dict returned by mocked analyse_with_tiago
# ---------------------------------------------------------------------------

def _minimal_tiago_analysis(supplier: str = "Meo Energia") -> dict:
    return {
        "generated_at": "2026-03-29",
        "source": "tiagofelicia.pt",
        "power_label": "10.35 kVA",
        "current_supplier": supplier,
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
            "supplier_not_found": False,
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
                "supplier_not_found": False,
                "best_simple": {"supplier": "Luzboa", "total_eur": 150.0},
                "best_bihorario": {"supplier": "Luzboa", "total_eur": 150.0},
                "recommended_option": "simples",
                "difference_simple_vs_bi_eur": 0.0,
                "needs_change": False,
                "saving_vs_current_eur": None,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Task 1 — monthly_workflow.py multi-location tests
# ---------------------------------------------------------------------------

def test_run_workflow_accepts_location_dict(multi_location_config, sample_csv):
    """MULTI-03: run_workflow(config, location, project_root, input_xlsx) runs without error."""
    from monthly_workflow import run_workflow, load_config, project_root_from_config

    config = load_config(multi_location_config)
    project_root = project_root_from_config(multi_location_config)
    location = config["locations"][0]

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.return_value = _minimal_tiago_analysis(location["current_contract"]["supplier"])
        result = run_workflow(config=config, location=location, project_root=project_root, input_xlsx=sample_csv)

    assert result["status"] == "ok"


def test_run_workflow_reads_contract_from_location(multi_location_config, sample_csv):
    """MULTI-03: render_report uses location['current_contract']['supplier'], not root-level."""
    from monthly_workflow import run_workflow, load_config, project_root_from_config

    config = load_config(multi_location_config)
    project_root = project_root_from_config(multi_location_config)
    location = config["locations"][0]  # casa — supplier "Meo Energia"

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.return_value = _minimal_tiago_analysis(location["current_contract"]["supplier"])
        result = run_workflow(config=config, location=location, project_root=project_root, input_xlsx=sample_csv)

    report_text = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Meo Energia" in report_text


def test_run_workflow_writes_to_location_paths(multi_location_config, sample_csv):
    """MULTI-03: Processed CSV written to location['pipeline']['processed_csv_path']."""
    from monthly_workflow import run_workflow, load_config, project_root_from_config

    config = load_config(multi_location_config)
    project_root = project_root_from_config(multi_location_config)
    location = config["locations"][0]  # casa

    with patch("monthly_workflow.convert_xlsx_to_monthly_csv") as mock_conv, \
         patch("monthly_workflow.analyse_with_tiago") as mock_at:
        mock_conv.side_effect = lambda src, dst, **kw: shutil.copy(sample_csv, dst)
        mock_at.return_value = _minimal_tiago_analysis(location["current_contract"]["supplier"])
        result = run_workflow(config=config, location=location, project_root=project_root, input_xlsx=sample_csv)

    # processed CSV should be inside data/casa/processed/
    assert "casa" in result["processed_csv_path"]
    # report should be inside data/casa/reports/
    assert "casa" in result["report_path"]


def test_main_location_filter(multi_location_config):
    """MULTI-03: main() with --location casa processes only casa."""
    import monthly_workflow

    call_location_ids = []

    def fake_run_workflow(config, location, project_root, input_xlsx=None):
        call_location_ids.append(location["id"])
        return {"status": "ok", "location": location["id"]}

    with patch.object(monthly_workflow, "run_workflow", side_effect=fake_run_workflow), \
         patch("sys.argv", ["monthly_workflow.py", "--config", str(multi_location_config), "--location", "casa"]):
        exit_code = monthly_workflow.main()

    assert exit_code == 0
    assert call_location_ids == ["casa"]


def test_main_all_locations(multi_location_config):
    """MULTI-03: main() without --location processes all locations sequentially."""
    import monthly_workflow

    call_location_ids = []

    def fake_run_workflow(config, location, project_root, input_xlsx=None):
        call_location_ids.append(location["id"])
        return {"status": "ok", "location": location["id"]}

    config = json.loads(multi_location_config.read_text(encoding="utf-8"))
    expected_count = len(config["locations"])

    with patch.object(monthly_workflow, "run_workflow", side_effect=fake_run_workflow), \
         patch("sys.argv", ["monthly_workflow.py", "--config", str(multi_location_config)]):
        exit_code = monthly_workflow.main()

    assert exit_code == 0
    assert len(call_location_ids) == expected_count


def test_main_unknown_location_exits_1(multi_location_config):
    """MULTI-03: main() with --location xyz exits with code 1."""
    import monthly_workflow

    with patch("sys.argv", ["monthly_workflow.py", "--config", str(multi_location_config), "--location", "xyz"]):
        exit_code = monthly_workflow.main()

    assert exit_code == 1


# ---------------------------------------------------------------------------
# Task 2 — process_latest_download.py CPE routing + eredes_download.py CPE hint
# ---------------------------------------------------------------------------

def test_process_routes_xlsx_by_cpe(multi_location_config, tmp_path):
    """MULTI-04: XLSX named with casa CPE is routed to casa location."""
    import process_latest_download as pld

    # Place an XLSX with casa's CPE in a fake watch_dir
    watch_dir = tmp_path / "downloads"
    watch_dir.mkdir()
    xlsx = watch_dir / "Consumos_PT0002000084968079SX_20260326042940.xlsx"
    xlsx.write_bytes(b"fake xlsx content")

    routed_location_ids = []

    def fake_run_workflow(config, location, project_root, input_xlsx=None):
        routed_location_ids.append(location["id"])
        return {"status": "ok"}

    # Patch config to use our custom watch_dir
    original_config = json.loads(multi_location_config.read_text(encoding="utf-8"))
    original_config["eredes"]["local_download_watch_dir"] = str(watch_dir)
    original_config["eredes"]["local_download_glob"] = "Consumos_*.xlsx"
    patched_config_path = tmp_path / "config" / "system.json"
    patched_config_path.parent.mkdir(parents=True, exist_ok=True)
    patched_config_path.write_text(json.dumps(original_config, indent=2), encoding="utf-8")

    with patch.object(pld, "run_workflow", side_effect=fake_run_workflow):
        result = pld.process_latest_download(config_path=patched_config_path)

    assert routed_location_ids == ["casa"]
    assert result.get("status") == "ok"


def test_process_skips_unknown_cpe(multi_location_config, tmp_path):
    """MULTI-04: XLSX with unknown CPE returns status='skipped', reason='unknown_cpe'."""
    import process_latest_download as pld

    watch_dir = tmp_path / "downloads"
    watch_dir.mkdir()
    xlsx = watch_dir / "Consumos_PT9999UNKNOWNCPE_20260326042940.xlsx"
    xlsx.write_bytes(b"fake xlsx content")

    original_config = json.loads(multi_location_config.read_text(encoding="utf-8"))
    original_config["eredes"]["local_download_watch_dir"] = str(watch_dir)
    original_config["eredes"]["local_download_glob"] = "Consumos_*.xlsx"
    patched_config_path = tmp_path / "config" / "system.json"
    patched_config_path.parent.mkdir(parents=True, exist_ok=True)
    patched_config_path.write_text(json.dumps(original_config, indent=2), encoding="utf-8")

    result = pld.process_latest_download(config_path=patched_config_path)

    assert result["status"] == "skipped"
    assert result["reason"] == "unknown_cpe"


def test_process_tracker_per_location(multi_location_config, tmp_path):
    """MULTI-04: Tracker saved to location['pipeline']['last_processed_tracker_path']."""
    import process_latest_download as pld

    watch_dir = tmp_path / "downloads"
    watch_dir.mkdir()
    xlsx = watch_dir / "Consumos_PT0002000084968079SX_20260326042940.xlsx"
    xlsx.write_bytes(b"fake xlsx content")

    original_config = json.loads(multi_location_config.read_text(encoding="utf-8"))
    original_config["eredes"]["local_download_watch_dir"] = str(watch_dir)
    original_config["eredes"]["local_download_glob"] = "Consumos_*.xlsx"
    patched_config_path = tmp_path / "config" / "system.json"
    patched_config_path.parent.mkdir(parents=True, exist_ok=True)
    patched_config_path.write_text(json.dumps(original_config, indent=2), encoding="utf-8")

    project_root = patched_config_path.resolve().parent.parent
    # Expected tracker path for casa
    casa_tracker = project_root / "state" / "casa" / "last_processed_download.json"

    def fake_run_workflow(config, location, project_root, input_xlsx=None):
        return {"status": "ok"}

    with patch.object(pld, "run_workflow", side_effect=fake_run_workflow):
        pld.process_latest_download(config_path=patched_config_path)

    assert casa_tracker.exists(), f"Tracker nao encontrado em {casa_tracker}"


def test_eredes_cpe_hint_in_notification(tmp_path):
    """MULTI-06: download_latest_xlsx external_firefox path calls notify_mac with CPE hint."""
    from eredes_download import download_latest_xlsx

    config_path = tmp_path / "config" / "system.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    watch_dir = tmp_path / "downloads"
    watch_dir.mkdir()

    config = {
        "eredes": {
            "home_url": "https://balcaodigital.e-redes.pt/home",
            "storage_state_path": "state/eredes_storage_state.json",
            "download_url": "https://balcaodigital.e-redes.pt/consumptions/history",
            "download_mode": "external_firefox",
            "browser_app": "Firefox",
            "interactive_wait_seconds": 5,
            "local_download_watch_dir": str(watch_dir),
            "local_download_glob": "Consumos_*.xlsx",
        },
        "locations": [
            {
                "id": "casa",
                "cpe": "PT0002000084968079SX",
            }
        ],
    }
    # Create fake storage state so it passes the existence check
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "eredes_storage_state.json").write_text("{}", encoding="utf-8")

    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    notify_calls = []

    def fake_notify(title, message):
        notify_calls.append((title, message))

    def fake_open(*args, **kwargs):
        pass

    # Place a new XLSX in watch_dir so the watcher finds it immediately
    import time
    before_time = time.time()
    new_xlsx = watch_dir / "Consumos_PT0002000084968079SX_20260326042940.xlsx"
    new_xlsx.write_bytes(b"fake")

    with patch("eredes_download.notify_mac", side_effect=fake_notify), \
         patch("subprocess.run", side_effect=fake_open):
        # The function will scan and find the file immediately and return
        result = download_latest_xlsx(config_path=config_path, cpe_hint="PT0002000084968079SX")

    # Check that a notification was sent with CPE in the message
    cpe_in_message = any("PT0002000084968079SX" in msg for _, msg in notify_calls)
    assert cpe_in_message, f"CPE hint not found in notify_mac calls: {notify_calls}"
