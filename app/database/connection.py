import sqlite3
import os
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

from app.config.settings import get_settings


def get_db_path() -> Path:
    settings = get_settings()
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_connection(db_path: Path = None, *, session_bound=False) -> sqlite3.Connection:
    settings = get_settings()
    if db_path is None and (settings.app_env == "production" or os.environ.get("DATABASE_BACKEND") == "postgres"):
        if not settings.database_url:
            raise ValueError("PostgreSQL requires DATABASE_URL")
        from app.database.postgres import PostgresConnection
        return PostgresConnection(settings.database_url,session_bound=session_bound)
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(
        str(db_path),
        timeout=30.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row

    # Performance & reliability pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


@contextmanager
def db_session(db_path: Path = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
