"""Signed receipt-only compatibility for a still-registered Test Mode webhook.
No network client, dispatch, customer enrollment or entitlement writer.
"""
import hashlib,hmac,json,logging,re
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
EVENTS={'subscription.'+x for x in ('authenticated','activated','charged','completed','updated','pending','halted','cancelled','paused','resumed')}
logger=logging.getLogger(__name__)

def validate(body,signature,event_id):
    s=get_settings();secret=s.razorpay_webhook_secret.get_secret_value()
    if not secret:raise HTTPException(503,'A separate webhook verification secret is required.')
    if len(body)>262144:raise HTTPException(413,'Webhook body is too large.')
    if not isinstance(signature,str) or not re.fullmatch('[a-fA-F0-9]{64}',signature) or not hmac.compare_digest(hmac.new(secret.encode(),body,hashlib.sha256).hexdigest(),signature.lower()):raise HTTPException(400,'Webhook signature verification failed.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',event_id or ''):raise HTTPException(400,'A provider event identifier is required.')
    try:
        event=json.loads(body)
        kind=event['event']
        if kind not in EVENTS:return {'accepted':True,'ignored':True}
        sub=event['payload']['subscription']['entity'];key=sub['id']
        if not isinstance(key,str) or not re.fullmatch('sub_[A-Za-z0-9]{1,80}',key):raise ValueError()
    except (ValueError,KeyError,TypeError):raise HTTPException(400,'Invalid subscription webhook.') from None
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
    if not local or local['organization_id'] not in {v.strip() for v in get_settings().billing_test_workspaces.split(',') if v.strip()}:
        # Signed events for another app/account subscription are never enrolled.
        logger.info('Razorpay webhook ignored: subscription is not enrolled for restricted Test Mode')
        return {'accepted':True,'ignored':True}
    digest=hashlib.sha256(body).hexdigest();stamp=now()
    c.execute('INSERT INTO billing_webhook_events(mode,event_id,body_hash,event_type,provider_subscription_id,next_attempt_at,received_at,status) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(mode,event_id) DO NOTHING',('test',event_id,digest,kind,key,stamp,stamp,'IGNORED'))
    saved=c.execute('SELECT body_hash FROM billing_webhook_events WHERE mode=? AND event_id=?',('test',event_id)).fetchone()
    if saved[0]!=digest:raise HTTPException(409,'Event identifier was reused with different content.')
    return {'accepted':True,'durable':True}
