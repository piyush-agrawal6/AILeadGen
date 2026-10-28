from unittest.mock import Mock
from datetime import datetime,timedelta,timezone
from app.api.services.cloud_executor import run_job
from app.worker import claim_run
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.models import PipelineRun
from app.database.repositories import PipelineRunRepository


def test_cloud_job_only_receives_run_id_override():
    session=Mock();session.post.return_value.status_code=200;session.post.return_value.json.return_value={"name":"operation/test"}
    assert run_job(42,session)=="operation/test"
    body=session.post.call_args.kwargs["json"]
    assert body=={"overrides":{"taskCount":1,"containerOverrides":[{"env":[{"name":"LEADENGINE_RUN_ID","value":"42"}]}]}}
    assert session.post.call_args.kwargs["timeout"]==30


def test_worker_claim_and_cancellation_are_persistent(tmp_path):
    conn=get_connection(tmp_path/"worker.db");run_migrations(conn)
    run=PipelineRun(market="Austin",vertical="dentists",target=5,status="QUEUED");PipelineRunRepository(conn).create(run);conn.commit()
    assert claim_run(conn,run.id,"first")
    conn.execute("UPDATE pipeline_runs SET status='RUNNING' WHERE id=?",(run.id,));conn.commit()
    assert not claim_run(conn,run.id,"second")
    PipelineRunRepository(conn).cancel_run(run.id);conn.commit()
    assert not claim_run(conn,run.id,"third")
    assert conn.execute("SELECT cancellation_requested FROM pipeline_runs WHERE id=?",(run.id,)).fetchone()[0]==1
    conn.close()


def test_expired_worker_becomes_resumable_without_losing_observations(tmp_path):
    from app.api.services.cloud_executor import reconcile_expired
    conn=get_connection(tmp_path/'expired.db');run_migrations(conn)
    run=PipelineRun(market='Austin',vertical='dentists',target=5,status='RUNNING')
    PipelineRunRepository(conn).create(run)
    conn.execute("UPDATE pipeline_runs SET lease_owner='dead-worker',lease_expires_at=? WHERE id=?",((datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(),run.id))
    assert reconcile_expired(conn)==1
    saved=conn.execute('SELECT status,lease_owner FROM pipeline_runs WHERE id=?',(run.id,)).fetchone()
    assert saved['status']=='INTERRUPTED' and saved['lease_owner'] is None
    assert reconcile_expired(conn)==0
    conn.close()
