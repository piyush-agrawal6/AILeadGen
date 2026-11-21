import asyncio,uuid
from unittest.mock import AsyncMock
from fastapi import HTTPException
import pytest
from app.config.settings import get_settings
from app.platform.context import workspace_scope
from app.intent_radar import actions,crm_actions as crm,models,service as radar,providers
from app.integrations import hubspot,service
from app.database.prospects import now
from test_prospecting_only import owned
from test_intent_radar import radar as radar_fixture,run,source_result

@pytest.mark.parametrize('fault',[None,'timeout','readback'])
def test_exact_portal_create_is_once_and_confirmed_only_on_readback(radar_fixture,monkeypatch,fault):
    c,path,org,other=radar_fixture;actor='controlled@example.test';s=get_settings()
    for k,v in dict(radar_actions_enabled=True,radar_hubspot_enabled=True,heysow_workspace_management_enabled=True,heysow_customer_integrations_enabled=True,radar_hubspot_write_portals='84').items():monkeypatch.setattr(s,k,v)
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()));conn=str(uuid.uuid4());stamp=now()
    c.execute("insert into radar_crm_connections(id,organization_id,provider,status,portal_id,created_at,updated_at) values(?,?,'HUBSPOT','CONNECTED','84',?,?)",(conn,org,stamp,stamp));c.commit()
    writes=[];reads=[]
    async def adapter(method,path,token,body=None,params=None):
        if method=='POST':
            writes.append(body);assert path.endswith('/companies')
            if fault=='timeout':raise TimeoutError()
            return {'id':'810'}
        reads.append(path);return {'id':'810','properties':{} if fault=='readback' and len(reads)==1 else writes[0]['properties']}
    monkeypatch.setattr(service,'access_token',AsyncMock(return_value=('offline',1)));monkeypatch.setattr(hubspot,'match',AsyncMock(return_value={'items':[],'more':False}));monkeypatch.setattr(hubspot,'crm_json',adapter)
    with workspace_scope(c,actor,org):
        run(c,path,models.Search(keywords=['website']));op=radar.opportunity(c,radar.listing(c,'signals')['items'][0]['id']);c.commit()
        body=crm.Draft(request_id=uuid.uuid4(),opportunity_id=op['id'],connection_id=conn,operation='create',kind='companies',identifier='example.test',fields={'name':'Disposable test'});a=asyncio.run(crm.prepare(c,body));assert not writes
        with pytest.raises(HTTPException):asyncio.run(crm.approve(c,a['id'],actions.Approval(digest='0'*64)))
        approval=actions.Approval(digest=a['digest']);first=asyncio.run(crm.approve(c,a['id'],approval));c.commit()
        assert first['execution']=={None:'CONFIRMED','timeout':'UNCERTAIN','readback':'VERIFY'}[fault]
        second=asyncio.run(crm.approve(c,a['id'],approval));c.commit();assert len(writes)==1 and second['execution']==('UNCERTAIN' if fault=='timeout' else 'CONFIRMED')
        assert actions.owned(c,org,a['id'])['status']==('NEEDS_REVIEW' if fault=='timeout' else 'SUCCEEDED')
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):asyncio.run(crm.approve(c,a['id'],approval))
