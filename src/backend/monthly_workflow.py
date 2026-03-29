from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from eredes_download import download_latest_xlsx
from eredes_to_monthly_csv import convert_xlsx_to_monthly_csv
from tiagofelicia_compare import analyse_with_tiago


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_root_from_config(config_path: Path) -> Path:
    return config_path.resolve().parent.parent


def resolve_path(project_root: Path, relative_path: str) -> Path:
    return (project_root / relative_path).resolve()


def latest_xlsx_in_dir(directory: Path) -> Path | None:
    files = sorted(directory.glob("*.xlsx"))
    return files[-1] if files else None


def render_report(config: dict[str, Any], analysis: dict[str, Any], xlsx_path: Path, csv_path: Path) -> str:
    latest = analysis["history_summary"]
    seasonality = analysis["seasonality"]
    winner_counts = Counter(item["top_3"][0]["supplier"] for item in analysis["history"])
    lines = [
        "---",
        f"title: Relatório Eletricidade - {date.today().isoformat()}",
        "tags:",
        "  - hobbies/casa",
        "  - energia",
        "  - eletricidade",
        "  - relatorio",
        "created: " + date.today().isoformat(),
        "status: active",
        "area: hobbies",
        "---",
        "",
        f"# Relatório Eletricidade - {date.today().isoformat()}",
        "",
        "## Resultado",
        "",
        f"- Fornecedor atual: `{config['current_contract']['supplier']}`",
        f"- Potência contratada: `{config['current_contract']['power_label']}`",
        f"- Melhor opção no mês mais recente: `{latest['latest_top_3'][0]['supplier']}`",
        f"- Melhor ciclo horário: `{latest['latest_recommendation']}`",
        f"- Mudança recomendada: `{ 'sim' if latest['latest_change_needed'] else 'nao' }`",
        f"- Poupança estimada no último mês: `{latest['latest_saving_vs_current_eur']}` EUR",
        "",
        "## Top 3 mais recente",
        "",
    ]

    for idx, row in enumerate(latest["latest_top_3"], start=1):
        lines.append(
            f"{idx}. `{row['supplier']}` | `{row['plan']}` | `{row['cycle']}` | `{row['total_eur']}` EUR"
        )

    lines.extend(
        [
            "",
            "## Histórico",
            "",
            f"- Meses analisados: `{latest['months_analysed']}`",
            f"- `bihorario` venceu em `{latest['bihorario_wins']}` meses",
            f"- `simples` venceu em `{latest['simple_wins']}` meses",
            f"- Fornecedor mais frequente em 1.º lugar: `{winner_counts.most_common(1)[0][0]}`",
            "",
            "## Sazonalidade",
            "",
            f"- Consumo médio mensal: `{seasonality['avg_monthly_total_kwh']}` kWh",
            f"- Percentagem média em vazio: `{round(seasonality['avg_vazio_ratio'] * 100, 2)}`%",
            f"- Inverno médio: `{seasonality['winter_avg_kwh']}` kWh",
            f"- Verão médio: `{seasonality['summer_avg_kwh']}` kWh",
            "",
            "## Artefactos",
            "",
            f"- XLSX E-REDES: `{xlsx_path}`",
            f"- CSV mensal: `{csv_path}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def write_status(status_path: Path, payload: dict[str, Any]) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def notify_mac(title: str, message: str) -> None:
    subprocess.run(
        ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
        check=False,
        capture_output=True,
        text=True,
    )


def run_workflow(config_path: Path, input_xlsx: Path | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    project_root = project_root_from_config(config_path)
    pipeline = config["pipeline"]

    raw_dir = resolve_path(project_root, config["eredes"]["download_dir"])
    processed_csv_path = resolve_path(project_root, pipeline["processed_csv_path"])
    analysis_json_path = resolve_path(project_root, pipeline["analysis_json_path"])
    report_dir = resolve_path(project_root, pipeline["report_dir"])
    status_path = resolve_path(project_root, pipeline["status_path"])
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        if input_xlsx is not None:
            xlsx_path = input_xlsx.resolve()
        else:
            xlsx_path = download_latest_xlsx(config_path)
        if not xlsx_path.exists():
            raise RuntimeError("O ficheiro XLSX de entrada nao existe.")

        convert_xlsx_to_monthly_csv(
            xlsx_path,
            processed_csv_path,
            drop_partial_last_month=bool(pipeline.get("drop_partial_last_month", True)),
        )

        analysis = analyse_with_tiago(
            consumption_path=processed_csv_path,
            power_label=config["current_contract"]["power_label"],
            current_supplier=config["current_contract"]["supplier"],
            current_plan_contains=config["current_contract"].get("current_plan_contains"),
            months_limit=config["pipeline"].get("months_limit"),
        )
        analysis_json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        report_name = f"relatorio_eletricidade_{date.today().isoformat()}.md"
        report_path = report_dir / report_name
        report_path.write_text(render_report(config, analysis, xlsx_path, processed_csv_path), encoding="utf-8")

        status = {
            "status": "ok",
            "generated_at": datetime.now().isoformat(),
            "xlsx_path": str(xlsx_path),
            "processed_csv_path": str(processed_csv_path),
            "analysis_json_path": str(analysis_json_path),
            "report_path": str(report_path),
            "latest_change_needed": analysis["history_summary"]["latest_change_needed"],
            "latest_recommendation": analysis["history_summary"]["latest_recommendation"],
            "latest_saving_vs_current_eur": analysis["history_summary"]["latest_saving_vs_current_eur"],
        }
        write_status(status_path, status)
        if pipeline.get("notify_on_completion", False):
            notify_mac(
                "Eletricidade",
                f"Relatório pronto. Melhor ciclo: {analysis['history_summary']['latest_recommendation']}",
            )
        return status
    except Exception as exc:
        status = {
            "status": "error",
            "generated_at": datetime.now().isoformat(),
            "error": str(exc),
        }
        write_status(status_path, status)
        if pipeline.get("notify_on_completion", False):
            notify_mac("Eletricidade", f"Falha no job mensal: {exc}")
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workflow mensal completo: E-REDES -> CSV -> Tiago Felicia -> relatório.")
    parser.add_argument("--config", required=True, help="Config JSON do sistema.")
    parser.add_argument("--input-xlsx", help="Usa um XLSX manual em vez do download automatico.")
    parser.add_argument(
        "--allow-partial-last-month",
        action="store_true",
        help="Permite processar um ficheiro manual mesmo que o ultimo mes esteja incompleto.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config_path = Path(args.config)
    if args.allow_partial_last_month:
        config = load_config(config_path)
        config["pipeline"]["drop_partial_last_month"] = False
        tmp_path = config_path.parent / "_runtime_partial_override.json"
        tmp_path.write_text(json.dumps(config, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        try:
            result = run_workflow(
                config_path=tmp_path,
                input_xlsx=Path(args.input_xlsx) if args.input_xlsx else None,
            )
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        result = run_workflow(
            config_path=config_path,
            input_xlsx=Path(args.input_xlsx) if args.input_xlsx else None,
        )
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
