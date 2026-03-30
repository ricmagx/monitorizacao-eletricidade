"""Servico de ranking de fornecedores e recomendacao de mudanca.

Calcula ranking anual a partir de history[].top_3 + current_supplier_result
e constroi dados para o banner de recomendacao.
"""
from collections import defaultdict

SAVING_THRESHOLD_EUR = 50  # Per D-09: limiar para mostrar banner de recomendacao


def calculate_annual_ranking(
    analysis: dict | None,
    current_supplier_name: str,
) -> list[dict]:
    """Calcula ranking de fornecedores por custo anual estimado.

    Algoritmo:
    1. Iterar history[]
    2. Para cada mes, recolher todos os fornecedores de top_3 + current_supplier_result
    3. Somar total_eur por fornecedor ao longo dos meses
    4. Extrapolar para 12 meses: custo_anual = (soma_total / n_meses) * 12
    5. Ordenar por custo_anual (menor primeiro)
    6. Devolver top-5 + fornecedor actual (per D-08)

    Args:
        analysis: Dict de load_analysis_json ou None.
        current_supplier_name: Nome do fornecedor actual (para marcar is_current).

    Returns:
        Lista de dicts com keys: supplier, plan, custo_anual_estimado, is_current.
        Lista vazia se sem dados.
    """
    if not analysis or "history" not in analysis:
        return []

    history = analysis["history"]
    if not history:
        return []

    # Acumular custo total e plano por fornecedor
    supplier_totals: dict = defaultdict(lambda: {"total_eur": 0.0, "plan": "", "months_seen": 0})

    for entry in history:
        # Processar top_3
        for s in entry.get("top_3", []):
            name = s.get("supplier", "")
            if not name:
                continue
            supplier_totals[name]["total_eur"] += s.get("total_eur", 0)
            supplier_totals[name]["plan"] = s.get("plan", "")
            supplier_totals[name]["months_seen"] += 1

        # Processar current_supplier_result
        csr = entry.get("current_supplier_result", {})
        csr_name = csr.get("supplier", "")
        if csr_name:
            supplier_totals[csr_name]["total_eur"] += csr.get("total_eur", 0)
            supplier_totals[csr_name]["plan"] = csr.get("plan", "")
            supplier_totals[csr_name]["months_seen"] += 1

    # Calcular custo anual estimado (extrapolado para 12 meses)
    ranked = []
    for supplier, data in supplier_totals.items():
        if data["months_seen"] > 0:
            custo_anual = (data["total_eur"] / data["months_seen"]) * 12
        else:
            custo_anual = 0.0
        ranked.append({
            "supplier": supplier,
            "plan": data["plan"],
            "custo_anual_estimado": round(custo_anual, 2),
            "is_current": supplier == current_supplier_name,
        })

    ranked.sort(key=lambda x: x["custo_anual_estimado"])

    # Top-5 + fornecedor actual (per D-08)
    top5 = ranked[:5]
    current_in_top5 = any(r["is_current"] for r in top5)
    if not current_in_top5:
        current_entry = next((r for r in ranked if r["is_current"]), None)
        if current_entry:
            top5.append(current_entry)

    return top5


def build_recommendation(analysis: dict | None) -> dict:
    """Constroi dados para o banner de recomendacao.

    Per D-09: Banner "Podes poupar ~X EUR/ano mudando para [Fornecedor]"
    So aparece se poupanca anual > SAVING_THRESHOLD_EUR (50 EUR/ano).

    A poupanca mensal do history_summary e extrapolada para 12 meses.

    Args:
        analysis: Dict de load_analysis_json ou None.

    Returns:
        Dict com show=True, supplier, saving_eur, message — se poupanca significativa.
        Dict com show=False — se nao significativa ou sem dados.
    """
    if not analysis or "history_summary" not in analysis:
        return {"show": False}

    hs = analysis["history_summary"]
    saving_monthly = hs.get("latest_saving_vs_current_eur", 0)
    # Extrapolacao simples: poupanca mensal * 12
    saving_annual = saving_monthly * 12

    if saving_annual <= SAVING_THRESHOLD_EUR:
        return {"show": False}

    # Melhor fornecedor: primeiro do latest_top_3
    top3 = hs.get("latest_top_3", [])
    best_supplier = top3[0]["supplier"] if top3 else "desconhecido"

    saving_rounded = int(round(saving_annual, 0))
    return {
        "show": True,
        "supplier": best_supplier,
        "saving_eur": float(saving_rounded),
        "message": f"Podes poupar ~{saving_rounded} EUR/ano mudando para {best_supplier}",
    }
