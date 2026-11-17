"""Synthetic provider lifecycle against real account, quota and isolation logic."""
import json,time,uuid
from datetime import datetime,timezone
from unittest.mock import Mock
import pytest
from pydantic import SecretStr
from fastapi import HTTPException
from test_customer_accounts import customer,accounts,verified,signup
from app.billing import subscription_access as access,subscriptions as service,subscription_sync as sync,creem,commercial,commercial_usage
from app.billing.subscription_schema import EVENT_SQL,CONTRACT_SQL
from app.platform.context import workspace_scope,job_scope
from app.database.connection import db_session
from app.database.prospects import now

def iso(stamp):return datetime.fromtimestamp(stamp,timezone.utc).isoformat()

@pytest.fixture
def subscribed(customer,monkeypatch):
 c,s=customer;c.executescript(EVENT_SQL+CONTRACT_SQL);c.commit()
 for k,v in {'subscription_onboarding_required':True,'subscription_terms_version':access.POLICY,'creem_environment':'production','creem_api_key':SecretStr('synthetic'),'intent_radar_stage':'Beta','intent_radar_growth_enabled':True}.items():monkeypatch.setattr(s,k,v)
 result,_=verified(c);org=result['organization_id'];actor='person@example.com'
 stamp=int(time.time());provider_id='sub_fixture';customer_id='cust_fixture';product_id='prod_fixture';checkout_id='ch_fixture';key=str(uuid.uuid4());plan={**commercial.plan('starter'),'version':commercial.catalog()['version']}
 c.execute("INSERT INTO subscription_billing_profiles(organization_id,country,status,verification_source,verification_reference,verified_at,updated_at) VALUES(?,'US','VERIFIED','fixture-provider','fixture-evidence',?,?)",(org,now(),now()))
 c.execute("INSERT INTO subscription_customers(provider,environment,organization_id,customer_id,created_at) VALUES('creem','production',?,?,?)",(org,customer_id,now()))
 c.execute("INSERT INTO subscription_checkouts(id,organization_id,created_by,provider,environment,plan_code,variant,request_id,request_hash,customer_id,product_id,provider_checkout_id,status,country,currency,amount_minor,trial_days,terms_version,accepted_at,disclosure_json,created_at,updated_at) VALUES(?,?,?,'creem','production','starter','trial',?,?,?,?,?,'PENDING','US','USD',5900,3,?,?,?,?,?)",(key,org,actor,str(uuid.uuid4()),'fixture',customer_id,product_id,checkout_id,access.POLICY,now(),'{}',now(),now()))
 c.commit()
 state={'id':provider_id,'mode':'prod','status':'trialing','collection_method':'charge_automatically','product':product_id,'customer':customer_id,'current_period_start_date':iso(stamp),'current_period_end_date':iso(stamp+259200),'next_transaction_date':iso(stamp+259200),'updated_at':iso(stamp),'created_at':iso(stamp)}
 product={'id':product_id,'mode':'prod','price':5900,'currency':'USD','billing_type':'recurring','billing_period':'every-month','trial_period_days':3,'trial_price':0,'tax_mode':'inclusive'}
 checkout={'id':checkout_id,'mode':'prod','status':'completed','request_id':key,'subscription':provider_id,'customer':customer_id,'product':product_id}
 customer_data={'id':customer_id,'mode':'prod','email':actor,'external_id':org,'country':'US'}
 monkeypatch.setattr(creem,'get_subscription',lambda *a,**kw:dict(state))
 monkeypatch.setattr(creem,'get_product',lambda *a,**kw:dict(product))
 monkeypatch.setattr(creem,'get_checkout',lambda *a,**kw:dict(checkout))
 monkeypatch.setattr(creem,'get_customer',lambda *a,**kw:dict(customer_data))
 return c,s,org,actor,state,product,checkout,customer_data

def test_new_signup_has_no_trial_or_access_and_radar_cannot_bypass(subscribed):
 c,s,org,actor,*_=subscribed
 assert c.execute('SELECT COUNT(*) FROM access_periods').fetchone()[0]==0
 assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==0
 assert access.required(c,org)
 with workspace_scope(c,actor,org):
  with pytest.raises(HTTPException) as denied:access.require_product(c,org)
  assert denied.value.status_code==402
  from app.intent_radar.permissions import context
  with pytest.raises(HTTPException) as denied:context(c)
  assert denied.value.status_code==402
  assert service.summary(c)['required'] and not service.summary(c)['active']
  assert service.owner(c).organization_id==org  # billing is still accessible

def test_card_trial_provider_verified_once_and_exact_quota(subscribed):
 c,s,org,actor,state,*_=subscribed
 with workspace_scope(c,actor,org):
  result=sync.reconcile_subscription(state['id'],'production');again=sync.reconcile_subscription(state['id'],'production')
  assert result['id']==again['id']
  row=access.require_product(c,org)
  assert row['paid_end']-row['paid_start']==259200
  assert json.loads(row['plan_json'])['limits']==access.TRIAL_LIMITS
  assert c.execute('SELECT COUNT(*) FROM subscription_trials').fetchone()[0]==1
  assert commercial_usage.reserve(c,{'searches':5},'five');c.commit()
  with pytest.raises(HTTPException) as limit:commercial_usage.reserve(c,{'searches':1},'sixth')
  assert limit.value.status_code==429;c.rollback()

def test_mismatched_card_country_price_checkout_or_environment_never_grants(subscribed):
 c,s,org,actor,state,product,checkout,customer_data=subscribed
 with workspace_scope(c,actor,org):
  for target,key,bad in [(state,'collection_method','charge_manually'),(state,'mode','test'),(product,'price',590),(checkout,'status','pending'),(checkout,'request_id','foreign'),(customer_data,'external_id','foreign')]:
   before=target[key];target[key]=bad
   with pytest.raises(creem.Rejected):sync.reconcile_subscription(state['id'],'production')
   target[key]=before
   assert access.active(c,org) is None
 assert c.execute('SELECT COUNT(*) FROM subscription_contracts').fetchone()[0]==0

def test_expiry_failed_payment_cancel_and_out_of_order_cannot_extend_trial(subscribed):
 c,s,org,actor,state,*_=subscribed
 with workspace_scope(c,actor,org):
  sync.reconcile_subscription(state['id'],'production');end=access.active(c,org)['paid_end'];stamp=int(time.time())
  state.update(status='scheduled_cancel',updated_at=iso(stamp+1))
  sync.reconcile_subscription(state['id'],'production')
  assert access.active(c,org)['paid_end']==end and access.active(c,org)['cancel_confirmed_at']
  state.update(status='trialing',updated_at=iso(stamp-1))
  sync.reconcile_subscription(state['id'],'production')
  assert access.active(c,org)['cancel_confirmed_at']
  state.update(status='unpaid',updated_at=iso(stamp+2))
  sync.reconcile_subscription(state['id'],'production');assert access.active(c,org) is None
  c.execute('UPDATE subscription_contracts SET status=\'trialing\',period_end=? WHERE organization_id=?',(stamp-1,org));c.commit()
  assert access.active(c,org) is None

def test_paid_initial_and_renewal_require_independent_transaction_and_do_not_duplicate(subscribed,monkeypatch):
 c,s,org,actor,state,product,checkout,_=subscribed
 start=int(time.time());state.update(status='active',last_transaction_id='tran_fixture',current_period_start_date=iso(start),current_period_end_date=iso(start+2678400),next_transaction_date=iso(start+2678400))
 transaction={'id':'tran_fixture','mode':'prod','subscription':state['id'],'customer':'cust_fixture','currency':'USD','amount_paid':5900,'status':'paid','period_start':start,'period_end':start+2678400}
 monkeypatch.setattr(creem,'get_transaction',lambda *a,**kw:dict(transaction))
 with workspace_scope(c,actor,org):
  sync.reconcile_subscription(state['id'],'production');sync.reconcile_subscription(state['id'],'production')
  assert c.execute('SELECT COUNT(*) FROM subscription_payments').fetchone()[0]==1
  assert access.active(c,org)['paid_end']==start+2678400
  transaction['status']='refunded';state['updated_at']=iso(start+1)
  sync.reconcile_subscription(state['id'],'production');assert access.active(c,org) is None
  assert c.execute('SELECT COUNT(*) FROM subscription_payments').fetchone()[0]==1

def test_one_global_provider_including_india_has_no_country_admission_gate(subscribed):
 c,s,org,actor,state,product,checkout,customer_data=subscribed
 with workspace_scope(c,actor,org):
  c.execute('DELETE FROM subscription_billing_profiles WHERE organization_id=?',(org,));c.commit()
  assert service.route(c,org)==('creem',None)
  customer_data['country']='IN'
  sync.reconcile_subscription(state['id'],'production')
  assert access.require_product(c,org)
  assert service.profile(c,org)['country']=='IN'
  assert not any('PayU' in v or 'country must' in v for v in service.blockers(c,org,'paid'))

def test_setup_budget_is_job_bound_and_never_unlocks_dashboard(subscribed):
 c,s,org,actor,*_=subscribed
 key=str(uuid.uuid4());request_id=str(uuid.uuid4());stamp=now()
 c.execute("INSERT INTO organization_profile_jobs(id,organization_id,created_by,request_id,website,status,created_at,updated_at,source_kind,use_ai) VALUES(?,?,?,?,?,'QUEUED',?,?,'WEBSITE',1)",(key,org,actor,request_id,'https://example.com',stamp,stamp));c.commit()
 with workspace_scope(c,actor,org),access.setup_scope(c,key):
  assert commercial_usage.reserve(c,{'ai_calls':1},'company-profile:'+key);c.commit()
  with pytest.raises(HTTPException):commercial_usage.reserve(c,{'searches':1},'company-profile:'+key)
  with pytest.raises(HTTPException):commercial_usage.reserve(c,{'ai_calls':1},'some-other-operation')
  c.rollback()
 with workspace_scope(c,actor,org):
  with pytest.raises(HTTPException):access.require_product(c,org)
 assert c.execute('SELECT COUNT(*) FROM subscription_setup_reservations').fetchone()[0]==1
 assert c.execute('SELECT COUNT(*) FROM subscription_trials').fetchone()[0]==0

def test_no_subscription_fields_are_client_writable():
 from pydantic import ValidationError
 for key in ('country','organization_id','customer_id','provider','paid','mandate_verified'):
  with pytest.raises(ValidationError):service.Checkout(plan_code='starter',variant='trial',request_id=uuid.uuid4(),terms_version=access.POLICY,accepted_terms=True,accepted_recurring=True,**{key:'override'})

def test_checkout_is_durable_idempotent_and_return_never_activates(subscribed,monkeypatch):
 c,s,org,actor,state,product,checkout,_=subscribed
 monkeypatch.setattr(s,'subscription_checkout_enabled',True)
 c.execute("UPDATE subscription_checkouts SET status='CANCELLED'")
 c.execute("INSERT INTO subscription_provider_readiness(provider,environment,checkout_verified,recurring_verified,trial_verified,merchant_verified,verification_reference,verified_at) VALUES('creem','production',1,1,1,1,'synthetic-acceptance',?)",(now(),))
 c.execute("INSERT INTO subscription_products(provider,environment,plan_code,variant,product_id,price_minor,currency,interval,trial_days,catalog_hash,verified_json,verified_at) VALUES('creem','production','starter','trial','prod_fixture',5900,'USD','every-month',3,?,?,?)",(commercial.catalog()['catalog_sha256'],json.dumps(product),now()));c.commit()
 calls=[]
 def create(method,path,**kw):
  assert path=='/checkouts' and method=='POST'
  calls.append(kw['body'])
  assert kw['body']['customer']=={'id':'cust_fixture'}
  # Actual Creem create omits request_id; its independent GET echoes it.
  return {'id':'ch_new_fixture','mode':'prod','checkout_url':'https://checkout.creem.io/ch_new_fixture'}
 monkeypatch.setattr(creem,'request',create)
 monkeypatch.setattr(creem,'get_checkout',lambda *a,**kw:{'id':'ch_new_fixture','mode':'prod','request_id':calls[0]['request_id'],'product':'prod_fixture','metadata':calls[0]['metadata']})
 body=service.Checkout(plan_code='starter',variant='trial',request_id=uuid.uuid4(),terms_version=access.POLICY,accepted_terms=True,accepted_recurring=True)
 with workspace_scope(c,actor,org):
  value=service.start(body);again=service.start(body)
  assert value==again and len(calls)==1
  assert access.active(c,org) is None
  with pytest.raises(HTTPException):service.start(body.model_copy(update={'request_id':uuid.uuid4()}))

def test_real_signed_http_keeps_billing_accessible_but_denies_full_product(subscribed,monkeypatch):
 import hashlib,hmac
 from fastapi.testclient import TestClient
 from app.api.server import app
 from app.api.security import canonical_request
 from app.accounts import service as account_service,models,sessions
 c,s,org,actor,*_=subscribed
 # A completed company row and manual product enrollment must not bypass Step5.
 c.execute("UPDATE organization_onboarding SET status='COMPLETED' WHERE organization_id=?",(org,));c.commit()
 session=account_service.login(models.Login(email=actor,password='An isolated secure passphrase 926!'),'fixture-client')
 assert session['authenticated']
 monkeypatch.setattr(s,'app_env','development');monkeypatch.setattr(s,'auth_disabled_local',False)
 def signed(client,path):
  stamp=str(int(time.time()));nonce=str(uuid.uuid4());token=session['session_token']
  signature=hmac.new(s.api_signing_secret.encode(),canonical_request(stamp,nonce,'GET',path,b'',actor,token,'').encode(),hashlib.sha256).hexdigest()
  return client.get(path,headers={'x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':signature,'x-le-session':token})
 with TestClient(app) as client:
  assert signed(client,'/api/billing/subscription').status_code==200
  assert signed(client,'/api/organization/profile').status_code==200
  response=signed(client,'/api/intent-radar/overview/summary')
  assert response.status_code==402,response.text
  assert response.json()['code']=='PAYMENT_REQUIRED'

def test_country_writer_is_absent_from_subscription_contract():
 assert not hasattr(service,'request_country') and not hasattr(service,'BillingCountry')

def test_expired_checkout_allows_retry_without_granting_access(subscribed,monkeypatch):
 c,s,org,actor,_,_,checkout,_=subscribed
 checkout.update(status='expired',metadata={'planebyte_checkout':checkout['request_id'],'planebyte_workspace':org})
 with workspace_scope(c,actor,org):
  service.refresh_checkout(c,org)
  assert c.execute('SELECT status FROM subscription_checkouts WHERE organization_id=?',(org,)).fetchone()[0]=='EXPIRED'
  assert access.active(c,org) is None

def test_retired_payu_creation_is_denied_before_provider_work():
 from app.platform.modules import guard_route
 for path in ('/api/organization/billing/access/orders','/api/billing/payments/payu/callback'):
  with pytest.raises(HTTPException) as e:guard_route(path,organization_id='synthetic',role='OWNER',method='POST')
  assert e.value.status_code==410
