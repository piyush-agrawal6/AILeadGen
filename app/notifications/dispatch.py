"""Bounded transactional outbox pump using the existing Cloud Run worker."""
import asyncio,time,uuid,logging
from app.accounts import security
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.notifications import transactional as mail


def prepare():
    mail.require_enabled();stamp=int(time.time())
    # Recovery lookup is asynchronous and has the same public acknowledgment for
    # absent, password-enabled and Google-only accounts.
    with db_session() as c:
        pending=[r[0] for r in c.execute("SELECT id FROM account_recovery_requests WHERE status='QUEUED' ORDER BY created_at,id LIMIT 2").fetchall()]
    from app.accounts.service import prepare_recovery
    for key in pending:prepare_recovery(key)
    claimed=[]
    with db_session() as c:
        security.lock(c,'transactional-dispatch')
        from app.billing.fixed_term import expiry_notices
        expiry_notices(c,2)
        c.execute("UPDATE transactional_notifications SET status='CANCELLED',payload_encrypted=NULL,execution_name=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE status IN ('QUEUED','SENDING') AND expires_at<=?",(now(),stamp))
        # An uncertain provider response retains its immutable payload/key for
        # retry. A stale cloud launch is not proof a message was delivered.
        c.execute("UPDATE transactional_notifications SET status='QUEUED',execution_name=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE status IN ('QUEUED','SENDING') AND lease_until<=? AND attempts<3 AND dispatch_attempts<3",(now(),stamp))
        c.execute("UPDATE transactional_notifications SET status='FAILED',payload_encrypted=NULL,execution_name=NULL,lease_token=NULL,lease_until=NULL,error_code='DELIVERY_ATTEMPTS_EXHAUSTED',updated_at=? WHERE status IN ('QUEUED','SENDING') AND lease_until<=? AND (attempts>=3 OR dispatch_attempts>=3)",(now(),stamp))
        c.execute("UPDATE transactional_notifications SET status='FAILED',payload_encrypted=NULL,error_code='DISPATCH_ATTEMPTS_EXHAUSTED',updated_at=? WHERE status='QUEUED' AND execution_name IS NULL AND dispatch_attempts>=3",(now(),))
        active=c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE status IN ('QUEUED','SENDING') AND execution_name IS NOT NULL AND lease_until>?",(stamp,)).fetchone()[0]
        for row in c.execute("SELECT * FROM transactional_notifications WHERE status='QUEUED' AND execution_name IS NULL AND available_at<=? AND expires_at>? AND attempts<3 AND dispatch_attempts<3 ORDER BY created_at,id LIMIT ?",(stamp,stamp,min(1,max(0,2-active)))).fetchall():
            if not mail.authorized(c,row):
                c.execute("UPDATE transactional_notifications SET status='CANCELLED',payload_encrypted=NULL,updated_at=? WHERE id=?",(now(),row['id']));continue
            marker='DISPATCHING:'+str(uuid.uuid4())
            c.execute('UPDATE transactional_notifications SET execution_name=?,dispatch_attempts=dispatch_attempts+1,lease_until=?,updated_at=? WHERE id=?',(marker,stamp+120,now(),row['id']))
            claimed.append((row['id'],marker))
    return claimed


def record(key,marker,operation):
    # Warm workers may finish before Cloud Run acknowledges launch. CAS on the
    # unique dispatch marker cannot overwrite a newer launch or settled outcome.
    with db_session() as c:c.execute('UPDATE transactional_notifications SET execution_name=? WHERE id=? AND execution_name=?',(operation,key,marker))


async def tick():
    if not get_settings().transactional_mail_enabled:return
    rows=await asyncio.to_thread(prepare)
    for key,marker in rows:
        try:
            if get_settings().app_env=='production':
                from app.api.services.cloud_executor import run_job
                operation=await asyncio.to_thread(run_job,None,notification_id=key)
                await asyncio.to_thread(record,key,marker,operation)
            else:await asyncio.to_thread(mail.deliver,key)
        except Exception as error:
            # Unknown launch outcomes retain the lease before another attempt.
            logging.getLogger(__name__).warning('Transactional dispatch unavailable (%s)',type(error).__name__)


async def loop():
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception as error:logging.getLogger(__name__).warning('Transactional outbox unavailable (%s)',type(error).__name__)
        await asyncio.sleep(2)
