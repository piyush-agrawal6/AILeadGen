import json
import sqlite3
from app.database import migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.acquisition.preferences import load


def test_scoped_acquisition_upgrade_preserves_global_provider_state_and_snapshot(tmp_path,monkeypatch):
    source=sqlite3.connect(tmp_path/'acquisition-source.db');source.row_factory=sqlite3.Row
    complete=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:20]);migrations.run_migrations(source)
    other=create_organization(source,'customer@example.test','Customer workspace')['organization_id']
    config={'enabled':{'firecrawl':False},'budgets':{'max_searches':2},'ai_providers':{'VERTEX_AI':{'status':'DEGRADED'}}}
    source.execute('INSERT INTO acquisition_preferences(id,configuration_json,updated_by,updated_at) VALUES(1,?,?,?)',(json.dumps(config),'owner','2026-11-05'))
    source.execute('INSERT INTO acquisition_ai_cache(fingerprint,actor,task,result_json,expires_at,created_at) VALUES(?,?,?,?,?,?)',('historical-key','owner','LEGACY','{}','2030-01-01','2026-11-05'))
    source.commit();snapshot=sqlite3.connect(tmp_path/'acquisition-snapshot.db');source.backup(snapshot)
    monkeypatch.setattr(migrations,'MIGRATIONS',complete[:21])
    assert migrations.run_migrations(source)==1
    assert migrations.run_migrations(source)==0
    assert json.loads(source.execute('SELECT configuration_json FROM acquisition_preferences').fetchone()[0])==config
    owner=source.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(INTERNAL,)).fetchone()[0]
    with workspace_scope(source,owner,INTERNAL):assert load(source)=={key:config[key] for key in ('enabled','budgets')}
    with workspace_scope(source,'customer@example.test',other):assert load(source)=={}
    assert source.execute('SELECT organization_id FROM acquisition_ai_cache WHERE fingerprint=?',('historical-key',)).fetchone()[0] is None
    assert source.execute('PRAGMA foreign_key_check').fetchall()==[]
    restored=sqlite3.connect(tmp_path/'acquisition-restored.db');snapshot.backup(restored)
    assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==20
    assert restored.execute("SELECT name FROM sqlite_master WHERE name='organization_acquisition_preferences'").fetchone() is None
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    source.close();snapshot.close();restored.close()
