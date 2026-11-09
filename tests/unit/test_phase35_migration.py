from app.database import migrations
from app.database.connection import get_connection
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID


def test_phase35_preserves_canonical_workflow_foreign_keys_and_notes(tmp_path,monkeypatch,request):
    conn=get_connection(tmp_path/'migration.db');all_migrations=migrations.MIGRATIONS
    with monkeypatch.context() as patch:
        patch.setattr(migrations,'MIGRATIONS',all_migrations[:4]);assert migrations.run_migrations(conn)==4
    run=PipelineRun(market='Austin',vertical='dentists',target=5);PipelineRunRepository(conn).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    business=Business(name='Preserved Dentist',normalized_name='preserved dentist',vertical='dentists',city='Austin',run_id=run.id,website='https://preserved.example');BusinessRepository(conn).insert(business)
    from tests.workspace_fixtures import historical_observation,bind_internal_workspace
    from app.database.prospects import now
    pid=historical_observation(conn,business);repo=ProspectRepository(conn)
    for email in ('a@example.com','b@example.com'):conn.execute('INSERT INTO users(id,email,display_name) VALUES(?,?,?)',(email,email,email))
    conn.execute("UPDATE prospects SET lead_status='CONTACTED',assigned_to='b@example.com' WHERE id=?",(pid,))
    conn.execute('INSERT INTO prospect_notes(id,prospect_id,body,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?)',('retained-note',pid,'Preserve this note.','a@example.com',now(),now()));conn.commit()
    assert migrations.run_migrations(conn)==len(all_migrations)-4
    bind_internal_workspace(conn,request)
    after=repo.dossier(business.id)
    assert after['id']==pid and after['lead_status']=='CONTACTED' and after['assigned_to']=='b@example.com'
    assert after['notes'][0]['body']=='Preserve this note.'
    assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
    repo.workflow(pid,'a@example.com',lead_status='LOST');assert repo.dossier(business.id)['lead_status']=='LOST'
    assert migrations.run_migrations(conn)==0
    conn.close()
