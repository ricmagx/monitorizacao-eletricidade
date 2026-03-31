"""Servico de ingestao de XLSX E-REDES para SQLite."""
from pathlib import Path
from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.backend.cpe_routing import extract_cpe_from_filename
from src.backend.eredes_to_monthly_csv import parse_xlsx_to_dict
from src.db.schema import consumo_mensal
from src.web.services.locais_service import get_local_by_cpe


def ingerir_xlsx(tmp_path: Path, filename: str, engine: Engine) -> dict:
    """Ingere XLSX E-REDES: detecta CPE, resolve local, escreve em SQLite.

    Args:
        tmp_path: Path para o ficheiro XLSX temporario no disco.
        filename: Nome original do ficheiro (para extrair CPE).
        engine: SQLAlchemy engine.

    Returns:
        Dict com keys: erro (str|None), location_id, location_name, cpe,
        meses_inseridos (int), meses_total (int), periodo_inicio, periodo_fim.
    """
    # 1. Extrair CPE do nome de ficheiro
    cpe = extract_cpe_from_filename(filename)
    if not cpe:
        return {"erro": "CPE nao detectado no ficheiro. Associe o ficheiro ao local manualmente."}

    # 2. Resolver location via SQLite (tabela locais)
    local = get_local_by_cpe(cpe, engine)
    if not local:
        return {"erro": f"CPE {cpe} nao corresponde a nenhum local configurado."}

    # 3. Parse XLSX em memoria
    try:
        monthly_data = parse_xlsx_to_dict(tmp_path, drop_partial_last_month=True)
    except ValueError as e:
        return {"erro": str(e)}

    if not monthly_data:
        return {"erro": "Ficheiro XLSX nao contem dados de consumo validos."}

    # 4. Escrever em SQLite com idempotencia
    meses_inseridos = 0
    with engine.begin() as conn:
        for ym, totals in monthly_data.items():
            stmt = sqlite_insert(consumo_mensal).values(
                location_id=local["id"],
                year_month=ym,
                total_kwh=totals["total_kwh"],
                vazio_kwh=totals["vazio_kwh"],
                fora_vazio_kwh=totals["fora_vazio_kwh"],
            ).on_conflict_do_nothing(
                index_elements=["location_id", "year_month"]
            )
            result = conn.execute(stmt)
            meses_inseridos += result.rowcount

    return {
        "erro": None,
        "location_id": local["id"],
        "location_name": local["name"],
        "cpe": cpe,
        "meses_inseridos": meses_inseridos,
        "meses_total": len(monthly_data),
        "periodo_inicio": min(monthly_data.keys()),
        "periodo_fim": max(monthly_data.keys()),
    }
