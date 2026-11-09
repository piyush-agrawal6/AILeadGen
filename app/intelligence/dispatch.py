"""Dispatch through the existing Cloud Run worker or two local tasks."""
import asyncio
from app.database.connection import db_session
from app.config.settings import get_settings
from app.intelligence.jobs import owned,execute
_tasks=set()

async def launch(key):
    if len(_tasks)>=2:return
    with db_session() as c:
        row=owned(c,key)
        from app.workflows.service import lock
        lock(c)
        active=c.execute("SELECT COUNT(*) FROM intelligence_jobs WHERE status IN ('QUEUED','RUNNING') AND execution_name IS NOT NULL").fetchone()[0]
        if active>=2:return
        changed=c.execute("UPDATE intelligence_jobs SET execution_name='DISPATCHING',dispatch_attempts=dispatch_attempts+1 WHERE id=? AND organization_id=? AND status='QUEUED' AND execution_name IS NULL AND dispatch_attempts<3",(key,row['organization_id'])).rowcount
        if not changed:return
    try:
        if get_settings().app_env=='production':
            from app.api.services.cloud_executor import run_job
            operation=await asyncio.to_thread(run_job,None,intelligence_job_id=key)
            with db_session() as c:c.execute("UPDATE intelligence_jobs SET execution_name=? WHERE id=? AND organization_id=? AND execution_name='DISPATCHING'",(operation,key,row['organization_id']))
        else:
            task=asyncio.create_task(asyncio.to_thread(execute,key));_tasks.add(task)
            def done(completed):
                _tasks.discard(completed)
                failure=completed.exception() if not completed.cancelled() else None
                if failure:
                    with db_session() as c:c.execute("UPDATE intelligence_jobs SET status='FAILED',error_code='WORKER_AUTHORIZATION_OR_EXECUTION_FAILED',lease_owner=NULL,lease_until=NULL WHERE id=? AND organization_id=? AND status IN ('QUEUED','RUNNING')",(key,row['organization_id']))
                asyncio.create_task(dispatch_owned())
            task.add_done_callback(done)
    except Exception:
        with db_session() as c:c.execute("UPDATE intelligence_jobs SET status='FAILED',error_code='DISPATCH_FAILED',execution_name=NULL WHERE id=? AND organization_id=? AND status='QUEUED'",(key,row['organization_id']))

async def dispatch_owned(connection=None):
    from app.platform.context import organization
    try:org=organization()
    except Exception:return
    query="SELECT id FROM intelligence_jobs WHERE organization_id=? AND status='QUEUED' AND execution_name IS NULL ORDER BY created_at LIMIT 2"
    if connection is not None:keys=[row[0] for row in connection.execute(query,(org,)).fetchall()]
    else:
        with db_session() as c:keys=[row[0] for row in c.execute(query,(org,)).fetchall()]
    for key in keys:await launch(key)
