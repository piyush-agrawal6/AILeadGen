"""Opt-in tests against real PostgreSQL, isolated in a disposable schema."""
import os
import uuid
import pytest
import psycopg
from psycopg import sql
from app.config.settings import get_settings
from app.database.postgres import PostgresConnection
from app.database.migrations import run_migrations, verify_schema, MIGRATIONS
from app.database.models import Business, PipelineRun, PipelineRunEvent
from app.database.repositories import BusinessRepository, PipelineRunRepository, PipelineRunEventRepository
from app.database.prospects import ProspectRepository

pytestmark = pytest.mark.skipif(os.environ.get("RUN_POSTGRES_TESTS") != "1", reason="Set RUN_POSTGRES_TESTS=1 for real PostgreSQL integration")


def test_real_postgres_permanent_deletion(postgres,monkeypatch):
    from unittest.mock import Mock
    from app.api.services.deletion import preview,delete
    c=postgres;run_migrations(c)
    run=PipelineRun(market='Deletion QA',vertical='dentists',target=5,status='COMPLETED');PipelineRunRepository(c).create(run)
    b=Business(name='Postgres deletion QA',normalized_name='postgres deletion qa',vertical='dentists',run_id=run.id,website='https://delete-qa.invalid');BusinessRepository(c).insert(b)
    ProspectRepository(c).observe(b);c.commit()
    monkeypatch.setattr('app.api.services.deletion.artifact_storage',lambda:Mock())
    p=preview(c,'scan',str(run.id));c.commit()
    assert delete(c,'scan',str(run.id),'DELETE',p['token'],'a@example.com')['deleted']
    assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0


@pytest.fixture
def postgres():
    url = get_settings().database_url
    assert url, "DATABASE_URL is required"
    schema = "leadengine_test_" + uuid.uuid4().hex
    admin = psycopg.connect(url, autocommit=True)
    admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    conn = None
    try:
        conn = PostgresConnection(url, schema=schema)
        yield conn
    finally:
        if conn:
            conn.close()
        admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


def test_real_postgres_repositories_and_shared_workflow(postgres):
    conn = postgres
    assert run_migrations(conn) == len(MIGRATIONS)
    assert run_migrations(conn) == 0
    verify_schema(conn)
    runs = PipelineRunRepository(conn)
    run = PipelineRun(market="Austin", vertical="dentists", target=5)
    run_id = runs.create(run)
    business = Business(name="Independent Dental", normalized_name="independent dental", vertical="dentists", city="Austin", run_id=run_id, website="https://independent.example")
    BusinessRepository(conn).insert(business)
    assert BusinessRepository(conn).get_by_id(business.id).name == business.name
    repo = ProspectRepository(conn)
    prospect_id = repo.observe(business)
    repo.workflow(prospect_id, "a@example.com", lead_status="SHORTLISTED", assigned_to="b@example.com")
    repo.add_note(prospect_id, "b@example.com", "Public booking flow needs work.")
    event = PipelineRunEvent(run_id=run_id, stage="TEST", event_type="TEST", message="Persisted across processes")
    PipelineRunEventRepository(conn).create(event)
    conn.commit()
    dossier = repo.dossier(business.id)
    assert dossier["assigned_to"] == "b@example.com"
    assert dossier["lead_status"] == "SHORTLISTED"
    assert dossier["notes"][0]["created_by"] == "b@example.com"
    assert PipelineRunEventRepository(conn).list_by_run(run_id)[0].message == event.message
    assert BusinessRepository(conn).search_leads()[1] == 1
    run.status = "COMPLETED"
    runs.update(run)
    conn.commit()
    assert runs.get_by_id(run_id).status == "COMPLETED"
    # Phase 3.5 is additive: existing assignment and notes survive LOST, while
    # report versions belong to the same canonical prospect on PostgreSQL.
    repo.workflow(prospect_id,"a@example.com",lead_status="LOST")
    from app.reports.service import create_report
    first=create_report(conn,business.id,prospect_id,'a@example.com')
    assert create_report(conn,business.id,prospect_id,'a@example.com')['id']==first['id']
    conn.execute("UPDATE client_reports SET status='READY' WHERE id=?",(first['id'],))
    second=create_report(conn,business.id,prospect_id,'a@example.com')
    conn.commit()
    assert first['version']==1 and second['version']==2
    assert repo.dossier(business.id)['lead_status']=='LOST'
    assert repo.dossier(business.id)['notes'][0]['body']=='Public booking flow needs work.'


def test_worker_session_lock_survives_commit_and_releases_on_close():
    url=get_settings().database_url
    first=PostgresConnection(url,session_bound=True)
    second=PostgresConnection(url,session_bound=True)
    lock=int(uuid.uuid4().hex[:7],16)
    try:
        assert first.execute('SELECT pg_try_advisory_lock(6919444,?)',(lock,)).fetchone()[0]
        first.commit()
        assert not second.execute('SELECT pg_try_advisory_lock(6919444,?)',(lock,)).fetchone()[0]
        second.commit();first.close();first=None
        assert second.execute('SELECT pg_try_advisory_lock(6919444,?)',(lock,)).fetchone()[0]
    finally:
        if first:first.close()
        second.close()
