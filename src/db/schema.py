"""Definicao de tabelas SQLAlchemy Core para monitorizacao de eletricidade."""
from datetime import datetime, timezone
from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Float, DateTime, Text,
    UniqueConstraint,
)

metadata = MetaData()

consumo_mensal = Table(
    "consumo_mensal", metadata,
    Column("id", Integer, primary_key=True),
    Column("location_id", String(64), nullable=False),
    Column("year_month", String(7), nullable=False),
    Column("total_kwh", Float, nullable=False),
    Column("vazio_kwh", Float, nullable=False),
    Column("fora_vazio_kwh", Float, nullable=False),
    UniqueConstraint("location_id", "year_month", name="uq_consumo_loc_month"),
)

comparacoes = Table(
    "comparacoes", metadata,
    Column("id", Integer, primary_key=True),
    Column("location_id", String(64), nullable=False),
    Column("year_month", String(7), nullable=False),
    Column("top_3_json", Text),
    Column("current_supplier_result_json", Text),
    Column("generated_at", String(32)),
    Column("cached_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    UniqueConstraint("location_id", "year_month", name="uq_comparacao_loc_month"),
)

custos_reais = Table(
    "custos_reais", metadata,
    Column("id", Integer, primary_key=True),
    Column("location_id", String(64), nullable=False),
    Column("year_month", String(7), nullable=False),
    Column("custo_eur", Float, nullable=False),
    Column("source", String(64)),
    Column("detalhe_json", Text, nullable=True),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
    UniqueConstraint("location_id", "year_month", name="uq_custos_loc_month"),
)

locais = Table(
    "locais", metadata,
    Column("id", String(64), primary_key=True),
    Column("name", String(128), nullable=False),
    Column("cpe", String(64), nullable=False, unique=True),
    Column("current_supplier", String(128)),
    Column("current_plan_contains", String(128)),
    Column("power_label", String(32)),
    Column("created_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)
