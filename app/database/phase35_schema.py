"""Client-report metadata and the additive LOST workflow value."""
import re

PHASE35_SQL="""
CREATE TABLE IF NOT EXISTS client_reports (
 id TEXT PRIMARY KEY, prospect_id TEXT NOT NULL REFERENCES prospects(id),
 business_id INTEGER NOT NULL REFERENCES businesses(id), created_at TEXT NOT NULL,
 created_by TEXT NOT NULL, version INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('QUEUED','GENERATING','READY','FAILED')),
 object_key TEXT UNIQUE, snapshot_json TEXT NOT NULL, error_message TEXT,
 execution_name TEXT, lease_owner TEXT, lease_expires_at TEXT, updated_at TEXT NOT NULL,
 UNIQUE(prospect_id,version)
);
CREATE INDEX IF NOT EXISTS idx_client_reports_prospect ON client_reports(prospect_id,version);
CREATE INDEX IF NOT EXISTS idx_client_reports_queue ON client_reports(status,created_at);
"""


def apply_phase35(conn,postgres):
    if postgres:
        conn.execute('ALTER TABLE prospects DROP CONSTRAINT prospects_lead_status_check')
        conn.execute("ALTER TABLE prospects ADD CONSTRAINT prospects_lead_status_check CHECK(lead_status IN ('NEW','SHORTLISTED','CONTACTED','REPLIED','NOT_INTERESTED','DO_NOT_CONTACT','WON','LOST'))")
        conn.executescript(PHASE35_SQL)
        return
    # SQLite's supported table-rebuild procedure expands CHECK while preserving
    # every column, ID, index and incoming foreign-key reference. Never rename
    # the old table: that would rewrite the child tables' references.
    conn.commit()
    conn.execute('PRAGMA foreign_keys=OFF')
    try:
        conn.execute('BEGIN IMMEDIATE')
        original=conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='prospects'").fetchone()[0]
        indexes=[row[0] for row in conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='prospects' AND sql IS NOT NULL").fetchall()]
        expanded=re.sub(r'CREATE TABLE\s+(?:"prospects"|prospects)', 'CREATE TABLE prospects_phase35',original,count=1,flags=re.I)
        if "'LOST'" not in expanded:expanded=re.sub(r"'WON'\s*\)","'WON','LOST')",expanded,count=1)
        if "'LOST'" not in expanded:raise RuntimeError('Unexpected prospect status constraint; migration stopped')
        conn.execute(expanded)
        columns=','.join('"'+row[1].replace('"','""')+'"' for row in conn.execute('PRAGMA table_info(prospects)').fetchall())
        conn.execute(f'INSERT INTO prospects_phase35({columns}) SELECT {columns} FROM prospects')
        conn.execute('DROP TABLE prospects')
        conn.execute('ALTER TABLE prospects_phase35 RENAME TO prospects')
        for statement in indexes:conn.execute(statement)
        for statement in PHASE35_SQL.split(';'):
            if statement.strip():conn.execute(statement)
        if conn.execute('PRAGMA foreign_key_check').fetchall():raise RuntimeError('Foreign-key verification failed; migration rolled back')
        conn.commit()
    except Exception:
        conn.rollback();raise
    finally:conn.execute('PRAGMA foreign_keys=ON')
