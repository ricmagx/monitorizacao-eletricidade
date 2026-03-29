from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class MonthlyConsumption:
    year_month: str
    total_kwh: float
    vazio_kwh: float
    fora_vazio_kwh: float

    @property
    def year(self) -> int:
        return int(self.year_month.split("-")[0])

    @property
    def month(self) -> int:
        return int(self.year_month.split("-")[1])

    @property
    def vazio_ratio(self) -> float:
        if self.total_kwh <= 0:
            return 0.0
        return self.vazio_kwh / self.total_kwh

    @property
    def days_in_month(self) -> int:
        year, month = self.year, self.month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        return (next_month - date(year, month, 1)).days


@dataclass(frozen=True)
class Tariff:
    tariff_id: str
    supplier: str
    plan: str
    tariff_type: str
    energy_simple: float | None
    energy_vazio: float | None
    energy_fora_vazio: float | None
    fixed_daily_power: float
    source_url: str
    valid_from: str | None
    valid_to: str | None


def load_monthly_consumption(path: Path) -> list[MonthlyConsumption]:
    rows: list[MonthlyConsumption] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"year_month", "total_kwh", "vazio_kwh", "fora_vazio_kwh"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(f"Faltam colunas no CSV de consumo: {missing_str}")

        for raw in reader:
            rows.append(
                MonthlyConsumption(
                    year_month=raw["year_month"],
                    total_kwh=float(raw["total_kwh"]),
                    vazio_kwh=float(raw["vazio_kwh"]),
                    fora_vazio_kwh=float(raw["fora_vazio_kwh"]),
                )
            )

    if not rows:
        raise ValueError("O CSV de consumo esta vazio.")
    return rows


def load_tariffs(path: Path) -> list[Tariff]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    tariffs = []
    for raw in payload["tariffs"]:
        energy = raw.get("energy", {})
        fixed_daily = raw.get("fixed_daily", {})
        tariffs.append(
            Tariff(
                tariff_id=raw["id"],
                supplier=raw["supplier"],
                plan=raw["plan"],
                tariff_type=raw["type"],
                energy_simple=energy.get("simples"),
                energy_vazio=energy.get("vazio"),
                energy_fora_vazio=energy.get("fora_vazio"),
                fixed_daily_power=float(fixed_daily.get("power_contract", 0.0)),
                source_url=raw.get("source_url", ""),
                valid_from=raw.get("valid_from"),
                valid_to=raw.get("valid_to"),
            )
        )
    if not tariffs:
        raise ValueError("O catalogo de tarifarios esta vazio.")
    return tariffs


def load_current_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "current_tariff_id" not in payload:
        raise ValueError("O ficheiro do contrato atual precisa de current_tariff_id.")
    return payload


def load_alert_settings(path: Path | None) -> dict[str, Any]:
    defaults = {
        "min_monthly_saving_eur": 8.0,
        "min_annual_saving_eur": 96.0,
        "require_current_prices": True,
        "require_manual_review": True,
    }
    if path is None:
        return defaults
    payload = json.loads(path.read_text(encoding="utf-8"))
    defaults.update(payload.get("alerts", {}))
    return defaults


def annual_cost_for_tariff(
    monthly_rows: list[MonthlyConsumption], tariff: Tariff
) -> tuple[float, list[dict[str, Any]]]:
    monthly_costs: list[dict[str, Any]] = []
    total_cost = 0.0
    for row in monthly_rows:
        fixed_cost = tariff.fixed_daily_power * row.days_in_month
        if tariff.tariff_type == "simples":
            if tariff.energy_simple is None:
                raise ValueError(f"Tarifario simples sem preco simples: {tariff.tariff_id}")
            energy_cost = row.total_kwh * tariff.energy_simple
        elif tariff.tariff_type == "bihorario":
            if tariff.energy_vazio is None or tariff.energy_fora_vazio is None:
                raise ValueError(
                    f"Tarifario bihorario sem preco vazio/fora_vazio: {tariff.tariff_id}"
                )
            energy_cost = (
                row.vazio_kwh * tariff.energy_vazio
                + row.fora_vazio_kwh * tariff.energy_fora_vazio
            )
        else:
            raise ValueError(f"Tipo de tarifario nao suportado: {tariff.tariff_type}")

        month_cost = fixed_cost + energy_cost
        total_cost += month_cost
        monthly_costs.append(
            {
                "year_month": row.year_month,
                "fixed_cost_eur": round(fixed_cost, 2),
                "energy_cost_eur": round(energy_cost, 2),
                "total_cost_eur": round(month_cost, 2),
            }
        )

    return round(total_cost, 2), monthly_costs


def month_name(month: int) -> str:
    names = {
        1: "jan",
        2: "fev",
        3: "mar",
        4: "abr",
        5: "mai",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "set",
        10: "out",
        11: "nov",
        12: "dez",
    }
    return names[month]


def seasonal_summary(monthly_rows: list[MonthlyConsumption]) -> dict[str, Any]:
    by_month: dict[int, list[MonthlyConsumption]] = {}
    for row in monthly_rows:
        by_month.setdefault(row.month, []).append(row)

    monthly_profile = []
    for month, rows in sorted(by_month.items()):
        avg_total = mean(item.total_kwh for item in rows)
        avg_vazio_ratio = mean(item.vazio_ratio for item in rows)
        monthly_profile.append(
            {
                "month": month,
                "label": month_name(month),
                "avg_total_kwh": round(avg_total, 2),
                "avg_vazio_ratio": round(avg_vazio_ratio, 4),
            }
        )

    avg_total_year = mean(item.total_kwh for item in monthly_rows)
    avg_vazio_year = mean(item.vazio_ratio for item in monthly_rows)
    winter = [r.total_kwh for r in monthly_rows if r.month in {11, 12, 1, 2}]
    summer = [r.total_kwh for r in monthly_rows if r.month in {6, 7, 8, 9}]
    return {
        "avg_monthly_total_kwh": round(avg_total_year, 2),
        "avg_vazio_ratio": round(avg_vazio_year, 4),
        "winter_avg_kwh": round(mean(winter), 2) if winter else None,
        "summer_avg_kwh": round(mean(summer), 2) if summer else None,
        "monthly_profile": monthly_profile,
    }


def recommendation_text(
    current_result: dict[str, Any],
    best_result: dict[str, Any],
    alert_settings: dict[str, Any],
) -> dict[str, Any]:
    annual_saving = round(current_result["annual_cost_eur"] - best_result["annual_cost_eur"], 2)
    monthly_saving = round(annual_saving / 12, 2)
    needs_change = (
        annual_saving >= alert_settings["min_annual_saving_eur"]
        and monthly_saving >= alert_settings["min_monthly_saving_eur"]
        and best_result["tariff_id"] != current_result["tariff_id"]
    )
    return {
        "needs_change": needs_change,
        "annual_saving_eur": annual_saving,
        "monthly_saving_eur": monthly_saving,
        "message": (
            f"Mudar para {best_result['supplier']} - {best_result['plan']}"
            if needs_change
            else "Nao ha necessidade clara de mudanca com os limiares atuais"
        ),
    }


def analyse(
    consumption_path: Path,
    tariffs_path: Path,
    contract_path: Path,
    alerts_path: Path | None = None,
) -> dict[str, Any]:
    monthly_rows = load_monthly_consumption(consumption_path)
    tariffs = load_tariffs(tariffs_path)
    current_contract = load_current_contract(contract_path)
    alert_settings = load_alert_settings(alerts_path)

    tariff_map = {tariff.tariff_id: tariff for tariff in tariffs}
    current_tariff_id = current_contract["current_tariff_id"]
    if current_tariff_id not in tariff_map:
        raise ValueError(f"Tarifario atual nao encontrado no catalogo: {current_tariff_id}")

    results = []
    for tariff in tariffs:
        annual_cost, monthly_costs = annual_cost_for_tariff(monthly_rows, tariff)
        results.append(
            {
                "tariff_id": tariff.tariff_id,
                "supplier": tariff.supplier,
                "plan": tariff.plan,
                "type": tariff.tariff_type,
                "annual_cost_eur": annual_cost,
                "monthly_costs": monthly_costs,
                "source_url": tariff.source_url,
            }
        )

    results.sort(key=lambda item: item["annual_cost_eur"])
    top_3 = results[:3]
    current_result = next(item for item in results if item["tariff_id"] == current_tariff_id)
    best_result = results[0]
    mono_best = next((item for item in results if item["type"] == "simples"), None)
    bi_best = next((item for item in results if item["type"] == "bihorario"), None)

    period_recommendation = None
    if mono_best and bi_best:
        diff = round(abs(mono_best["annual_cost_eur"] - bi_best["annual_cost_eur"]), 2)
        better = mono_best if mono_best["annual_cost_eur"] < bi_best["annual_cost_eur"] else bi_best
        period_recommendation = {
            "recommended_type": better["type"],
            "annual_difference_eur": diff,
            "mono_best_annual_cost_eur": mono_best["annual_cost_eur"],
            "bi_best_annual_cost_eur": bi_best["annual_cost_eur"],
            "message": (
                "Bihorario compensa face ao melhor mono-horario"
                if better["type"] == "bihorario"
                else "Mono-horario compensa face ao melhor bihorario"
            ),
        }

    return {
        "generated_at": date.today().isoformat(),
        "consumption_months": len(monthly_rows),
        "seasonality": seasonal_summary(monthly_rows),
        "current_contract": {
            "supplier": current_contract.get("supplier"),
            "plan": current_contract.get("plan"),
            "tariff_id": current_tariff_id,
            "annual_cost_eur": current_result["annual_cost_eur"],
        },
        "top_3_suppliers": top_3,
        "period_recommendation": period_recommendation,
        "change_recommendation": recommendation_text(current_result, best_result, alert_settings),
        "all_results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compara comercializadores de eletricidade com base no consumo mensal."
    )
    parser.add_argument("--consumption", required=True, help="CSV com consumo mensal.")
    parser.add_argument("--tariffs", required=True, help="JSON com catalogo de tarifarios.")
    parser.add_argument("--contract", required=True, help="JSON com contrato atual.")
    parser.add_argument("--alerts", help="JSON com regras de alerta.")
    parser.add_argument("--output", help="Ficheiro JSON de saida.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = analyse(
        consumption_path=Path(args.consumption),
        tariffs_path=Path(args.tariffs),
        contract_path=Path(args.contract),
        alerts_path=Path(args.alerts) if args.alerts else None,
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
