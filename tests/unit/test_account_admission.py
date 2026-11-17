"""Synthetic verified-broker claims; no real OAuth, accounts or provider traffic."""
import hashlib,hmac,json,time,uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.platform import admission
from app.platform.context import workspace_scope
from app.api.organization import create_organization
from app.api.security import canonical_request
from app.api.server import app


@pytest.fixture
def accounts(tmp_path,monkeypatch):
    s=get_settings();path=tmp_path/'admission.db'
    for name,value in {'database_path':str(path),'app_env':'development','auth_disabled_local':False,'allowed_user_emails':'internal@example.com','api_signing_secret':'synthetic-admission-signing-secret-32-characters','heysow_workspace_management_enabled':True,'heysow_customer_access_enabled':True,'heysow_public_registration_enabled':True,'heysow_google_admission_client_id':'synthetic-google-client','heysow_terms_version':'synthetic-review-version'}.items():monkeypatch.setattr(s,name,value)
    c=get_connection(path);run_migrations(c)
    yield c,s
    c.close()


def claim(email='new@example.com',subject='verified-google-subject',**updates):
    return admission.GoogleAdmission(email=email,google_subject=subject,client_id='synthetic-google-client',email_verified=True,terms_version='synthetic-review-version',accepted_at=int(time.time()),acceptance_nonce=str(uuid.uuid4()),**updates)


def signed(client,s,method,path,actor,body=None):
    raw=json.dumps(body,separators=(',',':')).encode() if body is not None else b''
    stamp=str(int(time.time()));nonce=str(uuid.uuid4())
    digest=hmac.new(s.api_signing_secret.encode(),canonical_request(stamp,nonce,method,path,raw,actor).encode(),hashlib.sha256).hexdigest()
    return client.request(method,path,content=raw,headers={'content-type':'application/json','x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':digest})


def test_registration_is_gated_and_never_creates_implicit_membership(accounts):
    c,s=accounts;body=claim();before=c.total_changes
    with pytest.raises(HTTPException):admission.admit(c,body,actor=body.email,broker_verified=False)
    assert c.total_changes==before
    s.heysow_public_registration_enabled=False
    with pytest.raises(HTTPException):admission.admit(c,body,actor=body.email,broker_verified=True)
    assert not c.execute('SELECT * FROM account_admissions').fetchall()
    s.heysow_public_registration_enabled=True
    result=admission.admit(c,body,actor=body.email,broker_verified=True);c.commit()
    assert result['status']=='ACTIVE' and result['workspace_required']
    assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',(body.email,)).fetchone()[0]==0
    assert 'google_subject' not in result


def test_identity_consent_binding_and_replay_do_not_adopt_another_account(accounts):
    c,_=accounts;first=claim();admission.admit(c,first,actor=first.email,broker_verified=True);c.commit()
    assert admission.admit(c,first,actor=first.email,broker_verified=True)['existing']
    assert c.execute('SELECT COUNT(*) FROM account_terms_acceptances').fetchone()[0]==1
    for bad in (first.model_copy(update={'google_subject':'different-google-account'}),claim(email='other@example.com',subject=first.google_subject),claim(email='third@example.com',subject='new-subject').model_copy(update={'acceptance_nonce':first.acceptance_nonce}),first.model_copy(update={'email_verified':False}),first.model_copy(update={'client_id':'wrong-client'}),first.model_copy(update={'accepted_at':int(time.time())-700})):
        with pytest.raises(HTTPException):admission.admit(c,bad,actor=bad.email,broker_verified=True)
    assert c.execute('SELECT COUNT(*) FROM account_admissions').fetchone()[0]==1


def test_signed_broker_account_can_create_only_its_own_workspace(accounts):
    c,s=accounts;body=claim()
    with TestClient(app) as client:
        assert client.post(admission.PATH,json=body.model_dump()).status_code==401
        result=signed(client,s,'POST',admission.PATH,body.email,body.model_dump());assert result.status_code==200,result.text
        assert signed(client,s,'GET','/api/operations/dashboard',body.email).json()['code']=='ORGANIZATION_REQUIRED'
        created=signed(client,s,'POST','/api/organization/workspaces',body.email,{'name':'Independent Google customer','request_id':str(uuid.uuid4())})
        assert created.status_code==201,created.text
        org=created.json()['organization_id']
        assert c.execute('SELECT role FROM organization_memberships WHERE user_id=? AND organization_id=?',(body.email,org)).fetchone()[0]=='OWNER'
        assert c.execute("SELECT COUNT(*) FROM organization_memberships WHERE user_id=? AND organization_id<>?",(body.email,org)).fetchone()[0]==0
        assert signed(client,s,'GET','/api/operations/dashboard',body.email).json()['code']=='ONBOARDING_INCOMPLETE'
        c.execute("UPDATE account_admissions SET status='SUSPENDED' WHERE user_id=?",(body.email,));c.commit()
        assert signed(client,s,'GET','/api/organization/workspaces',body.email).status_code==401
        with pytest.raises(HTTPException):
            with workspace_scope(c,body.email,org):pass


def test_existing_admitted_identity_can_login_when_new_registration_is_closed(accounts):
    c,s=accounts;body=claim();admission.admit(c,body,actor=body.email,broker_verified=True);c.commit()
    s.heysow_public_registration_enabled=False
    login=body.model_copy(update={'acceptance_nonce':None,'accepted_at':None,'terms_version':''})
    assert admission.admit(c,login,actor=body.email,broker_verified=True)['existing']
    s.heysow_customer_access_enabled=False
    assert not admission.access(c,body.email)
    with pytest.raises(HTTPException):admission.admit(c,login,actor=body.email,broker_verified=True)


def test_admission_migration_is_additive_and_preserves_existing_workspace(accounts,monkeypatch):
    import sqlite3
    import app.database.migrations as migrations
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;full=migrations.MIGRATIONS
    monkeypatch.setattr(migrations,'MIGRATIONS',full[:-1]);run_migrations(c)
    org=create_organization(c,'historical@example.com','Historical organization')['organization_id'];c.commit()
    before=dict(c.execute('SELECT * FROM organizations WHERE id=?',(org,)).fetchone())
    monkeypatch.setattr(migrations,'MIGRATIONS',full)
    assert run_migrations(c)==1 and run_migrations(c)==0
    assert dict(c.execute('SELECT * FROM organizations WHERE id=?',(org,)).fetchone())==before
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    c.close()


def private_invite(c,email='invited@example.com',role='VIEWER'):
    from app.platform.invitations import create,InviteCreate
    owner='internal@example.com'
    org=create_organization(c,owner,'Private invitation workspace')['organization_id']
    with workspace_scope(c,owner,org):
        invite=create(c,InviteCreate(email=email,role=role))
    c.commit()
    return org,invite


def test_invited_broker_admission_keeps_public_closed_and_requires_explicit_membership(accounts):
    c,s=accounts;org,invite=private_invite(c)
    s.heysow_public_registration_enabled=False;s.heysow_invited_registration_enabled=True
    body=claim(email=invite['email'],invitation_token=invite['token'])
    with TestClient(app) as client:
        result=signed(client,s,'POST',admission.PATH,body.email,body.model_dump())
        assert result.status_code==200,result.text
        assert result.headers['cache-control']=='private, no-store'
        assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',(body.email,)).fetchone()[0]==0
        assert c.execute('SELECT status FROM workspace_invitations WHERE id=?',(invite['id'],)).fetchone()[0]=='PENDING'
        assert signed(client,s,'GET','/api/operations/dashboard',body.email).json()['code']=='ORGANIZATION_REQUIRED'
        outsider=claim(email='uninvited@example.com',subject='outsider')
        assert signed(client,s,'POST',admission.PATH,outsider.email,outsider.model_dump()).status_code==403
        accepted=signed(client,s,'POST','/api/organization/invitations/respond',body.email,{'token':invite['token'],'action':'ACCEPT'})
        assert accepted.status_code==200,accepted.text
        assert c.execute('SELECT role FROM organization_memberships WHERE user_id=? AND organization_id=?',(body.email,org)).fetchone()[0]=='VIEWER'
        assert signed(client,s,'POST','/api/organization/invitations/respond',body.email,{'token':invite['token'],'action':'ACCEPT'}).status_code==409
        c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE user_id=? AND organization_id=?",(body.email,org));c.commit()
        assert signed(client,s,'GET','/api/operations/dashboard',body.email).json()['code']=='ORGANIZATION_REQUIRED'
    assert not s.heysow_public_registration_enabled
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
    assert invite['token'] not in str(c.execute('SELECT * FROM account_admissions').fetchall())


@pytest.mark.parametrize('failure',['disabled','wrong_recipient','expired','revoked','inviter_removed','inviter_demoted','workspace_archived'])
def test_invited_admission_rejects_stale_or_foreign_authority_without_creating_account(accounts,failure):
    c,s=accounts;org,invite=private_invite(c)
    s.heysow_public_registration_enabled=False;s.heysow_invited_registration_enabled=failure!='disabled'
    body=claim(email='foreign@example.com' if failure=='wrong_recipient' else invite['email'],invitation_token=invite['token'])
    if failure=='expired':c.execute("UPDATE workspace_invitations SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",(invite['id'],))
    if failure=='revoked':c.execute("UPDATE workspace_invitations SET status='REVOKED' WHERE id=?",(invite['id'],))
    if failure=='inviter_removed':c.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=?",(org,))
    if failure=='inviter_demoted':c.execute("UPDATE organization_memberships SET role='MEMBER' WHERE organization_id=?",(org,))
    if failure=='workspace_archived':c.execute("UPDATE organizations SET status='ARCHIVED' WHERE id=?",(org,))
    c.commit();before=c.total_changes
    with pytest.raises(HTTPException):admission.admit(c,body,actor=body.email,broker_verified=True)
    assert c.total_changes==before
    assert c.execute('SELECT COUNT(*) FROM account_admissions').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM account_terms_acceptances').fetchone()[0]==0


def test_suspended_customer_inviter_cannot_admit_new_accounts(accounts):
    from app.platform.invitations import create,InviteCreate
    c,s=accounts;owner=claim(email='customer-owner@example.com',subject='customer-owner')
    admission.admit(c,owner,actor=owner.email,broker_verified=True);c.commit()
    org=create_organization(c,owner.email,'Customer inviter')['organization_id']
    with workspace_scope(c,owner.email,org):invite=create(c,InviteCreate(email='teammate@example.com'))
    c.execute("UPDATE account_admissions SET status='SUSPENDED' WHERE user_id=?",(owner.email,));c.commit()
    s.heysow_public_registration_enabled=False;s.heysow_invited_registration_enabled=True
    body=claim(email=invite['email'],subject='teammate',invitation_token=invite['token'])
    with pytest.raises(HTTPException):admission.admit(c,body,actor=body.email,broker_verified=True)
    assert c.execute('SELECT COUNT(*) FROM account_admissions WHERE user_id=?',(body.email,)).fetchone()[0]==0


def test_changed_terms_block_customer_requests_but_allow_signed_viewer_reconsent(accounts):
    from app.platform.invitations import respond,InviteRespond
    c,s=accounts;org,invite=private_invite(c)
    body=claim(email=invite['email']);admission.admit(c,body,actor=body.email,broker_verified=True)
    respond(c,body.email,InviteRespond(token=invite['token'],action='ACCEPT'));c.commit()
    s.heysow_public_registration_enabled=False;s.heysow_invited_registration_enabled=False
    s.heysow_terms_version='new-synthetic-approved-version'
    assert not admission.access(c,body.email)
    with TestClient(app) as client:
        assert signed(client,s,'GET','/api/organization/workspaces',body.email).status_code==401
        renewed=body.model_copy(update={'terms_version':s.heysow_terms_version,'acceptance_nonce':str(uuid.uuid4())})
        response=signed(client,s,'POST',admission.PATH,body.email,renewed.model_dump())
        assert response.status_code==200,response.text
        assert signed(client,s,'GET','/api/organization/workspaces',body.email).status_code==200
    assert c.execute('SELECT role FROM organization_memberships WHERE user_id=? AND organization_id=?',(body.email,org)).fetchone()[0]=='VIEWER'
