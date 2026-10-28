"""Idempotent copy preserving the source database and all historical observations."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings
from app.database.postgres import PostgresConnection
from app.database.migrations import run_migrations

TABLES = ["users", "scan_campaigns", "prospects", "business_identities", "pipeline_runs", "businesses", "website_profiles", "contacts", "lighthouse_results", "findings", "lead_scores", "pipeline_run_events", "prospect_observations", "prospect_notes", "opportunity_scores", "artifact_objects", "shared_settings"]


def migrate(source, target, report_path):
    report = {}
    available = {r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in TABLES:
        if table not in available:
            continue
        columns = [r[1] for r in source.execute(f'PRAGMA table_info("{table}")')]
        rows = source.execute(f'SELECT * FROM "{table}"').fetchall()
        placeholders = ','.join('?' for _ in columns)
        names = ','.join('"'+c+'"' for c in columns)
        if rows:
            target.executemany(f'INSERT INTO "{table}" ({names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING', [tuple(row) for row in rows])
        # Validate every source primary key, not merely the total target count.
        pks = [r[1] for r in source.execute(f'PRAGMA table_info("{table}")') if r[5]]
        for offset in range(0,len(rows),500):
            batch=rows[offset:offset+500]
            if pks:
                key_columns=','.join('"'+key+'"' for key in pks)
                keys=[tuple(row[columns.index(key)] for key in pks) for row in batch]
                groups=','.join('('+','.join('?' for _ in pks)+')' for _ in keys)
                count=target.execute(f'SELECT COUNT(*) FROM "{table}" WHERE ({key_columns}) IN ({groups})',[value for key in keys for value in key]).fetchone()[0]
                if count != len(batch):raise RuntimeError(f"Migration verification failed for {table}")
        count = target.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        report[table] = {"source": len(rows), "target": count, "verified": True}
        if table in {"pipeline_runs", "businesses", "website_profiles", "contacts", "lighthouse_results", "findings", "pipeline_run_events"}:
            target.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE((SELECT MAX(id) FROM {table}),1), EXISTS(SELECT 1 FROM {table}))")
    # A desktop process cannot survive import. Preserve observations and offer
    # explicit resume instead of displaying an indefinitely running historical run.
    interrupted=target.execute("UPDATE pipeline_runs SET status='INTERRUPTED',error_message='Desktop execution ended before cloud migration; resume explicitly.' WHERE campaign_id IS NULL AND status IN ('RUNNING','QUEUED')").rowcount
    report["historical_executions"]={"marked_interrupted":interrupted}
    target.commit()
    Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/lead_engine.db")
    parser.add_argument("--report", default="docs/sqlite-postgres-migration.json")
    args = parser.parse_args()
    source = sqlite3.connect(Path(args.source).resolve().as_uri()+"?mode=ro", uri=True)
    source.execute("BEGIN")
    target = PostgresConnection(get_settings().database_url)
    try:
        run_migrations(target)
        migrate(source, target, args.report)
        print(f"Verified migration report: {args.report}; source unchanged.")
    except Exception:
        target.rollback()
        raise
    finally:
        source.close()
        target.close()
