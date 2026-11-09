from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.api.server import app
from app.config.settings import get_settings
from app.acquisition.config import AcquisitionSettings
from app.acquisition import ai as gateway
from app.icp import ai
from app.database.connection import db_session


@pytest.fixture
def client(tmp_path,monkeypatch):
    settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'icp-ai.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
    monkeypatch.setattr(settings,'heysow_icp_ai_enabled',True)
    config=AcquisitionSettings(_env_file=None,VERTEX_AI_ENABLED=True,AI_PRIMARY_PROVIDER='vertex')
    monkeypatch.setattr(ai,'provider_settings',lambda:config)
    provider=AsyncMock();monkeypatch.setattr(gateway,'provider',lambda c:provider)
    with TestClient(app) as client:yield client,provider,settings


def test_ai_proposes_only_requested_criteria_caches_and_never_creates_profile(client):
    http,provider,settings=client
    provider.structured.return_value=ai.Draft(name='Dental clinics',criteria={'company':{'industries':['dental clinics'],'countries':['India'],'employee_min':10,'employee_max':100},'contact':{'job_titles':['owners']}})
    body={'prompt':'Find dental clinics in India with 10 to 100 employees. Target owners.'}
    result=http.post('/api/organization/icps/interpret',json=body);assert result.status_code==200,result.text
    assert result.json()['review_required'] and not result.json()['profile_created']
    assert result.json()['draft']['status']=='INACTIVE'
    again=http.post('/api/organization/icps/interpret',json=body);assert again.status_code==200 and again.json()['cached']
    assert provider.structured.call_count==1
    status=http.get('/api/organization/icps/ai-status').json();assert status['requests_used_today']==1
    assert http.get('/api/organization/icps').json()['total']==0
    with db_session() as c:
        assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_unsupported_criteria_are_rejected_and_failed_calls_still_use_budget(client,monkeypatch):
    http,provider,settings=client
    provider.structured.return_value=ai.Draft(name='Unsupported country',criteria={'company':{'countries':['Germany']}})
    failed=http.post('/api/organization/icps/interpret',json={'prompt':'Find dental clinics in India.'})
    assert failed.status_code==503
    assert http.get('/api/organization/icps').json()['total']==0
    assert http.get('/api/organization/icps/ai-status').json()['requests_used_today']==1
    monkeypatch.setattr(settings,'heysow_icp_ai_daily_limit',1)
    quota=http.post('/api/organization/icps/interpret',json={'prompt':'Find legal firms in India.'})
    assert quota.status_code==429 and provider.structured.call_count==1


def test_disabled_assistance_never_calls_provider_and_manual_builder_remains_available(client):
    http,provider,settings=client;settings.heysow_icp_ai_enabled=False
    assert http.post('/api/organization/icps/interpret',json={'prompt':'Find dental clinics in India.'}).status_code==503
    provider.structured.assert_not_called()
    assert http.get('/api/organization/icps').status_code==200
