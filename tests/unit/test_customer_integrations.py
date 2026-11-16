"""Tenant connection acceptance uses synthetic OAuth/Sheets responses only."""
import asyncio
import json
from urllib.parse import urlsplit,parse_qs
from unittest.mock import AsyncMock,Mock
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform.memberships import change_role
from app.config.settings import get_settings
from app.acquisition.config import AcquisitionSettings
from app.acquisition import sheets
from app.integrations import service,google_sheets
from app.integrations.crypto import seal,open_envelope

OWNER='customer@example.com'
TOKENS={'access_token':'synthetic-access','refresh_token':'synthetic-refresh','expires_in':3600,'scope':sheets.SCOPE}

@pytest.fixture
def workspace(tmp_path,monkeypatch):
    settings=get_settings();monkeypatch.setattr(settings,'heysow_workspace_management_enabled',True);monkeypatch.setattr(settings,'heysow_customer_integrations_enabled',True)
    monkeypatch.setattr(settings,'heysow_integration_encryption_key',Fernet.generate_key().decode())
    monkeypatch.setattr(settings,'allowed_user_emails',OWNER+',viewer@example.com')
    path=tmp_path/'customer.db';monkeypatch.setattr(settings,'database_path',str(path))
    config=AcquisitionSettings(_env_file=None,AUTH_GOOGLE_ID='fixture-client',AUTH_GOOGLE_SECRET='fixture-secret',GOOGLE_SHEETS_REDIRECT_URI='https://example.test/acquisition/sheets/callback')
    monkeypatch.setattr('app.acquisition.config.settings',lambda:config)
    c=get_connection(path);run_migrations(c)
    first=create_organization(c,OWNER,'First customer')['organization_id'];second=create_organization(c,OWNER,'Second customer')['organization_id']
    # These are existing, authorized Lead Engine customer fixtures. New SaaS
    # organizations intentionally receive no default Lead Engine entitlement.
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id IN (?,?) AND product='LEADGEN'",(first,second));c.commit()
    yield c,first,second,path
    c.close()

def start(c):
    authorization=service.authorize(c)
    query=parse_qs(urlsplit(authorization['authorization_url']).query)
    row=c.execute('SELECT * FROM organization_integrations WHERE organization_id=?',(service.organization(),)).fetchone()
    c.commit();return query['state'][0],dict(row),query

def test_disabled_integration_and_missing_key_fail_before_provider_or_database(monkeypatch):
    monkeypatch.setattr(get_settings(),'heysow_customer_integrations_enabled',False)
    c=Mock()
    with pytest.raises(HTTPException) as disabled:service.listing(c)
    assert disabled.value.status_code==503;c.execute.assert_not_called()
    monkeypatch.setattr(get_settings(),'heysow_integration_encryption_key','')
    with pytest.raises(HTTPException):seal({},organization_id='a',connection_id='b',provider=service.PROVIDER,purpose='CREDENTIALS')

def test_scoped_encrypted_connection_and_shared_read_only_transport(workspace,monkeypatch):
    c,first,second,path=workspace;provider=AsyncMock(return_value=TOKENS);monkeypatch.setattr(sheets,'token_request',provider)
    reader=AsyncMock(return_value={'properties':{'title':'Controlled sheet'},'sheets':[{'properties':{'sheetId':1,'title':'Business rows','gridProperties':{'rowCount':10,'columnCount':5}}}]});monkeypatch.setattr(sheets,'read_with_token',reader)
    with workspace_scope(c,OWNER,first):
        state,row,query=start(c)
        assert query['scope']==[sheets.SCOPE] and query['code_challenge_method']==['S256']
        stored=c.execute('SELECT * FROM integration_oauth_states').fetchone();assert state not in str(dict(stored))
        result=asyncio.run(service.connect(c,state,'controlled-code'));c.commit()
        assert result['status']=='CONNECTED' and 'credentials' not in json.dumps(result)
        raw=dict(c.execute('SELECT * FROM organization_integrations WHERE id=?',(row['id'],)).fetchone())
        assert 'synthetic-access' not in str(raw) and 'synthetic-refresh' not in str(raw)
        data=asyncio.run(google_sheets.metadata(c,row['id'],'controlled-sheet-id'));assert data['title']=='Controlled sheet'
        assert reader.call_args.args[0]=='synthetic-access'
        assert 'synthetic' not in json.dumps(service.listing(c))
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,state,'controlled-code'))
        assert provider.call_count==1
    with workspace_scope(c,OWNER,second):
        with pytest.raises(HTTPException) as foreign:asyncio.run(google_sheets.metadata(c,row['id'],'controlled-sheet-id'))
        assert foreign.value.status_code==404 and reader.call_count==1
        _,other,_=start(c)
        # A database ciphertext swap must not cross tenants, even for one actor.
        c.execute("UPDATE organization_integrations SET status='CONNECTED',credentials_ciphertext=? WHERE id=?",(raw['credentials_ciphertext'],other['id']));c.commit()
        with pytest.raises(HTTPException) as swapped:asyncio.run(service.access_token(c,other['id']))
        assert swapped.value.status_code==409 and reader.call_count==1
    assert c.execute('SELECT COUNT(*) FROM acquisition_google_connections').fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_replaced_expired_states_and_broader_permissions_are_rejected(workspace,monkeypatch):
    import hashlib
    c,first,second,path=workspace;provider=AsyncMock(return_value={**TOKENS,'scope':sheets.SCOPE+' https://www.googleapis.com/auth/spreadsheets'});monkeypatch.setattr(sheets,'token_request',provider)
    with workspace_scope(c,OWNER,first):
        replaced,row,_=start(c);expired,_,_=start(c)
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,replaced,'controlled-code'))
        c.execute("UPDATE integration_oauth_states SET expires_at='2000-01-01T00:00:00+00:00' WHERE state_hash=?",(hashlib.sha256(expired.encode()).hexdigest(),));c.commit()
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,expired,'controlled-code'))
        provider.assert_not_called()
        fresh,_,_=start(c)
        with pytest.raises(HTTPException) as broader:asyncio.run(service.connect(c,fresh,'controlled-code'))
        assert broader.value.status_code==409 and provider.call_count==1
        stored=service.owned(c,row['id']);assert stored['credentials_ciphertext'] is None and stored['last_error_code']=='OAUTH_RESPONSE_REJECTED'
        exposed='heysow_integration_encryption_key' in get_settings().model_dump()
        assert not exposed

def test_oauth_state_cannot_cross_workspace_and_failed_exchange_is_single_use(workspace,monkeypatch):
    c,first,second,path=workspace;provider=AsyncMock(side_effect=sheets.SheetsUnavailable('fixture failure'));monkeypatch.setattr(sheets,'token_request',provider)
    with workspace_scope(c,OWNER,first):state,row,_=start(c)
    with workspace_scope(c,OWNER,second):
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,state,'controlled-code'))
        assert provider.call_count==0
    with workspace_scope(c,OWNER,first):
        with pytest.raises(HTTPException) as failed:asyncio.run(service.connect(c,state,'controlled-code'))
        assert failed.value.status_code==503
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,state,'controlled-code'))
        assert provider.call_count==1
        assert service.owned(c,row['id'])['last_error_code']=='OAUTH_UNAVAILABLE'

def test_disconnect_during_exchange_cannot_resurrect_and_explicit_reconnect_works(workspace,monkeypatch):
    c,first,second,path=workspace
    with workspace_scope(c,OWNER,first):
        state,row,_=start(c)
        async def cancelled(_):service.disconnect(c,row['id']);c.commit();return TOKENS
        monkeypatch.setattr(sheets,'token_request',cancelled)
        with pytest.raises(HTTPException) as stale:asyncio.run(service.connect(c,state,'controlled-code'))
        assert stale.value.status_code==409
        assert service.owned(c,row['id'])['credentials_ciphertext'] is None
        assert service.owned(c,row['id'])['status']=='DISCONNECTED'
        fresh,_,_=start(c);monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value=TOKENS))
        assert asyncio.run(service.connect(c,fresh,'controlled-code'))['status']=='CONNECTED';c.commit()
        disconnected=service.disconnect(c,row['id']);c.commit()
        assert disconnected=={'status':'DISCONNECTED','provider_access_revoked':False}
        assert service.owned(c,row['id'])['credentials_ciphertext'] is None

def test_refresh_lease_prevents_duplicate_calls_and_preserves_rotated_refresh_token(workspace,monkeypatch):
    c,first,second,path=workspace
    with workspace_scope(c,OWNER,first):
        state,row,_=start(c);monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value=TOKENS));asyncio.run(service.connect(c,state,'controlled-code'));c.commit()
        row=service.owned(c,row['id']);credentials=service.token_value(TOKENS);credentials['expires_at']='2000-01-01T00:00:00+00:00'
        c.execute('UPDATE organization_integrations SET credentials_ciphertext=? WHERE id=?',(seal(credentials,**service.context(row,'CREDENTIALS')),row['id']));c.commit()
        calls=[]
        async def refresh(payload):
            calls.append(payload)
            other=get_connection(path)
            try:
                with workspace_scope(other,OWNER,first):
                    with pytest.raises(HTTPException) as busy:await service.access_token(other,row['id'])
                    assert busy.value.status_code==429
            finally:other.close()
            return {**TOKENS,'access_token':'renewed-access','refresh_token':'renewed-refresh'}
        monkeypatch.setattr(sheets,'token_request',refresh)
        assert asyncio.run(service.access_token(c,row['id']))[0]=='renewed-access'
        assert len(calls)==1 and calls[0]['refresh_token']=='synthetic-refresh'
        stored=service.owned(c,row['id']);assert open_envelope(stored['credentials_ciphertext'],**service.context(stored,'CREDENTIALS'))['refresh_token']=='renewed-refresh'

def test_revoked_manager_cannot_finish_exchange_and_viewers_cannot_read_provider(workspace,monkeypatch):
    c,first,second,path=workspace
    with workspace_scope(c,OWNER,first):
        change_role(c,OWNER,'viewer@example.com','VIEWER');state,row,_=start(c)
        async def revoked(_):
            c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=? AND user_id=?",(first,OWNER));c.commit();return TOKENS
        monkeypatch.setattr(sheets,'token_request',revoked)
        with pytest.raises(HTTPException) as denied:asyncio.run(service.connect(c,state,'controlled-code'))
        assert denied.value.status_code==403 and service.owned(c,row['id'])['credentials_ciphertext'] is None
    provider=AsyncMock();monkeypatch.setattr(sheets,'read_with_token',provider)
    with workspace_scope(c,'viewer@example.com',first):
        assert service.listing(c)['can_manage'] is False
        with pytest.raises(HTTPException) as denied:asyncio.run(google_sheets.metadata(c,row['id'],'controlled-sheet-id'))
        assert denied.value.status_code==403;provider.assert_not_called()

def test_customer_connections_api_is_gated_and_never_returns_credentials(workspace,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    c,first,second,path=workspace
    from app.platform.workspaces import select_workspace
    select_workspace(c,OWNER,first);c.commit()
    with TestClient(app) as client:
        listing=client.get('/api/organization/integrations');assert listing.status_code==200 and listing.json()['items']==[]
        response=client.post('/api/organization/integrations/google-sheets/authorize');assert response.status_code==200
        assert response.headers['cache-control']=='no-store'
        state=parse_qs(urlsplit(response.json()['authorization_url']).query)['state'][0]
        monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value=TOKENS))
        rejected=client.post('/api/organization/integrations/google-sheets/connect',json={'state':state,'code':'controlled-code','organization_id':second});assert rejected.status_code==422
        connected=client.post('/api/organization/integrations/google-sheets/connect',json={'state':state,'code':'controlled-code'});assert connected.status_code==200
        assert 'synthetic' not in connected.text and 'ciphertext' not in client.get('/api/organization/integrations').text
        monkeypatch.setattr(get_settings(),'heysow_customer_integrations_enabled',False)
        assert client.get('/api/organization/integrations').status_code==503
        assert client.delete('/api/organization/integrations/'+connected.json()['id']).status_code==503
