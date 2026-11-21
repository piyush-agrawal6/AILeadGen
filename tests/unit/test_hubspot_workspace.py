import asyncio
from urllib.parse import parse_qs,urlsplit
from pydantic import SecretStr
import pytest
from fastapi import HTTPException
from app.config.settings import get_settings
from app.integrations import hubspot,service
from app.platform.context import workspace_scope
from test_customer_integrations import workspace,OWNER

def test_workspace_oauth_requires_portal_and_cannot_replay(workspace,monkeypatch):
    c,org,other,path=workspace;s=get_settings();monkeypatch.setattr(s,'radar_hubspot_client_id','fixture-id');monkeypatch.setattr(s,'radar_hubspot_client_secret',SecretStr('fixture-only'));monkeypatch.setattr(s,'radar_hubspot_redirect_uri',hubspot.CALLBACK)
    calls=[]
    async def exchange(path,data):
        calls.append(path)
        if path=='token':return {'access_token':'private-fixture-token','refresh_token':'private-fixture-refresh','expires_in':1800,'hub_id':84}
        return {'active':True,'hub_id':84,'client_id':'fixture-id','app_id':62975250,'scopes':hubspot.SCOPES.split()}
    monkeypatch.setattr(hubspot,'token_request',exchange)
    with workspace_scope(c,OWNER,org):
        auth=service.authorize(c,spec=hubspot.spec());u=urlsplit(auth['authorization_url']);assert u.netloc=='app.hubspot.com';state=parse_qs(u.query)['state'][0];c.commit()
    with workspace_scope(c,OWNER,other):
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,state,'code',spec=hubspot.spec()))
    with workspace_scope(c,OWNER,org):
        row=asyncio.run(service.connect(c,state,'code',spec=hubspot.spec()));c.commit();assert calls==['token','token/introspect'] and row['status']=='CONNECTED' and 'access_token' not in row
        assert 'private-fixture' not in service.owned(c,row['id'],spec=hubspot.spec())['credentials_ciphertext']
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,state,'code',spec=hubspot.spec()))
        service.disconnect(c,row['id'],spec=hubspot.spec());assert service.owned(c,row['id'],spec=hubspot.spec())['credentials_ciphertext'] is None
