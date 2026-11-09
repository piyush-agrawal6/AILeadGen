import sqlite3
import pytest
from app.database import migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.platform.context import workspace_scope
from app.mail import contacted


@pytest.mark.parametrize('target',[23,24,25,26,27,39,40])
def test_foundation_upgrade_preserves_history_and_restores_previous_schema(tmp_path,monkeypatch,target):
    complete=migrations.MIGRATIONS
    c=sqlite3.connect(tmp_path/'source.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:target-1]);migrations.run_migrations(c)
    owner=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(INTERNAL,)).fetchone()[0]
    with workspace_scope(c,owner,INTERNAL):contacted.record(c,message_id='migration-retained-message',email='retained@example.test',sent_at='2026-11-05T00:00:00+00:00')
    tables=('organizations','organization_memberships','organization_profiles','organization_settings','contacted_recipients','ideal_customer_profiles','organization_onboarding')
    before={table:[tuple(row) for row in c.execute('SELECT * FROM '+table)] for table in tables}
    c.commit();snapshot=sqlite3.connect(tmp_path/'snapshot.db');c.backup(snapshot)
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:target])
    assert migrations.run_migrations(c)==1
    assert migrations.run_migrations(c)==0
    for table,rows in before.items():assert [tuple(row) for row in c.execute('SELECT * FROM '+table)]==rows
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    restored=sqlite3.connect(tmp_path/'restored.db');snapshot.backup(restored)
    assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==target-1
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    for table,rows in before.items():assert restored.execute('SELECT * FROM '+table).fetchall()==rows
    c.close();snapshot.close();restored.close()
