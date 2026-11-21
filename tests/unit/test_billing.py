from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from test_intent_radar import radar,owned
from app.billing import catalog
from app.config.settings import get_settings
from app.platform.context import workspace_scope

@pytest.fixture
def billing(radar,monkeypatch):
    monkeypatch.setattr(get_settings(),'razorpay_webhook_secret',SecretStr('fixture-receipt-only'));return radar

def test_handoff_rejects_other_products_and_arbitrary_destinations():
    assert catalog.handoff('intent-radar','growth')['destination']=='/billing?plan=growth'
    for product,plan in [('lead-engine','starter'),('intent-radar','https://evil.example'),('intent-radar','missing')]:
        with pytest.raises(HTTPException):catalog.handoff(product,plan)

def test_retired_endpoints_cannot_create_charge_and_signed_event_is_not_access(billing,monkeypatch):
    import hashlib,hmac,json,uuid
    from app.api.routes.billing import retired
    from app.billing import service,webhooks
    from app.database.prospects import now
    c,_,org,_=billing;monkeypatch.setattr(get_settings(),'billing_enabled',True);monkeypatch.setattr(get_settings(),'billing_test_workspaces',org)
    with pytest.raises(HTTPException) as gone:retired()
    assert gone.value.status_code==410
    stamp=now();key=str(uuid.uuid4())
    c.execute("INSERT INTO billing_subscriptions(id,organization_id,created_by,mode,request_id,plan_code,plan_json,provider_id,status,next_reconcile_at,created_at,updated_at) VALUES(?,?,?,'test',?,'starter','{}','sub_retired','active',?,?,?)",(key,org,'controlled@example.test',key,stamp,stamp,stamp))
    body=json.dumps({'event':'subscription.charged','payload':{'subscription':{'entity':{'id':'sub_retired'}}}}).encode()
    sign=lambda b:hmac.new(b'fixture-receipt-only',b,hashlib.sha256).hexdigest()
    for _ in range(2):assert webhooks.receive(c,body,sign(body),'evt_replay')['durable']
    changed=body+b' '
    with pytest.raises(HTTPException) as conflict:webhooks.receive(c,changed,sign(changed),'evt_replay')
    assert conflict.value.status_code==409
    assert c.execute('SELECT status FROM billing_webhook_events').fetchone()[0]=='IGNORED'
    assert not service.granted(c,org) and not c.execute('SELECT 1 FROM billing_payments').fetchone()

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
