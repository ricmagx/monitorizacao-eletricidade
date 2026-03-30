from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parent.parent


def resolve_path(project_root: Path, relative_path: str) -> Path:
    return (project_root / relative_path).resolve()


def notify_mac(title: str, message: str) -> None:
    # TODO Phase 7: substituir por notificacao web
    logger.info("Notificacao reminder [%s]: %s", title, message)


def open_browser(browser_app: str, url: str) -> None:
    # TODO Phase 7: substituir por notificacao web (browser nao disponivel no Docker)
    logger.info("open_browser desactivado no Docker: browser_app=%s url=%s", browser_app, url)


def run_reminder(config_path: Path) -> list[dict[str, Any]]:
    config = load_config(config_path)
    project_root = project_root_from_config(config_path)
    browser_app = config["eredes"].get("browser_app", "Firefox")
    download_url = config["eredes"]["download_url"]

    results = []
    for loc in config["locations"]:
        location_name = loc.get("name", loc["id"])
        status_path = resolve_path(project_root, loc["pipeline"]["status_path"])
        status_path.parent.mkdir(parents=True, exist_ok=True)

        message = f"[{location_name}] Descarregue o mes anterior completo da E-REDES e depois processe o XLSX."
        notify_mac(f"Eletricidade -- {location_name}", message)
        open_browser(browser_app, download_url)

        status = {
            "status": "waiting_for_download",
            "generated_at": datetime.now().isoformat(),
            "location": loc["id"],
            "message": message,
            "browser_app": browser_app,
            "download_url": download_url,
        }
        status_path.write_text(json.dumps(status, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        results.append(status)

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lembrete mensal: abre E-REDES e notifica o utilizador.")
    parser.add_argument("--config", required=True, help="Config JSON do sistema.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    results = run_reminder(Path(args.config))
    print(json.dumps(results, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
