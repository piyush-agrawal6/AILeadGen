import sqlite3
import uuid
from app.database import migrations
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform.company_profiles import read_profile,save_profile,CompanyUpdate


def test_company_autofill_upgrade_preserves_profiles_jobs_and_tested_restore(tmp_path,monkeypatch):
    latest=migrations.MIGRATIONS;source=sqlite3.connect(tmp_path/'before.db');source.row_factory=sqlite3.Row
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:27]);migrations.run_migrations(source)
    org=create_organization(source,'controlled@example.test','Preserved company')['organization_id']
    stamp='2026-11-06T00:00:00+00:00';key=str(uuid.uuid4())
    source.execute("INSERT INTO organization_profile_jobs(id,organization_id,created_by,request_id,website,status,created_at,updated_at) VALUES(?,?,?,?,?,'QUEUED',?,?)",(key,org,'controlled@example.test',str(uuid.uuid4()),'https://example.com',stamp,stamp))
    source.commit();backup=sqlite3.connect(tmp_path/'rollback.db');source.backup(backup)
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:28]);assert migrations.run_migrations(source)==1;assert migrations.run_migrations(source)==0
    job=dict(source.execute('SELECT * FROM organization_profile_jobs WHERE id=?',(key,)).fetchone());assert job['source_kind']=='WEBSITE' and job['use_ai']==0 and job['input_text']==''
    with workspace_scope(source,'controlled@example.test',org):
        before=read_profile(source);assert before['name']=='Preserved company' and before['specialties']==[]
        values={k:v for k,v in before.items() if k in CompanyUpdate.model_fields};values['specialties']=['Cloud engineering'];save_profile(source,CompanyUpdate.model_validate(values))
        assert read_profile(source)['specialties']==['Cloud engineering']
    assert source.execute('PRAGMA foreign_key_check').fetchall()==[]
    restored=sqlite3.connect(tmp_path/'restored.db');backup.backup(restored)
    assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==27
    assert 'specialties_json' not in [row[1] for row in restored.execute('PRAGMA table_info(organization_profiles)')]
    assert restored.execute('SELECT website FROM organization_profile_jobs WHERE id=?',(key,)).fetchone()[0]=='https://example.com'
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    restored.close();backup.close();source.close()
