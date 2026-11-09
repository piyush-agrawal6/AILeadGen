import sqlite3
import uuid
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform import onboarding as setup
from app.platform.company_profiles import read_profile,save_profile,CompanyUpdate
from app.icp import service as icps
from app.icp.models import Create


@pytest.fixture
def db():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    org=create_organization(c,'setup@example.test','Setup company')['organization_id']
    other=create_organization(c,'foreign@example.test','Foreign company')['organization_id']
    yield c,org,other
    c.close()


def test_manual_setup_resumes_validates_real_records_and_completes_without_actions(db):
    c,org,_=db
    with workspace_scope(c,'setup@example.test',org):
        initial=setup.read(c);assert initial['revision']==0 and initial['status']=='IN_PROGRESS'
        draft=setup.save(c,setup.Setup(revision=0,objectives=['FIND_CUSTOMERS'],current_step='SERVICES'))
        with pytest.raises(HTTPException) as incomplete:setup.complete(c,setup.Completion(revision=draft['revision']))
        assert incomplete.value.status_code==422
        # An unchanged initial company name still creates a real saved profile.
        company=read_profile(c);assert company['version'] is None
        save_profile(c,CompanyUpdate.model_validate({key:value for key,value in company.items() if key in CompanyUpdate.model_fields}))
        assert read_profile(c)['version'] is not None
        profile=icps.create(c,Create(name='Our market',criteria={'company':{'industries':['Dentistry']}},status='ACTIVE',request_id=uuid.uuid4()))
        final=setup.Setup(revision=draft['revision'],objectives=['FIND_CUSTOMERS'],services=[{'name':'Software engineering'}],default_icp_id=profile['id'],preferences={'geography_mode':'SELECTED','countries':['India'],'geography_confirmed':True,'integrations_skipped':True},current_step='REVIEW')
        saved=setup.save(c,final)
        with pytest.raises(HTTPException) as conflict:setup.save(c,final)
        assert conflict.value.status_code==409
        result=setup.complete(c,setup.Completion(revision=saved['revision']))
        assert result=={'status':'COMPLETED','discovery_started':False,'outreach_started':False}
        assert setup.complete(c,setup.Completion(revision=saved['revision']))==result
        assert setup.read(c)['status']=='COMPLETED'
        assert c.execute("SELECT COUNT(*) FROM audit_log WHERE action='ONBOARDING_COMPLETED' AND organization_id=?",(org,)).fetchone()[0]==1
    for table in ('pipeline_runs','acquisition_jobs','email_messages'):
        assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_setup_rejects_foreign_icp_and_inactive_default(db):
    c,org,other=db
    with workspace_scope(c,'foreign@example.test',other):
        foreign=icps.create(c,Create(name='Foreign target',criteria={'company':{'countries':['India']}},request_id=uuid.uuid4()))
    with workspace_scope(c,'setup@example.test',org):
        before=c.total_changes
        with pytest.raises(HTTPException):setup.save(c,setup.Setup(revision=0,default_icp_id=foreign['id']))
        assert c.total_changes==before
        assert setup.read(c)['revision']==0
    with pytest.raises(HTTPException):setup.read(c)
    with pytest.raises(ValidationError):setup.Preferences(start_discovery=True)


def test_setup_read_only_member_cannot_save_and_old_services_are_preserved(db):
    from app.platform.memberships import change_role
    c,org,_=db
    with workspace_scope(c,'setup@example.test',org):
        setup.save(c,setup.Setup(revision=0,services=[{'name':'Old service'}]))
        setup.save(c,setup.Setup(revision=1,services=[{'name':'New service'}]))
        assert c.execute('SELECT COUNT(*) FROM organization_services WHERE organization_id=?',(org,)).fetchone()[0]==2
        assert setup.read(c)['services'][0]['name']=='New service'
        change_role(c,'setup@example.test','viewer@example.test','VIEWER')
    with workspace_scope(c,'viewer@example.test',org):
        assert setup.read(c)['can_edit'] is False
        with pytest.raises(HTTPException):setup.save(c,setup.Setup(revision=2))


def test_onboarding_read_rechecks_membership_and_rejects_invalid_saved_preferences(db):
    c,org,_=db
    with workspace_scope(c,'setup@example.test',org):
        setup.save(c,setup.Setup(revision=0))
        c.execute("UPDATE organization_setup SET preferences_json='{}' WHERE organization_id=?",(org,))
        assert setup.read(c)['preferences']['geography_mode']=='GLOBAL'
        c.execute("UPDATE organization_setup SET preferences_json='[]' WHERE organization_id=?",(org,))
        with pytest.raises(ValidationError):setup.read(c)
        c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=? AND user_id='setup@example.test'",(org,))
        with pytest.raises(HTTPException) as revoked:setup.read(c)
        assert revoked.value.status_code==403


def test_onboarding_api_gates_identity_and_does_not_trust_completed_flags(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'setup-api.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,setup@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',False)
    with TestClient(app) as client:
        assert client.get('/api/organization/onboarding').status_code==503
        monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
        with db_session() as c:create_organization(c,'setup@example.test','Setup company')
        headers={'x-le-user':'setup@example.test'}
        initial=client.get('/api/organization/onboarding',headers=headers);assert initial.status_code==200,initial.text
        assert initial.json()['status']=='IN_PROGRESS'
        assert client.put('/api/organization/onboarding',headers=headers,json={'revision':0,'status':'COMPLETED'}).status_code==422
        saved=client.put('/api/organization/onboarding',headers=headers,json={'revision':0,'objectives':['BUILD_LISTS']});assert saved.status_code==200,saved.text
        incomplete=client.post('/api/organization/onboarding/complete',headers=headers,json={'revision':1})
        assert incomplete.status_code==422 and incomplete.json()['detail']['code']=='SETUP_INCOMPLETE'
        product=client.get('/api/operations/dashboard',headers=headers)
        assert product.status_code==403 and product.json()['code']=='ONBOARDING_INCOMPLETE'


def test_incomplete_workspace_can_configure_only_permitted_settings_not_execute_product(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    from app.platform.memberships import change_role
    settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'setup-settings.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,setup@example.test,viewer@example.test,new@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
    with TestClient(app) as client:
        with db_session() as c:
            org=create_organization(c,'setup@example.test','Setup company')['organization_id']
            with workspace_scope(c,'setup@example.test',org):change_role(c,'setup@example.test','viewer@example.test','VIEWER')
        owner={'x-le-user':'setup@example.test'};viewer={'x-le-user':'viewer@example.test'};new={'x-le-user':'new@example.test'}
        for path in ('/api/settings','/api/automation/targets','/api/users','/api/markets','/api/verticals'):
            assert client.get(path,headers=owner).status_code==200,path
            assert client.get(path,headers=new).status_code==403,path
        # Verified read access does not grant configuration writes or product execution.
        assert client.put('/api/settings',headers=viewer,json={}).status_code==403
        assert client.post('/api/workflow/email-runs',headers=owner,json={}).status_code==403
        assert client.post('/api/scans',headers=owner,json={}).status_code==403
        assert client.get('/api/operations/dashboard',headers=owner).json()['code']=='ONBOARDING_INCOMPLETE'
        progress=client.get('/api/organization/onboarding/progress',headers=owner).json()
        assert progress['total_steps']==6 and progress['completed_steps']==0
        assert client.get('/api/organization/onboarding/progress',headers=viewer).json()['can_edit'] is False
