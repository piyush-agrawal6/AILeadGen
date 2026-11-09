"""One-time invitations use real migrated memberships; no delivery providers."""
import hashlib
import sqlite3
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.database.migrations import run_migrations
from app.api.organization import create_organization,membership_role
from app.platform.context import workspace_scope
from app.platform import invitations as inv


@pytest.fixture
def db():
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    run_migrations(c)
    org=create_organization(c,'invite-owner@example.test','Inviting company')['organization_id']
    other=create_organization(c,'outsider@example.test','Other company')['organization_id']
    yield c,org,other
    c.close()


def issue(c,org,**kwargs):
    with workspace_scope(c,'invite-owner@example.test',org):
        return inv.create(c,inv.InviteCreate(email='recipient@example.test',**kwargs))


def test_hashed_single_use_capability_and_inviter_notification(db):
    c,org,other=db
    result=issue(c,org,role='VIEWER')
    stored=dict(c.execute('SELECT * FROM workspace_invitations').fetchone())
    assert result['token'] not in str(stored)
    assert stored['token_hash']==hashlib.sha256(result['token'].encode()).hexdigest()
    with pytest.raises(HTTPException) as missing:
        inv.respond(c,'outsider@example.test',inv.InviteRespond(token=result['token'],action='ACCEPT'))
    assert missing.value.status_code==404
    assert membership_role(c,'outsider@example.test',org) is None
    # A selected foreign workspace cannot turn this into a grant to that workspace.
    with workspace_scope(c,'outsider@example.test',other):
        accepted=inv.respond(c,'recipient@example.test',inv.InviteRespond(token=result['token'],action='ACCEPT'))
    assert accepted=={'status':'ACCEPTED','organization_id':org}
    assert membership_role(c,'recipient@example.test',org)=='VIEWER'
    assert membership_role(c,'recipient@example.test',other) is None
    assert c.execute('SELECT active_organization_id FROM user_profiles WHERE user_id=?',('recipient@example.test',)).fetchone() is None
    with pytest.raises(HTTPException) as reused:
        inv.respond(c,'recipient@example.test',inv.InviteRespond(token=result['token'],action='ACCEPT'))
    assert reused.value.status_code==409
    with workspace_scope(c,'invite-owner@example.test',org):
        listed=inv.list_invitations(c)
        assert listed['items'][0]['status']=='ACCEPTED'
        assert 'token' not in str(listed) and 'token_hash' not in str(listed)
        assert inv.notifications(c)['items'][0]['kind']=='INVITATION_ACCEPTED'
    with workspace_scope(c,'outsider@example.test',other):
        assert inv.notifications(c)=={'items':[]}


@pytest.mark.parametrize('end_state',['REJECT','REVOKE','EXPIRE','INVITER_REVOKED'])
def test_invalidated_invitations_never_grant_membership(db,end_state):
    c,org,other=db;result=issue(c,org)
    if end_state=='REJECT':
        assert inv.respond(c,'recipient@example.test',inv.InviteRespond(token=result['token'],action='REJECT'))['status']=='REJECTED'
    elif end_state=='REVOKE':
        with workspace_scope(c,'invite-owner@example.test',org):inv.revoke(c,result['id'])
    elif end_state=='EXPIRE':c.execute("UPDATE workspace_invitations SET expires_at='2000-01-01T00:00:00+00:00'")
    else:c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=? AND user_id=?",(org,'invite-owner@example.test'))
    with pytest.raises(HTTPException):inv.respond(c,'recipient@example.test',inv.InviteRespond(token=result['token'],action='ACCEPT'))
    assert membership_role(c,'recipient@example.test',org) is None


def test_role_boundaries_duplicate_and_foreign_revoke(db):
    c,org,other=db
    from app.platform.memberships import change_role
    with workspace_scope(c,'invite-owner@example.test',org):change_role(c,'invite-owner@example.test','admin@example.test','ADMIN')
    with workspace_scope(c,'admin@example.test',org):
        with pytest.raises(HTTPException):inv.create(c,inv.InviteCreate(email='recipient@example.test',role='ADMIN'))
        result=inv.create(c,inv.InviteCreate(email='recipient@example.test',role='MEMBER'))
        with pytest.raises(HTTPException):inv.create(c,inv.InviteCreate(email='recipient@example.test'))
    with workspace_scope(c,'outsider@example.test',other):
        with pytest.raises(HTTPException) as denied:inv.revoke(c,result['id'])
        assert denied.value.status_code==404
    with pytest.raises(ValidationError):inv.InviteCreate(email='recipient@example.test',role='OWNER')
    with pytest.raises(ValidationError):inv.InviteCreate(email='recipient@example.test',organization_id=other)
    with pytest.raises(ValidationError):inv.InviteRespond(token=result['token'],action='ACCEPT',organization_id=other)
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
