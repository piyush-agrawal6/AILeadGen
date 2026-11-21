"""Already-settled synthetic contract for quota tests, independent of network I/O."""
import json,time,uuid
from app.billing import commercial
from app.billing.subscription_schema import EVENT_SQL,CONTRACT_SQL
from app.database.prospects import now

def seed(c,org,owner,monkeypatch,code='starter'):
    from app.config.settings import get_settings
    settings=get_settings();monkeypatch.setattr(settings,'subscription_onboarding_required',True);monkeypatch.setattr(settings,'creem_environment','test');monkeypatch.setattr(settings,'billing_test_workspaces',org)
    exists=c.execute("SELECT to_regclass('subscription_contracts')").fetchone()[0] if getattr(c,'backend',None)=='postgres' else c.execute("SELECT name FROM sqlite_master WHERE name='subscription_contracts'").fetchone()
    if not exists:c.executescript(EVENT_SQL+CONTRACT_SQL)
    key=str(uuid.uuid4());start=int(time.time())-60;end=start+3600;stamp=now();plan=dict(commercial.plan(code),version=commercial.catalog()['version']);price=plan['monthly_minor']
    c.execute("INSERT INTO subscription_checkouts(id,organization_id,created_by,provider,environment,plan_code,variant,request_id,request_hash,customer_id,product_id,status,country,currency,amount_minor,trial_days,terms_version,accepted_at,disclosure_json,created_at,updated_at) VALUES(?,?,?,'creem','test',?,'paid',?,'fixture','cust_fixture','prod_fixture','COMPLETED','US','USD',?,0,'fixture',?,'{}',?,?)",(key,org,owner,code,key,price,stamp,stamp,stamp))
    c.execute("INSERT INTO subscription_contracts(id,organization_id,created_by,provider,environment,provider_id,customer_id,checkout_id,plan_code,plan_json,status,recurring_authorized,period_start,period_end,verified_at,created_at,updated_at) VALUES(?,?,?,'creem','test',?,'cust_fixture',?,?,?,'active',1,?,?,?,?,?)",(key,org,owner,'sub_'+key,key,code,json.dumps(plan),start,end,stamp,stamp,stamp))
    c.execute("INSERT INTO subscription_workspace_slots(organization_id,environment,contract_id) VALUES(?,'test',?)",(org,key))
    c.execute("INSERT INTO subscription_payments(provider,environment,payment_id,organization_id,contract_id,amount_minor,currency,status,period_start,period_end,evidence_json,recorded_at) VALUES('creem','test',?,?,?,?,'USD','paid',?,?,'{}',?)",(key,org,key,price,start,end,stamp));c.commit();return key,start,end
