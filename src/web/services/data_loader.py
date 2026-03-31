"""Servico de leitura de dados do pipeline de monitorizacao de eletricidade.

Funcoes de leitura de CSV de consumo mensal, JSON de analise tiagofelicia,
monthly_status, custos reais, e calculo de indicador de frescura.
Tambem inclui funcoes SQLite para locais criados via UI (Phase 9).
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.engine import Engine

from src.db.schema import (
    consumo_mensal as consumo_mensal_table,
    comparacoes as comparacoes_table,
    custos_reais as custos_reais_table,
)


def load_locations(config_path: Path, engine=None) -> list:
    """Le locais de config/system.json e complementa com locais do SQLite.

    Locais de config.json mantem formato original (com pipeline, current_contract).
    Locais que existem apenas em SQLite (criados via UI Phase 7) sao adicionados
    com formato compativel — aparecem no selector mas podem nao ter pipeline data.

    Args:
        config_path: Path para o ficheiro config/system.json.
        engine: SQLAlchemy engine (opcional). Se fornecido, merge com SQLite.

    Returns:
        Lista de dicts com os locais configurados. Retorna [] se nenhuma fonte tem dados.
    """
    # 1. Ler config.json (fonte original)
    config_locations = []
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        config_locations = config.get("locations", [])
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # 2. Se engine fornecido, merge com SQLite
    if engine is not None:
        try:
            from src.web.services.locais_service import get_all_locais
            sqlite_locais = get_all_locais(engine)
        except Exception:
            return config_locations

        # IDs ja presentes no config.json
        config_ids = {loc["id"] for loc in config_locations}

        # Adicionar locais do SQLite que nao existem no config.json
        for loc in sqlite_locais:
            if loc["id"] not in config_ids:
                config_locations.append({
                    "id": loc["id"],
                    "name": loc["name"],
                    "cpe": loc.get("cpe", ""),
                    "current_contract": {
                        "supplier": loc.get("current_supplier", ""),
                        "current_plan_contains": loc.get("current_plan_contains", ""),
                        "power_label": loc.get("power_label", ""),
                    },
                    # pipeline ausente — dashboard deve tratar gracefully
                })

    return config_locations


def load_consumo_csv(csv_path: Path) -> list:
    """Le CSV de consumo mensal. Retorna lista de dicts com valores float.

    Args:
        csv_path: Path para o ficheiro CSV de consumo mensal.

    Returns:
        Lista de dicts com keys year_month (str), total_kwh, vazio_kwh,
        fora_vazio_kwh (float). Retorna [] se ficheiro nao existe.
    """
    try:
        rows = []
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "year_month": row["year_month"],
                    "total_kwh": float(row["total_kwh"]),
                    "vazio_kwh": float(row["vazio_kwh"]),
                    "fora_vazio_kwh": float(row["fora_vazio_kwh"]),
                })
        return rows
    except (FileNotFoundError, KeyError, ValueError):
        return []


def load_analysis_json(json_path: Path) -> dict | None:
    """Le JSON de analise tiagofelicia. Retorna dict ou None se nao existe.

    Args:
        json_path: Path para o ficheiro JSON de analise.

    Returns:
        Dict com os dados de analise, ou None se o ficheiro nao existe.
    """
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_monthly_status(status_path: Path) -> dict | None:
    """Le state/{local}/monthly_status.json. Retorna dict ou None se nao existe.

    Args:
        status_path: Path para o ficheiro monthly_status.json.

    Returns:
        Dict com o estado mensal, ou None se o ficheiro nao existe.
    """
    try:
        with open(status_path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def load_custos_reais(custos_path: Path) -> dict:
    """Le custos_reais.json e retorna entries dict. {} se nao existe.

    Args:
        custos_path: Path para o ficheiro custos_reais.json.

    Returns:
        Dict com year_month como chave e custo_eur como valor float. {} se nao existe.
    """
    if not custos_path.exists():
        return {}
    try:
        data = json.loads(custos_path.read_text(encoding="utf-8"))
        return data.get("entries", {})
    except (json.JSONDecodeError, OSError):
        return {}


def save_custo_real(custos_path: Path, year_month: str, custo_eur: float) -> None:
    """Adiciona/actualiza entry em custos_reais.json. Cria ficheiro se nao existe.

    Args:
        custos_path: Path para o ficheiro custos_reais.json.
        year_month: Mes no formato "YYYY-MM".
        custo_eur: Custo real da factura em EUR.
    """
    entries = load_custos_reais(custos_path)
    entries[year_month] = custo_eur
    custos_path.parent.mkdir(parents=True, exist_ok=True)
    custos_path.write_text(
        json.dumps(
            {"updated_at": datetime.now().isoformat(), "entries": entries},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def build_custo_chart_data(
    consumo_data: list,
    analysis: dict | None,
    custos_reais: dict,
) -> dict:
    """Constroi dados para o grafico de custo misto (bar estimativa + line custo real).

    Args:
        consumo_data: Lista de dicts de load_consumo_csv.
        analysis: Dict de load_analysis_json ou None.
        custos_reais: Dict de load_custos_reais.

    Returns:
        Dict com:
          - labels: lista de year_month
          - estimativa_data: custo do fornecedor actual por mes (None se sem dados)
          - custo_real_data: custo real por mes (None para meses sem dado — gap na linha)
    """
    labels = [row["year_month"] for row in consumo_data]

    # Estimativa do fornecedor actual por mes
    estimativa_by_month = {}
    if analysis and "history" in analysis:
        for entry in analysis["history"]:
            ym = entry.get("year_month")
            csr = entry.get("current_supplier_result", {})
            if ym and "total_eur" in csr:
                estimativa_by_month[ym] = round(csr["total_eur"], 2)

    estimativa_data = [estimativa_by_month.get(ym) for ym in labels]
    custo_real_data = [custos_reais.get(ym) for ym in labels]  # None se nao existe

    return {"labels": labels, "estimativa_data": estimativa_data, "custo_real_data": custo_real_data}


FRESH_THRESHOLD_HOURS = 48


def get_freshness_info(status: dict | None) -> dict:
    """Calcula frescura a partir do status mensal.

    Args:
        status: Dict do monthly_status.json, ou None.

    Returns:
        Dict com:
          - days_ago (int|None): dias desde o ultimo relatorio
          - is_stale (bool): True se > 40 dias ou sem dados
          - generated_at (str|None): data de geracao em formato ISO
          - source (str): "fresh" | "cache" | "none"
    """
    STALE_THRESHOLD_DAYS = 40

    if status is None or "generated_at" not in status:
        return {"days_ago": None, "is_stale": True, "generated_at": None, "source": "none"}

    generated_at_str = status["generated_at"]
    try:
        # Suportar formatos com e sem timezone
        # Formato tipico: "2026-03-29T22:40:59.508976"
        generated_at = datetime.fromisoformat(generated_at_str)

        # Normalizar para UTC se sem timezone
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = now - generated_at
        days_ago = delta.days
        hours_ago = delta.total_seconds() / 3600

        source = "fresh" if hours_ago <= FRESH_THRESHOLD_HOURS else "cache"

        return {
            "days_ago": days_ago,
            "is_stale": days_ago > STALE_THRESHOLD_DAYS,
            "generated_at": generated_at_str,
            "source": source,
        }
    except (ValueError, TypeError):
        return {"days_ago": None, "is_stale": True, "generated_at": generated_at_str, "source": "none"}


# ---------------------------------------------------------------------------
# Funcoes SQLite — leitura directa de BD para locais sem pipeline CSV (Phase 9)
# ---------------------------------------------------------------------------


def load_consumo_sqlite(location_id: str, engine: Engine) -> list:
    """Le consumo mensal de SQLite para um local. Retorna lista de dicts ordenada por year_month.

    Args:
        location_id: ID do local (ex: "casa").
        engine: SQLAlchemy engine com tabelas criadas.

    Returns:
        Lista de dicts com keys year_month, total_kwh, vazio_kwh, fora_vazio_kwh.
        Retorna [] se sem dados.
    """
    stmt = (
        select(consumo_mensal_table)
        .where(consumo_mensal_table.c.location_id == location_id)
        .order_by(consumo_mensal_table.c.year_month)
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        return [
            {
                "year_month": row._mapping["year_month"],
                "total_kwh": row._mapping["total_kwh"],
                "vazio_kwh": row._mapping["vazio_kwh"],
                "fora_vazio_kwh": row._mapping["fora_vazio_kwh"],
            }
            for row in rows
        ]
    except Exception:
        return []


def build_analysis_from_sqlite(location_id: str, engine: Engine) -> dict | None:
    """Constroi dict de analise a partir de comparacoes SQLite.

    Compativel com calculate_annual_ranking() e build_recommendation() — tem
    "history" e "history_summary".

    Args:
        location_id: ID do local.
        engine: SQLAlchemy engine.

    Returns:
        Dict com history e history_summary, ou None se sem dados.
    """
    stmt = (
        select(comparacoes_table)
        .where(comparacoes_table.c.location_id == location_id)
        .order_by(comparacoes_table.c.year_month)
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
    except Exception:
        return None

    if not rows:
        return None

    history = []
    for row in rows:
        m = row._mapping
        # top_3_json e current_supplier_result_json podem ser None
        try:
            top_3 = json.loads(m["top_3_json"]) if m["top_3_json"] else []
        except (json.JSONDecodeError, TypeError):
            top_3 = []
        try:
            csr = json.loads(m["current_supplier_result_json"]) if m["current_supplier_result_json"] else {}
        except (json.JSONDecodeError, TypeError):
            csr = {}
        history.append({
            "year_month": m["year_month"],
            "top_3": top_3,
            "current_supplier_result": csr,
        })

    # Derivar history_summary do ultimo mes
    last = history[-1]
    last_top_3 = last["top_3"]
    last_csr = last["current_supplier_result"]
    last_csr_cost = last_csr.get("total_eur", 0.0) if last_csr else 0.0
    best_cost = last_top_3[0].get("total_eur", 0.0) if last_top_3 else 0.0
    saving = round(last_csr_cost - best_cost, 2) if last_csr else None

    history_summary = {
        "months_analysed": len(history),
        "latest_top_3": last_top_3,
        "latest_current_supplier_result": last_csr,
        "latest_saving_vs_current_eur": saving,
    }

    return {
        "history": history,
        "history_summary": history_summary,
    }


def load_custos_reais_sqlite(location_id: str, engine: Engine) -> dict:
    """Le custos reais de SQLite. Retorna dict {year_month: custo_eur}.

    Formato compativel com o que build_custo_chart_data() espera.

    Args:
        location_id: ID do local.
        engine: SQLAlchemy engine.

    Returns:
        Dict {year_month: custo_eur}. Retorna {} se sem dados.
    """
    stmt = (
        select(custos_reais_table)
        .where(custos_reais_table.c.location_id == location_id)
    )
    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        return {row._mapping["year_month"]: row._mapping["custo_eur"] for row in rows}
    except Exception:
        return {}


def load_ultimo_detalhe_sqlite(location_id: str, engine: Engine) -> dict | None:
    """Retorna detalhe_json da fatura mais recente com detalhe, ou None.

    Args:
        location_id: ID do local.
        engine: SQLAlchemy engine.

    Returns:
        Dict com 'linhas', 'custo_real_kwh_fv', etc. ou None se sem dados.
    """
    stmt = (
        select(custos_reais_table)
        .where(
            custos_reais_table.c.location_id == location_id,
            custos_reais_table.c.detalhe_json.isnot(None),
        )
        .order_by(custos_reais_table.c.year_month.desc())
        .limit(1)
    )
    try:
        with engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
        if row and row._mapping["detalhe_json"]:
            return json.loads(row._mapping["detalhe_json"])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Funcoes de analise multi-ano (Phase 11)
# ---------------------------------------------------------------------------

_MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
              "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def build_consumo_multi_ano(consumo_data: list) -> dict:
    """Agrupa dados de consumo por ano para grafico multi-ano.

    Args:
        consumo_data: Lista de dicts com year_month, vazio_kwh, fora_vazio_kwh.

    Returns:
        Dict com:
          - anos: lista de anos ordenados ASC (ex: ["2023","2024","2025"])
          - meses: lista de abreviacoes PT (["Jan","Fev",...,"Dez"])
          - datasets: lista de {"ano": str, "vazio": [12 valores], "fora_vazio": [12 valores]}
            Cada lista tem 12 entradas (None para meses sem dados).
    """
    # Agrupar por ano
    anos_data: dict[str, dict[int, tuple[float, float]]] = {}
    for row in consumo_data:
        ym = row["year_month"]
        ano = ym[:4]
        mes_idx = int(ym[5:7]) - 1  # 0-based (0=Jan, 11=Dez)
        if ano not in anos_data:
            anos_data[ano] = {}
        anos_data[ano][mes_idx] = (row["vazio_kwh"], row["fora_vazio_kwh"])

    anos = sorted(anos_data.keys())
    datasets = []
    for ano in anos:
        vazio = [None] * 12
        fora_vazio = [None] * 12
        for mes_idx, (v, fv) in anos_data[ano].items():
            vazio[mes_idx] = v
            fora_vazio[mes_idx] = fv
        datasets.append({"ano": ano, "vazio": vazio, "fora_vazio": fora_vazio})

    return {"anos": anos, "meses": _MESES_PT, "datasets": datasets}


def build_resumo_anual(consumo_data: list, comparacoes_history: list | None) -> list:
    """Constroi resumo anual de consumo e custo por ano.

    Args:
        consumo_data: Lista de dicts com year_month, total_kwh.
        comparacoes_history: Lista de entries com year_month e current_supplier_result,
            ou None se sem dados de comparacao.

    Returns:
        Lista de dicts ordenada por ano ASC com:
          - ano: str
          - consumo_total_kwh: float
          - custo_total_eur: float | None (None se sem dados de comparacao)
    """
    # Agregar consumo por ano
    consumo_por_ano: dict[str, float] = {}
    for row in consumo_data:
        ano = row["year_month"][:4]
        consumo_por_ano[ano] = consumo_por_ano.get(ano, 0.0) + row["total_kwh"]

    # Agregar custo por ano (se comparacoes_history fornecida)
    custo_por_ano: dict[str, float] | None = None
    if comparacoes_history is not None:
        custo_por_ano = {}
        for entry in comparacoes_history:
            ano = entry["year_month"][:4]
            csr = entry.get("current_supplier_result", {})
            eur = csr.get("total_eur") if csr else None
            if eur is not None:
                custo_por_ano[ano] = custo_por_ano.get(ano, 0.0) + eur

    result = []
    for ano in sorted(consumo_por_ano.keys()):
        custo = custo_por_ano.get(ano) if custo_por_ano is not None else None
        result.append({
            "ano": ano,
            "consumo_total_kwh": round(consumo_por_ano[ano], 2),
            "custo_total_eur": round(custo, 2) if custo is not None else None,
        })
    return result


def build_comparacao_meses(
    consumo_data: list,
    comparacoes_history: list | None,
    ano1: str,
    ano2: str,
    mes: str,
) -> dict:
    """Compara o mesmo mes entre dois anos — consumo kWh e custo EUR.

    Args:
        consumo_data: Lista de dicts com year_month, total_kwh.
        comparacoes_history: Lista de entries com year_month e current_supplier_result,
            ou None se sem dados de comparacao.
        ano1: Primeiro ano (ex: "2023").
        ano2: Segundo ano (ex: "2024").
        mes: Mes no formato "MM" zero-padded (ex: "03").

    Returns:
        Dict com:
          - mes: str
          - ano1: str
          - ano2: str
          - consumo_ano1: float | None
          - consumo_ano2: float | None
          - custo_ano1: float | None
          - custo_ano2: float | None
    """
    ym1 = f"{ano1}-{mes}"
    ym2 = f"{ano2}-{mes}"

    # Consumo
    consumo_by_ym = {row["year_month"]: row["total_kwh"] for row in consumo_data}
    consumo_ano1 = consumo_by_ym.get(ym1)
    consumo_ano2 = consumo_by_ym.get(ym2)

    # Custo
    custo_ano1 = None
    custo_ano2 = None
    if comparacoes_history:
        for entry in comparacoes_history:
            ym = entry["year_month"]
            csr = entry.get("current_supplier_result", {})
            if ym == ym1 and csr:
                custo_ano1 = csr.get("total_eur")
            elif ym == ym2 and csr:
                custo_ano2 = csr.get("total_eur")

    return {
        "mes": mes,
        "ano1": ano1,
        "ano2": ano2,
        "consumo_ano1": consumo_ano1,
        "consumo_ano2": consumo_ano2,
        "custo_ano1": custo_ano1,
        "custo_ano2": custo_ano2,
    }


def get_freshness_from_sqlite(location_id: str, engine: Engine) -> dict:
    """Calcula frescura a partir de MAX(cached_at) de comparacoes SQLite.

    Usa FRESH_THRESHOLD_HOURS (48h) para determinar source=fresh vs source=cache.
    Usa o mesmo threshold de 40 dias que get_freshness_info() para is_stale.

    Args:
        location_id: ID do local.
        engine: SQLAlchemy engine.

    Returns:
        Dict com:
          - days_ago (int|None): dias desde cached_at
          - is_stale (bool): True se > 40 dias ou sem dados
          - generated_at (str|None): ISO timestamp de cached_at
          - source (str): "fresh" | "cache" | "none"
        Se sem comparacoes: source="none".
    """
    STALE_THRESHOLD_DAYS = 40
    FRESH_THRESHOLD_HOURS = 48

    stmt = (
        select(func.max(comparacoes_table.c.cached_at))
        .where(comparacoes_table.c.location_id == location_id)
    )
    try:
        with engine.connect() as conn:
            max_cached_at = conn.execute(stmt).scalar()
    except Exception:
        return {"days_ago": None, "is_stale": True, "generated_at": None, "source": "none"}

    if max_cached_at is None:
        return {"days_ago": None, "is_stale": True, "generated_at": None, "source": "none"}

    try:
        # cached_at pode ser datetime ou string ISO
        if isinstance(max_cached_at, str):
            cached_at = datetime.fromisoformat(max_cached_at)
        else:
            cached_at = max_cached_at

        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = now - cached_at
        days_ago = delta.days
        hours_ago = delta.total_seconds() / 3600

        source = "fresh" if hours_ago <= FRESH_THRESHOLD_HOURS else "cache"

        return {
            "days_ago": days_ago,
            "is_stale": days_ago > STALE_THRESHOLD_DAYS,
            "generated_at": cached_at.isoformat(),
            "source": source,
        }
    except (ValueError, TypeError, AttributeError):
        return {"days_ago": None, "is_stale": True, "generated_at": None, "source": "none"}
