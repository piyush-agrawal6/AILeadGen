"""Additive 18→19 upgrade, repeatability and isolated snapshot restoration."""
import sqlite3
from app.database import migrations


def test_invitation_upgrade_preserves_existing_workspace_and_restores_snapshot(tmp_path,monkeypatch):
    source=sqlite3.connect(tmp_path/'source.db');source.row_factory=sqlite3.Row
    complete=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:18])
    migrations.run_migrations(source)
    before={table:[tuple(r) for r in source.execute('SELECT * FROM '+table).fetchall()] for table in ('organizations','organization_memberships','organization_settings','user_profiles','organization_onboarding')}
    snapshot=sqlite3.connect(tmp_path/'snapshot.db');source.backup(snapshot)
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:19])
    assert migrations.run_migrations(source)==1
    assert migrations.run_migrations(source)==0
    assert source.execute("SELECT COUNT(*) FROM workspace_invitations").fetchone()[0]==0
    for table,rows in before.items():assert [tuple(r) for r in source.execute('SELECT * FROM '+table).fetchall()]==rows
    assert source.execute('PRAGMA foreign_key_check').fetchall()==[]
    restored=sqlite3.connect(tmp_path/'restored.db');snapshot.backup(restored)
    assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==18
    assert restored.execute("SELECT name FROM sqlite_master WHERE name='workspace_invitations'").fetchone() is None
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    for table,rows in before.items():assert restored.execute('SELECT * FROM '+table).fetchall()==rows
    source.close();snapshot.close();restored.close()


def test_creation_ledger_upgrade_preserves_invitation_and_restores_schema19(tmp_path,monkeypatch):
    from app.config.settings import get_settings
    # Reproduce the historical schema-19 runtime, before billing accounts existed.
    monkeypatch.setattr(get_settings(),'shared_billing_accounts_enabled',False)
    from app.platform.context import workspace_scope
    from app.platform.invitations import create,InviteCreate
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as internal
    source=sqlite3.connect(tmp_path/'creation-source.db');source.row_factory=sqlite3.Row
    complete=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:19]);migrations.run_migrations(source)
    owner=source.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(internal,)).fetchone()[0]
    with workspace_scope(source,owner,internal):create(source,InviteCreate(email='migration-recipient@example.com'))
    source.commit()
    before=[tuple(row) for row in source.execute('SELECT * FROM workspace_invitations').fetchall()]
    snapshot=sqlite3.connect(tmp_path/'creation-snapshot.db');source.backup(snapshot)
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:20])
    assert migrations.run_migrations(source)==1
    assert migrations.run_migrations(source)==0
    assert [tuple(row) for row in source.execute('SELECT * FROM workspace_invitations').fetchall()]==before
    assert source.execute('SELECT COUNT(*) FROM workspace_creation_requests').fetchone()[0]==0
    restored=sqlite3.connect(tmp_path/'creation-restored.db');snapshot.backup(restored)
    assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==19
    assert restored.execute("SELECT name FROM sqlite_master WHERE name='workspace_creation_requests'").fetchone() is None
    assert restored.execute('SELECT * FROM workspace_invitations').fetchall()==before
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert source.execute('PRAGMA foreign_key_check').fetchall()==[]
    source.close();snapshot.close();restored.close()
