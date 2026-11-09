"""Reuse the existing executor; local preview has a bounded periodic outbox pump."""
import asyncio,secrets
from datetime import datetime,timedelta,timezone
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.platform.context import workspace_scope
from app.api.organization import membership_role
from app.webhooks import service
_tasks=set()


async def tick():
    if not get_settings().heysow_webhooks_enabled or len(_tasks)>=2:return
    with db_session() as c:
        rows=[dict(row) for row in c.execute("""SELECT e.* FROM webhook_endpoints e
            JOIN organizations o ON o.id=e.organization_id AND o.status='ACTIVE'
            JOIN organization_memberships m ON m.organization_id=e.organization_id AND m.user_id=e.created_by AND m.status='ACTIVE' AND m.role IN ('OWNER','ADMIN')
            WHERE e.status='ACTIVE'
            AND (e.dispatch_until IS NULL OR e.dispatch_until<?) AND EXISTS
            (SELECT 1 FROM webhook_deliveries d WHERE d.endpoint_id=e.id AND
             ((d.attempts<5 AND d.status IN ('QUEUED','RETRY') AND d.next_attempt_at<=?) OR (d.status='DELIVERING' AND d.lease_until<?)))
            ORDER BY COALESCE(e.last_dispatch_at,e.created_at),e.id LIMIT 2""",(now(),now(),now())).fetchall()]
    for row in rows:
        if len(_tasks)>=2:break
        with db_session() as c:
            # A persisted endpoint creator must still have active administrative authority.
            if membership_role(c,row['created_by'],row['organization_id']) not in ('OWNER','ADMIN'):continue
            with workspace_scope(c,row['created_by'],row['organization_id']):
                from app.workflows.service import lock
                lock(c)
                if c.execute('SELECT COUNT(*) FROM webhook_endpoints WHERE dispatch_until>?',(now(),)).fetchone()[0]>=2:continue
                token=secrets.token_hex(16);expiry=(datetime.now(timezone.utc)+timedelta(seconds=180)).isoformat()
                changed=c.execute("UPDATE webhook_endpoints SET dispatch_token=?,dispatch_until=?,last_dispatch_at=? WHERE id=? AND organization_id=? AND status='ACTIVE' AND (dispatch_until IS NULL OR dispatch_until<?)",(token,expiry,now(),row['id'],row['organization_id'],now())).rowcount
                if not changed:continue
                c.commit()
                if get_settings().app_env=='production':
                    from app.api.services.cloud_executor import run_job
                    try:await asyncio.to_thread(run_job,None,webhook_endpoint_id=row['id'],webhook_dispatch_token=token)
                    except Exception:
                        c.execute("UPDATE webhook_endpoints SET dispatch_token=NULL,dispatch_until=NULL,last_error_code='DISPATCH_FAILED' WHERE id=? AND organization_id=? AND dispatch_token=?",(row['id'],row['organization_id'],token))
                else:
                    from app.webhooks.worker import execute_async
                    task=asyncio.create_task(execute_async(row['id'],dispatch_token=token));_tasks.add(task)
                    def done(completed):
                        _tasks.discard(completed)
                        if not completed.cancelled():completed.exception()
                    task.add_done_callback(done)


async def preview_loop():
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception as error:
            import logging
            logging.getLogger(__name__).warning('Webhook dispatcher unavailable (%s)',type(error).__name__)
        await asyncio.sleep(5)

async def shutdown():
    pending=list(_tasks)
    for task in pending:task.cancel()
    if pending:await asyncio.gather(*pending,return_exceptions=True)
    _tasks.clear()
