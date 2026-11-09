import sqlite3
from app.database import migrations

def test_assistant_additive_upgrade_and_restored_snapshot_preserve_all_existing_tables(tmp_path,monkeypatch):
 c=sqlite3.connect(tmp_path/'before.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');latest=migrations.MIGRATIONS
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:31]);migrations.run_migrations(c);c.commit()
 tables=[row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'schema_migrations'").fetchall()];before={name:[tuple(row) for row in c.execute('SELECT * FROM '+name).fetchall()] for name in tables}
 backup=sqlite3.connect(tmp_path/'rollback.db');c.backup(backup)
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:32]);assert migrations.run_migrations(c)==1;assert migrations.run_migrations(c)==0
 assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
 for name,rows in before.items():assert [tuple(row) for row in c.execute('SELECT * FROM '+name).fetchall()]==rows
 restored=sqlite3.connect(tmp_path/'restored.db');backup.backup(restored)
 assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==31
 assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 c.close();backup.close();restored.close()
