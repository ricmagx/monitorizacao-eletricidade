"""Testes para migrações Alembic — criação de tabelas a partir de DB vazia."""
import os
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


@pytest.fixture
def alembic_config(tmp_path):
    db_path = str(tmp_path / "test_migration.db")
    os.environ["DB_PATH"] = db_path
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    yield cfg, db_path
    os.environ.pop("DB_PATH", None)


def test_upgrade_creates_tables(alembic_config):
    """alembic upgrade head cria as 3 tabelas e alembic_version a partir de DB vazia."""
    cfg, db_path = alembic_config
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path}")
    tables = inspect(engine).get_table_names()
    assert "consumo_mensal" in tables
    assert "comparacoes" in tables
    assert "custos_reais" in tables
    assert "alembic_version" in tables
    engine.dispose()


def test_upgrade_idempotent(alembic_config):
    """Executar upgrade head duas vezes nao causa erros."""
    cfg, db_path = alembic_config
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # segunda vez — sem erros
