"""Verified raw-body Creem inbox. A receipt never grants product access."""
import hashlib,hmac,json,re
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.notifications.transactional import cipher

MAX_BYTES=262144
EVENTS=frozenset(('checkout.completed','subscription.active','subscription.paid',
 'subscription.trialing','subscription.canceled','subscription.scheduled_cancel',
 'subscription.expired','subscription.paused','subscription.update',
 'subscription.past_due','subscription.unpaid','refund.created','dispute.created'))

def secret_for(environment):
 s=get_settings()
 # Test mode never accepts the production secret, including on a test runtime.
 return (s.creem_webhook_secret if environment=='production' else s.creem_test_webhook_secret).get_secret_value()

def receive(raw,signature,*,environment=None):
 environment=environment or get_settings().creem_environment
 secret=secret_for(environment)
 if not secret:raise HTTPException(503,'Creem webhook signing is not configured.')
 if len(raw)>MAX_BYTES:raise HTTPException(413,'Webhook payload exceeds the allowed size.')
 if not isinstance(signature,str) or not re.fullmatch(r'[a-fA-F0-9]{64}',signature):raise HTTPException(400,'Invalid webhook signature.')
 digest=hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
 if not hmac.compare_digest(digest,signature.lower()):raise HTTPException(400,'Invalid webhook signature.')
 try:
  data=json.loads(raw)
  if not isinstance(data,dict):raise ValueError()
  event_id=data['id'];kind=data['eventType'];obj=data['object'];created=data['created_at']
  if not isinstance(event_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',event_id) or not isinstance(kind,str) or not re.fullmatch(r'[a-z_]+\.[a-z_]+',kind) or len(kind)>80 or not isinstance(obj,dict) or type(created) is not int or created<=0:raise ValueError()
  object_id=obj.get('id','')
  if not isinstance(object_id,str) or len(object_id)>200:raise ValueError()
  mode=obj.get('mode')
  if mode is not None and mode!=('prod' if environment=='production' else 'test'):raise ValueError()
 except (ValueError,KeyError,TypeError,UnicodeError):raise HTTPException(400,'Invalid webhook event.') from None
 body_hash=hashlib.sha256(raw).hexdigest()
 with db_session() as c:
  # Database uniqueness is authoritative across instances and concurrent replay.
  encrypted=cipher().encrypt(raw).decode()
  inserted=c.execute("INSERT INTO subscription_provider_events(provider,environment,event_id,event_type,body_hash,object_id,payload_encrypted,status,received_at) VALUES('creem',?,?,?,?,?,?,?,?) ON CONFLICT(provider,environment,event_id) DO NOTHING",(environment,event_id,kind,body_hash,object_id,encrypted,'PENDING' if kind in EVENTS else 'IGNORED',now())).rowcount
  prior=c.execute("SELECT body_hash,status FROM subscription_provider_events WHERE provider='creem' AND environment=? AND event_id=?",(environment,event_id)).fetchone()
  if not prior or not hmac.compare_digest(prior['body_hash'],body_hash):raise HTTPException(409,'Webhook event identity conflicts with its recorded payload.')
 return {'received':True,'duplicate':inserted==0,'event_id':event_id}
