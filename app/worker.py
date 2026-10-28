"""Cloud Run Job entrypoint. Claims a run once and resumes its observations."""
import asyncio
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from app.database.connection import get_connection, db_session
from app.database.migrations import verify_schema
from app.database.repositories import PipelineRunRepository
from app.pipeline.runner import PipelineRunner
from app.config.settings import get_settings


def claim_run(conn, run_id, owner):
    postgres = getattr(conn,"backend",None) == "postgres"
    if postgres:
        if not conn.execute("SELECT pg_try_advisory_lock(6919445,?)", (run_id,)).fetchone()[0]:
            return False
        conn.execute("SELECT pg_advisory_xact_lock(691944304)")
        active = conn.execute("SELECT COUNT(*) FROM pipeline_runs WHERE lease_owner IS NOT NULL AND status IN ('RUNNING','QUEUED') AND id<>?", (run_id,)).fetchone()[0]
        if active >= get_settings().max_active_scans:
            conn.execute("UPDATE pipeline_runs SET status='QUEUED',execution_name=NULL,lease_owner=NULL,lease_expires_at=NULL WHERE id=?", (run_id,))
            conn.commit()
            return False
    timestamp = datetime.now(timezone.utc)
    expiry = (timestamp+timedelta(seconds=120)).isoformat()
    running = "status='RUNNING'" if postgres else "(status='RUNNING' AND (lease_expires_at IS NULL OR lease_expires_at<?))"
    parameters = (owner,expiry,run_id) if postgres else (owner,expiry,run_id,timestamp.isoformat())
    changed = conn.execute("UPDATE pipeline_runs SET lease_owner=?,lease_expires_at=? WHERE id=? AND cancellation_requested=0 AND COALESCE(failure_class,'transient')<>'permanent' AND (status IN ('QUEUED','FAILED','INTERRUPTED') OR "+running+")", parameters).rowcount
    conn.commit()
    return changed == 1


def execute(run_id):
    owner = str(uuid.uuid4())
    lock_connection = get_connection(session_bound=True)
    verify_schema(lock_connection,minimum_version=4)
    stop = threading.Event()
    def heartbeat():
        while not stop.wait(25):
            try:
                with db_session() as conn:
                    conn.execute("UPDATE pipeline_runs SET lease_expires_at=? WHERE id=? AND lease_owner=?", ((datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat(),run_id,owner))
            except Exception:
                pass
    try:
        if not claim_run(lock_connection,run_id,owner):
            return
        thread = threading.Thread(target=heartbeat,daemon=True)
        thread.start()
        run = PipelineRunRepository(lock_connection).get_by_id(run_id)
        if run and run.run_configuration and run.run_configuration.get("fixture"):
            if get_settings().app_env != "test":
                raise ValueError("Fixture execution is forbidden outside test mode")
            from app.pipeline.fixtures import run_fixture
            run_fixture(run_id)
        elif run:
            asyncio.run(PipelineRunner().run(market=run.market,vertical=run.vertical,target=run.target,run_id=run_id,run_configuration=run.run_configuration))
    finally:
        stop.set()
        with db_session() as conn:
            conn.execute("UPDATE pipeline_runs SET lease_owner=NULL,lease_expires_at=NULL WHERE id=? AND lease_owner=?", (run_id,owner))
            row = conn.execute("SELECT campaign_id FROM pipeline_runs WHERE id=?",(run_id,)).fetchone()
            if row and row[0]:
                from app.api.routes.campaigns import campaign_detail
                campaign_detail(conn,row[0],persist=True)
        lock_connection.close()
        from app.api.services.cloud_executor import dispatch_queued
        dispatch_queued()


if __name__ == "__main__":
    if os.environ.get('LEADENGINE_EMAIL_SYNC')=='1':
        from app.mail.service import sync_mailbox
        try:sync_mailbox()
        except Exception:raise SystemExit('Bounded email sync could not complete; check provider health.') from None
        raise SystemExit(0)
    if os.environ.get("LEADENGINE_CANARY") == "1":
        from app.cloud_doctor import worker_canary
        worker_canary()
        raise SystemExit(0)
    report_id=os.environ.get('LEADENGINE_REPORT_ID','')
    if report_id:
        from app.reports.service import execute_report
        try:execute_report(str(uuid.UUID(report_id)))
        finally:
            from app.api.services.cloud_executor import dispatch_queued
            dispatch_queued()
        raise SystemExit(0)
    raw = os.environ.get("LEADENGINE_RUN_ID", "")
    if not raw.isdigit() or int(raw)<1:
        raise SystemExit("LEADENGINE_RUN_ID must be a positive run ID")
    execute(int(raw))
