"""Durable bounded dispatch through the existing worker; no new infrastructure."""
import asyncio,uuid
from datetime import datetime,timedelta,timezone
from app.database.prospects import now
from app.config.settings import get_settings
from app.database.connection import db_session
from app.platform.company_discovery import owned,require_enabled,execute
_tasks=set()


def _claim(key):
    require_enabled()
    from app.api.organization import require_role
    from app.platform.context import current,organization
    from app.workflows.service import lock
    with db_session() as c:
        row=owned(c,key);require_role(c,current().actor,organization(),('OWNER','ADMIN'))
        lock(c)
        active=c.execute("SELECT COUNT(*) FROM organization_profile_jobs WHERE status IN ('QUEUED','RUNNING') AND execution_name IS NOT NULL AND (lease_expires_at IS NULL OR lease_expires_at>?)",(now(),)).fetchone()[0]
        if active>=2 or row['status']!='QUEUED' or row['execution_name']:return False
        token=str(uuid.uuid4());expiry=(datetime.now(timezone.utc)+timedelta(seconds=90)).isoformat()
        changed=c.execute("UPDATE organization_profile_jobs SET execution_name='DISPATCHING',lease_owner=?,lease_expires_at=? WHERE id=? AND organization_id=? AND status='QUEUED' AND execution_name IS NULL",(token,expiry,key,organization())).rowcount
        return token if changed==1 else None


def _record(key,token,operation=None,failed=False):
    from app.platform.context import organization
    with db_session() as c:
        if failed:c.execute("UPDATE organization_profile_jobs SET status='FAILED',error_code='REVIEW_DISPATCH_FAILED',execution_name=NULL,lease_owner=NULL,lease_expires_at=NULL WHERE id=? AND organization_id=? AND status='QUEUED' AND execution_name='DISPATCHING' AND lease_owner=?",(key,organization(),token))
        else:c.execute("UPDATE organization_profile_jobs SET execution_name=? WHERE id=? AND organization_id=? AND execution_name='DISPATCHING' AND lease_owner=?",(operation,key,organization(),token))


async def launch(key):
    if len(_tasks)>=2:return
    token=await asyncio.to_thread(_claim,key)
    if not token:return
    try:
        if get_settings().app_env=='production':
            from app.api.services.cloud_executor import run_job
            operation=await asyncio.to_thread(run_job,None,profile_job_id=key)
            await asyncio.to_thread(_record,key,token,operation)
        else:
            task=asyncio.create_task(asyncio.to_thread(execute,key));_tasks.add(task);task.add_done_callback(_tasks.discard)
    except Exception:
        await asyncio.to_thread(_record,key,token,failed=True)
