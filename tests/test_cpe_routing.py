"""Tests for CPE extraction from filename and location lookup (MULTI-04)."""
import pytest
from cpe_routing import extract_cpe_from_filename, find_location_by_cpe


# Locations de teste representando o schema real
SAMPLE_LOCATIONS = [
    {
        "id": "casa",
        "name": "Casa",
        "cpe": "PT0002000084968079SX",
        "current_contract": {},
        "pipeline": {},
    },
    {
        "id": "apartamento",
        "name": "Apartamento",
        "cpe": "PT000200XXXXXXXXXX",
        "current_contract": {},
        "pipeline": {},
    },
]


def test_extract_cpe_from_real_filename():
    """MULTI-04: Extrai CPE de nome real com range de datas."""
    result = extract_cpe_from_filename(
        "Consumos_PT0002000084968079SX_2026-02-07_2026-03-26_20260326043814.xlsx"
    )
    assert result == "PT0002000084968079SX"


def test_extract_cpe_short_format():
    """MULTI-04: Extrai CPE de nome curto (sem range de datas)."""
    result = extract_cpe_from_filename(
        "Consumos_PT0002000084968079SX_20260326042940.xlsx"
    )
    assert result == "PT0002000084968079SX"


def test_extract_cpe_no_match():
    """MULTI-04: Retorna None para ficheiro sem padrao CPE."""
    result = extract_cpe_from_filename("random_file.xlsx")
    assert result is None


def test_extract_cpe_from_path_string():
    """MULTI-04: Funciona mesmo com path completo como string."""
    result = extract_cpe_from_filename(
        "/Users/ricmag/Downloads/Consumos_PT0002000084968079SX_20260326042940.xlsx"
    )
    assert result == "PT0002000084968079SX"


def test_find_location_by_cpe():
    """MULTI-04: Encontra location pelo CPE correcto."""
    result = find_location_by_cpe(SAMPLE_LOCATIONS, "PT0002000084968079SX")
    assert result is not None
    assert result["id"] == "casa"


def test_find_location_by_cpe_unknown():
    """MULTI-04: Retorna None para CPE desconhecido."""
    result = find_location_by_cpe(SAMPLE_LOCATIONS, "PT9999999999999999XX")
    assert result is None


def test_find_location_by_cpe_empty_list():
    """MULTI-04: Retorna None para lista vazia."""
    result = find_location_by_cpe([], "PT0002000084968079SX")
    assert result is None
