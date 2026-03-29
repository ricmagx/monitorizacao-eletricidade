from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


HOME_URL = "https://balcaodigital.e-redes.pt/home"


def visible_actions(page) -> list[str]:
    items = page.locator("a,button").evaluate_all(
        """
els => els
  .map(e => (e.innerText || e.getAttribute('aria-label') || '').trim())
  .filter(Boolean)
"""
    )
    return list(dict.fromkeys(items))


def bootstrap_session(storage_state_path: Path, context_path: Path) -> None:
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        )
        context = browser.new_context()
        page = context.new_page()
        page.goto(HOME_URL, wait_until="networkidle", timeout=60000)

        print("Faça login no Balcão Digital da E-REDES e navegue até à página de onde costuma descarregar o Excel.")
        input("Quando estiver autenticado e na página certa, pressione Enter aqui no terminal.")

        context.storage_state(path=str(storage_state_path))
        context_info = {
            "captured_at": datetime.now().isoformat(),
            "current_url": page.url,
            "visible_actions": visible_actions(page),
        }
        context_path.write_text(json.dumps(context_info, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        browser.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap manual da sessao E-REDES para reutilizacao automatica."
    )
    parser.add_argument("--storage-state", required=True, help="Ficheiro JSON da sessao Playwright.")
    parser.add_argument(
        "--context-output",
        required=True,
        help="JSON com URL e acoes visiveis da pagina onde o utilizador terminou o bootstrap.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    bootstrap_session(Path(args.storage_state), Path(args.context_output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
