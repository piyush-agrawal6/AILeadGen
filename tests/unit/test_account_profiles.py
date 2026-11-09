import sqlite3
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.database.migrations import run_migrations
from app.platform import account_profiles as profiles
from app.api.organization import create_organization
from app.platform.workspaces import select_workspace


def test_personal_profile_preserves_workspace_selection_and_never_updates_another_user():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    org=create_organization(c,'profile-owner@example.test','Profile company')['organization_id']
    select_workspace(c,'profile-owner@example.test',org)
    before=profiles.read(c,'profile-owner@example.test')
    fields={key:value for key,value in before.items() if key!='email'}
    body=profiles.AccountUpdate(**{**fields,'display_name':'Profile Owner','job_title':'Engineer','timezone':'Asia/Kolkata','locale':'en-IN','phone':'+91 1234'})
    after=profiles.save(c,'profile-owner@example.test',body)
    assert after['display_name']=='Profile Owner' and after['timezone']=='Asia/Kolkata'
    assert c.execute('SELECT active_organization_id FROM user_profiles WHERE user_id=?',('profile-owner@example.test',)).fetchone()[0]==org
    assert profiles.read(c,'different@example.test')['display_name']=='different'
    with pytest.raises(HTTPException) as conflict:profiles.save(c,'profile-owner@example.test',body)
    assert conflict.value.status_code==409
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    c.close()


@pytest.mark.parametrize('field,value',[('timezone','not/a/timezone'),('locale','<script>'),('display_name','\n'),('job_title','bad\x00title')])
def test_profile_rejects_invalid_preferences(field,value):
    with pytest.raises(ValidationError):profiles.AccountUpdate(**{**{'display_name':'User','version':'a'*64},field:value})


def test_account_profile_api_allows_viewer_personal_edit_without_org_mutation(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    from app.platform.context import workspace_scope
    from app.platform.memberships import change_role
    settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'profile-api.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,viewer@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',False)
    with TestClient(app) as client:
        assert client.get('/api/profile').status_code==503
        with db_session() as c:
            org=c.execute('SELECT organization_id FROM organization_memberships WHERE user_id=?',('owner@example.test',)).fetchone()[0]
            with workspace_scope(c,'owner@example.test',org):change_role(c,'owner@example.test','viewer@example.test','VIEWER')
        monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
        headers={'x-le-user':'viewer@example.test'}
        initial=client.get('/api/profile',headers=headers).json();body={key:value for key,value in initial.items() if key!='email'}
        body['display_name']='Viewer preferred name'
        assert client.put('/api/profile',json={**body,'user_id':'owner@example.test'},headers=headers).status_code==422
        saved=client.put('/api/profile',json=body,headers=headers);assert saved.status_code==200,saved.text
        assert saved.json()['email']=='viewer@example.test'
        assert client.get('/api/profile').json()['display_name']!='Viewer preferred name'
