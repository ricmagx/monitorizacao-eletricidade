from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def project_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parent.parent


def plist_content(
    label: str,
    python_bin: str,
    process_script: Path,
    config_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    watch_paths: list[str],
) -> str:
    watch_paths_xml = "\n".join(f"    <string>{path}</string>" for path in watch_paths)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python_bin}</string>
    <string>{process_script}</string>
    <string>--config</string>
    <string>{config_path}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{project_root_from_config(config_path)}</string>
  <key>WatchPaths</key>
  <array>
{watch_paths_xml}
  </array>
  <key>StandardOutPath</key>
  <string>{stdout_path}</string>
  <key>StandardErrorPath</key>
  <string>{stderr_path}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera um ficheiro plist launchd para processar novos XLSX da E-REDES.")
    parser.add_argument("--config", required=True, help="Config JSON do sistema.")
    parser.add_argument("--output", required=True, help="Caminho do plist a gerar.")
    parser.add_argument("--python-bin", default="python3", help="Binario Python a usar no launchd.")
    parser.add_argument(
        "--label",
        default="com.ricmag.monitorizacao-eletricidade.process-latest",
        help="Label launchd.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_root = project_root_from_config(config_path)
    process_script = (project_root / "src/backend/process_latest_download.py").resolve()
    stdout_path = (project_root / "state/launchd.process.stdout.log").resolve()
    stderr_path = (project_root / "state/launchd.process.stderr.log").resolve()
    watch_paths = config.get("watcher", {}).get("watch_paths", [str(Path.home() / "Downloads")])
    content = plist_content(
        label=args.label,
        python_bin=args.python_bin,
        process_script=process_script,
        config_path=config_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        watch_paths=watch_paths,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
