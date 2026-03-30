"""Testes para schema SQLAlchemy e engine SQLite com WAL mode."""
import pytest
from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.db.schema import metadata, consumo_mensal, comparacoes, custos_reais


@pytest.fixture
def db_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_consumo_mensal_columns(db_engine):
    """Tabela consumo_mensal tem todas as colunas esperadas."""
    inspector = inspect(db_engine)
    cols = {c["name"] for c in inspector.get_columns("consumo_mensal")}
    assert "id" in cols
    assert "location_id" in cols
    assert "year_month" in cols
    assert "total_kwh" in cols
    assert "vazio_kwh" in cols
    assert "fora_vazio_kwh" in cols


def test_consumo_unique(db_engine):
    """UNIQUE constraint em (location_id, year_month) impede duplicados."""
    from sqlalchemy.exc import IntegrityError
    with db_engine.connect() as conn:
        conn.execute(consumo_mensal.insert(), {
            "location_id": "casa",
            "year_month": "2025-01",
            "total_kwh": 100.0,
            "vazio_kwh": 40.0,
            "fora_vazio_kwh": 60.0,
        })
        conn.commit()
        with pytest.raises(IntegrityError):
            conn.execute(consumo_mensal.insert(), {
                "location_id": "casa",
                "year_month": "2025-01",
                "total_kwh": 200.0,
                "vazio_kwh": 80.0,
                "fora_vazio_kwh": 120.0,
            })
            conn.commit()


def test_consumo_upsert(db_engine):
    """Upsert via on_conflict_do_update substitui registo existente."""
    with db_engine.connect() as conn:
        # Inserir registo inicial
        conn.execute(consumo_mensal.insert(), {
            "location_id": "casa",
            "year_month": "2025-02",
            "total_kwh": 100.0,
            "vazio_kwh": 40.0,
            "fora_vazio_kwh": 60.0,
        })
        conn.commit()

        # Upsert com valores actualizados
        stmt = sqlite_insert(consumo_mensal).values(
            location_id="casa",
            year_month="2025-02",
            total_kwh=200.0,
            vazio_kwh=80.0,
            fora_vazio_kwh=120.0,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["location_id", "year_month"],
            set_={
                "total_kwh": stmt.excluded.total_kwh,
                "vazio_kwh": stmt.excluded.vazio_kwh,
                "fora_vazio_kwh": stmt.excluded.fora_vazio_kwh,
            },
        )
        conn.execute(stmt)
        conn.commit()

        # Verificar que o valor foi actualizado
        result = conn.execute(
            consumo_mensal.select().where(
                consumo_mensal.c.location_id == "casa",
                consumo_mensal.c.year_month == "2025-02",
            )
        ).fetchone()
        assert result.total_kwh == 200.0

        # Verificar que existe apenas 1 registo
        count = conn.execute(
            consumo_mensal.select().where(consumo_mensal.c.location_id == "casa")
        ).fetchall()
        assert len(count) == 1


def test_comparacoes_columns(db_engine):
    """Tabela comparacoes tem todas as colunas esperadas, incluindo cached_at."""
    inspector = inspect(db_engine)
    cols = {c["name"] for c in inspector.get_columns("comparacoes")}
    assert "id" in cols
    assert "location_id" in cols
    assert "year_month" in cols
    assert "top_3_json" in cols
    assert "current_supplier_result_json" in cols
    assert "generated_at" in cols
    assert "cached_at" in cols


def test_custos_reais_columns(db_engine):
    """Tabela custos_reais tem todas as colunas esperadas."""
    inspector = inspect(db_engine)
    cols = {c["name"] for c in inspector.get_columns("custos_reais")}
    assert "id" in cols
    assert "location_id" in cols
    assert "year_month" in cols
    assert "custo_eur" in cols
    assert "source" in cols
    assert "created_at" in cols


def test_custos_unique(db_engine):
    """UNIQUE constraint em (location_id, year_month) impede duplicados em custos_reais."""
    from sqlalchemy.exc import IntegrityError
    with db_engine.connect() as conn:
        conn.execute(custos_reais.insert(), {
            "location_id": "casa",
            "year_month": "2025-01",
            "custo_eur": 50.0,
            "source": "manual",
        })
        conn.commit()
        with pytest.raises(IntegrityError):
            conn.execute(custos_reais.insert(), {
                "location_id": "casa",
                "year_month": "2025-01",
                "custo_eur": 60.0,
                "source": "upload_pdf",
            })
            conn.commit()


def test_wal_mode(db_engine):
    """WAL mode e activado apos conexao (PRAGMA journal_mode retorna 'wal')."""
    with db_engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode")).fetchone()
        assert result[0] == "wal"


def test_foreign_keys(db_engine):
    """PRAGMA foreign_keys esta ON."""
    with db_engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
        assert result[0] == 1
