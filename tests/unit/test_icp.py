import sqlite3
import uuid
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.database.migrations import run_migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform.memberships import change_role
from app.icp import service
from app.icp.models import Create,Update,Criteria


@pytest.fixture
def tenants():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    owner=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(INTERNAL,)).fetchone()[0]
    other=create_organization(c,'second@example.test','Second company')['organization_id']
    yield c,owner,other
    c.close()


def request(**values):
    return Create.model_validate({'name':'Dental practices','criteria':{'company':{'industries':['Dentistry'],'countries':['United Kingdom'],'employee_min':10,'employee_max':100},'contact':{'job_titles':['Owner','Practice manager']}},'request_id':str(uuid.uuid4()),**values})


def test_icp_versions_conflicts_and_state_changes_do_not_launch_work(tenants):
    c,owner,other=tenants
    with workspace_scope(c,owner,INTERNAL):
        body=request();first=service.create(c,body)
        assert first['revision']==1 and first['status']=='INACTIVE'
        assert service.create(c,body)['id']==first['id']
        assert service.listing(c)['total']==1
        fields={key:first[key] for key in ('name','description','status','criteria','revision')}
        second=service.update(c,first['id'],Update.model_validate({**fields,'status':'ACTIVE'}))
        assert second['revision']==2 and second['status']=='ACTIVE'
        with pytest.raises(HTTPException) as conflict:service.update(c,first['id'],Update.model_validate({**fields,'name':'Stale edit'}))
        assert conflict.value.status_code==409
        assert [row['revision'] for row in service.history(c,first['id'])['items']]==[2,1]
        assert service.compare(c,first['id'],1,2)['changes']=={'status':{'before':'INACTIVE','after':'ACTIVE'}}
        fields['revision']=2
        archived=service.update(c,first['id'],Update.model_validate({**fields,'status':'ARCHIVED'}))
        assert archived['revision']==3
    assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM acquisition_jobs').fetchone()[0]==0
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_icp_foreign_ids_and_read_only_members_cannot_mutate(tenants):
    c,owner,other=tenants
    with workspace_scope(c,owner,INTERNAL):
        first=service.create(c,request())
        change_role(c,owner,'viewer@example.test','VIEWER')
    with workspace_scope(c,'second@example.test',other):
        assert service.listing(c)['total']==0
        for operation in (lambda:service.get(c,first['id']),lambda:service.history(c,first['id']),lambda:service.compare(c,first['id'],1,1)):
            with pytest.raises(HTTPException) as denied:operation()
            assert denied.value.status_code==404
    with workspace_scope(c,'viewer@example.test',INTERNAL):
        assert service.get(c,first['id'])['name']=='Dental practices'
        assert service.listing(c)['can_edit'] is False
        before=c.total_changes
        with pytest.raises(HTTPException):service.create(c,request())
        assert c.total_changes==before
    with pytest.raises(HTTPException):service.listing(c)


def test_icp_criteria_integrity_and_ownership_fields_are_not_inferred():
    with pytest.raises(ValidationError):Criteria.model_validate({})
    with pytest.raises(ValidationError):request(criteria={'company':{'employee_min':100,'employee_max':10}})
    with pytest.raises(ValidationError):request(criteria={'company':{'revenue_min':float('nan')}})
    with pytest.raises(ValidationError):request(organization_id=str(uuid.uuid4()))
    with pytest.raises(ValidationError):request(criteria={'company':{'industries':['a'*181]}})
    result=request(criteria={'company':{'industries':[' Dental ','Dental'],'countries':['India']}})
    assert result.criteria.company.industries==['Dental']
    assert result.criteria.contact.job_titles==[]
    assert result.criteria.company.revenue_min is None


def test_icp_configured_limit_does_not_break_idempotent_retry(tenants,monkeypatch):
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(),'heysow_icp_limit',1)
    c,owner,_=tenants
    with workspace_scope(c,owner,INTERNAL):
        body=request();first=service.create(c,body)
        assert service.create(c,body)['id']==first['id']
        with pytest.raises(HTTPException) as limited:service.create(c,request())
        assert limited.value.status_code==409


def test_icp_api_gate_duplicates_history_and_foreign_ids(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'icp-api.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,foreign@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',False)
    with TestClient(app) as client:
        assert client.get('/api/organization/icps').status_code==503
        monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
        with db_session() as c:create_organization(c,'foreign@example.test','Foreign company')
        payload=request().model_dump(mode='json')
        assert client.post('/api/organization/icps',json={**payload,'organization_id':str(uuid.uuid4())}).status_code==422
        created=client.post('/api/organization/icps',json=payload);assert created.status_code==201,created.text
        row=created.json();key=row['id']
        duplicate=client.post('/api/organization/icps/'+key+'/duplicate',json={'name':'Second segment','request_id':str(uuid.uuid4())})
        assert duplicate.status_code==201,duplicate.text
        assert duplicate.json()['id']!=key and duplicate.json()['status']=='INACTIVE'
        history=client.get('/api/organization/icps/'+key+'/versions');assert history.status_code==200,history.text
        assert history.json()['total']==1 and history.json()['items'][0]['snapshot']['id']==key
        for suffix in ('','/versions','/compare?before=1&after=1'):
            assert client.get('/api/organization/icps/'+key+suffix,headers={'x-le-user':'foreign@example.test'}).status_code==404
        assert client.get('/api/organization/icps?page=0').status_code==422
