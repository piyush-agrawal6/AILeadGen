"""Real password/session code with isolated DB and encrypted test-only outbox.

No provider message, Google completion or paid transaction is claimed here.
"""
import json,re,time,uuid
import pytest
from pydantic import SecretStr,ValidationError
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_account_admission import accounts,claim
from app.accounts import models,service,sessions,google,policy,passwords
from app.notifications import transactional as mail
from app.platform import admission
from app.database.connection import db_session
from app.api.server import app
from app.api.security import canonical_request
import hashlib,hmac

PASSWORD='An isolated secure passphrase 926!'
@pytest.fixture
def customer(accounts,monkeypatch):
    c,s=accounts
    for name,value in {'heysow_accounts_enabled':True,'heysow_access_periods_enabled':True,'transactional_mail_enabled':True,'resend_api_key':SecretStr('fixture-only-not-a-live-key'),'resend_from_email':'PlaneByte <accounts@planebyte.com>'}.items():monkeypatch.setattr(s,name,value)
    monkeypatch.setattr(policy,'mailbox_domain_available',lambda _:True)
    return c,s

def signup(email='person@example.com',**updates):
    return models.Signup(email=email,password=SecretStr(PASSWORD),name='Test person',company_name='Test company',terms_version='synthetic-review-version',accepted_terms=True,request_id=uuid.uuid4(),**updates)

def otp(c,key):
    row=c.execute('SELECT payload_encrypted FROM transactional_notifications WHERE authority_id=? ORDER BY created_at DESC LIMIT 1',(key,)).fetchone()
    payload=json.loads(mail.cipher().decrypt(row[0].encode()))
    return re.search(r'code is (\d{6})',payload['text']).group(1)

def verified(c,body=None):
    body=body or signup();receipt=service.begin_signup(body,'fixture-client')
    result=service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=otp(c,receipt['challenge_id'])),'fixture-client')
    assert result['verified']
    return result,receipt

def sign(client,s,path,actor,body,session='',client_id='a'*64):
    raw=json.dumps(body,separators=(',',':')).encode();stamp=str(int(time.time()));nonce=str(uuid.uuid4())
    signature=hmac.new(s.api_signing_secret.encode(),canonical_request(stamp,nonce,'POST',path,raw,actor,session,client_id).encode(),hashlib.sha256).hexdigest()
    return client.post(path,content=raw,headers={'content-type':'application/json','x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':signature,'x-le-client':client_id,'x-le-session':session})

def test_signup_verifies_once_creates_only_owned_trial_and_real_session(customer):
    c,s=customer;body=signup();receipt=service.begin_signup(body,'fixture-client')
    assert not c.execute('SELECT 1 FROM users WHERE id=?',(body.email,)).fetchone()
    assert service.begin_signup(body,'fixture-client')['challenge_id']==receipt['challenge_id']
    raw=otp(c,receipt['challenge_id'])
    record=c.execute('SELECT * FROM account_verifications').fetchone()
    assert raw not in record['payload_json'] and record['code_hash']!=raw
    result=service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=raw),'fixture-client')
    assert result['verified'] and result['trial']['limits']['ai_calls']==3
    assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',(body.email,)).fetchone()[0]==1
    with db_session() as d:
        value=sessions.exchange(d,result['login_ticket'])
        sessions.validate(d,body.email,value['session_token'])
    with db_session() as d:
        with pytest.raises(HTTPException):sessions.exchange(d,result['login_ticket'])
    assert not service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=raw),'fixture-client')['verified']
    assert c.execute('SELECT COUNT(*) FROM commercial_contracts').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM payu_access_orders').fetchone()[0]==0

def test_wrong_expired_code_and_capability_do_not_create_account(customer):
    c,_=customer;receipt=service.begin_signup(signup(),'fixture-client')
    body=dict(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code='not-code')
    for _ in range(5):assert not service.verify_email(models.Verify(**body),'fixture-client')['verified']
    assert c.execute('SELECT attempts FROM account_verifications').fetchone()[0]==5
    assert not service.verify_email(models.Verify(**{**body,'code':otp(c,receipt['challenge_id'])}),'fixture-client')['verified']
    assert c.execute('SELECT COUNT(*) FROM customer_accounts').fetchone()[0]==0

@pytest.mark.parametrize('email',['a@gmail.com','a@mailinator.com','a@sub.gmail.com','.a@example.com','a..b@example.com','a@-example.com','a@example..com'])
def test_personal_disposable_and_malformed_rejected(email):
    with pytest.raises((ValueError,ValidationError)):signup(email)

def test_duplicate_signup_cannot_replace_password_or_link_google(customer):
    c,_=customer;result,_=verified(c)
    account=dict(c.execute('SELECT * FROM customer_accounts').fetchone())
    c.execute("UPDATE account_verifications SET created_at='2026-01-01T00:00:00+00:00'");c.commit()
    receipt=service.begin_signup(signup(),'other-client')
    row=c.execute('SELECT purpose,payload_encrypted FROM transactional_notifications WHERE authority_id=?',(receipt['challenge_id'],)).fetchone()
    assert row['purpose']=='SIGNUP_NOTICE'
    assert c.execute('SELECT password_hash FROM customer_accounts').fetchone()[0]==account['password_hash']
    with pytest.raises(HTTPException) as denied:admission.admit(c,claim(email='person@example.com'),actor='person@example.com',broker_verified=True)
    assert denied.value.status_code==409
    assert not c.execute('SELECT google_subject FROM customer_accounts').fetchone()[0]

def test_reset_is_one_use_revokes_sessions_and_never_auto_logs_in(customer):
    c,_=customer;verified(c)
    login=service.login(models.Login(email='person@example.com',password=PASSWORD),'fixture-client')
    assert login['authenticated']
    request=service.recover(models.Recovery(email='person@example.com',request_id=uuid.uuid4()),'fixture-client')
    notification=service.prepare_recovery(request['recovery_request_id'])
    encoded=c.execute('SELECT payload_encrypted FROM transactional_notifications WHERE id=?',(notification,)).fetchone()[0]
    token=json.loads(mail.cipher().decrypt(encoded.encode()))['text'].split('?token=')[1].split('\n')[0]
    reset=models.Reset(token=token,password='Another isolated passphrase 309!')
    assert service.reset_password(reset,'fixture-client')['reset']
    assert not service.reset_password(reset,'fixture-client')['reset']
    with pytest.raises(HTTPException):sessions.validate(c,'person@example.com',login['session_token'])
    assert not service.login(models.Login(email='person@example.com',password=PASSWORD),'fixture-client')['authenticated']
    assert service.login(models.Login(email='person@example.com',password='Another isolated passphrase 309!'),'fixture-client')['authenticated']
    assert c.execute('SELECT email FROM account_recovery_requests').fetchone()[0] is None

def test_unknown_and_google_only_recovery_queue_uniform_no_fake_reset(customer):
    c,_=customer
    for email in ('unknown@example.com','google@example.com'):
        if email.startswith('google'):
            admission.admit(c,claim(email=email,subject='google-only-subject'),actor=email,broker_verified=True);c.commit()
        result=service.recover(models.Recovery(email=email,request_id=uuid.uuid4()),'fixture-client')
        assert result['accepted'] and service.prepare_recovery(result['recovery_request_id']) is None
    assert c.execute('SELECT COUNT(*) FROM account_recovery_tokens').fetchone()[0]==0

def test_explicit_link_requires_current_session_and_exact_google_identity(customer):
    c,_=customer;verified(c)
    login=service.login(models.Login(email='person@example.com',password=PASSWORD),'fixture-client')
    link=google.begin_link(c,'person@example.com',login['session_token']);c.commit()
    body=claim(email='person@example.com',link_token=SecretStr(link['link_token']))
    result=admission.admit(c,body,actor=body.email,broker_verified=True);c.commit()
    assert result['status']=='ACTIVE'
    with pytest.raises(HTTPException):admission.admit(c,claim(email='other@example.com',subject=body.google_subject),actor='other@example.com',broker_verified=True)
    assert c.execute('SELECT COUNT(*) FROM customer_accounts').fetchone()[0]==1

def test_google_password_link_needs_mailbox_and_original_session(customer):
    c,_=customer;body=claim(email='google@example.com');login=admission.admit(c,body,actor=body.email,broker_verified=True);c.commit()
    receipt=service.start_password(c,body.email,login['session_token'],models.SetPassword(password=PASSWORD,request_id=uuid.uuid4()));c.commit()
    code=otp(c,receipt['challenge_id'])
    result=service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=code),'fixture-client')
    assert result['verified']
    assert service.login(models.Login(email=body.email,password=PASSWORD),'fixture-client')['authenticated']
    with pytest.raises(HTTPException):sessions.validate(c,body.email,login['session_token'])

def test_signed_bootstrap_exact_paths_redacts_secrets_and_binds_session(customer):
    c,s=customer;path='/api/organization/accounts/login';client=TestClient(app)
    assert client.post(path,json={'email':'person@example.com','password':PASSWORD}).status_code==401
    secret='MUST-NOT-APPEAR-IN-RESPONSE'
    result=sign(client,s,'/api/organization/accounts/signup','person@example.com',{'password':secret,'email':'person@example.com'})
    assert result.status_code==422 and secret not in result.text
    result,_=verified(c)
    with db_session() as d:login=sessions.exchange(d,result['login_ticket'])
    response=sign(client,s,'/api/organization/accounts/session','person@example.com',{},session=login['session_token'])
    assert response.status_code==200 and 'session_token' not in response.text
    assert sign(client,s,'/api/organization/accounts/session','person@example.com',{},session='x'*43).status_code==401
    assert sign(client,s,'/api/organization/accounts/not-a-bootstrap','person@example.com',{}).status_code==401
    sign(client,s,'/api/organization/accounts/logout','person@example.com',{},session=login['session_token'])
    assert sign(client,s,'/api/organization/accounts/session','person@example.com',{},session=login['session_token']).status_code==401

def test_password_storage_is_real_scrypt_and_not_reversible():
    encoded=passwords.hash_password(PASSWORD)
    assert encoded.startswith('scrypt$1$131072$8$1$') and PASSWORD not in encoded
    assert passwords.verify(PASSWORD,encoded) and not passwords.verify('Different secure passphrase',encoded)


def test_google_signup_cannot_bypass_disabled_native_access_enforcement(customer,monkeypatch):
    c,s=customer;monkeypatch.setattr(s,'heysow_access_periods_enabled',False)
    body=claim(email='unpaid@example.com')
    with pytest.raises(HTTPException) as denied:admission.admit(c,body,actor=body.email,broker_verified=True)
    assert denied.value.status_code==503
    assert c.execute('SELECT COUNT(*) FROM customer_accounts').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==0


def test_privacy_intake_export_and_cross_account_boundary(customer):
    from app.accounts import privacy
    c,s=customer;verified(c)
    login=service.login(models.Login(email='person@example.com',password=PASSWORD),'fixture-client')
    token=login['session_token'];actor='person@example.com'
    exported=privacy.account_export(c,actor,token)
    assert exported['account']['email']==actor
    assert not any(value in json.dumps(exported) for value in ('password_hash','token_hash','google_subject',token))
    request=privacy.PrivacyRequest(kind='CLOSE_AND_DELETE',request_id=uuid.uuid4(),confirmed=True)
    first=privacy.create(c,actor,token,request)
    again=privacy.create(c,actor,token,privacy.PrivacyRequest(kind='CLOSE_AND_DELETE',request_id=uuid.uuid4(),confirmed=True))
    assert first['id']==again['id'] and first['data_deleted'] is False
    assert c.execute('SELECT status FROM customer_accounts').fetchone()[0]=='ACTIVE'
    assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==1
    assert privacy.requests(c,actor,token)['items'][0]['status']=='REQUESTED'
    for operation in (privacy.account_export,privacy.requests):
        with pytest.raises(HTTPException):operation(c,'other@example.com',token)
    c.execute("UPDATE customer_sessions SET created_at='2020-01-01T00:00:00+00:00'")
    with pytest.raises(HTTPException) as denied:privacy.create(c,actor,token,request)
    assert denied.value.status_code==401


def test_verified_closure_is_operator_only_tracks_deadlines_and_retains_history(customer):
    from app.accounts import privacy
    c,s=customer;verified(c);login=service.login(models.Login(email='person@example.com',password=PASSWORD),'fixture-client');actor='person@example.com'
    request=privacy.create(c,actor,login['session_token'],privacy.PrivacyRequest(kind='CLOSE_AND_DELETE',request_id=uuid.uuid4(),confirmed=True))
    with pytest.raises(HTTPException):privacy.verify_closure(c,request['id'],actor,'review-case-123')
    operator=s.allowed_emails[0]
    result=privacy.verify_closure(c,request['id'],operator,'review-case-123')
    assert not result['data_deleted'] and result['backup_target_at']-result['ordinary_data_due_at']==60*86400
    assert privacy.verify_closure(c,request['id'],operator,'review-case-123')==result
    with pytest.raises(HTTPException):sessions.validate(c,actor,login['session_token'])
    assert c.execute('SELECT COUNT(*) FROM customer_accounts').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]>=1

@pytest.mark.parametrize('email',['person@gmail.com','person@yahoo.com','person@hotmail.com','person@outlook.com','person@icloud.com','person@mailinator.com','person@sub.gmail.com'])
def test_personal_identity_never_bypasses_existing_google_allowlist_or_sessions(customer,email):
    c,s=customer;s.allowed_user_emails=email
    body=claim(email=email)
    before=c.total_changes
    for operation in (lambda:google.admit(c,body),lambda:sessions.create(c,email,'GOOGLE'),lambda:service.login(models.Login(email=email,password=PASSWORD),'personal-denial'),lambda:service.recover(models.Recovery(email=email,request_id=uuid.uuid4()),'personal-denial')):
        with pytest.raises(HTTPException) as error:operation()
        assert error.value.status_code==403
    assert c.total_changes==before
    assert not c.execute('SELECT 1 FROM customer_accounts WHERE email=?',(email,)).fetchone()


def test_controlled_signup_is_exact_allowlist_and_rechecked_at_verification(customer):
    c,s=customer;s.heysow_public_registration_enabled=False;s.heysow_invited_registration_enabled=False
    s.heysow_registration_acceptance_emails='person@example.com'
    receipt=service.begin_signup(signup(),'controlled-client')
    with pytest.raises(HTTPException):service.begin_signup(signup('other@example.com'),'other-controlled-client')
    raw=otp(c,receipt['challenge_id']);s.heysow_registration_acceptance_emails=''
    with pytest.raises(HTTPException):service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=raw),'controlled-client')
    assert not c.execute('SELECT 1 FROM customer_accounts').fetchone()
    s.heysow_registration_acceptance_emails='person@example.com'
    result=service.verify_email(models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=raw),'controlled-client')
    assert result['verified'] and result['trial']['limits']['searches']==5
