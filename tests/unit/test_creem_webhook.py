"""Synthetic signatures and transport only; no actual Creem delivery claimed."""
import hashlib,hmac,json,time
from pydantic import SecretStr
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_customer_accounts import customer,accounts
from app.billing import creem_events
from app.billing.subscription_schema import EVENT_SQL
from app.api.server import app

@pytest.fixture
def inbox(customer,monkeypatch):
 c,s=customer;c.executescript(EVENT_SQL);c.commit()
 monkeypatch.setattr(s,'creem_webhook_secret',SecretStr('synthetic-production-signing-secret'))
 monkeypatch.setattr(s,'creem_test_webhook_secret',SecretStr('synthetic-test-signing-secret'))
 monkeypatch.setattr(s,'creem_environment','production')
 return c,s

def event(**updates):
 return {'id':'evt_synthetic_123','eventType':'subscription.paid','created_at':int(time.time()*1000),'object':{'id':'sub_synthetic','mode':'prod','customer':{'email':'private@example.com'}},**updates}
def signed(s,value):
 raw=json.dumps(value,separators=(',',':')).encode()
 return raw,hmac.new(s.creem_webhook_secret.get_secret_value().encode(),raw,hashlib.sha256).hexdigest()

def test_signed_event_is_encrypted_durable_and_idempotent_without_grant(inbox):
 c,s=inbox;raw,sig=signed(s,event())
 assert creem_events.receive(raw,sig)['duplicate'] is False
 assert creem_events.receive(raw,sig)['duplicate'] is True
 row=c.execute('SELECT * FROM subscription_provider_events').fetchone()
 assert row['status']=='PENDING' and row['environment']=='production'
 assert 'private@example.com' not in row['payload_encrypted']
 assert c.execute('SELECT COUNT(*) FROM access_periods').fetchone()[0]==0
 assert c.execute('SELECT COUNT(*) FROM customer_accounts').fetchone()[0]==0

def test_tampering_missing_signature_and_environment_cannot_write(inbox):
 c,s=inbox;raw,sig=signed(s,event())
 for body,signature in [(raw+b' ',sig),(raw,''),(raw,'0'*64),(raw,'not-hex')]:
  with pytest.raises(HTTPException) as error:creem_events.receive(body,signature)
  assert error.value.status_code==400
 with pytest.raises(HTTPException):creem_events.receive(raw,sig,environment='test')
 raw,sig=signed(s,event(object={'id':'sub_synthetic','mode':'test'}))
 with pytest.raises(HTTPException):creem_events.receive(raw,sig)
 assert c.execute('SELECT COUNT(*) FROM subscription_provider_events').fetchone()[0]==0

def test_missing_secret_and_conflicting_event_identity_fail_closed(inbox,monkeypatch):
 c,s=inbox;raw,sig=signed(s,event());creem_events.receive(raw,sig)
 other,other_sig=signed(s,event(eventType='subscription.canceled'))
 with pytest.raises(HTTPException) as error:creem_events.receive(other,other_sig)
 assert error.value.status_code==409
 monkeypatch.setattr(s,'creem_webhook_secret',SecretStr(''))
 with pytest.raises(HTTPException) as error:creem_events.receive(raw,sig)
 assert error.value.status_code==503
 assert c.execute('SELECT COUNT(*) FROM subscription_provider_events').fetchone()[0]==1

def test_public_raw_body_route_has_own_auth_and_strict_size_limit(inbox,monkeypatch):
 c,s=inbox
 from contextlib import contextmanager
 from app.api import server
 @contextmanager
 def isolated_session():
  try:yield c;c.commit()
  except Exception:c.rollback();raise
 monkeypatch.setattr(creem_events,'db_session',isolated_session)
 monkeypatch.setattr(server,'verify_schema',lambda:None)
 for k,v in {'app_env':'production','auth_disabled_local':False,'database_background_polling_enabled':False,'transactional_mail_enabled':False}.items():monkeypatch.setattr(s,k,v)
 raw,sig=signed(s,event())
 with TestClient(app) as client:
  assert client.post('/api/billing/webhooks/creem',content=raw,headers={'creem-signature':sig}).status_code==200
  assert client.post('/api/billing/webhooks/creem',content=raw).status_code==400
  assert client.post('/api/billing/webhooks/creem',content=b'x'*(creem_events.MAX_BYTES+1)).status_code==413
  assert client.get('/api/billing/webhooks/creem').status_code==401
  assert client.post('/api/billing/webhooks/creem/not-a-route',content=raw,headers={'creem-signature':sig}).status_code==401
  assert client.post('/api/billing/webhooks/creem/test',content=raw,headers={'creem-signature':sig}).status_code==400

def test_unknown_signed_event_is_retained_but_not_activated(inbox):
 c,s=inbox;raw,sig=signed(s,event(eventType='new.unsupported'))
 assert creem_events.receive(raw,sig)['received']
 assert c.execute('SELECT status FROM subscription_provider_events').fetchone()[0]=='IGNORED'
