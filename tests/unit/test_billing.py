"""Isolated financial/state/tenant tests. No provider/payment acceptance claims."""
import hashlib,hmac,json,time,uuid
from unittest.mock import Mock
from pydantic import SecretStr,ValidationError
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned
from app.config.settings import get_settings
from app.platform.context import workspace_scope
from app.api.organization import products,create_organization
from app.billing import catalog,provider,service,usage,webhooks

@pytest.fixture
def billing(radar,monkeypatch):
    c,path,org,other=radar;s=get_settings()
    for name,value in {'billing_provider':'razorpay','billing_enabled':True,'billing_test_workspaces':org,'billing_test_mode':True,'razorpay_key_id':'rzp_test_fixture','razorpay_key_secret':SecretStr('synthetic-api-secret'),'razorpay_webhook_secret':SecretStr('synthetic-webhook-secret'),'razorpay_test_plan_id_starter':'plan_fixture1','razorpay_test_plan_id_growth':'plan_fixture2','razorpay_test_plan_id_scale':'plan_fixture3'}.items():monkeypatch.setattr(s,name,value)
    return c,path,org,other

def mock_provider(monkeypatch):
    state={'id':'sub_fixture1','plan_id':'plan_fixture1','quantity':1,'status':'created','notes':{},'paid_count':0,'customer_id':None}
    start=int(time.time())-60;end=start+3600
    invoice={'id':'inv_fixture1','subscription_id':state['id'],'customer_id':'cust_fixture1','status':'paid','amount':10000,'amount_paid':10000,'amount_due':0,'currency':'INR','billing_start':start,'billing_end':end,'payment_id':'pay_fixture1','order_id':'order_fixture1'}
    payment={'id':'pay_fixture1','status':'captured','captured':True,'amount':10000,'currency':'INR','order_id':'order_fixture1','invoice_id':'inv_fixture1','amount_refunded':0}
    def call(method,path,payload=None,params=None):
        if path.startswith('plans/'):
            return {'id':path.split('/')[1],'period':'monthly','interval':1,'item':{'amount':10000,'currency':'INR','active':True}}
        if path=='subscriptions' and method=='POST':state['notes']=payload['notes'];return dict(state)
        if path.endswith('/cancel'):state['status']='active' if payload['cancel_at_cycle_end'] else 'cancelled';return dict(state)
        if path.startswith('subscriptions/'):return dict(state)
        if path=='invoices':return {'items':[invoice]}
        if path.startswith('payments/'):return dict(payment)
        raise AssertionError(path)
    api=Mock(side_effect=call);monkeypatch.setattr(provider,'request',api)
    return state,invoice,payment,api,start,end

def create(c):return service.create(c,service.Create(plan_code='starter',request_id=uuid.uuid4(),confirm_test_mode=True))
def activate(c,row,state,start,end):
    state.update(status='active',paid_count=1,customer_id='cust_fixture1',current_start=start,current_end=end)
    return service.reconcile(c,row['id'])

def test_default_off_live_mode_forbidden_and_catalog_not_commercial(billing,monkeypatch):
    c,_,org,_=billing
    with pytest.raises(ValidationError):catalog.Plan(code='starter',name='Live offer',mode='live')
    assert all(p.internal_test_only and p.product=='INTENT_RADAR' for p in catalog.plans().values())
    with workspace_scope(c,'controlled@example.test',org):
        monkeypatch.setattr(get_settings(),'billing_enabled',False)
        with pytest.raises(HTTPException):service.info(c)
    fresh=create_organization(c,'brandnew@example.test','New customer')['organization_id']
    assert not products(c,fresh)['LEADGEN']

def test_workspace_owner_and_allowlist_checks_precede_provider(billing,monkeypatch):
    c,_,org,other=billing;api=Mock();monkeypatch.setattr(provider,'request',api)
    with pytest.raises(HTTPException):service.info(c)
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):create(c)
    c.execute("UPDATE organization_memberships SET role='ADMIN' WHERE organization_id=?",(org,));c.commit()
    with workspace_scope(c,'controlled@example.test',org):
        assert not service.info(c)['can_manage']
        with pytest.raises(HTTPException):create(c)
    api.assert_not_called()

def test_creation_idempotency_unknown_outcome_and_slot_block(billing,monkeypatch):
    c,_,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        body=service.Create(plan_code='starter',request_id=uuid.uuid4(),confirm_test_mode=True)
        first=service.create(c,body);again=service.create(c,body)
        assert first['id']==again['id'] and len([x for x in api.call_args_list if x.args[0]=='POST'])==1
        with pytest.raises(HTTPException):create(c)
        c.execute("UPDATE billing_subscriptions SET status='cancelled' WHERE id=?",(first['id'],));c.commit()
        original=api.side_effect
        def failure(method,path,payload=None,params=None):
            if method=='POST':raise provider.ProviderUnavailable('Synthetic uncertain timeout')
            return original(method,path,payload,params)
        api.side_effect=failure
        with pytest.raises(HTTPException):create(c)
        assert c.execute("SELECT COUNT(*) FROM billing_subscriptions WHERE status='OUTCOME_UNKNOWN'").fetchone()[0]==1
        with pytest.raises(HTTPException):create(c)

def test_checkout_signature_alone_never_grants_and_foreign_ids_denied(billing,monkeypatch):
    c,_,org,other=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        row=create(c)
        sig=hmac.new(b'synthetic-api-secret',b'pay_fixture1|sub_fixture1',hashlib.sha256).hexdigest()
        result=service.verify(c,row['id'],service.Verification(payment_id='pay_fixture1',signature=sig))
        assert not result['settled_current_period'] and not service.active(c,org)
        assert service.checkout(c,row['id'])['subscription_id']=='sub_fixture1'
        with pytest.raises(HTTPException):service.verify(c,row['id'],service.Verification(payment_id='pay_fixture1',signature='0'*64))
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException) as err:service.owned(c,row['id'])
        assert err.value.status_code==404

def test_paid_invoice_payment_matching_entitlements_cancellation_preserves_manual(billing,monkeypatch):
    c,_,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        row=create(c);c.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=? AND product='INTENT_RADAR'",(org,));c.commit()
        result=activate(c,row,state,start,end)
        assert result['settled_current_period'] and products(c,org)['INTENT_RADAR']
        assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==1
        service.reconcile(c,row['id']);assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==1
        pay['amount_refunded']=10000
        with pytest.raises(provider.ProviderRejected):service.reconcile(c,row['id'])
        pay['amount_refunded']=0
        c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(org,));c.commit()
        cancelled=service.cancel(c,row['id'],service.Cancel(at_cycle_end=False,confirm=True))
        assert cancelled['status']=='cancelled' and not service.active(c,org) and products(c,org)['INTENT_RADAR']

def test_cycle_quotas_replays_renewals_and_capacity(billing,monkeypatch):
    c,_,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        row=create(c);activate(c,row,state,start,end)
        usage.reserve(c,{'searches':20},'request-a');usage.reserve(c,{'searches':20},'request-a')
        assert c.execute("SELECT used FROM billing_usage WHERE dimension='searches'").fetchone()[0]==20
        with pytest.raises(HTTPException) as err:usage.reserve(c,{'searches':1},'request-b')
        assert err.value.status_code==429
        with pytest.raises(HTTPException):usage.reserve(c,{'searches':19},'request-a')
        with pytest.raises(HTTPException):usage.capacity(c,'monitors',3)
        c.commit()
        # A verified new provider period creates a separate bucket; old history stays.
        start+=30;end+=30;inv.update(billing_start=start,billing_end=end,id='inv_fixture2',payment_id='pay_fixture2');pay.update(id='pay_fixture2',invoice_id='inv_fixture2')
        activate(c,row,state,start,end);usage.reserve(c,{'searches':1},'request-b');c.commit()
        assert c.execute("SELECT COUNT(*) FROM billing_usage WHERE dimension='searches'").fetchone()[0]==2
        state['status']='pending';service.reconcile(c,row['id']);assert not service.active(c,org)

def test_pending_mandate_catches_up_missed_paid_history_without_grant(billing,monkeypatch):
    c,_,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        row=create(c);activate(c,row,state,start,end)
        inv.update(id='inv_fixture2',payment_id='pay_fixture2',billing_start=end,billing_end=end+3600)
        pay.update(id='pay_fixture2',invoice_id='inv_fixture2')
        state.update(status='pending',paid_count=2,current_start=end+3600,current_end=end+7200)
        result=service.reconcile(c,row['id'])
        assert result['status']=='pending' and result['paid_start'] is None and not result['settled_current_period']
        assert not service.active(c,org)
        assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==2
        saved=c.execute("SELECT period_start,period_end FROM billing_payments WHERE provider_id='pay_fixture2'").fetchone()
        assert (saved['period_start'],saved['period_end'])==(end,end+3600)
        service.reconcile(c,row['id']);assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==2

def test_history_catchup_bounds_provider_reads_and_prioritizes_current_period(billing,monkeypatch):
    c,_,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        row=create(c);original=api.side_effect
        invoices=[dict(inv,id='inv_history'+str(i),payment_id='pay_history'+str(i),billing_start=start+i*3600,billing_end=end+i*3600) for i in range(6)]
        payments={i['payment_id']:dict(pay,id=i['payment_id'],invoice_id=i['id']) for i in invoices}
        def history(method,path,payload=None,params=None):
            assert not c.in_transaction,'Provider I/O must not retain an idle transaction.'
            if path=='invoices':return {'items':invoices}
            if path.startswith('payments/'):return payments[path.split('/')[1]]
            return original(method,path,payload,params)
        api.side_effect=history
        state.update(status='active',customer_id='cust_fixture1',paid_count=6,current_start=invoices[0]['billing_start'],current_end=invoices[0]['billing_end'])
        api.reset_mock();result=service.reconcile(c,row['id'])
        assert result['settled_current_period']
        assert [x.args[1] for x in api.call_args_list if x.args[1].startswith('payments/')][0]=='payments/pay_history0'
        assert len([x for x in api.call_args_list if x.args[1].startswith('payments/')])==3
        assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==3
        # Current settlement is always rechecked, leaving two bounded catch-up
        # slots; old callbacks cannot multiply stored payment rows.
        service.reconcile(c,row['id']);service.reconcile(c,row['id'])
        assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==6

def test_raw_webhook_signature_duplicates_body_mismatch_and_no_direct_grant(billing,monkeypatch):
    c,_,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):row=create(c)
    raw=json.dumps({'event':'subscription.activated','payload':{'subscription':{'entity':{'id':'sub_fixture1','status':'active'}}}}).encode()
    sig=hmac.new(b'synthetic-webhook-secret',raw,hashlib.sha256).hexdigest()
    for _ in range(2):assert webhooks.receive(c,raw,sig,'event_fixture')['durable']
    assert c.execute('SELECT COUNT(*) FROM billing_webhook_events').fetchone()[0]==1
    assert not service.active(c,org)
    with pytest.raises(HTTPException):webhooks.receive(c,raw+b' ',sig,'event_fixture')
    with pytest.raises(HTTPException):webhooks.receive(c,raw+b' ',hmac.new(b'synthetic-webhook-secret',raw+b' ',hashlib.sha256).hexdigest(),'event_fixture')
    c.commit();assert webhooks.tick(1)['processed']==1
    assert c.execute("SELECT status FROM billing_webhook_events").fetchone()[0]=='PROCESSED'
    assert not service.active(c,org)

def test_handoff_rejects_other_products_and_arbitrary_destinations():
    assert catalog.handoff('intent-radar','growth')['destination']=='/billing?plan=growth'
    for product,plan in [('lead-engine','starter'),('intent-radar','https://evil.example'),('intent-radar','missing')]:
        with pytest.raises(HTTPException):catalog.handoff(product,plan)

def test_http_webhook_verifies_before_database_and_prefixes_stay_protected(billing,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import create_app
    from app.api.security import InternalAuthenticationMiddleware
    c,path,org,_=billing
    monkeypatch.setattr(get_settings(),'api_signing_secret','synthetic-signing-secret-not-used-for-webhooks')
    # Bad signatures cannot reach the DB-backed workspace authentication broker.
    called=Mock(side_effect=AssertionError('Invalid webhook must not touch database'))
    monkeypatch.setattr(InternalAuthenticationMiddleware,'authenticated',called)
    app=create_app()
    with TestClient(app,raise_server_exceptions=False) as client:
        monkeypatch.setattr(get_settings(),'app_env','production')
        response=client.post('/api/billing/webhooks/razorpay',content=b'{}',headers={'x-razorpay-signature':'0'*64,'x-razorpay-event-id':'evt_invalid'})
        assert response.status_code==400
        assert client.post('/api/billing/webhooks/razorpay/other',json={}).status_code==401
    called.assert_not_called()

def test_old_webhooks_cannot_restore_cancelled_subscription_and_retry_is_bounded(billing,monkeypatch):
    c,path,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        row=create(c);activate(c,row,state,start,end)
        service.cancel(c,row['id'],service.Cancel(at_cycle_end=False,confirm=True))
    for i,kind in enumerate(['subscription.charged','subscription.activated']):
        raw=json.dumps({'event':kind,'payload':{'subscription':{'entity':{'id':'sub_fixture1','status':'active'}}}}).encode()
        webhooks.receive(c,raw,hmac.new(b'synthetic-webhook-secret',raw,hashlib.sha256).hexdigest(),'old_event_'+str(i))
    c.commit();assert webhooks.tick(2)['processed']==2
    assert c.execute('SELECT status FROM billing_subscriptions WHERE id=?',(row['id'],)).fetchone()[0]=='cancelled'
    assert not service.active(c,org)
    raw=json.dumps({'event':'subscription.charged','payload':{'subscription':{'entity':{'id':'sub_fixture1'}}}}).encode()
    webhooks.receive(c,raw,hmac.new(b'synthetic-webhook-secret',raw,hashlib.sha256).hexdigest(),'retry_event');c.commit()
    api.side_effect=provider.ProviderUnavailable('Synthetic provider outage')
    for _ in range(7):
        c.execute("UPDATE billing_webhook_events SET next_attempt_at='2000-01-01' WHERE event_id='retry_event'");c.commit();webhooks.tick(1)
    r=c.execute("SELECT status,attempts FROM billing_webhook_events WHERE event_id='retry_event'").fetchone()
    assert r['status']=='FAILED' and r['attempts']==5

def test_paid_subscription_scheduler_eligibility_and_worker_leadgen_denial(billing,monkeypatch):
    from app.intent_radar.schedules import eligible_sql
    from app.intelligence import jobs
    c,path,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):
        row=create(c);activate(c,row,state,start,end)
        c.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=?",(org,));c.commit()
        predicate,args=eligible_sql('m')
        assert c.execute('SELECT COUNT(*) FROM organization_memberships m WHERE '+predicate,args).fetchone()[0]==1
        assert products(c,org)['INTENT_RADAR'] and not products(c,org)['LEADGEN']
        with pytest.raises(HTTPException):jobs.create(c,jobs.Start(kind='COMPANY_ENRICH',resource_ids=['123']))

def test_terminal_subscriptions_stop_polling_but_signed_events_still_reconcile(billing,monkeypatch):
    c,path,org,_=billing;state,inv,pay,api,start,end=mock_provider(monkeypatch)
    with workspace_scope(c,'controlled@example.test',org):row=create(c)
    for status in service.TERMINAL:
        c.execute("UPDATE billing_subscriptions SET status=?,next_reconcile_at='2000-01-01' WHERE id=?",(status,row['id']));c.commit()
        api.reset_mock();webhooks.tick(1);api.assert_not_called()
    # Active mandates still recover missing webhooks, but without renewing any
    # terminal mandate. A genuine receipt can safely refresh a terminal record.
    c.execute("UPDATE billing_subscriptions SET status='created' WHERE id=?",(row['id'],));c.commit()
    webhooks.tick(1);assert api.called
    state['status']='cancelled'
    c.execute("UPDATE billing_subscriptions SET status='cancelled',next_reconcile_at='2000-01-01' WHERE id=?",(row['id'],));c.commit()
    raw=json.dumps({'event':'subscription.cancelled','payload':{'subscription':{'entity':{'id':state['id']}}}}).encode()
    webhooks.receive(c,raw,hmac.new(b'synthetic-webhook-secret',raw,hashlib.sha256).hexdigest(),'terminal_receipt');c.commit()
    api.reset_mock();assert webhooks.tick(1)['processed']==1
    assert api.call_count==2
    assert c.execute('SELECT status FROM billing_subscriptions WHERE id=?',(row['id'],)).fetchone()[0]=='cancelled'

def test_ignored_webhook_diagnostics_exclude_payload_and_untrusted_log_text(billing,caplog):
    c,_,org,_=billing
    caplog.set_level('INFO',logger='app.billing.webhooks')
    for kind in ('payment.captured','payment.captured\nforged-log'):
        raw=json.dumps({'event':kind,'private':'must-not-be-logged'}).encode()
        signature=hmac.new(b'synthetic-webhook-secret',raw,hashlib.sha256).hexdigest()
        assert webhooks.receive(c,raw,signature,'ignored_type')['ignored']
    assert 'payment.captured' in caplog.text and 'UNKNOWN' in caplog.text
    assert 'must-not-be-logged' not in caplog.text and 'forged-log' not in caplog.text
    assert not c.execute('SELECT 1 FROM billing_webhook_events').fetchone()

def test_new_workspaces_cannot_bypass_lead_engine_via_direct_workers(billing,monkeypatch):
    from app.database.models import PipelineRun
    from app.database.repositories import PipelineRunRepository
    from app.platform.context import job_scope
    c,path,org,_=billing
    with workspace_scope(c,'controlled@example.test',org):
        run=PipelineRun(market='Controlled',vertical='hospitality',target=1,run_configuration={'created_by':'controlled@example.test'})
        PipelineRunRepository(c).create(run,organization=org)
    c.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=? AND product='LEADGEN'",(org,));c.commit()
    with pytest.raises(HTTPException) as blocked:
        with job_scope(c,'scan',run.id):raise AssertionError('A disabled product must not enter the worker.')
    assert blocked.value.status_code==404

def test_additive_billing_bridge_requires_46_before_enabling(billing,monkeypatch,tmp_path):
    from app.database.connection import get_connection
    from app.database import migrations
    c=get_connection(tmp_path/'bridge.db');full=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',full[:45]);migrations.run_migrations(c)
    monkeypatch.setattr(migrations,'MIGRATIONS',full)
    monkeypatch.setattr(get_settings(),'billing_enabled',False);migrations.verify_schema(c)
    monkeypatch.setattr(get_settings(),'billing_enabled',True)
    with pytest.raises(RuntimeError):migrations.verify_schema(c)
    assert migrations.run_migrations(c)==len(full)-45
    migrations.verify_schema(c);assert migrations.run_migrations(c)==0;c.close()

def test_verified_test_plan_mapping_install_is_scoped_and_idempotent(billing):
    from scripts.prepare_razorpay_test_plans import install
    c,path,org,_=billing
    state={code:{'status':'VERIFIED','test_only':True,'provider_plan_id':'plan_'+code,'catalog_hash':'verified-'+code} for code in ('starter','growth','scale')}
    install(c,state,organization=org,owner='controlled@example.test');install(c,state,organization=org,owner='controlled@example.test')
    assert c.execute('SELECT COUNT(*) FROM billing_plan_mappings').fetchone()[0]==3
    with pytest.raises(RuntimeError):install(c,state,organization=org,owner='foreign@example.test')
    state['growth']['provider_plan_id']='plan_other'
    with pytest.raises(RuntimeError):install(c,state,organization=org,owner='controlled@example.test')
    c.rollback();assert c.execute("SELECT provider_plan_id FROM billing_plan_mappings WHERE code='growth'").fetchone()[0]=='plan_growth'
