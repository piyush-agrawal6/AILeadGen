"""API actor authority, default gate and viewer acceptance use real middleware."""
def test_invitation_api_matches_authenticated_identity_and_stays_gated(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.config.settings import get_settings
    from app.database.connection import db_session
    from app.api.organization import create_organization,membership_role
    from app.platform.context import workspace_scope
    from app.platform.memberships import change_role
    settings=get_settings()
    monkeypatch.setattr(settings,'database_path',str(tmp_path/'invitation-api.db'))
    monkeypatch.setattr(settings,'allowed_user_emails','owner@example.test,recipient@example.test,other@example.test')
    monkeypatch.setattr(settings,'heysow_workspace_management_enabled',False)
    with TestClient(app) as client:
        assert client.post('/api/organization/invitations',json={'email':'recipient@example.test'}).status_code==503
        monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True)
        with db_session() as c:
            org=c.execute('SELECT organization_id FROM organization_memberships WHERE user_id=?',('owner@example.test',)).fetchone()[0]
            other=create_organization(c,'other@example.test','Other company')['organization_id']
            with workspace_scope(c,'other@example.test',other):change_role(c,'other@example.test','recipient@example.test','VIEWER')
        result=client.post('/api/organization/invitations',json={'email':'recipient@example.test','role':'MEMBER'})
        assert result.status_code==201,result.text
        assert result.headers['cache-control']=='no-store'
        token=result.json()['token']
        body={'token':token,'action':'ACCEPT'}
        assert client.post('/api/organization/invitations/respond',json=body).status_code==404
        assert client.post('/api/organization/invitations/respond',json={**body,'actor':'recipient@example.test'}).status_code==422
        accepted=client.post('/api/organization/invitations/respond',json=body,headers={'x-le-user':'recipient@example.test'})
        assert accepted.status_code==200,accepted.text
        assert accepted.json()['organization_id']==org
        assert client.post('/api/organization/invitations/respond',json=body,headers={'x-le-user':'recipient@example.test'}).status_code==409
        with db_session() as c:
            assert membership_role(c,'recipient@example.test',other)=='VIEWER'
            assert membership_role(c,'recipient@example.test',org)=='MEMBER'
