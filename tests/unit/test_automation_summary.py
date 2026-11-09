"""Customer summaries never contain platform diagnostics, even through caches."""
import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.api.server import app
from app.api.schemas.automation import CustomerSummary
from app.api.organization import complete_onboarding
from app.automation.views import customer_summary
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import workspace_scope
from app.platform.memberships import change_role
from app.platform.workspaces import select_workspace
from test_customer_integrations import workspace, OWNER


def seed_summary(c, org, *, manual=1, queued=1):
    stamp=now()
    for index in range(manual+queued):
        key=str(uuid.uuid4())
        c.execute('INSERT INTO prospects(id,organization_id,first_seen_at,last_seen_at,updated_at) VALUES(?,?,?,?,?)',(key,org,stamp,stamp,stamp))
        c.execute('INSERT INTO master_lead_state(prospect_id,organization_id,qualified_at,contact_state,updated_at) VALUES(?,?,?,?,?)',(key,org,stamp,'MANUAL_CONTACT_REQUIRED' if index<manual else 'EMAIL_QUEUED',stamp))
        if index>=manual:
            c.execute('INSERT INTO automation_email_queue(prospect_id,recipient,queued_at,idempotency_key) VALUES(?,?,?,?)',(key,'published@fixture.example',stamp,str(uuid.uuid4())))


@pytest.fixture
def summary_workspace(workspace,monkeypatch):
    c,org,other,path=workspace
    complete_onboarding(c,org);complete_onboarding(c,other)
    seed_summary(c,org);seed_summary(c,other,manual=3,queued=2)
    c.execute("INSERT INTO automation_runs(day,status,started_at,target,error_code) VALUES('2026-11-08','FAILED','2026-11-08T00:00:00+00:00',987,'INTERNAL_ONLY_MARKER')")
    c.execute("UPDATE automation_controls SET pause_reason='INTERNAL_CONTROL_MARKER' WHERE id=1")
    with workspace_scope(c,OWNER,org):
        for role in ('ADMIN','MEMBER','VIEWER'):change_role(c,OWNER,role.lower()+'@summary.example',role)
    monkeypatch.setattr(get_settings(),'allowed_user_emails',','.join([OWNER,*[r.lower()+'@summary.example' for r in ('ADMIN','MEMBER','VIEWER')]]))
    c.commit()
    return c,org,other,path


@pytest.mark.parametrize('role',['OWNER','ADMIN','MEMBER','VIEWER'])
def test_customer_summary_roles_receive_only_owned_allowlisted_counts(summary_workspace,role):
    c,org,_,_=summary_workspace
    actor=OWNER if role=='OWNER' else role.lower()+'@summary.example'
    select_workspace(c,actor,org);c.commit()
    with TestClient(app) as client:
        response=client.get('/api/automation/summary',headers={'x-le-user':actor})
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='private, no-store'
    data=response.json()
    assert set(data)=={'today','environment','contact_counts','queue'}
    assert data['today']['manual']==1 and data['today']['queued']==1
    assert data['today']['qualified']==2
    assert data['queue']==[{'status':'QUEUED','count':1}]
    assert set(data['environment'])=={'daily_lead_target','daily_email_target','hourly_limit','daily_limit'}
    assert 'INTERNAL_' not in response.text and 'runs' not in data and 'controls' not in data


def test_summary_does_not_expose_diagnostics_through_alternate_customer_routes(summary_workspace):
    c,org,_,_=summary_workspace
    select_workspace(c,OWNER,org);c.commit()
    with TestClient(app) as client:
        for path in ('/api/automation/markets','/api/foundation/health','/api/system'):
            response=client.get(path,headers={'x-le-user':OWNER})
            assert response.status_code==403,path
            assert 'INTERNAL_' not in response.text


def test_summary_switching_workspace_is_live_and_never_reuses_cached_internal_data(summary_workspace,monkeypatch):
    from app.api.read_cache import READS,read_cache
    c,org,other,_=summary_workspace
    assert '/api/automation/summary' not in READS
    async def should_not_cache(*args):raise AssertionError('Sensitive summary must bypass Redis')
    monkeypatch.setattr(read_cache,'command',should_not_cache)
    with TestClient(app) as client:
        for target,count in ((org,1),(other,3),(org,1)):
            select_workspace(c,OWNER,target);c.commit()
            response=client.get('/api/automation/summary',headers={'x-le-user':OWNER})
            assert response.status_code==200 and response.json()['today']['manual']==count
        response=client.get('/api/automation/summary?organization_id='+other,headers={'x-le-user':OWNER})
        assert response.json()['today']['manual']==1


def test_summary_rejects_absent_foreign_and_revoked_context(summary_workspace):
    c,org,other,_=summary_workspace
    with pytest.raises(HTTPException):customer_summary(c)
    with workspace_scope(c,OWNER,org):
        with pytest.raises(HTTPException) as foreign:customer_summary(c,other)
        assert foreign.value.status_code==404
        c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=? AND user_id=?",(org,OWNER))
        with pytest.raises(HTTPException) as revoked:customer_summary(c)
        assert revoked.value.status_code==403
    with TestClient(app) as client:
        assert client.get('/api/automation/summary',headers={'x-le-user':'unknown@example.test'}).status_code==403


def test_summary_schema_and_http_response_strip_unexpected_nested_fields(summary_workspace,monkeypatch):
    c,org,_,_=summary_workspace
    with workspace_scope(c,OWNER,org):data=customer_summary(c)
    for record in (data,data['today'],data['environment'],*data['contact_counts'],*data['queue']):
        record['internal_diagnostics']={'token':'INTERNAL_FIELD_MARKER'}
    clean=CustomerSummary.model_validate(data).model_dump()
    assert 'INTERNAL_FIELD_MARKER' not in str(clean)
    monkeypatch.setattr('app.automation.views.customer_summary',lambda *args: data)
    select_workspace(c,OWNER,org);c.commit()
    with TestClient(app) as client:
        response=client.get('/api/automation/summary',headers={'x-le-user':OWNER})
        assert response.status_code==200 and 'INTERNAL_FIELD_MARKER' not in response.text
    data['today']['manual']={'internal':'secret'}
    with pytest.raises(ValidationError):CustomerSummary.model_validate(data)
