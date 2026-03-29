from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from energy_compare import MonthlyConsumption, load_monthly_consumption, seasonal_summary
from playwright.sync_api import Page, sync_playwright


SITE_URL = "https://www.tiagofelicia.pt/eletricidade-tiagofelicia.html"


def euros_to_float(text: str) -> float:
    cleaned = text.replace("€", "").replace(" ", "")
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    return float(cleaned)


def parse_row(cells: list[str], cycle_label: str, year_month: str) -> dict[str, Any]:
    lines = [line.strip() for line in cells[0].splitlines() if line.strip()]
    supplier = lines[0] if lines else ""
    plan = lines[1] if len(lines) > 1 else ""
    product_type = lines[2] if len(lines) > 2 else ""
    return {
        "supplier": supplier,
        "plan": plan,
        "product_type": product_type,
        "cycle": cycle_label,
        "year_month": year_month,
        "total_eur": euros_to_float(cells[1]),
        "energy_rate": cells[2].strip(),
        "power_rate": cells[3].strip(),
    }


def parse_results_table(page: Page, cycle_label: str, year_month: str) -> list[dict[str, Any]]:
    rows = page.locator("table tbody tr")
    count = rows.count()
    results: list[dict[str, Any]] = []
    for idx in range(count):
        cells = [cell.strip() for cell in rows.nth(idx).locator("td").all_inner_texts()]
        if len(cells) < 4:
            continue
        results.append(parse_row(cells, cycle_label=cycle_label, year_month=year_month))
    if not results:
        raise RuntimeError("Nao foi possivel extrair resultados da tabela do simulador.")
    return results


def open_complete_simulation(page: Page) -> None:
    page.goto(SITE_URL, wait_until="networkidle", timeout=60000)
    page.click('button:has-text("📝 Simulação Completa")')
    page.wait_for_timeout(1000)


def run_simple_simulation(page: Page, power_label: str, total_kwh: float, year_month: str) -> list[dict[str, Any]]:
    page.select_option("#potencia", label=power_label, force=True)
    page.select_option("#ciclo", value="Simples", force=True)
    page.fill("#kwh_S", str(round(total_kwh, 3)), force=True)
    page.dispatch_event("#kwh_S", "change")
    page.locator("#kwh_S").press("Tab")
    page.wait_for_timeout(4000)
    return parse_results_table(page, cycle_label="Simples", year_month=year_month)


def run_bi_simulation(
    page: Page, power_label: str, vazio_kwh: float, fora_vazio_kwh: float, year_month: str
) -> list[dict[str, Any]]:
    page.select_option("#potencia", label=power_label, force=True)
    page.select_option("#ciclo", value="Bi-horário - Ciclo Diário", force=True)
    page.wait_for_timeout(1000)
    page.fill("#kwh_V", str(round(vazio_kwh, 3)), force=True)
    page.fill("#kwh_F", str(round(fora_vazio_kwh, 3)), force=True)
    page.dispatch_event("#kwh_V", "change")
    page.locator("#kwh_V").press("Tab")
    page.dispatch_event("#kwh_F", "change")
    page.locator("#kwh_F").press("Tab")
    page.wait_for_timeout(4000)
    return parse_results_table(page, cycle_label="Bi-horário - Ciclo Diário", year_month=year_month)


def pick_current_result(
    combined: list[dict[str, Any]], current_supplier: str, current_plan_contains: str | None
) -> dict[str, Any] | None:
    supplier_lower = current_supplier.lower()
    plan_lower = current_plan_contains.lower() if current_plan_contains else None
    candidates = [item for item in combined if item["supplier"].lower() == supplier_lower]
    if plan_lower:
        exact = [item for item in candidates if plan_lower in item["plan"].lower()]
        if exact:
            return min(exact, key=lambda item: item["total_eur"])
    if candidates:
        return min(candidates, key=lambda item: item["total_eur"])
    return None


def compare_month(
    page: Page,
    month_row: MonthlyConsumption,
    power_label: str,
    current_supplier: str,
    current_plan_contains: str | None,
) -> dict[str, Any]:
    simple = run_simple_simulation(
        page, power_label=power_label, total_kwh=month_row.total_kwh, year_month=month_row.year_month
    )
    bi = run_bi_simulation(
        page,
        power_label=power_label,
        vazio_kwh=month_row.vazio_kwh,
        fora_vazio_kwh=month_row.fora_vazio_kwh,
        year_month=month_row.year_month,
    )
    combined = sorted(simple + bi, key=lambda item: item["total_eur"])
    current = pick_current_result(combined, current_supplier, current_plan_contains)
    supplier_not_found = current is None
    best_simple = min(simple, key=lambda item: item["total_eur"])
    best_bi = min(bi, key=lambda item: item["total_eur"])
    recommended = best_simple if best_simple["total_eur"] < best_bi["total_eur"] else best_bi
    recommendation_type = "simples" if recommended is best_simple else "bihorario"
    return {
        "year_month": month_row.year_month,
        "top_3": combined[:3],
        "current_supplier_result": current,
        "best_simple": best_simple,
        "best_bihorario": best_bi,
        "recommended_option": recommendation_type,
        "difference_simple_vs_bi_eur": round(abs(best_simple["total_eur"] - best_bi["total_eur"]), 2),
        "supplier_not_found": supplier_not_found,
        "needs_change": (
            current is not None and round(current["total_eur"] - combined[0]["total_eur"], 2) > 0.0
        ),
        "saving_vs_current_eur": (
            round(current["total_eur"] - combined[0]["total_eur"], 2) if current is not None else None
        ),
    }


def summarise_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    simple_wins = [item for item in history if item["recommended_option"] == "simples"]
    bi_wins = [item for item in history if item["recommended_option"] == "bihorario"]
    latest = history[-1]
    any_supplier_not_found = any(item.get("supplier_not_found", False) for item in history)
    return {
        "months_analysed": len(history),
        "simple_wins": len(simple_wins),
        "bihorario_wins": len(bi_wins),
        "latest_month": latest["year_month"],
        "latest_recommendation": latest["recommended_option"],
        "latest_top_3": latest["top_3"],
        "latest_current_supplier_result": latest["current_supplier_result"],
        "latest_change_needed": latest["needs_change"],
        "latest_saving_vs_current_eur": latest["saving_vs_current_eur"],
        "supplier_not_found": any_supplier_not_found,
    }


def analyse_with_tiago(
    consumption_path: Path,
    power_label: str,
    current_supplier: str,
    current_plan_contains: str | None = None,
    months_limit: int | None = None,
) -> dict[str, Any]:
    monthly_rows = load_monthly_consumption(consumption_path)
    if months_limit is not None:
        monthly_rows = monthly_rows[-months_limit:]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 2600})
        open_complete_simulation(page)

        history = []
        for row in monthly_rows:
            history.append(
                compare_month(
                    page=page,
                    month_row=row,
                    power_label=power_label,
                    current_supplier=current_supplier,
                    current_plan_contains=current_plan_contains,
                )
            )

        browser.close()

    return {
        "generated_at": date.today().isoformat(),
        "source": "tiagofelicia.pt",
        "power_label": power_label,
        "current_supplier": current_supplier,
        "current_plan_contains": current_plan_contains,
        "seasonality": seasonal_summary(monthly_rows),
        "history_summary": summarise_history(history),
        "history": history,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compara resultados do simulador Tiago Felicia para simples e bihorario."
    )
    parser.add_argument("--consumption", required=True, help="CSV com consumo mensal.")
    parser.add_argument("--power", required=True, help='Potencia contratada, ex: "6.90 kVA".')
    parser.add_argument("--current-supplier", required=True, help="Fornecedor atual.")
    parser.add_argument("--current-plan-contains", help="Parte do nome do plano atual.")
    parser.add_argument("--months-limit", type=int, help="Limita o numero de meses analisados.")
    parser.add_argument("--output", help="Ficheiro JSON de saida.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = analyse_with_tiago(
        consumption_path=Path(args.consumption),
        power_label=args.power,
        current_supplier=args.current_supplier,
        current_plan_contains=args.current_plan_contains,
        months_limit=args.months_limit,
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
