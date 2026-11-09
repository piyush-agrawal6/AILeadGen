import sqlite3
import uuid
import pytest
from fastapi import HTTPException
from app.database.migrations import run_migrations
from app.platform.workspaces import WorkspaceCreate,create_workspace,select_workspace
from app.api.organization import create_organization,resolve,membership_role


def test_creation_has_account_scoped_idempotency_and_explicit_owner(monkeypatch):
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(),'heysow_workspace_management_enabled',True)
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    body=WorkspaceCreate(name='Controlled new company',request_id=uuid.uuid4())
    result=create_workspace(c,'creator@example.test',body)
    org=result['organization_id']
    assert membership_role(c,'creator@example.test',org)=='OWNER'
    assert resolve(c,'creator@example.test')['organization_id']==org
    assert resolve(c,'creator@example.test')['onboarding_status']=='IN_PROGRESS'
    assert c.execute('SELECT COUNT(*) FROM prospects WHERE organization_id=?',(org,)).fetchone()[0]==0
    assert create_workspace(c,'creator@example.test',body)=={'organization_id':org,'reused':True}
    assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',('creator@example.test',)).fetchone()[0]==1
    with pytest.raises(HTTPException) as conflict:create_workspace(c,'creator@example.test',WorkspaceCreate(name='Changed company',request_id=body.request_id))
    assert conflict.value.status_code==409
    # The same request ID from a different account is not a capability for org.
    other=create_workspace(c,'other@example.test',body)['organization_id']
    assert other!=org and membership_role(c,'other@example.test',org) is None
    second=create_organization(c,'creator@example.test','Second explicit organization')['organization_id']
    assert second!=org
    assert resolve(c,'creator@example.test')['organization_id']==org
    select_workspace(c,'creator@example.test',second)
    assert create_workspace(c,'creator@example.test',body)['organization_id']==org
    assert resolve(c,'creator@example.test')['organization_id']==second
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    c.close()


def test_workspace_creation_api_uses_signed_account_and_blocks_product_access_until_onboarded(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    settings=get_settings()
    monkeypatch.setattr(settings,'database_path',str(tmp_path/'create-api.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,new-account@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',False)
    body={'name':'New customer','request_id':str(uuid.uuid4())}
    with TestClient(app) as client:
        assert client.post('/api/organization/workspaces',json=body).status_code==503
        monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
        headers={'x-le-user':'new-account@example.test'}
        assert client.post('/api/organization/workspaces',headers=headers,json={**body,'owner':'owner@example.test'}).status_code==422
        created=client.post('/api/organization/workspaces',headers=headers,json=body)
        assert created.status_code==201,created.text
        own=client.get('/api/organization/workspaces',headers=headers).json()
        assert len(own['items'])==1 and own['items'][0]['role']=='OWNER'
        assert own['active_organization_id']==created.json()['organization_id']
        denied=client.get('/api/operations/dashboard',headers=headers)
        assert denied.status_code==403 and denied.json()['code']=='ONBOARDING_INCOMPLETE'
        assert client.get('/api/organization/profile',headers=headers).status_code==200


def test_workspace_creation_uses_configured_safety_limit(monkeypatch):
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(),'heysow_workspace_creation_limit',1)
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    first=WorkspaceCreate(name='Only owned workspace',request_id=uuid.uuid4())
    created=create_workspace(c,'limited@example.test',first)
    # An idempotent retry remains available at the limit.
    assert create_workspace(c,'limited@example.test',first)['organization_id']==created['organization_id']
    with pytest.raises(HTTPException) as limit:create_workspace(c,'limited@example.test',WorkspaceCreate(name='Over limit',request_id=uuid.uuid4()))
    assert limit.value.status_code==409
    c.close()


def test_workspace_creation_name_matches_profile_contract():
    from pydantic import ValidationError
    for value in ('a',' a ','  ','bad\x00name'):
        with pytest.raises(ValidationError):WorkspaceCreate(name=value,request_id=uuid.uuid4())


@pytest.mark.parametrize('stored_id,stored_email',[
    ('requester@example.test','different@example.test'),
    ('historical-different-id','requester@example.test'),
])
def test_conflicting_identity_is_not_adopted_for_workspace_creation(stored_id,stored_email):
    from app.api.organization import OrganizationError
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    c.execute('INSERT INTO users(id,email,display_name) VALUES(?,?,?)',(stored_id,stored_email,'Existing identity'))
    before=c.execute('SELECT COUNT(*) FROM organization_memberships').fetchone()[0]
    with pytest.raises(OrganizationError):
        create_workspace(c,'requester@example.test',WorkspaceCreate(name='Must not be created',request_id=uuid.uuid4()))
    assert c.execute('SELECT COUNT(*) FROM organization_memberships').fetchone()[0]==before
    assert c.execute('SELECT email FROM users WHERE id=?',(stored_id,)).fetchone()[0]==stored_email
    c.close()
