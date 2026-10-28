from typing import Generator
import sqlite3

from app.database.connection import db_session, get_connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Dependency that yields a managed SQLite connection."""
    with db_session() as conn:
        yield conn
