"""Servico CRUD de locais em SQLite."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from sqlalchemy import Engine, select, insert, update

from src.db.schema import locais


def get_all_locais(engine: Engine) -> list[dict]:
    """Retorna todos os locais ordenados por nome."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(locais).order_by(locais.c.name)
        ).fetchall()
    return [dict(row._mapping) for row in rows]


def get_local_by_id(local_id: str, engine: Engine) -> dict | None:
    """Retorna um local pelo id ou None."""
    with engine.connect() as conn:
        row = conn.execute(
            select(locais).where(locais.c.id == local_id)
        ).fetchone()
    return dict(row._mapping) if row else None


def get_local_by_cpe(cpe: str, engine: Engine) -> dict | None:
    """Retorna um local pelo CPE ou None."""
    with engine.connect() as conn:
        row = conn.execute(
            select(locais).where(locais.c.cpe == cpe)
        ).fetchone()
    return dict(row._mapping) if row else None


def create_local(local_id: str, name: str, cpe: str, engine: Engine) -> dict:
    """Cria um novo local. Retorna dict do local criado.

    Args:
        local_id: Slug unico (ex: 'escritorio'). Gerado a partir do nome se nao fornecido.
        name: Nome livre (ex: 'Escritorio Porto').
        cpe: CPE E-REDES (ex: 'PT0002000084968079SX').
        engine: SQLAlchemy engine.

    Returns:
        Dict com dados do local criado.

    Raises:
        ValueError: Se CPE ja existe na tabela.
    """
    existing = get_local_by_cpe(cpe, engine)
    if existing:
        raise ValueError(f"CPE {cpe} ja esta associado ao local '{existing['name']}'.")

    with engine.begin() as conn:
        conn.execute(insert(locais).values(
            id=local_id,
            name=name,
            cpe=cpe,
            created_at=datetime.now(timezone.utc),
        ))
    return get_local_by_id(local_id, engine)


def update_local(local_id: str, name: str, cpe: str, engine: Engine) -> dict | None:
    """Actualiza o nome e CPE de um local.

    Returns:
        Dict actualizado do local, ou None se local nao existe.

    Raises:
        ValueError: Se CPE ja pertence a outro local.
    """
    existing_cpe = get_local_by_cpe(cpe, engine)
    if existing_cpe and existing_cpe["id"] != local_id:
        raise ValueError(f"CPE {cpe} ja esta associado ao local '{existing_cpe['name']}'.")

    with engine.begin() as conn:
        result = conn.execute(
            update(locais)
            .where(locais.c.id == local_id)
            .values(name=name, cpe=cpe)
        )
    if result.rowcount == 0:
        return None
    return get_local_by_id(local_id, engine)


def delete_local(local_id: str, engine: Engine) -> bool:
    """Apaga um local pelo id. Retorna True se apagado, False se nao existia."""
    from sqlalchemy import delete as sql_delete
    with engine.begin() as conn:
        result = conn.execute(
            sql_delete(locais).where(locais.c.id == local_id)
        )
    return result.rowcount > 0


def update_fornecedor(local_id: str, supplier: str, plan_contains: str | None, engine: Engine) -> dict | None:
    """Actualiza o fornecedor actual de um local.

    Returns:
        Dict actualizado do local, ou None se local nao existe.
    """
    with engine.begin() as conn:
        result = conn.execute(
            update(locais)
            .where(locais.c.id == local_id)
            .values(
                current_supplier=supplier,
                current_plan_contains=plan_contains,
            )
        )
    if result.rowcount == 0:
        return None
    return get_local_by_id(local_id, engine)


def update_tarifario(
    local_id: str,
    preco_vazio_kwh: float,
    preco_fora_vazio_kwh: float,
    engine: Engine,
) -> dict | None:
    """Guarda os precos de tarifario e actualiza o Home Assistant.

    preco_vazio_kwh      -> input_number.custo_noite
    preco_fora_vazio_kwh -> input_number.custo_dia
    """
    with engine.begin() as conn:
        result = conn.execute(
            update(locais)
            .where(locais.c.id == local_id)
            .values(
                preco_vazio_kwh=preco_vazio_kwh,
                preco_fora_vazio_kwh=preco_fora_vazio_kwh,
            )
        )
    if result.rowcount == 0:
        return None

    _push_tarifario_to_ha(preco_vazio_kwh, preco_fora_vazio_kwh)
    return get_local_by_id(local_id, engine)


def _push_tarifario_to_ha(preco_vazio: float, preco_fora_vazio: float) -> None:
    """Envia os precos para os input_number do Home Assistant via Supervisor API."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return

    _ha_set_input_number("input_number.custo_noite", preco_vazio, token)
    _ha_set_input_number("input_number.custo_dia", preco_fora_vazio, token)


def _ha_set_input_number(entity_id: str, value: float, token: str) -> None:
    payload = json.dumps({"entity_id": entity_id, "value": value}).encode()
    req = urllib.request.Request(
        "http://supervisor/core/api/services/input_number/set_value",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # HA indisponivel nao deve bloquear o guardado
