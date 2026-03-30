"""Servico de leitura de dados do pipeline de monitorizacao de eletricidade.

Funcoes de leitura de CSV de consumo mensal, JSON de analise tiagofelicia,
monthly_status, custos reais, e calculo de indicador de frescura.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


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


def get_freshness_info(status: dict | None) -> dict:
    """Calcula frescura a partir do status mensal.

    Args:
        status: Dict do monthly_status.json, ou None.

    Returns:
        Dict com:
          - days_ago (int|None): dias desde o ultimo relatorio
          - is_stale (bool): True se > 40 dias ou sem dados
          - generated_at (str|None): data de geracao em formato ISO
    """
    STALE_THRESHOLD_DAYS = 40

    if status is None or "generated_at" not in status:
        return {"days_ago": None, "is_stale": True, "generated_at": None}

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

        return {
            "days_ago": days_ago,
            "is_stale": days_ago > STALE_THRESHOLD_DAYS,
            "generated_at": generated_at_str,
        }
    except (ValueError, TypeError):
        return {"days_ago": None, "is_stale": True, "generated_at": generated_at_str}
