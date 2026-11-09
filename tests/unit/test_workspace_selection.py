"""Explicit workspace selection never creates membership or bypasses revocation."""
import sqlite3
import pytest
from fastapi import HTTPException
from app.database.migrations import run_migrations
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID as INTERNAL
from app.api.organization import create_organization,resolve,membership_role
from app.platform.context import workspace_scope
from app.platform.memberships import change_role
from app.platform.workspaces import select_workspace


def test_selection_requires_active_membership_and_does_not_fall_back(monkeypatch):
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(),'heysow_workspace_management_enabled',True)
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;run_migrations(c)
    owner=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(INTERNAL,)).fetchone()[0]
    other=create_organization(c,'second@example.test','Second workspace')['organization_id']
    with workspace_scope(c,'second@example.test',other):change_role(c,'second@example.test',owner,'MEMBER')
    assert resolve(c,owner) is None
    select_workspace(c,owner,other)
    assert resolve(c,owner)['organization_id']==other
    assert membership_role(c,owner,other)=='MEMBER'
    before=c.total_changes
    with pytest.raises(HTTPException):select_workspace(c,'second@example.test',INTERNAL)
    assert c.total_changes==before
    c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id=? AND organization_id=?",(owner,other))
    assert resolve(c,owner) is None
    select_workspace(c,owner,INTERNAL)
    assert resolve(c,owner)['organization_id']==INTERNAL
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    c.close()


def test_workspace_api_is_gated_and_only_switches_authenticated_user(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    settings=get_settings();monkeypatch.setattr(settings,'database_path',str(tmp_path/'workspace-api.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,second@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',False)
    with TestClient(app) as client:
        assert client.get('/api/organization/workspaces').status_code==503
        with db_session() as c:
            other=create_organization(c,'second@example.test','Second workspace')['organization_id']
            with workspace_scope(c,'second@example.test',other):change_role(c,'second@example.test','owner@example.test','VIEWER')
        monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
        page=client.get('/api/organization/workspaces');assert page.status_code==200,page.text
        assert page.json()['active_organization_id'] is None and len(page.json()['items'])==2
        assert client.put('/api/organization/active',json={'organization_id':other,'actor':'second@example.test'}).status_code==422
        assert client.put('/api/organization/active',json={'organization_id':other}).status_code==200
        assert client.get('/api/organization/workspaces').json()['active_organization_id']==other
        assert client.put('/api/organization/active',json={'organization_id':INTERNAL}).status_code==200
        assert client.put('/api/organization/active',json={'organization_id':other}).status_code==200
        assert client.put('/api/organization/active',json={'organization_id':INTERNAL},headers={'x-le-user':'second@example.test'}).status_code==404
        with db_session() as c:
            assert c.execute('SELECT COUNT(*) FROM user_profiles WHERE user_id=? AND active_organization_id=?',('owner@example.test',other)).fetchone()[0]==1
