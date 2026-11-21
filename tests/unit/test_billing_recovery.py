import time,uuid
from fastapi import HTTPException
import pytest
from test_subscription_payment import subscribed,customer,accounts,iso
from app.billing import subscriptions as billing,subscription_sync as sync,subscription_access as access,creem,commercial,plan_changes
from app.platform.context import workspace_scope
from app.database.prospects import now

def ready(c,s,monkeypatch):
    monkeypatch.setattr(s,'subscription_checkout_enabled',True)
    c.execute("INSERT INTO subscription_provider_readiness(provider,environment,checkout_verified,recurring_verified,trial_verified,merchant_verified,verification_reference,verified_at) VALUES('creem','production',1,1,1,1,'isolated-fixture',?)",(now(),))
    for code in ('starter','growth','scale'):
        c.execute("INSERT INTO subscription_products(provider,environment,plan_code,variant,product_id,price_minor,currency,interval,trial_days,catalog_hash,verified_json,verified_at) VALUES('creem','production',?,'paid',?,?,'USD','every-month',0,?,'{}',?)",(code,'prod_'+code,commercial.plan(code)['monthly_minor'],commercial.catalog()['catalog_sha256'],now()))
    c.commit()

def test_provider_period_precision_does_not_expand_coverage():
    sub={'current_period_start_date':'2026-11-21T06:28:43.139Z','current_period_end_date':'2026-12-21T06:28:43.139Z'}
    def matches(a,b):return sync.covers_period({'period_start':a,'period_end':b},sub)
    assert matches(1795242523139,1797834523139) and matches(1795242523,1797834523)
    assert not matches(1795242523140,1797834523139) and not matches(1795242523139,1797834523138)
    assert not matches(1795242523,1797834523139) and not matches('1795242523139',1797834523139)

@pytest.mark.parametrize('code',['starter','growth','scale'])
def test_ended_trial_to_verified_paid_keeps_trial_history(subscribed,monkeypatch,code):
    c,s,org,actor,state,p,checkout,_=subscribed;ready(c,s,monkeypatch);t=int(time.time());state.update(status='canceled',current_period_start_date=iso(t-259300),current_period_end_date=iso(t-100))
    with workspace_scope(c,actor,org):
        old=sync.reconcile_subscription(state['id'],'production');life=billing.summary(c);assert life['lifecycle']['phase']=='trial_ended' and not life['trial_eligible'] and life['lifecycle']['can_purchase']
        remote={};calls=[];original=dict(checkout);original_sub=dict(state)
        def request(method,path,**kw):
            if method=='GET':return {'items':[original_sub],'pagination':{'next_page':None}}
            assert path=='/checkouts';body=kw['body'];assert body['customer']=={'id':'cust_fixture'} and body['product_id']=='prod_'+code
            remote.update(body,id='ch_paid',mode='prod',product=body['product_id'],customer='cust_fixture');calls.append(path);return {'id':'ch_paid','checkout_url':'https://checkout.creem.io/test/fixture','mode':'prod'}
        monkeypatch.setattr(creem,'request',request);monkeypatch.setattr(creem,'get_product',lambda key,**kw: dict(p,id=key,trial_period_days=0,price=commercial.plan(code)['monthly_minor']) if key=='prod_'+code else dict(p));monkeypatch.setattr(creem,'get_checkout',lambda key,**kw:dict(remote) if key=='ch_paid' else original)
        body=billing.Checkout(plan_code=code,variant='paid',request_id=uuid.uuid4(),terms_version=access.POLICY,accepted_terms=True,accepted_recurring=True);one=billing.start(body);assert billing.start(body)==one and len(calls)==1 and not access.active(c,org)
        remote.update(status='completed',subscription='sub_paid');state.update(id='sub_paid',status='active',product='prod_'+code,current_period_start_date=iso(t),current_period_end_date=iso(t+2678400),last_transaction_id='tran_paid')
        monkeypatch.setattr(creem,'get_subscription',lambda key,**kw:dict(original_sub) if key=='sub_fixture' else dict(state));monkeypatch.setattr(creem,'get_transaction',lambda *a,**kw:{'id':'tran_paid','mode':'prod','customer':'cust_fixture','subscription':'sub_paid','currency':'USD','status':'paid','amount_paid':commercial.plan(code)['monthly_minor'],'period_start':t,'period_end':t+2678400});billing.refresh_checkout(c,org)
        assert access.active(c,org)['plan_code']==code;sync.reconcile_subscription('sub_fixture','production');assert access.active(c,org)['id']!=old['id'];assert c.execute('SELECT COUNT(*) FROM subscription_trials').fetchone()[0]==1
        from app.platform.workspaces import create_workspace,WorkspaceCreate
        monkeypatch.setattr(s,'shared_billing_accounts_enabled',True)
        sibling=create_workspace(c,actor,WorkspaceCreate(name='Second paid-account workspace',request_id=uuid.uuid4(),billing_account_id=org))['organization_id'];c.commit()
    with workspace_scope(c,actor,sibling):
        assert access.require_product(c,sibling)['plan_code']==code and billing.summary(c)['lifecycle']['can_purchase'] is False
        sync.reconcile_subscription('sub_paid','production');assert c.execute('SELECT count(*) FROM subscription_payments').fetchone()[0]==1 and len(calls)==1

def test_paid_change_is_idempotent_and_activates_on_verified_renewal(subscribed,monkeypatch):
    c,s,org,actor,state,p,checkout,_=subscribed;ready(c,s,monkeypatch);t=int(time.time())-5;end=t+2678400
    state.update(status='active',current_period_start_date=iso(t),current_period_end_date=iso(end),last_transaction_id='tran_first');txn={'id':'tran_first','mode':'prod','customer':'cust_fixture','subscription':state['id'],'currency':'USD','status':'paid','amount_paid':5900,'period_start':t,'period_end':end}
    monkeypatch.setattr(creem,'get_transaction',lambda *a,**kw:dict(txn));posts=[]
    def upgrade(method,path,**kw):
        assert path=='/subscriptions/sub_fixture/upgrade' and kw['body']=={'product_id':'prod_growth','update_behavior':'proration-none'};posts.append(path);state.update(product='prod_growth');return dict(state)
    monkeypatch.setattr(creem,'request',upgrade);monkeypatch.setattr(creem,'get_product',lambda key,**kw:dict(p,id=key,price=14900,trial_period_days=0) if key=='prod_growth' else dict(p))
    with workspace_scope(c,actor,org):
        old=sync.reconcile_subscription(state['id'],'production');body=plan_changes.Change(expected_contract=old['id'],expected_period_end=end,request_id=uuid.uuid4(),terms_version=access.POLICY,accepted_renewal=True,plan_code='growth');assert plan_changes.change(body)['status']=='CONFIRMED';assert plan_changes.change(body)['status']=='CONFIRMED' and len(posts)==1
        assert access.active(c,org)['plan_code']=='starter';state.update(current_period_start_date=iso(end),current_period_end_date=iso(end+2592000),last_transaction_id='tran_next');txn.update(id='tran_next',amount_paid=14900,period_start=end,period_end=end+2592000);assert sync.reconcile_subscription(state['id'],'production')['plan_code']=='growth';assert c.execute('SELECT COUNT(*) FROM subscription_contracts').fetchone()[0]==1
