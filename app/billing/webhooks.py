"""Raw signed durable receipts; replayable workers re-read authoritative state.

No card data or untrusted entitlement payload is persisted. Duplicate/out-of-order
notifications trigger the same bounded reconciliation, never direct grants.
"""
import hashlib,json,logging,re,uuid
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from app.billing import provider,service
from app.config.settings import get_settings
from app.database.prospects import now
from app.database.connection import db_session

EVENTS={'subscription.'+x for x in ('authenticated','activated','charged','completed','updated','pending','halted','cancelled','paused','resumed')}
logger=logging.getLogger(__name__)

def validate(body,signature,event_id):
    provider.guard()
    s=get_settings();secret=s.razorpay_webhook_secret.get_secret_value()
    if not secret or secret==s.razorpay_key_secret.get_secret_value():raise HTTPException(503,'A separate webhook verification secret is required.')
    if len(body)>262144:raise HTTPException(413,'Webhook body is too large.')
    if not provider.verify_signature(body,signature,get_settings().razorpay_webhook_secret.get_secret_value()):raise HTTPException(400,'Webhook signature verification failed.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',event_id or ''):raise HTTPException(400,'A provider event identifier is required.')
    try:
        event=json.loads(body)
        kind=event['event']
        if kind not in EVENTS:return {'accepted':True,'ignored':True}
        sub=event['payload']['subscription']['entity'];key=provider.identifier(sub['id'],'sub')
    except (ValueError,KeyError,TypeError,provider.ProviderRejected):raise HTTPException(400,'Invalid subscription webhook.') from None
    return kind,key

def receive(c,body,signature,event_id):
    validated=validate(body,signature,event_id)
    if isinstance(validated,dict):
        kind=json.loads(body).get('event')
        safe_kind=kind if isinstance(kind,str) and re.fullmatch(r'[a-z_]{1,40}\.[a-z_]{1,40}',kind) else 'UNKNOWN'
        logger.info('Razorpay webhook ignored: unsupported event type %s',safe_kind)
        return validated
    kind,key=validated
    local=c.execute('SELECT organization_id FROM billing_subscriptions WHERE mode=? AND provider_id=?',('test',key)).fetchone()
    if not local or not service.test_allowed(local['organization_id']):
        # Signed events for another app/account subscription are never enrolled.
        logger.info('Razorpay webhook ignored: subscription is not enrolled for restricted Test Mode')
        return {'accepted':True,'ignored':True}
    digest=hashlib.sha256(body).hexdigest();stamp=now()
    c.execute('INSERT INTO billing_webhook_events(mode,event_id,body_hash,event_type,provider_subscription_id,next_attempt_at,received_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(mode,event_id) DO NOTHING',('test',event_id,digest,kind,key,stamp,stamp))
    saved=c.execute('SELECT body_hash FROM billing_webhook_events WHERE mode=? AND event_id=?',('test',event_id)).fetchone()
    if saved[0]!=digest:raise HTTPException(409,'Event identifier was reused with different content.')
    return {'accepted':True,'durable':True}

def tick(limit=10):
    """Existing dispatcher calls this; maximum ten events and ten due reads/tick."""
    if not get_settings().billing_enabled or not provider.configured():return {'processed':0,'configured':False}
    limit=max(1,min(10,limit));processed=0
    with db_session() as c:
        events=c.execute("SELECT mode,event_id FROM billing_webhook_events WHERE mode='test' AND status IN ('PENDING','RETRY','PROCESSING') AND attempts<5 AND next_attempt_at<=? AND (lease_until IS NULL OR lease_until<?) ORDER BY received_at,event_id LIMIT ?",(now(),now(),limit)).fetchall()
    for event in events:
        token=str(uuid.uuid4());lease=(datetime.now(timezone.utc)+timedelta(minutes=3)).isoformat()
        with db_session() as c:
            changed=c.execute("UPDATE billing_webhook_events SET status='PROCESSING',attempts=attempts+1,lease_token=?,lease_until=? WHERE mode=? AND event_id=? AND attempts<5 AND (lease_until IS NULL OR lease_until<?) AND status<>'PROCESSED'",(token,lease,event['mode'],event['event_id'],now())).rowcount
            if not changed:continue
            row=dict(c.execute('SELECT * FROM billing_webhook_events WHERE mode=? AND event_id=?',(event['mode'],event['event_id'])).fetchone())
            sub=c.execute('SELECT id FROM billing_subscriptions WHERE mode=? AND provider_id=?',(row['mode'],row['provider_subscription_id'])).fetchone()
        try:
            if sub:
                with db_session() as c:service.reconcile(c,sub['id'],worker=True)
            with db_session() as c:c.execute("UPDATE billing_webhook_events SET status='PROCESSED',processed_at=?,lease_until=NULL,error_code=NULL WHERE mode=? AND event_id=? AND lease_token=?",(now(),row['mode'],row['event_id'],token))
            processed+=1
        except Exception:
            with db_session() as c:c.execute("UPDATE billing_webhook_events SET status=?,next_attempt_at=?,lease_until=NULL,error_code='RECONCILIATION_REQUIRED' WHERE mode=? AND event_id=? AND lease_token=?",('FAILED' if row['attempts']>=5 else 'RETRY',(datetime.now(timezone.utc)+timedelta(minutes=min(240,2**row['attempts']))).isoformat(),row['mode'],row['event_id'],token))
    # Recover missed callbacks/webhooks from current provider state. Terminal
    # mandates need no recurring polling; a later signed event still reconciles
    # them through the durable receipt loop above. Preserve unresolved creation
    # records for explicit note-matching recovery.
    with db_session() as c:
        terminal=sorted(service.TERMINAL);marks=','.join('?' for _ in terminal)
        due=[dict(r) for r in c.execute("SELECT id,organization_id,failures FROM billing_subscriptions WHERE mode='test' AND provider_id IS NOT NULL AND status NOT IN ("+marks+") AND next_reconcile_at<=? ORDER BY next_reconcile_at,id LIMIT ?",(*terminal,now(),limit)).fetchall()]
    for sub in due:
        if not service.test_allowed(sub['organization_id']):continue
        try:
            with db_session() as c:service.reconcile(c,sub['id'],worker=True)
        except Exception:
            with db_session() as c:c.execute('UPDATE billing_subscriptions SET failures=failures+1,next_reconcile_at=? WHERE id=?',( (datetime.now(timezone.utc)+timedelta(minutes=min(240,2**min(sub['failures']+1,8)))).isoformat(),sub['id']))
    return {'processed':processed,'configured':True}
