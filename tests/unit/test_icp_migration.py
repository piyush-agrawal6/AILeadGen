import sqlite3
from app.database import migrations


def test_icp_upgrade_preserves_existing_accounts_settings_and_restores_snapshot(tmp_path,monkeypatch):
    c=sqlite3.connect(tmp_path/'icp-source.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
    complete=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:21]);migrations.run_migrations(c)
    tables=('organizations','organization_memberships','organization_profiles','organization_settings','workspace_invitations','organization_acquisition_preferences','acquisition_ai_cache')
    before={table:[tuple(row) for row in c.execute('SELECT * FROM '+table)] for table in tables}
    snapshot=sqlite3.connect(tmp_path/'icp-snapshot.db');c.backup(snapshot)
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:22])
    assert migrations.run_migrations(c)==1
    assert migrations.run_migrations(c)==0
    for table,rows in before.items():assert [tuple(row) for row in c.execute('SELECT * FROM '+table)]==rows
    assert c.execute('SELECT COUNT(*) FROM ideal_customer_profiles').fetchone()[0]==0
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    restored=sqlite3.connect(tmp_path/'icp-restored.db');snapshot.backup(restored)
    assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==21
    assert restored.execute("SELECT name FROM sqlite_master WHERE name='ideal_customer_profiles'").fetchone() is None
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    for table,rows in before.items():assert restored.execute('SELECT * FROM '+table).fetchall()==rows
    c.close();snapshot.close();restored.close()
