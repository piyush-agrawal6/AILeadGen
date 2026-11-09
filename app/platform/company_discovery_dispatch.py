"""Durable job dispatch through the existing worker; no new infrastructure."""
import asyncio
from app.config.settings import get_settings
from app.database.connection import db_session
from app.platform.company_discovery import owned,require_enabled,execute

_tasks=set()

async def launch(key):
    require_enabled()
    with db_session() as c:
        row=owned(c,key)
        if row['status']!='QUEUED' or row['execution_name']:return
        changed=c.execute("UPDATE organization_profile_jobs SET execution_name='DISPATCHING' WHERE id=? AND status='QUEUED' AND execution_name IS NULL",(key,)).rowcount
        if changed!=1:return
    try:
        if get_settings().app_env=='production':
            from app.api.services.cloud_executor import run_job
            operation=await asyncio.to_thread(run_job,None,profile_job_id=key)
            with db_session() as c:c.execute("UPDATE organization_profile_jobs SET execution_name=? WHERE id=? AND execution_name='DISPATCHING'",(operation,key))
        else:
            task=asyncio.create_task(asyncio.to_thread(execute,key));_tasks.add(task);task.add_done_callback(_tasks.discard)
    except Exception:
        with db_session() as c:c.execute("UPDATE organization_profile_jobs SET status='FAILED',error_code='REVIEW_DISPATCH_FAILED',execution_name=NULL WHERE id=? AND status='QUEUED' AND execution_name='DISPATCHING'",(key,))
