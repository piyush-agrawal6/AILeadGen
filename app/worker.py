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
    from app.platform.context import job_scope
    with db_session() as scope_conn:
        verify_schema(scope_conn)
        with job_scope(scope_conn,'scan',run_id):
            return _execute_owned(run_id)

def _execute_owned(run_id):
    owner = str(uuid.uuid4())
    lock_connection = get_connection(session_bound=True)
    verify_schema(lock_connection)
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
    customer_mailbox_id=os.environ.get('LEADENGINE_CUSTOMER_MAILBOX_ID','')
    if customer_mailbox_id:
        from app.mail.customer import sync_owned_account
        if not customer_mailbox_id.startswith('gmail-'):raise SystemExit('A persisted customer Gmail account ID is required.')
        account_id='gmail-'+str(uuid.UUID(customer_mailbox_id.removeprefix('gmail-')))
        sync_owned_account(account_id)
        raise SystemExit(0)
    sheet_export_id=os.environ.get('LEADENGINE_SHEET_EXPORT_ID','')
    if sheet_export_id:
        from app.integrations.sheet_exports import execute as execute_sheet_export
        asyncio.run(execute_sheet_export(str(uuid.UUID(sheet_export_id))))
        raise SystemExit(0)
    webhook_endpoint_id=os.environ.get('LEADENGINE_WEBHOOK_ENDPOINT_ID','')
    if webhook_endpoint_id:
        from app.webhooks.worker import execute as execute_webhook
        execute_webhook(str(uuid.UUID(webhook_endpoint_id)),dispatch_token=os.environ.get('LEADENGINE_WEBHOOK_DISPATCH_TOKEN',''))
        raise SystemExit(0)
    mode=os.environ.get('LEADENGINE_AUTOMATION_MODE')
    if mode:
        if mode=='webhooks-dispatch':
            from app.webhooks.service import enabled
            enabled()
        from app.workflows.health import record
        record(mode,'RUNNING')
        try:
            from app.automation.service import acquisition_tick,outreach_tick
            if mode=='inbox-sync':
                from app.mail.service import sync_internal_mailbox
                sync_internal_mailbox()
                from app.workflows.service import dispatch
                with db_session() as c:asyncio.run(dispatch(c))
            elif mode in ('daily-acquisition','hourly-outreach','workflow-dispatch'):
                from app.workflows.service import dispatch
                with db_session() as c:
                    verify_schema(c)
                    asyncio.run(dispatch(c))
            elif mode=='webhooks-dispatch':
                from app.webhooks.dispatch import tick
                asyncio.run(tick())
            else:raise SystemExit('Unsupported automation mode')
        except Exception as exc:
            record(mode,'FAILED',type(exc).__name__)
            raise
        else:record(mode,'READY')
        raise SystemExit(0)
    if os.environ.get('LEADENGINE_EMAIL_SYNC')=='1':
        from app.mail.service import sync_internal_mailbox
        try:sync_internal_mailbox()
        except Exception:raise SystemExit('Bounded email sync could not complete; check provider health.') from None
        raise SystemExit(0)
    if os.environ.get("LEADENGINE_CANARY") == "1":
        from app.cloud_doctor import worker_canary
        worker_canary()
        raise SystemExit(0)
    intelligence_job_id=os.environ.get('LEADENGINE_INTELLIGENCE_JOB_ID','')
    if intelligence_job_id:
        from app.intelligence.jobs import execute as execute_intelligence
        execute_intelligence(str(uuid.UUID(intelligence_job_id)))
        raise SystemExit(0)
    profile_job_id=os.environ.get('LEADENGINE_PROFILE_DISCOVERY_ID','')
    if profile_job_id:
        from app.platform.company_discovery import execute as execute_profile
        execute_profile(str(uuid.UUID(profile_job_id)))
        raise SystemExit(0)
    report_id=os.environ.get('LEADENGINE_REPORT_ID','')
    if report_id:
        raise SystemExit('Assessment jobs are excluded from Lead Engine; historical reports are preserved.')
    raw = os.environ.get("LEADENGINE_RUN_ID", "")
    if not raw.isdigit() or int(raw)<1:
        raise SystemExit("LEADENGINE_RUN_ID must be a positive run ID")
    execute(int(raw))
