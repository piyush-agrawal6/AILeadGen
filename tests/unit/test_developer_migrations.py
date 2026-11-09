import sqlite3
from app.database import migrations

def test_keys_and_protocol_approval_upgrade_restore_preserve_customer_records(tmp_path,monkeypatch):
 c=sqlite3.connect(tmp_path/'source.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');latest=migrations.MIGRATIONS;monkeypatch.setattr(migrations,'MIGRATIONS',latest[:33]);migrations.run_migrations(c);c.commit()
 names=[row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'schema_migrations'").fetchall()];before={table:[dict(row) for row in c.execute('SELECT * FROM '+table).fetchall()] for table in names};backup=sqlite3.connect(tmp_path/'snapshot.db');c.backup(backup)
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:35]);assert migrations.run_migrations(c)==2;assert migrations.run_migrations(c)==0
 assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
 for table,rows in before.items():assert [dict(row) for row in c.execute('SELECT * FROM '+table).fetchall()]==rows
 restored=sqlite3.connect(tmp_path/'restored.db');backup.backup(restored)
 assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==33;assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 c.close();backup.close();restored.close()
