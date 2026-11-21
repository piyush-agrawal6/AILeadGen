"""Bounded transactional outbox pump using the existing Cloud Run worker."""
import asyncio,time,uuid,logging
from app.accounts import security
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.notifications import transactional as mail


def prepare(notification_id=None):
    mail.require_enabled();stamp=int(time.time())
    # Recovery lookup is asynchronous and has the same public acknowledgment for
    # absent, password-enabled and Google-only accounts.
    with db_session() as c:
        pending=[] if notification_id else [r[0] for r in c.execute("SELECT id FROM account_recovery_requests WHERE status='QUEUED' ORDER BY created_at,id LIMIT 2").fetchall()]
    from app.accounts.service import prepare_recovery
    for key in pending:prepare_recovery(key)
    claimed=[]
    with db_session() as c:
        security.lock(c,'transactional-dispatch')
        c.execute("UPDATE transactional_notifications SET status='CANCELLED',payload_encrypted=NULL,execution_name=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE status IN ('QUEUED','SENDING') AND expires_at<=?",(now(),stamp))
        # An uncertain provider response retains its immutable payload/key for
        # retry. A stale cloud launch is not proof a message was delivered.
        c.execute("UPDATE transactional_notifications SET status='QUEUED',execution_name=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE status IN ('QUEUED','SENDING') AND lease_until<=? AND attempts<3 AND dispatch_attempts<3",(now(),stamp))
        c.execute("UPDATE transactional_notifications SET status='FAILED',payload_encrypted=NULL,execution_name=NULL,lease_token=NULL,lease_until=NULL,error_code='DELIVERY_ATTEMPTS_EXHAUSTED',updated_at=? WHERE status IN ('QUEUED','SENDING') AND lease_until<=? AND (attempts>=3 OR dispatch_attempts>=3)",(now(),stamp))
        c.execute("UPDATE transactional_notifications SET status='FAILED',payload_encrypted=NULL,error_code='DISPATCH_ATTEMPTS_EXHAUSTED',updated_at=? WHERE status='QUEUED' AND execution_name IS NULL AND dispatch_attempts>=3",(now(),))
        active=c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE status IN ('QUEUED','SENDING') AND execution_name IS NOT NULL AND lease_until>?",(stamp,)).fetchone()[0]
        for row in c.execute("SELECT * FROM transactional_notifications WHERE status='QUEUED' AND execution_name IS NULL AND available_at<=? AND expires_at>? AND attempts<3 AND dispatch_attempts<3 "+(" AND id=?" if notification_id else "")+" ORDER BY created_at,id LIMIT ?",(stamp,stamp,*([notification_id] if notification_id else []),min(1,max(0,2-active)))).fetchall():
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


def enqueue_notification(key):
    """Finish the durable launch while request CPU is available.

    The outbox remains authoritative. No provider payload enters the API and an
    uncertain Cloud Run acknowledgement keeps its lease/idempotency key.
    """
    if not get_settings().transactional_mail_enabled or get_settings().app_env=='test':return
    try:
        for notification,marker in prepare(notification_id=key):
            if get_settings().app_env=='production':
                from app.api.services.cloud_executor import run_job
                operation=run_job(None,notification_id=notification)
                record(notification,marker,operation)
            else:mail.deliver(notification)
        # The background pump may have claimed this same row just before this
        # request. Keep request CPU alive for its bounded launch acknowledgement
        # instead of returning while an idle Cloud Run instance freezes it.
        deadline=time.monotonic()+10
        while get_settings().app_env=='production' and time.monotonic()<deadline:
            with db_session() as c:row=c.execute('SELECT status,execution_name FROM transactional_notifications WHERE id=?',(key,)).fetchone()
            if not row or row['status']!='QUEUED' or not (row['execution_name'] or '').startswith('DISPATCHING:'):break
            time.sleep(.5)
    except Exception as error:
        logging.getLogger(__name__).warning('Request transactional launch unavailable (%s)',type(error).__name__)


def enqueue_recovery(key):
    """Identical launch work for known/unknown accounts; lookup stays in worker."""
    if not get_settings().transactional_mail_enabled or get_settings().app_env=='test':return
    try:
        if get_settings().app_env=='production':
            with db_session() as c:
                security.lock(c,'recovery-launch')
                if security.limited(c,'recovery-launch-day','global',get_settings().transactional_mail_daily_limit,86400):return
            from app.api.services.cloud_executor import run_job
            run_job(None,recovery_request_id=key)
        else:
            from app.accounts.service import prepare_recovery
            notification=prepare_recovery(key)
            if notification:enqueue_notification(notification)
    except Exception as error:
        logging.getLogger(__name__).warning('Request recovery launch unavailable (%s)',type(error).__name__)


def deliver_bounded(key):
    """Bounded worker retries, followed by a durable handoff to queued work."""
    deadline=time.monotonic()+75
    try:
        for _ in range(30):
            if time.monotonic()>=deadline:return
            mail.deliver(key)
            with db_session() as c:
                row=c.execute('SELECT status,available_at,attempts,expires_at FROM transactional_notifications WHERE id=?',(key,)).fetchone()
            if not row or row['status'] not in ('QUEUED','SENDING') or row['attempts']>=3 or row['expires_at']<=int(time.time()):return
            if row['status']=='SENDING':return # Another fenced worker owns it.
            delay=max(1,min(15,row['available_at']-int(time.time())))
            if time.monotonic()+delay>=deadline:return
            time.sleep(delay)
    finally:
        if get_settings().app_env!='test':
            try:asyncio.run(tick())
            except Exception as error:logging.getLogger(__name__).warning('Worker outbox handoff unavailable (%s)',type(error).__name__)
