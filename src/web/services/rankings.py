"""Servico de ranking de fornecedores e recomendacao de mudanca.

Calcula ranking anual a partir de history[].top_3 + current_supplier_result
e constroi dados para o banner de recomendacao.
"""
from calendar import monthrange
from collections import defaultdict

SAVING_THRESHOLD_EUR = 50  # Per D-09: limiar para mostrar banner de recomendacao


def _monthly_cost_from_detalhe(
    vazio_kwh: float,
    fora_vazio_kwh: float,
    days_in_month: int,
    detalhe: dict,
) -> float:
    """Calcula custo estimado de um mes usando precos da ultima fatura.

    Aplica preco_base x IVA de cada linha ao consumo/dias do mes.
    Suporta bi-horario (energia_fv + energia_vn) e mono (energia).

    Args:
        vazio_kwh: kWh consumidos em vazio nesse mes.
        fora_vazio_kwh: kWh consumidos fora de vazio nesse mes.
        days_in_month: Numero de dias do mes.
        detalhe: Dict detalhe_json da ultima fatura (com campo 'linhas').

    Returns:
        Custo estimado em EUR com IVA incluido.
    """
    by_tipo = {l["tipo"]: l for l in detalhe.get("linhas", [])}
    total = 0.0

    def com_iva(linha: dict) -> float:
        return linha["preco_base"] * (1 + linha.get("iva_pct", 23) / 100)

    # Energia (bi-horario ou simples)
    if "energia_fv" in by_tipo and "energia_vn" in by_tipo:
        total += fora_vazio_kwh * com_iva(by_tipo["energia_fv"])
        total += vazio_kwh * com_iva(by_tipo["energia_vn"])
    elif "energia" in by_tipo:
        total += (vazio_kwh + fora_vazio_kwh) * com_iva(by_tipo["energia"])

    # Custos fixos por dia (potencia, cav)
    for tipo in ("potencia", "cav"):
        if tipo in by_tipo:
            total += days_in_month * com_iva(by_tipo[tipo])

    # IEC (imposto por kWh)
    if "iec" in by_tipo:
        total += (vazio_kwh + fora_vazio_kwh) * com_iva(by_tipo["iec"])

    # DGEG (fixo por mes)
    if "dgeg" in by_tipo:
        total += com_iva(by_tipo["dgeg"])

    return total


def calculate_annual_ranking(
    analysis: dict | None,
    current_supplier_name: str,
    consumo_data: list | None = None,
    ultimo_detalhe: dict | None = None,
    custos_reais: dict | None = None,
    current_plan: str = "",
) -> list[dict]:
    """Calcula ranking de fornecedores por custo anual estimado.

    Algoritmo:
    1. Iterar history[]
    2. Para cada mes, recolher todos os fornecedores de top_3 + current_supplier_result
    3. Somar total_eur por fornecedor ao longo dos meses
    4. Extrapolar para 12 meses: custo_anual = (soma_total / n_meses) * 12
    5. Ordenar por custo_anual (menor primeiro)
    6. Devolver top-5 + fornecedor actual (per D-08)

    Se o fornecedor actual nao constar nos tarifarios comparados, usa fallback:
    - Prioridade 1: consumo_data + ultimo_detalhe → recalcula mes a mes com precos da fatura
    - Prioridade 2: custos_reais → usa totais das faturas directamente

    Args:
        analysis: Dict de load_analysis_json ou None.
        current_supplier_name: Nome do fornecedor actual (para marcar is_current).
        consumo_data: Lista de dicts {year_month, vazio_kwh, fora_vazio_kwh, total_kwh}.
        ultimo_detalhe: detalhe_json da ultima fatura (linhas com preco_base por tipo).
        custos_reais: Dict {year_month: custo_eur} — fallback secundario.
        current_plan: Nome do plano actual para label no ranking.

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

        # Processar current_supplier_result (pode ser None explicitamente)
        csr = entry.get("current_supplier_result") or {}
        csr_name = csr.get("supplier", "")
        if csr_name:
            supplier_totals[csr_name]["total_eur"] += csr.get("total_eur", 0)
            supplier_totals[csr_name]["plan"] = csr.get("plan", "")
            supplier_totals[csr_name]["months_seen"] += 1

    # Fallback primario: recalcular mes a mes com precos individuais da ultima fatura
    if (
        current_supplier_name
        and ultimo_detalhe
        and consumo_data
        and supplier_totals[current_supplier_name]["months_seen"] == 0
    ):
        for row in consumo_data:
            year, month = map(int, row["year_month"].split("-"))
            days = monthrange(year, month)[1]
            custo = _monthly_cost_from_detalhe(
                row["vazio_kwh"], row["fora_vazio_kwh"], days, ultimo_detalhe
            )
            supplier_totals[current_supplier_name]["total_eur"] += custo
            supplier_totals[current_supplier_name]["months_seen"] += 1
        supplier_totals[current_supplier_name]["plan"] = current_plan or "Contrato actual"
        supplier_totals[current_supplier_name]["from_custos_reais"] = True

    # Fallback secundario: totais das faturas reais (sem detalhe_json disponivel)
    elif (
        current_supplier_name
        and custos_reais
        and supplier_totals[current_supplier_name]["months_seen"] == 0
    ):
        for ym, custo_eur in custos_reais.items():
            supplier_totals[current_supplier_name]["total_eur"] += custo_eur
            supplier_totals[current_supplier_name]["months_seen"] += 1
        supplier_totals[current_supplier_name]["plan"] = current_plan or "Contrato actual"
        supplier_totals[current_supplier_name]["from_custos_reais"] = True

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
            "from_custos_reais": data.get("from_custos_reais", False),
        })

    ranked.sort(key=lambda x: x["custo_anual_estimado"])

    # Top-5 + fornecedor actual (per D-08)
    top5 = ranked[:5]
    current_in_top5 = any(r["is_current"] for r in top5)
    if not current_in_top5:
        current_entry = next((r for r in ranked if r["is_current"]), None)
        if current_entry:
            top5.append(current_entry)

    # Calcular poupanca potencial em relacao ao fornecedor actual
    current_annual = next(
        (r["custo_anual_estimado"] for r in top5 if r["is_current"]), None
    )
    for r in top5:
        if current_annual is not None:
            r["poupanca_potencial"] = round(current_annual - r["custo_anual_estimado"], 2)
        else:
            r["poupanca_potencial"] = None

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
    saving_monthly = hs.get("latest_saving_vs_current_eur") or 0
    # Extrapolacao simples: poupanca mensal * 12
    saving_annual = saving_monthly * 12

    if saving_annual <= SAVING_THRESHOLD_EUR:
        return {"show": False}

    # Melhor fornecedor: primeiro do latest_top_3
    top3 = hs.get("latest_top_3", [])
    best_supplier = top3[0]["supplier"] if top3 else "desconhecido"
    best_plan = top3[0].get("plan", "") if top3 else ""

    saving_rounded = int(round(saving_annual, 0))
    message = f"Mudando para {best_supplier} — plano {best_plan}, poupa cerca de {saving_rounded} EUR/ano"
    return {
        "show": True,
        "supplier": best_supplier,
        "plan": best_plan,
        "saving_eur": float(saving_rounded),
        "message": message,
    }
