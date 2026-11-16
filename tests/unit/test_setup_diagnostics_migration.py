import sqlite3
import uuid
import pytest
from app.database import migrations
from app.database.connection import get_connection
from app.api.organization import create_organization
from app.config.settings import get_settings


def test_schema51_is_additive_idempotent_and_cross_workspace_fk_is_enforced(tmp_path,monkeypatch):
    all_sql=migrations.MIGRATIONS
    c=get_connection(tmp_path/'upgrade.sqlite')
    monkeypatch.setattr(migrations,'MIGRATIONS',all_sql[:50]);migrations.run_migrations(c)
    org=create_organization(c,'first@example.test','First')['organization_id']
    other=create_organization(c,'second@example.test','Second')['organization_id']
    key=str(uuid.uuid4());stamp='2026-11-16T00:00:00+00:00'
    c.execute("INSERT INTO organization_profile_jobs(id,organization_id,created_by,request_id,website,status,attempts,error_code,created_at,updated_at) VALUES(?,?,?,?,?,'FAILED',1,'OLD_SAFE_CODE',?,?)",(key,org,'first@example.test',str(uuid.uuid4()),'https://example.com',stamp,stamp));c.commit()
    original=[tuple(r) for r in c.execute('SELECT * FROM organization_profile_jobs').fetchall()]
    backup=sqlite3.connect(tmp_path/'before.sqlite');c.backup(backup)
    monkeypatch.setattr(get_settings(),'heysow_setup_diagnostics_enabled',True)
    with pytest.raises(RuntimeError):migrations.verify_schema(c)
    monkeypatch.setattr(migrations,'MIGRATIONS',all_sql)
    assert migrations.run_migrations(c)==1 and migrations.run_migrations(c)==0
    migrations.verify_schema(c)
    assert [tuple(r) for r in c.execute('SELECT * FROM organization_profile_jobs').fetchall()]==original
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO organization_profile_job_events(id,organization_id,job_id,attempt,stage,outcome,duration_ms,created_at) VALUES(?,?,?,1,'ANALYZING','FAILED',1,?)",(str(uuid.uuid4()),other,key,stamp))
    c.rollback()
    c.execute("INSERT INTO organization_profile_job_events(id,organization_id,job_id,attempt,stage,outcome,error_code,duration_ms,created_at) VALUES(?,?,?,1,'ANALYZING','FAILED','AI_OUTPUT_INVALID',1,?)",(str(uuid.uuid4()),org,key,stamp));c.commit()
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    assert backup.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==50
    assert backup.execute('SELECT error_code FROM organization_profile_jobs WHERE id=?',(key,)).fetchone()[0]=='OLD_SAFE_CODE'
    backup.close();c.close()
