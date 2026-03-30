"""Motor SQLAlchemy com WAL mode para SQLite."""
import os
from pathlib import Path
from sqlalchemy import create_engine, event

DB_PATH = os.environ.get("DB_PATH", "data/energia.db")


def get_engine(db_path: str | None = None):
    """Cria engine SQLAlchemy para SQLite com WAL mode."""
    path = db_path or DB_PATH
    # Garantir que o directorio existe
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# Engine singleton para uso na app
engine = get_engine()
