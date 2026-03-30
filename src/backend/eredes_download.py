from __future__ import annotations

import argparse
import json
import logging
import time
from shutil import copy2
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


HOME_URL = "https://balcaodigital.e-redes.pt/home"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parent.parent


def resolve_path(project_root: Path, relative_path: str) -> Path:
    return (project_root / relative_path).resolve()


def click_first_visible_text(page, texts: list[str]) -> str:
    for text in texts:
        locator = page.locator(f'text="{text}"').first
        if locator.count() and locator.is_visible():
            locator.click()
            return text
    raise RuntimeError(f"Nao encontrei nenhum botao/link visivel para: {texts}")


def assert_logged_in(page) -> None:
    body = " ".join(page.locator("body").inner_text().split())
    if "Bem-vindo ao Balcão Digital" in body and "Login" in body and "Registe-se" in body:
        raise RuntimeError("Sessao E-REDES invalida ou expirada. Execute novo bootstrap de login.")


def notify_mac(title: str, message: str) -> None:
    # TODO Phase 7: substituir por notificacao web
    logger.info("Notificacao [%s]: %s", title, message)


def latest_matching_file(directory: Path, pattern: str, min_mtime: float) -> Path | None:
    files = [p for p in directory.glob(pattern) if p.is_file() and p.stat().st_mtime >= min_mtime]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def snapshot_matching_files(directory: Path, pattern: str) -> dict[str, float]:
    return {p.name: p.stat().st_mtime for p in directory.glob(pattern) if p.is_file()}


def changed_file_since_snapshot(directory: Path, pattern: str, before: dict[str, float]) -> Path | None:
    changed: list[Path] = []
    for path in directory.glob(pattern):
        if not path.is_file():
            continue
        previous_mtime = before.get(path.name)
        current_mtime = path.stat().st_mtime
        if previous_mtime is None or current_mtime > previous_mtime:
            changed.append(path)
    if not changed:
        return None
    return max(changed, key=lambda p: p.stat().st_mtime)


def download_latest_xlsx(config_path: Path, cpe_hint: str | None = None) -> Path:
    config = load_config(config_path)
    project_root = project_root_from_config(config_path)
    eredes = config["eredes"]

    storage_state_path = resolve_path(project_root, eredes["storage_state_path"])
    if not storage_state_path.exists():
        raise RuntimeError("Sessao E-REDES inexistente. Execute primeiro o bootstrap de login.")

    download_dir_base = eredes.get("download_dir_base") or eredes.get("download_dir", "data/raw/eredes")
    # Resolve a static download dir (substitui {location_id} pelo primeiro local se existir)
    download_dir = resolve_path(project_root, download_dir_base.replace("{location_id}", "raw"))
    download_dir.mkdir(parents=True, exist_ok=True)
    download_url = eredes.get("download_url") or HOME_URL
    navigation_click_texts = eredes.get("navigation_click_texts", [])
    download_button_candidates = eredes.get("download_button_candidates", [])
    timeout_ms = int(eredes.get("download_timeout_seconds", 60) * 1000)
    mode = eredes.get("download_mode", "assisted")
    interactive_wait_seconds = int(eredes.get("interactive_wait_seconds", 900))
    watch_dir = Path(eredes.get("local_download_watch_dir", "/app/data/uploads")).expanduser()
    watch_pattern = eredes.get("local_download_glob", "*.xlsx")
    browser_app = eredes.get("browser_app", "Firefox")

    if mode == "external_firefox":
        before_snapshot = snapshot_matching_files(watch_dir, watch_pattern)
        if cpe_hint:
            notify_mac("E-REDES", f"CPE: {cpe_hint} -- Seleccione o CPE correcto no portal e descarregue o Excel.")
        notify_mac(
            "E-REDES",
            "Abra o Firefox, descarregue o Excel e o sistema vai importar o ficheiro.",
        )
        # TODO Phase 7: substituir por notificacao web (open -a nao disponivel no Docker)
        logger.info("external_firefox mode: URL=%s browser_app=%s", download_url, browser_app)
        print(f"Modo external_firefox: aceda a {download_url} e descarregue o Excel.")
        deadline = time.time() + interactive_wait_seconds
        while time.time() < deadline:
            found = changed_file_since_snapshot(watch_dir, watch_pattern, before_snapshot)
            if found is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target = download_dir / f"{timestamp}_{found.name}"
                copy2(found, target)
                return target
            time.sleep(2)
        raise RuntimeError("Nao foi encontrado nenhum XLSX novo em Downloads apos o download no Firefox.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=(mode == "headless"))
        context = browser.new_context(storage_state=str(storage_state_path), accept_downloads=True)
        page = context.new_page()
        try:
            page.goto(download_url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            # The E-REDES portal may hold long-lived network requests on the security page.
            pass
        page.wait_for_timeout(2000)
        if mode == "headless":
            assert_logged_in(page)

        for text in navigation_click_texts:
            click_first_visible_text(page, [text])
            page.wait_for_timeout(1500)

        try:
            if mode == "headless":
                with page.expect_download(timeout=timeout_ms) as download_info:
                    click_first_visible_text(page, download_button_candidates)
                download = download_info.value
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                suggested_name = download.suggested_filename or f"eredes_{timestamp}.xlsx"
                target = download_dir / f"{timestamp}_{suggested_name}"
                download.save_as(str(target))
            else:
                before_snapshot = snapshot_matching_files(watch_dir, watch_pattern)
                notify_mac(
                    "E-REDES",
                    "Valide a segurança e clique em Exportar excel no Balcão Digital.",
                )
                print("Browser aberto em modo assistido. Valide a segurança e conclua o download do Excel.")
                target = None
                deadline = time.time() + interactive_wait_seconds
                while time.time() < deadline:
                    found = changed_file_since_snapshot(watch_dir, watch_pattern, before_snapshot)
                    if found is not None:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        target = download_dir / f"{timestamp}_{found.name}"
                        copy2(found, target)
                        break
                    page.wait_for_timeout(2000)
                if target is None:
                    raise RuntimeError("Nao foi encontrado nenhum XLSX novo em Downloads apos a exportacao.")
        except PlaywrightTimeoutError as exc:
            raise RuntimeError("Nao foi possivel concluir o download na pagina da E-REDES.") from exc

        context.storage_state(path=str(storage_state_path))
        browser.close()
        return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Descarrega o XLSX mensal da E-REDES usando sessao guardada.")
    parser.add_argument("--config", required=True, help="Config JSON do sistema.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    path = download_latest_xlsx(Path(args.config))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
