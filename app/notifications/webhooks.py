"""Resend/Svix raw-body authenticity, idempotency and durable suppression.

Algorithm: https://docs.svix.com/receiving/verifying-payloads/how-manual
Only metadata is retained; OTP/reset contents and recipient lists are not logged.
"""
import base64,hashlib,hmac,json,re,time
from datetime import datetime,timezone
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.accounts.security import lock

EVENTS={'email.delivered':'DELIVERED','email.bounced':'BOUNCED','email.complained':'COMPLAINED'}
RANK={'ACCEPTED':0,'DELIVERED':1,'BOUNCED':2,'COMPLAINED':3}

def verify(raw,headers):
    s=get_settings();secret=s.resend_webhook_secret.get_secret_value()
    if not s.transactional_mail_enabled or not secret.startswith('whsec_'):raise HTTPException(503,'Email event verification is unavailable.')
    identifier=headers.get('svix-id','');timestamp=headers.get('svix-timestamp','');signatures=headers.get('svix-signature','')
    if len(raw)>65536 or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}',identifier) or not re.fullmatch(r'[0-9]{10,12}',timestamp) or abs(int(time.time())-int(timestamp))>300 or len(signatures)>1000:raise HTTPException(400,'Invalid email event signature.')
    try:key=base64.b64decode(secret[6:],validate=True)
    except ValueError:raise HTTPException(503,'Email event verification is unavailable.') from None
    if len(key)<24:raise HTTPException(503,'Email event verification is unavailable.')
    expected=base64.b64encode(hmac.new(key,identifier.encode()+b'.'+timestamp.encode()+b'.'+raw,hashlib.sha256).digest()).decode()
    if not any(hmac.compare_digest(part[3:],expected) for part in signatures.split(' ') if part.startswith('v1,')):raise HTTPException(400,'Invalid email event signature.')
    return identifier

def reconcile(c,notification_id,provider_id):
    row=c.execute('SELECT * FROM transactional_notifications WHERE id=? AND provider_message_id=?',(notification_id,provider_id)).fetchone()
    if not row:return
    events=c.execute('SELECT event_type FROM transactional_notification_events WHERE provider_message_id=?',(provider_id,)).fetchall()
    desired=max([row['status'],*[EVENTS[r[0]] for r in events if r[0] in EVENTS]],key=lambda state:RANK.get(state,-1))
    c.execute('UPDATE transactional_notification_events SET notification_id=? WHERE provider_message_id=? AND notification_id IS NULL',(notification_id,provider_id))
    if desired in ('BOUNCED','COMPLAINED'):
        c.execute('INSERT INTO transactional_suppressions(account_email,reason,created_at) VALUES(?,?,?) ON CONFLICT(account_email) DO UPDATE SET reason=excluded.reason',(row['account_email'],desired,now()))
    if desired!=row['status']:c.execute('UPDATE transactional_notifications SET status=?,updated_at=? WHERE id=?',(desired,now(),notification_id))

def receive(c,raw,headers):
    identifier=verify(raw,headers)
    try:
        event=json.loads(raw);kind=event['type'];provider_id=event['data']['email_id']
        if not isinstance(kind,str) or not re.fullmatch(r'email\.[a-z_]{1,40}',kind) or not isinstance(provider_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',provider_id):raise ValueError()
    except (KeyError,TypeError,ValueError):raise HTTPException(400,'Invalid email event.') from None
    lock(c,'resend-event:'+identifier)
    prior=c.execute('SELECT provider_message_id,event_type FROM transactional_notification_events WHERE provider_event_id=?',(identifier,)).fetchone()
    if prior:
        if prior['provider_message_id']!=provider_id or prior['event_type']!=kind:raise HTTPException(409,'Email event identity conflicts with its recorded outcome.')
        return {'received':True,'duplicate':True}
    stamp=now();occurred=None
    try:
        provided=event.get('created_at')
        if isinstance(provided,str) and len(provided)<=40:
            parsed=datetime.fromisoformat(provided)
            if parsed.tzinfo:occurred=parsed.astimezone(timezone.utc).isoformat()
    except ValueError:pass
    c.execute('INSERT INTO transactional_notification_events(provider_event_id,provider_message_id,event_type,occurred_at,received_at) VALUES(?,?,?,?,?)',(identifier,provider_id,kind,occurred,stamp))
    row=c.execute('SELECT id FROM transactional_notifications WHERE provider_message_id=?',(provider_id,)).fetchone()
    if row:reconcile(c,row['id'],provider_id)
    return {'received':True,'duplicate':False}
