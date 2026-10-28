"""Bounded, database-backed Cloud Run dispatch; independent of browser sessions."""
import asyncio
import json
from datetime import datetime,timezone
from app.api.services.executor_contract import ScanExecutor
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.repositories import PipelineRunRepository


def run_job(run_id, session=None, *, report_id=None):
    settings = get_settings()
    if session is None:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        session = AuthorizedSession(credentials)
    url = f"https://run.googleapis.com/v2/projects/{settings.gcp_project_id}/locations/{settings.gcp_region}/jobs/{settings.cloud_run_job}:run"
    overrides={"taskCount":1,"containerOverrides":[{"env":[{"name":"LEADENGINE_RUN_ID","value":str(run_id) if run_id else ""},{"name":"LEADENGINE_REPORT_ID","value":report_id or ""}]}]}
    if report_id:overrides['timeout']='300s'
    else:overrides['containerOverrides'][0]['env']=overrides['containerOverrides'][0]['env'][:1]
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
    report_ids = []
    with db_session() as conn:
        if getattr(conn, "backend", None) == "postgres":
            conn.execute("SELECT pg_advisory_xact_lock(691944303)")
        else:
            conn.execute("BEGIN IMMEDIATE")
        reconcile_expired(conn)
        active = conn.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('QUEUED','RUNNING') AND execution_name IS NOT NULL").fetchone()[0]
        has_reports=conn.execute('SELECT COALESCE(MAX(version),0) FROM schema_migrations').fetchone()[0]>=5
        if has_reports:
            from app.reports.service import expire_reports
            expire_reports(conn)
            active+=conn.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING') AND execution_name IS NOT NULL").fetchone()[0]
        capacity = max(0, settings.max_active_scans - active)
        if has_reports:
            for row in conn.execute("SELECT id FROM client_reports WHERE status='QUEUED' AND execution_name IS NULL ORDER BY created_at LIMIT ?",(capacity,)).fetchall():
                conn.execute("UPDATE client_reports SET execution_name='DISPATCHING' WHERE id=?",(row[0],));report_ids.append(row[0])
            capacity-=len(report_ids)
        for row in conn.execute("SELECT id FROM pipeline_runs WHERE status='QUEUED' AND execution_name IS NULL AND cancellation_requested=0 ORDER BY id LIMIT ?", (capacity,)).fetchall():
            conn.execute("UPDATE pipeline_runs SET execution_name='DISPATCHING' WHERE id=? AND execution_name IS NULL", (row[0],))
            reserved.append(row[0])
    for report_id in report_ids:
        try:
            operation=run_job(None,report_id=report_id)
            with db_session() as conn:conn.execute("UPDATE client_reports SET execution_name=? WHERE id=?",(operation,report_id))
        except Exception:
            with db_session() as conn:conn.execute("UPDATE client_reports SET status='FAILED',error_message='Cloud worker dispatch failed' WHERE id=? AND status='QUEUED'",(report_id,))
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
