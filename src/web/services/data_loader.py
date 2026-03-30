"""Servico de leitura de dados do pipeline de monitorizacao de eletricidade.

Funcoes de leitura de CSV de consumo mensal, JSON de analise tiagofelicia,
monthly_status e calculo de indicador de frescura.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def load_locations(config_path: Path) -> list:
    """Le config/system.json e retorna locations[].

    Args:
        config_path: Path para o ficheiro config/system.json.

    Returns:
        Lista de dicts com os locais configurados. Retorna [] se ficheiro nao existe.
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        return config.get("locations", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


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
