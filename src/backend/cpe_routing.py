"""CPE routing utilities for multi-location support (MULTI-04).

Extrai o CPE do nome de ficheiro XLSX da E-REDES e faz lookup no array
de locations para determinar qual o local a processar.

Formato de nome esperado:
  Consumos_PT0002000084968079SX_2026-02-07_2026-03-26_20260326043814.xlsx
  Consumos_PT0002000084968079SX_20260326042940.xlsx
"""
import re
from pathlib import Path

# Padrao baseado em inspecao directa dos ficheiros reais em data/raw/eredes/
CPE_PATTERN = re.compile(r"Consumos_(PT\w+?)_")


def extract_cpe_from_filename(filename: str) -> str | None:
    """Extrai o CPE do nome de ficheiro XLSX da E-REDES.

    Args:
        filename: Nome ou path completo do ficheiro XLSX.

    Returns:
        CPE como string (ex: 'PT0002000084968079SX') ou None se nao encontrado.
    """
    m = CPE_PATTERN.search(Path(filename).name)
    return m.group(1) if m else None


def find_location_by_cpe(locations: list[dict], cpe: str) -> dict | None:
    """Procura uma location pelo CPE.

    Args:
        locations: Lista de dicts com schema de location (deve ter chave 'cpe').
        cpe: CPE a procurar (ex: 'PT0002000084968079SX').

    Returns:
        Dict da location correspondente ou None se nao encontrado.
    """
    for loc in locations:
        if loc.get("cpe") == cpe:
            return loc
    return None
