from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import energy_compare
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


def render_report(location: dict[str, Any], analysis: dict[str, Any], xlsx_path: Path, csv_path: Path) -> str:
    seasonality = analysis["seasonality"]
    source = analysis.get("source", "tiagofelicia.pt")
    is_local_catalog = source == "local_catalog"

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
    ]

    # Indicador de fonte (RES-01)
    if is_local_catalog:
        lines.extend([
            "> **Aviso:** Fonte: catalogo local (tiagofelicia.pt indisponivel — dados podem estar desactualizados)",
            f"> Razao: {analysis.get('fallback_reason', 'desconhecida')}",
            "",
        ])

    if is_local_catalog:
        # Estrutura de energy_compare.analyse()
        rec = analysis.get("change_recommendation", {})
        period_rec = analysis.get("period_recommendation", {})
        top_3 = analysis.get("top_3_suppliers", [])
        change_display = "sim" if rec.get("needs_change", False) else "nao"
        saving_eur = rec.get("monthly_saving_eur")
        saving_display = f"{saving_eur}" if saving_eur is not None else "N/A"
        recommended_cycle = period_rec.get("recommended_type", "N/A") if period_rec else "N/A"
        best_supplier = top_3[0]["supplier"] if top_3 else "N/A"
        lines.extend([
            f"- Fornecedor atual: `{location['current_contract']['supplier']}`",
            f"- Potência contratada: `{location['current_contract']['power_label']}`",
            f"- Melhor opção anual: `{best_supplier}`",
            f"- Melhor ciclo horário: `{recommended_cycle}`",
            f"- Mudança recomendada: `{change_display}`",
            f"- Poupança estimada mensal: `{saving_display}` EUR",
            "",
        ])
        lines.extend([
            "## Top 3 anual",
            "",
        ])
        for idx, row in enumerate(top_3[:3], start=1):
            lines.append(
                f"{idx}. `{row['supplier']}` | `{row['plan']}` | `{row['type']}` | `{row['annual_cost_eur']}` EUR/ano"
            )
        lines.extend([
            "",
            "## Informação",
            "",
            f"- Meses analisados: `{analysis.get('consumption_months', 'N/A')}`",
            "",
        ])
    else:
        # Estrutura de tiagofelicia_compare.analyse_with_tiago()
        latest = analysis["history_summary"]
        winner_counts = Counter(item["top_3"][0]["supplier"] for item in analysis["history"])

        change_display = "sim" if latest.get("latest_change_needed", False) else "nao"
        saving_display = latest["latest_saving_vs_current_eur"]
        if saving_display is None:
            saving_display = "N/A (fornecedor nao encontrado)"

        lines.extend([
            f"- Fornecedor atual: `{location['current_contract']['supplier']}`",
            f"- Potência contratada: `{location['current_contract']['power_label']}`",
            f"- Melhor opção no mês mais recente: `{latest['latest_top_3'][0]['supplier']}`",
            f"- Melhor ciclo horário: `{latest['latest_recommendation']}`",
            f"- Mudança recomendada: `{change_display}`",
            f"- Poupança estimada no último mês: `{saving_display}` EUR",
            "",
        ])

        # Aviso de fornecedor sem correspondencia (RES-03)
        if analysis.get("history_summary", {}).get("supplier_not_found", False):
            lines.extend([
                f"> **Aviso:** Fornecedor actual \"{location['current_contract']['supplier']}\" nao foi encontrado na tabela do simulador.",
                "> O ranking e apresentado sem comparacao com o contrato actual.",
                "",
            ])

        lines.extend([
            "## Top 3 mais recente",
            "",
        ])
        for idx, row in enumerate(latest["latest_top_3"], start=1):
            lines.append(
                f"{idx}. `{row['supplier']}` | `{row['plan']}` | `{row['cycle']}` | `{row['total_eur']}` EUR"
            )
        lines.extend([
            "",
            "## Histórico",
            "",
            f"- Meses analisados: `{latest['months_analysed']}`",
            f"- `bihorario` venceu em `{latest['bihorario_wins']}` meses",
            f"- `simples` venceu em `{latest['simple_wins']}` meses",
            f"- Fornecedor mais frequente em 1.º lugar: `{winner_counts.most_common(1)[0][0]}`",
            "",
        ])

    lines.extend([
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
    ])
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


def run_workflow(config: dict, location: dict, project_root: Path, input_xlsx: Path | None = None) -> dict[str, Any]:
    pipeline = location["pipeline"]

    raw_dir = resolve_path(project_root, pipeline["raw_dir"])
    processed_csv_path = resolve_path(project_root, pipeline["processed_csv_path"])
    analysis_json_path = resolve_path(project_root, pipeline["analysis_json_path"])
    report_dir = resolve_path(project_root, pipeline["report_dir"])
    status_path = resolve_path(project_root, pipeline["status_path"])
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        if input_xlsx is not None:
            xlsx_path = input_xlsx.resolve()
        else:
            xlsx_path = download_latest_xlsx(config_path=project_root / "config" / "system.json")
        if not xlsx_path.exists():
            raise RuntimeError("O ficheiro XLSX de entrada nao existe.")

        convert_xlsx_to_monthly_csv(
            xlsx_path,
            processed_csv_path,
            drop_partial_last_month=bool(pipeline.get("drop_partial_last_month", True)),
        )

        try:
            analysis = analyse_with_tiago(
                consumption_path=processed_csv_path,
                power_label=location["current_contract"]["power_label"],
                current_supplier=location["current_contract"]["supplier"],
                current_plan_contains=location["current_contract"].get("current_plan_contains"),
                months_limit=pipeline.get("months_limit"),
            )
            if "source" not in analysis:
                analysis["source"] = "tiagofelicia.pt"
        except Exception as exc:
            local_tariffs_path = resolve_path(project_root, pipeline["local_tariffs_path"])
            local_contract_path = resolve_path(project_root, pipeline["local_contract_path"])
            analysis = energy_compare.analyse(
                consumption_path=processed_csv_path,
                tariffs_path=local_tariffs_path,
                contract_path=local_contract_path,
            )
            analysis["source"] = "local_catalog"
            analysis["fallback_reason"] = str(exc)
        analysis_json_path.parent.mkdir(parents=True, exist_ok=True)
        analysis_json_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        report_name = f"relatorio_eletricidade_{date.today().isoformat()}.md"
        report_path = report_dir / report_name
        report_path.write_text(render_report(location, analysis, xlsx_path, processed_csv_path), encoding="utf-8")

        is_local_catalog = analysis.get("source") == "local_catalog"
        if is_local_catalog:
            rec = analysis.get("change_recommendation", {})
            period_rec = analysis.get("period_recommendation", {})
            status_latest_change = rec.get("needs_change", False)
            status_latest_recommendation = period_rec.get("recommended_type", "N/A") if period_rec else "N/A"
            status_latest_saving = rec.get("monthly_saving_eur")
        else:
            history_summary = analysis["history_summary"]
            status_latest_change = history_summary["latest_change_needed"]
            status_latest_recommendation = history_summary["latest_recommendation"]
            status_latest_saving = history_summary["latest_saving_vs_current_eur"]

        status = {
            "status": "ok",
            "generated_at": datetime.now().isoformat(),
            "xlsx_path": str(xlsx_path),
            "processed_csv_path": str(processed_csv_path),
            "analysis_json_path": str(analysis_json_path),
            "report_path": str(report_path),
            "latest_change_needed": status_latest_change,
            "latest_recommendation": status_latest_recommendation,
            "latest_saving_vs_current_eur": status_latest_saving,
            "source": analysis.get("source", "tiagofelicia.pt"),
            "fallback_reason": analysis.get("fallback_reason"),
        }
        write_status(status_path, status)
        if pipeline.get("notify_on_completion", False):
            notify_mac(
                "Eletricidade",
                f"[{location['name']}] Relatorio pronto. Melhor ciclo: {status_latest_recommendation}",
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
            notify_mac("Eletricidade", f"[{location['name']}] Falha no job mensal: {exc}")
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
    parser.add_argument(
        "--location",
        default=None,
        help="ID do local a processar (omitir = todos os locais).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    project_root = project_root_from_config(config_path)
    locations = config["locations"]

    if args.location:
        locations = [loc for loc in locations if loc["id"] == args.location]
        if not locations:
            print(f"Local '{args.location}' nao encontrado em config.", file=sys.stderr)
            return 1

    if args.allow_partial_last_month:
        # Override drop_partial_last_month for all locations
        for loc in locations:
            loc["pipeline"]["drop_partial_last_month"] = False

    results = []
    for loc in locations:
        result = run_workflow(
            config=config,
            location=loc,
            project_root=project_root,
            input_xlsx=Path(args.input_xlsx) if args.input_xlsx else None,
        )
        results.append({"location": loc["id"], **result})

    print(json.dumps(results, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
