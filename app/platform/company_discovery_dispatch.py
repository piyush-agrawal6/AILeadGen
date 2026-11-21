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
        # Recover only an expired reservation. A late worker is still fenced by
        # the persisted worker lease in execute(), and can never publish twice.
        if row['status'] in ('RUNNING','QUEUED') and row['lease_expires_at'] and row['lease_expires_at']<now():
            if row['attempts']>=3:
                c.execute("UPDATE organization_profile_jobs SET status='FAILED',error_code='REVIEW_ATTEMPTS_EXHAUSTED',lease_owner=NULL,lease_expires_at=NULL WHERE id=? AND organization_id=? AND lease_expires_at<?",(key,organization(),now()));return False
            c.execute("UPDATE organization_profile_jobs SET status='QUEUED',execution_name=NULL,lease_owner=NULL,lease_expires_at=NULL WHERE id=? AND organization_id=? AND status IN ('QUEUED','RUNNING') AND lease_expires_at<?",(key,organization(),now()));row=owned(c,key)
        active=c.execute("SELECT COUNT(*) FROM organization_profile_jobs WHERE status IN ('QUEUED','RUNNING') AND execution_name IS NOT NULL AND (lease_expires_at IS NULL OR lease_expires_at>?)",(now(),)).fetchone()[0]
        if active>=2 or row['status']!='QUEUED' or row['execution_name']:return False
        token=str(uuid.uuid4());expiry=(datetime.now(timezone.utc)+timedelta(seconds=90)).isoformat()
        changed=c.execute("UPDATE organization_profile_jobs SET execution_name=?,lease_owner=?,lease_expires_at=? WHERE id=? AND organization_id=? AND status='QUEUED' AND execution_name IS NULL",('DISPATCHING:'+token,token,expiry,key,organization())).rowcount
        return token if changed==1 else None


def _record(key,token,operation=None,failed=False):
    from app.platform.context import organization
    with db_session() as c:
        if failed:c.execute("UPDATE organization_profile_jobs SET status='FAILED',error_code='REVIEW_DISPATCH_FAILED',execution_name=NULL,lease_owner=NULL,lease_expires_at=NULL WHERE id=? AND organization_id=? AND status='QUEUED' AND execution_name=?",(key,organization(),'DISPATCHING:'+token))
        else:c.execute("UPDATE organization_profile_jobs SET execution_name=? WHERE id=? AND organization_id=? AND execution_name=?",(operation,key,organization(),'DISPATCHING:'+token))


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

def _candidates():
    with db_session() as c:
        return [dict(r) for r in c.execute("""SELECT j.id,j.created_by actor,j.organization_id FROM organization_profile_jobs j
            JOIN organizations o ON o.id=j.organization_id AND o.status='ACTIVE'
            JOIN organization_memberships m ON m.organization_id=o.id AND m.user_id=j.created_by AND m.status='ACTIVE' AND m.role IN ('OWNER','ADMIN')
            WHERE (j.status='QUEUED' AND j.execution_name IS NULL) OR (j.status IN ('QUEUED','RUNNING') AND j.lease_expires_at<?)
            ORDER BY j.created_at,j.id LIMIT 8""",(now(),)).fetchall()]

async def recover():
    if not get_settings().heysow_company_discovery_enabled:return
    from app.intent_radar.schedules import _dispatch_context
    from fastapi import HTTPException
    # Keep the candidate's verified identity; never inherit another request.
    for item in await asyncio.to_thread(_candidates):
        try:ctx=await asyncio.to_thread(_dispatch_context,item)
        except HTTPException:continue
        await asyncio.create_task(launch(item['id']),context=ctx)
