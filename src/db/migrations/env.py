"""Alembic env.py — configura migracao SQLite."""
import os
import sys
from pathlib import Path

# Garante que /app (raiz do projecto) está no sys.path — necessário no Docker
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from src.db.schema import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override URL from env var (Docker sets DB_PATH)
db_path = os.environ.get("DB_PATH", "data/energia.db")
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

target_metadata = metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
