"""Tests for multi-location config schema and directory structure (MULTI-01, MULTI-02)."""
import json
import pytest
from pathlib import Path


def test_config_has_locations_array(project_root):
    """MULTI-01: config/system.json deve ter chave 'locations' na raiz."""
    config_path = project_root / "config" / "system.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert "locations" in config, "config/system.json nao tem chave 'locations'"
    assert len(config["locations"]) >= 1, "locations deve ter pelo menos um elemento"
    assert config["locations"][0]["id"] == "casa"


def test_location_has_required_keys(project_root):
    """MULTI-01: Cada location deve ter as chaves obrigatorias."""
    config_path = project_root / "config" / "system.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    required_keys = {"id", "name", "cpe", "current_contract", "pipeline"}
    for loc in config["locations"]:
        for key in required_keys:
            assert key in loc, f"location '{loc.get('id', '?')}' nao tem chave '{key}'"


def test_casa_cpe_matches(project_root):
    """MULTI-01: CPE da casa deve ser PT0002000084968079SX."""
    config_path = project_root / "config" / "system.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    casa = next((loc for loc in config["locations"] if loc["id"] == "casa"), None)
    assert casa is not None, "Location 'casa' nao encontrada"
    assert casa["cpe"] == "PT0002000084968079SX"


def test_directory_structure(multi_location_config, tmp_path):
    """MULTI-02: Fixture multi_location_config deve criar estrutura de diretorios nested."""
    # Verificar que as diretorias para 'casa' existem
    assert (tmp_path / "data" / "casa" / "raw" / "eredes").is_dir()
    assert (tmp_path / "data" / "casa" / "processed").is_dir()
    assert (tmp_path / "data" / "casa" / "reports").is_dir()
    assert (tmp_path / "state" / "casa").is_dir()

    # Verificar que as diretorias para 'apartamento' existem
    assert (tmp_path / "data" / "apartamento" / "raw" / "eredes").is_dir()
    assert (tmp_path / "data" / "apartamento" / "processed").is_dir()
    assert (tmp_path / "data" / "apartamento" / "reports").is_dir()
    assert (tmp_path / "state" / "apartamento").is_dir()


def test_multi_location_config_fixture_schema(multi_location_config):
    """multi_location_config fixture deve ter schema locations correcto."""
    config = json.loads(multi_location_config.read_text(encoding="utf-8"))
    assert "locations" in config
    assert len(config["locations"]) == 2
    ids = [loc["id"] for loc in config["locations"]]
    assert "casa" in ids
    assert "apartamento" in ids
