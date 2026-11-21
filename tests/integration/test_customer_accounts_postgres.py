"""Customer credentials/trial concurrent accounting in disposable PG schemas."""
import json,time,uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from test_postgres import postgres,pytestmark
from app.database.postgres import PostgresConnection
from app.database.migrations import run_migrations,verify_schema
from app.database.prospects import now
from app.config.settings import get_settings
from app.accounts import service,security,sessions,policy,models
from app.billing import commercial_usage as usage,access_periods
from app.notifications import transactional as mail
from app.platform.context import workspace_scope


def test_postgres_customer_verification_concurrency_revocation_and_quota(postgres,monkeypatch):
    c=postgres;s=get_settings();run_migrations(c)
    for key,value in {'app_env':'test','heysow_accounts_enabled':True,'heysow_access_periods_enabled':True,'heysow_workspace_management_enabled':True,'heysow_customer_access_enabled':True,'heysow_public_registration_enabled':True,'heysow_terms_version':'pg-fixture-terms','api_signing_secret':'pg-fixture-secret-at-least-thirty-two-characters','transactional_mail_enabled':True,'resend_api_key':SecretStr('fixture-only'),'resend_from_email':'PlaneByte <accounts@planebyte.com>'}.items():monkeypatch.setattr(s,key,value)
    @contextmanager
    def connection(*args):
        d=PostgresConnection(s.database_url,schema=c.schema)
        try:yield d;d.commit()
        except BaseException:d.rollback();raise
        finally:d.close()
    for module in (service,security,mail):monkeypatch.setattr(module,'db_session',connection)
    monkeypatch.setattr(policy,'mailbox_domain_available',lambda _:True)
    actor='owner@example.com';body=models.Signup(email=actor,password='A PostgreSQL fixture passphrase 836!',name='PG owner',company_name='PG company',terms_version='pg-fixture-terms',accepted_terms=True,request_id=uuid.uuid4())
    receipt=service.begin_signup(body,'pg-fixture')
    encoded=c.execute('SELECT payload_encrypted FROM transactional_notifications WHERE authority_id=?',(receipt['challenge_id'],)).fetchone()[0];c.commit()
    import re
    code=re.search(r'code is (\d{6})',json.loads(mail.cipher().decrypt(encoded.encode()))['text']).group(1)
    request=models.Verify(challenge_id=receipt['challenge_id'],capability=receipt['capability'],code=code)
    def verify():return service.verify_email(request,'pg-fixture')
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:verify(),range(2)))
    assert sum(r['verified'] for r in results)==1
    result=next(r for r in results if r['verified']);org=result['organization_id']
    assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==1;c.commit()
    def reserve(index):
        with connection() as d:
            with workspace_scope(d,actor,org):
                try:usage.reserve(d,{'searches':1},'concurrent-'+str(index));usage.settle(d,'concurrent-'+str(index));return True
                except HTTPException as error:
                    assert error.status_code==429;return False
    with ThreadPoolExecutor(8) as pool:accepted=list(pool.map(reserve,range(8)))
    assert sum(accepted)==5
    assert c.execute("SELECT used,reserved FROM access_period_usage WHERE dimension='searches'").fetchone()['used']==5;c.commit()
    with connection() as d:
        authenticated=sessions.exchange(d,result['login_ticket']);sessions.validate(d,actor,authenticated['session_token']);sessions.revoke(d,actor,authenticated['session_token'])
    with connection() as d:
        with pytest.raises(HTTPException):sessions.validate(d,actor,authenticated['session_token'])
    c.execute("UPDATE access_periods SET status='EXPIRED'");c.commit()
    with workspace_scope(c,actor,org):
        with pytest.raises(HTTPException) as denied:usage.reserve(c,{'ai_calls':1},'expired')
        assert denied.value.status_code==402
    assert c.execute('SELECT COUNT(*) FROM commercial_contracts').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_postgres_schema47_to49_preserves_history_without_manufacturing_accounts(postgres,monkeypatch):
    import app.database.migrations as migrations
    full=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',full[:47]);run_migrations(postgres)
    before={table:postgres.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('users','organizations','organization_memberships','businesses','prospects','email_messages','billing_payments','commercial_contracts')};postgres.commit()
    monkeypatch.setattr(migrations,'MIGRATIONS',full)
    assert run_migrations(postgres)==len(full)-47 and run_migrations(postgres)==0
    verify_schema(postgres)
    assert all(postgres.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==count for table,count in before.items())
    for table in ('customer_accounts','customer_workspace_access','launch_trial_claims','payu_access_orders','access_periods','transactional_notifications'):
        assert postgres.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_postgres_fixed_term_fulfillment_race_and_refund_preserves_history(postgres,monkeypatch):
    from app.billing import fixed_term,payu_v2,payu
    from app.api.organization import ensure_user
    import hashlib
    from datetime import datetime,timezone
    c=postgres;s=get_settings();run_migrations(c);actor='payment-owner@example.com';org=str(uuid.uuid4());stamp=now()
    ensure_user(c,actor)
    c.execute("INSERT INTO organizations(id,name,slug,status,created_by_user_id,created_at,updated_at) VALUES(?,?,?,'ACTIVE',?,?,?)",(org,'Payment race','payment-race-'+uuid.uuid4().hex,actor,stamp,stamp))
    c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,'OWNER','ACTIVE',?,?)",(str(uuid.uuid4()),org,actor,stamp,stamp))
    from app.billing.accounts import register
    register(c,org,actor);c.commit()
    for key,value in {'heysow_access_periods_enabled':True,'fixed_term_billing_enabled':True,'payu_one_time_checkout_enabled':True,'payu_mode':'test','payu_merchant_key':'pg-fixture-key','payu_merchant_salt':SecretStr('pg-fixture-salt'),'payu_charge_currency':'USD','payu_currency_approved':True,'billing_test_workspaces':org,'billing_terms_version':'pg-terms','api_signing_secret':'pg-fixture-signing-secret-at-least-thirty-two-characters','transactional_mail_enabled':True,'resend_api_key':SecretStr('fixture-only'),'resend_from_email':'PlaneByte <accounts@planebyte.com>'}.items():monkeypatch.setattr(s,key,value)
    s.payu_merchant_capabilities_json=json.dumps({'test':{'provider':'payu','hosted_v2_verified':True,'charge_currencies':['USD'],'verification_reference':'SYNTHETIC ONLY','merchant_key_sha256':hashlib.sha256(s.payu_merchant_key.encode()).hexdigest()}})
    @contextmanager
    def connection(*args):
        d=PostgresConnection(s.database_url,schema=c.schema)
        try:yield d;d.commit()
        except BaseException:d.rollback();raise
        finally:d.close()
    monkeypatch.setattr(fixed_term,'db_session',connection)
    monkeypatch.setattr(payu_v2,'request',lambda *_:{'result':{'checkoutUrl':'https://test.payu.in/_payment_options?fixture'}})
    with workspace_scope(c,actor,org):
        order=fixed_term.create(fixed_term.Purchase(plan_code='starter',billing={'first_name':'Test','last_name':'Owner','address1':'1 Fixture Street','city':'Test City','state':'Test State','country':'US','postal_code':'12345','phone':'+12025550100'},request_id=uuid.uuid4(),terms_version='pg-terms',accepted_terms=True))
    key=order['order']['id']
    verified={'provider':'payu','mode':'test','transaction_id':'fixture','provider_payment_id':'123456789','amount':'59.00','currency':'USD','payment_verified':True,'recurring_verified':False}
    def fulfill(_):
        with connection() as d:
            with workspace_scope(d,actor,org):return fixed_term._fulfill(d,key,verified)
    with ThreadPoolExecutor(4) as pool:results=list(pool.map(fulfill,range(4)))
    assert len({r['period_start'] for r in results})==1
    assert c.execute("SELECT COUNT(*) FROM access_periods WHERE organization_id=? AND source_kind='PAYMENT'",(org,)).fetchone()[0]==1
    assert c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE purpose='PAYMENT_CONFIRMED'").fetchone()[0]==1;c.commit()
    monkeypatch.setattr(payu,'refund_actions',lambda _:[{'provider_refund_id':'1111','provider_payment_id':verified['provider_payment_id'],'amount_minor':5900,'currency':'USD','status':'SUCCEEDED'}])
    with workspace_scope(c,actor,org):
        result=fixed_term.reconcile(key)
        assert result['full_refund_verified'] and not result['refund_initiated']
        assert access_periods.active(c,org) is None
    assert c.execute('SELECT COUNT(*) FROM payu_access_orders WHERE organization_id=?',(org,)).fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM payu_refund_observations WHERE organization_id=?',(org,)).fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==0
