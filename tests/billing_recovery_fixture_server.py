"""Offline browser fixture: real workspace, routes and ledgers, no remote payment calls."""
import json,time,uuid
from pydantic import SecretStr
from tests.intent_only_fixture_server import app,settings,path
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as org
from app.database.connection import db_session
from app.database.prospects import now
from app.billing import commercial,creem,subscription_access as access
from app.billing.subscription_schema import EVENT_SQL,CONTRACT_SQL

assert settings.app_env=='test' and settings.database_path and 'data/e2e/' in str(path)
actor='founder@leadengine.example';customer='cust_browser';subid='sub_browser';started=int(time.time())-4*86400;ended=started+access.TRIAL_SECONDS
settings.subscription_onboarding_required=True;settings.subscription_terms_version=access.POLICY;settings.creem_environment='test';settings.creem_test_api_key=SecretStr('offline-only');settings.billing_enabled=False;settings.billing_test_workspaces=org
with db_session() as c:
    c.executescript(EVENT_SQL+CONTRACT_SQL);access.enroll(c,actor,org);ch=str(uuid.uuid4());contract=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO subscription_customers VALUES('creem','test',?,?,?)",(org,customer,stamp))
    c.execute("INSERT INTO subscription_checkouts(id,organization_id,created_by,provider,environment,plan_code,variant,request_id,request_hash,customer_id,product_id,provider_checkout_id,status,country,currency,amount_minor,trial_days,terms_version,accepted_at,disclosure_json,created_at,updated_at) VALUES(?,?,?,'creem','test','starter','trial',?,'fixture',?,'prod_trial','ch_trial','COMPLETED','US','USD',5900,3,?,?,'{}',?,?)",(ch,org,actor,str(uuid.uuid4()),customer,access.POLICY,stamp,stamp,stamp))
    c.execute("INSERT INTO subscription_contracts(id,organization_id,created_by,provider,environment,provider_id,customer_id,checkout_id,plan_code,plan_json,status,period_start,period_end,trial_start,trial_end,cancel_confirmed_at,verified_at,created_at,updated_at) VALUES(?,?,?,'creem','test',?,?,?,'starter',?,'canceled',?,?,?,?,?,?,?,?)",(contract,org,actor,subid,customer,ch,json.dumps(commercial.plan('starter')),started,ended,started,ended,stamp,stamp,stamp,stamp))
    c.execute('INSERT INTO subscription_workspace_slots VALUES(?,?,?)',(org,'test',contract));c.execute('INSERT INTO subscription_trials VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),actor,'leadengine.example',org,contract,access.POLICY,started,ended))
    for code in ('starter','growth','scale'):
        c.execute("INSERT INTO subscription_products VALUES('creem','test',?,'paid',?,?,'USD','every-month',0,?,'{}',?)",(code,'prod_'+code,commercial.plan(code)['monthly_minor'],commercial.catalog()['catalog_sha256'],stamp))

creem.get_subscription=lambda *args,**kw:{'id':subid,'mode':'test','status':'canceled','customer':customer}
creem.get_customer=lambda *args,**kw:{'id':customer,'mode':'test','external_id':org,'email':actor}
creem.get_product=lambda key,**kw:{'id':key,'mode':'test','price':commercial.plan(key[5:])['monthly_minor'],'currency':'USD','billing_type':'recurring','billing_period':'every-month','tax_mode':'inclusive'}
created={}
def offline(method,endpoint,**kw):
    if method=='GET' and endpoint=='/customers/'+customer+'/subscriptions':return {'items':[creem.get_subscription()],'pagination':{'next_page':None}}
    assert method=='POST' and endpoint=='/checkouts' and kw['body']['customer']=={'id':customer}
    key='ch_'+str(uuid.uuid4());p=kw['body'];created[key]={'id':key,'mode':'test','status':'pending','request_id':p['request_id'],'product':p['product_id'],'metadata':p['metadata']};return dict(created[key],checkout_url='https://checkout.creem.io/test/offline/'+key)
creem.request=offline;creem.get_checkout=lambda key,**kw:created[key]
