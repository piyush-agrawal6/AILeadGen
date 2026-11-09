"""Back up and restore-test only the fixed private local preview database.

The live database is not migrated or modified by this script. Normal local
preview startup applies the already-tested additive migration afterwards.
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def main():
    from app.database.migrations import run_migrations, MIGRATIONS
    root=Path(__file__).resolve().parents[2]
    source=root/'data/e2e/local-preview/workspace.db'
    if not source.is_file():raise RuntimeError('The private local preview database is missing.')
    folder=root/'data/backups'/('local-preview-pre'+str(len(MIGRATIONS))+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    folder.mkdir(mode=0o700,parents=True,exist_ok=False)
    live=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    backup=sqlite3.connect(folder/'workspace.db');(folder/'workspace.db').chmod(0o600);live.backup(backup);live.close()
    restored=sqlite3.connect(folder/'restore-check.db');restored.row_factory=sqlite3.Row
    (folder/'restore-check.db').chmod(0o600);backup.backup(restored)
    def fingerprint(c,table,columns):
        names=','.join('"'+name.replace('"','""')+'"' for name in columns)
        rows=[json.dumps(list(row),default=str,sort_keys=True) for row in c.execute('SELECT '+names+' FROM "'+table+'"')]
        return len(rows),hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest()
    tables=[row[0] for row in backup.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name<>'schema_migrations'")]
    columns={table:[row[1] for row in backup.execute('PRAGMA table_info("'+table+'")')] for table in tables}
    baseline={table:fingerprint(backup,table,columns[table]) for table in tables}
    before=backup.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
    applied=run_migrations(restored)
    assert run_migrations(restored)==0
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert restored.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert all(fingerprint(restored,table,columns[table])==value for table,value in baseline.items())
    manifest={'source':'data/e2e/local-preview/workspace.db','before_schema':before,'restored_schema':len(MIGRATIONS),'migrations_tested':applied,'original_table_count':len(tables),'all_original_values_preserved':True,'integrity':'ok','foreign_keys':'ok','live_database_modified':False,'production_changed':False}
    report=folder/'manifest.json';report.write_text(json.dumps(manifest,indent=2));report.chmod(0o600)
    backup.close();restored.close()
    print(json.dumps({'backup':str(folder),'restore_verified':True,'before_schema':before,'target_schema':len(MIGRATIONS)}))


if __name__=='__main__':main()
