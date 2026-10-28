"""Explicit additive schema migration entrypoint (PowerShell and containers)."""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database.connection import db_session
from app.database.migrations import run_migrations

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["sqlite", "postgres"], default="sqlite")
    args = parser.parse_args()
    os.environ["DATABASE_BACKEND"] = args.backend
    with db_session() as connection:
        print(f"Applied {run_migrations(connection)} additive migrations ({args.backend}).")
