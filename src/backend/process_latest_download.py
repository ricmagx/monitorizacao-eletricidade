from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cpe_routing import extract_cpe_from_filename, find_location_by_cpe
from monthly_workflow import run_workflow


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_matching_file(directory: Path, pattern: str) -> Path | None:
    files = [p for p in directory.glob(pattern) if p.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def project_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parent.parent


def resolve_path(project_root: Path, relative_path: str) -> Path:
    return (project_root / relative_path).resolve()


def file_signature(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def load_tracker(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_tracker(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def process_latest_download(config_path: Path, allow_partial_last_month: bool = False) -> dict[str, Any]:
    config = load_config(config_path)
    project_root = project_root_from_config(config_path)
    import os
    watch_dir = Path(config["eredes"].get("local_download_watch_dir", os.environ.get("UPLOAD_DIR", "data/uploads"))).expanduser()
    watch_pattern = config["eredes"].get("local_download_glob", "*.xlsx")
    latest = latest_matching_file(watch_dir, watch_pattern)
    if latest is None:
        raise RuntimeError(f"Nao encontrei nenhum XLSX em {watch_dir}")

    # Route by CPE extracted from filename
    cpe = extract_cpe_from_filename(latest.name)
    location = find_location_by_cpe(config["locations"], cpe) if cpe else None

    if location is None:
        return {
            "status": "skipped",
            "generated_at": datetime.now().isoformat(),
            "reason": "unknown_cpe",
            "cpe": cpe,
            "xlsx_path": str(latest.resolve()),
        }

    if allow_partial_last_month:
        location = dict(location)
        location["pipeline"] = dict(location["pipeline"])
        location["pipeline"]["drop_partial_last_month"] = False

    tracker_path = resolve_path(project_root, location["pipeline"]["last_processed_tracker_path"])
    latest_signature = file_signature(latest)
    previous = load_tracker(tracker_path)
    if previous == latest_signature:
        return {
            "status": "skipped",
            "generated_at": datetime.now().isoformat(),
            "reason": "latest_download_already_processed",
            "xlsx_path": latest_signature["path"],
        }

    result = run_workflow(config=config, location=location, project_root=project_root, input_xlsx=latest)

    if result.get("status") == "ok":
        save_tracker(tracker_path, latest_signature)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Processa o XLSX mais recente descarregado da E-REDES.")
    parser.add_argument("--config", required=True, help="Config JSON do sistema.")
    parser.add_argument(
        "--allow-partial-last-month",
        action="store_true",
        help="Permite processar ficheiros com ultimo mes incompleto.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = process_latest_download(
        config_path=Path(args.config),
        allow_partial_last_month=args.allow_partial_last_month,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
