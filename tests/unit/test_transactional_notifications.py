"""Provider transport is intercepted; no real messages or recipient exposure."""
import base64,hashlib,hmac,json,time,uuid
from pydantic import SecretStr
import pytest,httpx
from fastapi import HTTPException
from test_customer_accounts import customer,accounts,signup,otp
from app.notifications import transactional as mail,webhooks,dispatch
from app.accounts import service,models

def pending(c):
    receipt=service.begin_signup(signup(),'fixture-client')
    key=c.execute('SELECT id FROM transactional_notifications WHERE authority_id=?',(receipt['challenge_id'],)).fetchone()[0]
    return key,receipt

def signed(s,event,identifier='msg_fixture'):
    s.resend_webhook_secret=SecretStr('whsec_'+base64.b64encode(b'fixture-svix-signing-key-32-bytes!!').decode())
    raw=json.dumps(event,separators=(',',':')).encode();stamp=str(int(time.time()))
    digest=base64.b64encode(hmac.new(b'fixture-svix-signing-key-32-bytes!!',identifier.encode()+b'.'+stamp.encode()+b'.'+raw,hashlib.sha256).digest()).decode()
    return raw,{'svix-id':identifier,'svix-timestamp':stamp,'svix-signature':'v1,'+digest}

def test_encrypted_outbox_sends_once_and_purges_payload(customer,monkeypatch):
    c,s=customer;key,receipt=pending(c);calls=[]
    def send(payload,identity):
        calls.append(identity)
        assert otp(c,receipt['challenge_id']) in payload['text']
        return 'provider-fixture-id'
    monkeypatch.setattr(mail,'send_provider',send)
    mail.deliver(key);mail.deliver(key)
    row=c.execute('SELECT * FROM transactional_notifications WHERE id=?',(key,)).fetchone()
    assert row['status']=='ACCEPTED' and row['payload_encrypted'] is None and row['attempts']==1 and calls==[key]
    assert row['provider_message_id']=='provider-fixture-id'

def test_consumed_expired_or_suppressed_codes_cannot_send(customer,monkeypatch):
    c,s=customer;key,receipt=pending(c);calls=[]
    monkeypatch.setattr(mail,'send_provider',lambda *_:calls.append('unexpected'))
    c.execute('UPDATE account_verifications SET expires_at=0');c.commit()
    mail.deliver(key)
    assert not calls and c.execute('SELECT status FROM transactional_notifications').fetchone()[0]=='CANCELLED'

def test_uncertain_delivery_retries_identical_idempotency_key(customer,monkeypatch):
    c,s=customer;key,_=pending(c);calls=[]
    def timeout(payload,identity):calls.append((payload,identity));raise httpx.ReadTimeout('Fixture timeout')
    monkeypatch.setattr(mail,'send_provider',timeout)
    mail.deliver(key)
    row=c.execute('SELECT * FROM transactional_notifications').fetchone()
    assert row['status']=='QUEUED' and row['payload_encrypted'] and row['attempts']==1
    c.execute('UPDATE transactional_notifications SET available_at=0');c.execute("DELETE FROM account_rate_limits WHERE kind='notification-second'");c.commit()
    monkeypatch.setattr(mail,'send_provider',lambda payload,identity:(calls.append((payload,identity)) or 'provider-retried'))
    mail.deliver(key)
    assert calls[0]==calls[1] and c.execute('SELECT attempts FROM transactional_notifications').fetchone()[0]==2

def test_signed_bounce_duplicate_and_late_delivery_never_remove_suppression(customer,monkeypatch):
    c,s=customer;key,_=pending(c)
    monkeypatch.setattr(mail,'send_provider',lambda *_:'fixture-id')
    mail.deliver(key)
    raw,headers=signed(s,{'type':'email.bounced','data':{'email_id':'fixture-id'}})
    assert not webhooks.receive(c,raw,headers)['duplicate'];c.commit()
    assert webhooks.receive(c,raw,headers)['duplicate']
    raw,headers=signed(s,{'type':'email.delivered','data':{'email_id':'fixture-id'}},'msg_delivered')
    webhooks.receive(c,raw,headers)
    assert c.execute('SELECT status FROM transactional_notifications').fetchone()[0]=='BOUNCED'
    assert c.execute('SELECT COUNT(*) FROM transactional_suppressions').fetchone()[0]==1
    with pytest.raises(HTTPException):webhooks.receive(c,raw+b' ',headers)
    with pytest.raises(HTTPException):webhooks.receive(c,raw,{**headers,'svix-timestamp':'1000000000'})

def test_event_arriving_before_provider_ack_is_reconciled(customer,monkeypatch):
    c,s=customer;key,_=pending(c)
    raw,headers=signed(s,{'type':'email.complained','data':{'email_id':'early-fixture'}})
    webhooks.receive(c,raw,headers);c.commit()
    assert c.execute('SELECT notification_id FROM transactional_notification_events').fetchone()[0] is None
    monkeypatch.setattr(mail,'send_provider',lambda *_:'early-fixture')
    mail.deliver(key)
    assert c.execute('SELECT status FROM transactional_notifications').fetchone()[0]=='COMPLAINED'
    assert c.execute('SELECT notification_id FROM transactional_notification_events').fetchone()[0]==key

def test_bounded_dispatch_markers_do_not_overwrite_new_launch(customer):
    c,s=customer;key,_=pending(c)
    first=dispatch.prepare();assert len(first)==1 and first[0][0]==key
    assert dispatch.prepare()==[]
    c.execute('UPDATE transactional_notifications SET execution_name=? WHERE id=?',('newer-operation',key));c.commit()
    dispatch.record(key,first[0][1],'old-ack')
    assert c.execute('SELECT execution_name FROM transactional_notifications').fetchone()[0]=='newer-operation'
    c.execute('UPDATE transactional_notifications SET lease_until=0');c.commit()
    second=dispatch.prepare();assert len(second)==1 and second[0][1]!=first[0][1]
    assert c.execute('SELECT dispatch_attempts FROM transactional_notifications').fetchone()[0]==2

def test_notification_cloud_mode_clears_other_work_and_outreach_flags(customer):
    from app.api.services.cloud_executor import run_job
    c,s=customer;key,_=pending(c);seen=[]
    class Session:
        def post(self,url,**kw):seen.append(kw);return httpx.Response(200,json={'name':'fixture-cloud-operation'})
    assert run_job(None,Session(),notification_id=key)=='fixture-cloud-operation'
    options=seen[0]['json']['overrides'];env={r['name']:r['value'] for r in options['containerOverrides'][0]['env']}
    assert options['timeout']=='150s' and env['PLANEBYTE_NOTIFICATION_ID']==key
    assert env['LEADENGINE_RUN_ID']==env['LEADENGINE_INTELLIGENCE_JOB_ID']==env['LEADENGINE_AUTOMATION_MODE']==''
    assert env['LEADENGINE_EMAIL_SYNC']==env['LEADENGINE_CANARY']=='0'


def test_request_dispatch_launches_only_its_committed_notification(customer,monkeypatch):
    from app.api.services import cloud_executor
    c,s=customer;key,_=pending(c)
    other_receipt=service.begin_signup(signup('other@example.com'),'other-client')
    other=c.execute('SELECT id FROM transactional_notifications WHERE authority_id=?',(other_receipt['challenge_id'],)).fetchone()[0]
    monkeypatch.setattr(s,'app_env','production');launched=[]
    from app.database.connection import db_session
    from pathlib import Path
    monkeypatch.setattr(dispatch,'db_session',lambda:db_session(Path(s.database_path)))
    def launch(run_id,**kw):launched.append(kw);return 'request-cloud-operation'
    monkeypatch.setattr(cloud_executor,'run_job',launch)
    dispatch.enqueue_notification(key)
    assert launched==[{'notification_id':key}]
    assert c.execute('SELECT execution_name FROM transactional_notifications WHERE id=?',(key,)).fetchone()[0]=='request-cloud-operation'
    assert c.execute('SELECT execution_name FROM transactional_notifications WHERE id=?',(other,)).fetchone()[0] is None
    dispatch.enqueue_notification(key)
    assert len(launched)==1


def test_request_keeps_cpu_until_existing_background_launch_acknowledges(customer,monkeypatch):
    from app.api.services import cloud_executor
    c,s=customer;key,_=pending(c);claimed=dispatch.prepare();assert len(claimed)==1
    marker=claimed[0][1];monkeypatch.setattr(s,'app_env','production')
    from app.database.connection import db_session
    from pathlib import Path
    monkeypatch.setattr(dispatch,'db_session',lambda:db_session(Path(s.database_path)))
    monkeypatch.setattr(cloud_executor,'run_job',lambda *a,**k:pytest.fail('Must not duplicate an in-flight launch'))
    waits=[]
    def acknowledge(delay):waits.append(delay);dispatch.record(key,marker,'background-ack')
    monkeypatch.setattr(dispatch.time,'sleep',acknowledge)
    dispatch.enqueue_notification(key)
    assert waits and c.execute('SELECT execution_name FROM transactional_notifications WHERE id=?',(key,)).fetchone()[0]=='background-ack'


def test_recovery_dispatch_defers_identity_lookup_and_is_globally_bounded(customer,monkeypatch):
    from app.api.services import cloud_executor
    c,s=customer;monkeypatch.setattr(s,'app_env','production');monkeypatch.setattr(s,'transactional_mail_daily_limit',2)
    from app.database.connection import db_session
    from pathlib import Path
    monkeypatch.setattr(dispatch,'db_session',lambda:db_session(Path(s.database_path)))
    launched=[];monkeypatch.setattr(cloud_executor,'run_job',lambda *a,**k:launched.append(k) or 'recovery-op')
    monkeypatch.setattr(service,'prepare_recovery',lambda *a:pytest.fail('Account lookup must remain outside the public response'))
    keys=[str(uuid.uuid4()) for _ in range(3)]
    for key in keys:dispatch.enqueue_recovery(key)
    assert launched==[{'recovery_request_id':key} for key in keys[:2]]
    assert c.execute('SELECT COUNT(*) FROM transactional_notifications').fetchone()[0]==0


def test_recovery_cloud_override_is_bounded_and_clears_every_other_mode(customer):
    from app.api.services.cloud_executor import run_job
    _,_=customer;key=str(uuid.uuid4());seen=[]
    class Session:
        def post(self,url,**kw):seen.append(kw);return httpx.Response(200,json={'name':'fixture-recovery-operation'})
    assert run_job(None,Session(),recovery_request_id=key)=='fixture-recovery-operation'
    options=seen[0]['json']['overrides'];rows=options['containerOverrides'][0]['env'];env={r['name']:r['value'] for r in rows}
    assert len(rows)==len(env) and options['timeout']=='150s' and seen[0]['timeout']==8
    assert env['PLANEBYTE_ACCOUNT_RECOVERY_ID']==key and env['PLANEBYTE_NOTIFICATION_ID']==''
    assert env['LEADENGINE_RUN_ID']==env['LEADENGINE_AUTOMATION_MODE']==env['LEADENGINE_SHEET_EXPORT_ID']==''
    assert env['LEADENGINE_EMAIL_SYNC']==env['LEADENGINE_CANARY']=='0'


@pytest.mark.parametrize('failures,expected',[(1,'ACCEPTED'),(3,'FAILED')])
def test_worker_retry_is_bounded_idempotent_and_hands_off_outbox(customer,monkeypatch,failures,expected):
    from unittest.mock import AsyncMock
    c,s=customer;key,_=pending(c);clock=[int(time.time())];calls=[]
    monkeypatch.setattr(s,'app_env','development')
    monkeypatch.setattr(dispatch.time,'time',lambda:clock[0])
    monkeypatch.setattr(dispatch.time,'sleep',lambda delay:clock.__setitem__(0,clock[0]+delay))
    handoff=AsyncMock();monkeypatch.setattr(dispatch,'tick',handoff)
    def provider(payload,request_id):
        calls.append(request_id)
        if len(calls)<=failures:raise httpx.ReadTimeout('Synthetic retry')
        return 'fixture-provider-accepted'
    monkeypatch.setattr(mail,'send_provider',provider)
    dispatch.deliver_bounded(key)
    row=c.execute('SELECT status,attempts FROM transactional_notifications WHERE id=?',(key,)).fetchone()
    assert row['status']==expected and row['attempts']==min(3,failures+1)
    assert all(value==key for value in calls) and len(calls)<=3
    handoff.assert_awaited_once()


def test_signup_http_commits_outbox_and_launches_before_acknowledging(customer,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.database.connection import db_session
    from test_customer_accounts import sign,PASSWORD
    c,s=customer;body=signup();payload={**body.model_dump(mode='json'),'password':PASSWORD};launched=[]
    def launch(key):
        with db_session() as committed:
            row=committed.execute('SELECT account_email,status FROM transactional_notifications WHERE id=?',(key,)).fetchone()
            assert row and row['account_email']==body.email and row['status']=='QUEUED'
        launched.append(key)
    monkeypatch.setattr(dispatch,'enqueue_notification',launch)
    client=TestClient(app)
    response=sign(client,s,'/api/organization/accounts/signup',body.email,payload)
    assert response.status_code==200 and response.json()['accepted'] and launched
    assert 'notification_id' not in response.json()
