"""Bounded, database-backed Cloud Run dispatch; independent of browser sessions."""
import asyncio
import json
from datetime import datetime,timezone
from app.api.services.executor_contract import ScanExecutor
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.repositories import PipelineRunRepository


def run_job(run_id, session=None, *, report_id=None, profile_job_id=None, intelligence_job_id=None,webhook_endpoint_id=None,webhook_dispatch_token=None,sheet_export_id=None,notification_id=None):
    if sheet_export_id:
        from app.integrations.service import require_enabled
        require_enabled()
    if webhook_endpoint_id:
        from app.webhooks.service import enabled
        enabled()
    if report_id:
        from app.prospecting.policy import unavailable
        unavailable()
    settings = get_settings()
    if session is None:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        session = AuthorizedSession(credentials)
    url = f"https://run.googleapis.com/v2/projects/{settings.gcp_project_id}/locations/{settings.gcp_region}/jobs/{settings.cloud_run_job}:run"
    overrides={"taskCount":1,"containerOverrides":[{"env":[{"name":"LEADENGINE_RUN_ID","value":str(run_id) if run_id else ""},{"name":"LEADENGINE_REPORT_ID","value":report_id or ""}]}]}
    if notification_id:
        from app.notifications.transactional import require_enabled
        require_enabled()
        import uuid
        notification_id=str(uuid.UUID(notification_id))
        overrides['timeout']='90s'
        overrides['containerOverrides'][0]['env']=[{'name':'PLANEBYTE_NOTIFICATION_ID','value':notification_id}]+[{'name':key,'value':''} for key in ('LEADENGINE_AUTOMATION_MODE','LEADENGINE_REPORT_ID','LEADENGINE_RUN_ID','LEADENGINE_INTELLIGENCE_JOB_ID','LEADENGINE_PROFILE_DISCOVERY_ID','LEADENGINE_WEBHOOK_ENDPOINT_ID','LEADENGINE_WEBHOOK_DISPATCH_TOKEN','LEADENGINE_SHEET_EXPORT_ID')]+[{'name':'LEADENGINE_EMAIL_SYNC','value':'0'},{'name':'LEADENGINE_CANARY','value':'0'}]
    elif sheet_export_id:
        overrides['timeout']='90s'
        overrides['containerOverrides'][0]['env']=[{'name':'LEADENGINE_SHEET_EXPORT_ID','value':sheet_export_id}]+[{'name':key,'value':''} for key in ('LEADENGINE_AUTOMATION_MODE','LEADENGINE_REPORT_ID','LEADENGINE_RUN_ID','LEADENGINE_INTELLIGENCE_JOB_ID','LEADENGINE_PROFILE_DISCOVERY_ID','LEADENGINE_WEBHOOK_ENDPOINT_ID','LEADENGINE_WEBHOOK_DISPATCH_TOKEN')]+[{'name':'LEADENGINE_EMAIL_SYNC','value':'0'},{'name':'LEADENGINE_CANARY','value':'0'}]
    elif webhook_endpoint_id:
        from app.webhooks.service import enabled
        enabled()
        overrides['timeout']='150s'
        overrides['containerOverrides'][0]['env']=[{'name':'LEADENGINE_WEBHOOK_ENDPOINT_ID','value':webhook_endpoint_id},{'name':'LEADENGINE_WEBHOOK_DISPATCH_TOKEN','value':webhook_dispatch_token or ''}]+[{'name':key,'value':''} for key in ('LEADENGINE_AUTOMATION_MODE','LEADENGINE_REPORT_ID','LEADENGINE_RUN_ID','LEADENGINE_INTELLIGENCE_JOB_ID','LEADENGINE_PROFILE_DISCOVERY_ID')]+[{'name':'LEADENGINE_EMAIL_SYNC','value':'0'},{'name':'LEADENGINE_CANARY','value':'0'}]
    elif intelligence_job_id:
        overrides['timeout']='300s'
        overrides['containerOverrides'][0]['env']=[{'name':'LEADENGINE_INTELLIGENCE_JOB_ID','value':intelligence_job_id}]+[{'name':key,'value':''} for key in ('LEADENGINE_AUTOMATION_MODE','LEADENGINE_PROFILE_DISCOVERY_ID','LEADENGINE_REPORT_ID','LEADENGINE_RUN_ID')]+[{'name':'LEADENGINE_EMAIL_SYNC','value':'0'},{'name':'LEADENGINE_CANARY','value':'0'}]
    elif profile_job_id:
        overrides['timeout']='120s'
        overrides['containerOverrides'][0]['env']=[{'name':'LEADENGINE_PROFILE_DISCOVERY_ID','value':profile_job_id}]+[{'name':key,'value':''} for key in ('LEADENGINE_AUTOMATION_MODE','LEADENGINE_REPORT_ID','LEADENGINE_RUN_ID')]+[{'name':'LEADENGINE_EMAIL_SYNC','value':'0'},{'name':'LEADENGINE_CANARY','value':'0'}]
    elif report_id:overrides['timeout']='300s'
    elif not profile_job_id:overrides['containerOverrides'][0]['env']=overrides['containerOverrides'][0]['env'][:1]
    if not notification_id:overrides['containerOverrides'][0]['env'].append({'name':'PLANEBYTE_NOTIFICATION_ID','value':''})
    response = session.post(url, json={"overrides":overrides}, timeout=30)
    if response.status_code >= 400:
        # Cloud error bodies can contain infrastructure data: never expose them to UI.
        raise RuntimeError(f"Cloud Run job dispatch rejected (HTTP {response.status_code})")
    return response.json().get("name", "accepted")


def reconcile_expired(conn):
    return conn.execute("UPDATE pipeline_runs SET status='INTERRUPTED',lease_owner=NULL,lease_expires_at=NULL,execution_name=NULL,error_message='Worker heartbeat expired; resume from the saved observations.' WHERE lease_owner IS NOT NULL AND lease_expires_at<? AND status IN ('RUNNING','QUEUED')", (datetime.now(timezone.utc).isoformat(),)).rowcount


def dispatch_queued():
    settings = get_settings()
    reserved = []
    with db_session() as conn:
        if getattr(conn, "backend", None) == "postgres":
            conn.execute("SELECT pg_advisory_xact_lock(691944303)")
        else:
            conn.execute("BEGIN IMMEDIATE")
        reconcile_expired(conn)
        active = conn.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('QUEUED','RUNNING') AND execution_name IS NOT NULL").fetchone()[0]
        capacity = max(0, settings.max_active_scans - active)
        controls=conn.execute('SELECT scan_paused FROM automation_controls WHERE id=1').fetchone()
        if not controls or controls['scan_paused']:capacity=0
        for row in conn.execute("SELECT id FROM pipeline_runs WHERE status='QUEUED' AND execution_name IS NULL AND cancellation_requested=0 ORDER BY id LIMIT ?", (capacity,)).fetchall():
            conn.execute("UPDATE pipeline_runs SET execution_name='DISPATCHING' WHERE id=? AND execution_name IS NULL", (row[0],))
            reserved.append(row[0])
    for run_id in reserved:
        try:
            operation = run_job(run_id)
            with db_session() as conn:
                conn.execute("UPDATE pipeline_runs SET execution_name=? WHERE id=?", (operation,run_id))
        except Exception:
            with db_session() as conn:
                conn.execute("UPDATE pipeline_runs SET status='FAILED',failure_class='transient',error_message='Cloud worker dispatch failed; check worker configuration and retry.' WHERE id=? AND status='QUEUED'", (run_id,))
    return reserved


class CloudRunScanExecutor(ScanExecutor):
    async def start(self, run_id, market, vertical, target, settings=None):
        await asyncio.to_thread(dispatch_queued)

    async def cancel(self, run_id):
        with db_session() as conn:
            conn.execute("UPDATE pipeline_runs SET cancellation_requested=1 WHERE id=?", (run_id,))
            return PipelineRunRepository(conn).cancel_run(run_id)

    async def resume(self, run_id):
        with db_session() as conn:
            reconcile_expired(conn)
            run = PipelineRunRepository(conn).get_by_id(run_id)
            if not run or run.status not in ["FAILED","CANCELLED","INTERRUPTED"]:
                return False
            if conn.execute("SELECT lease_owner FROM pipeline_runs WHERE id=?",(run_id,)).fetchone()[0]:
                return False
            conn.execute("UPDATE pipeline_runs SET status='QUEUED',cancellation_requested=0,execution_name=NULL,lease_owner=NULL,lease_expires_at=NULL,failure_class=NULL WHERE id=?", (run_id,))
        await asyncio.to_thread(dispatch_queued)
        return True

    def status(self, run_id):
        with db_session() as conn:
            run = PipelineRunRepository(conn).get_by_id(run_id)
            return run.status if run else None
