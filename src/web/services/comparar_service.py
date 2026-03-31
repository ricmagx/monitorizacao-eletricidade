"""Comparacao de tarifarios usando dados locais (sem Playwright)."""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.db.schema import comparacoes
from src.web.services.data_loader import load_consumo_sqlite


def comparar_com_tarifarios(
    location_id: str,
    current_supplier: str | None,
    engine: Engine,
    tarifarios_path: Path,
) -> dict:
    """Calcula ranking de tarifarios para todos os meses do local e grava em comparacoes.

    Usa energy_compare.py local — nao requer Playwright nem acesso externo.

    Returns:
        {"meses": int} se OK, {"erro": str} se falhar.
    """
    from src.backend.energy_compare import (
        MonthlyConsumption,
        annual_cost_for_tariff,
        load_tariffs,
    )

    consumo_data = load_consumo_sqlite(location_id, engine)
    if not consumo_data:
        return {"erro": "Sem dados de consumo para este local. Importe um XLSX primeiro."}

    if not tarifarios_path.exists():
        return {"erro": f"Ficheiro de tarifarios nao encontrado: {tarifarios_path}"}

    try:
        tariffs = load_tariffs(tarifarios_path)
    except Exception as exc:
        return {"erro": f"Erro ao ler tarifarios.json: {exc}"}

    now = datetime.now(timezone.utc)

    for row in consumo_data:
        mc = MonthlyConsumption(
            year_month=row["year_month"],
            total_kwh=row["total_kwh"],
            vazio_kwh=row["vazio_kwh"],
            fora_vazio_kwh=row["fora_vazio_kwh"],
        )

        costs = []
        for t in tariffs:
            monthly_cost, _ = annual_cost_for_tariff([mc], t)
            costs.append({
                "supplier": t.supplier,
                "plan": t.plan,
                "total_eur": monthly_cost,
            })
        costs.sort(key=lambda x: x["total_eur"])
        top_3 = costs[:3]

        current_result = None
        if current_supplier:
            supplier_lower = current_supplier.lower()
            matches = [c for c in costs if c["supplier"].lower() == supplier_lower]
            if matches:
                current_result = matches[0]

        stmt = sqlite_insert(comparacoes).values(
            location_id=location_id,
            year_month=row["year_month"],
            top_3_json=json.dumps(top_3, ensure_ascii=False),
            current_supplier_result_json=(
                json.dumps(current_result, ensure_ascii=False) if current_result else None
            ),
            generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            cached_at=now,
        )
        upsert = stmt.on_conflict_do_update(
            index_elements=["location_id", "year_month"],
            set_={
                "top_3_json": stmt.excluded.top_3_json,
                "current_supplier_result_json": stmt.excluded.current_supplier_result_json,
                "generated_at": stmt.excluded.generated_at,
                "cached_at": now,
            },
        )
        with engine.begin() as conn:
            conn.execute(upsert)

    return {"meses": len(consumo_data)}
