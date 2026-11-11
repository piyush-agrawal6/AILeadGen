import asyncio,json,uuid
from unittest.mock import AsyncMock
import pytest
from test_intent_radar import radar,owned,source_result
from app.intent_radar import models,service,discovery,connectors
from app.platform.context import workspace_scope
from app.database.connection import get_connection
from app.intelligence import jobs

@pytest.mark.parametrize('boundary',['response','persistence'])
@pytest.mark.parametrize('revocation',['source','lease','cancel','pause'])
def test_revocation_blocks_signals_alerts_and_source_cache(radar,monkeypatch,boundary,revocation):
    c,path,org,_=radar
    with workspace_scope(c,'controlled@example.test',org):
        feed=str(uuid.uuid4());body=models.SourceConfig(name='Approved test feed',family='rss',endpoint='https://example.com/feed',policy_reference='Synthetic permission reference',attribution='Fixture publisher',enabled=True)
        c.execute('INSERT INTO intent_source_configs VALUES(?,?,?,?)',(org,feed,body.model_dump_json(),'2026-11-10'));c.commit()
        q=models.Search(keywords=['website'],sources=['rss'],feed_ids=[feed])
        m=service.save_monitor(c,models.Monitor(name='Fenced RSS',configuration=q,status='Active'));c.commit()
        job=discovery.create(c,models.Discovery(configuration=q,monitor_id=m['id']));c.commit()
        revoked=False
        def revoke():
            nonlocal revoked
            if revoked:return
            revoked=True;second=get_connection(path)
            if revocation=='source':second.execute('UPDATE intent_source_configs SET configuration_json=? WHERE organization_id=? AND id=?',(body.model_copy(update={'enabled':False}).model_dump_json(),org,feed))
            elif revocation=='lease':second.execute("UPDATE intelligence_jobs SET lease_owner='replacement-worker' WHERE id=? AND organization_id=?",(job['id'],org))
            elif revocation=='cancel':second.execute("UPDATE intelligence_jobs SET status='CANCELLED' WHERE id=? AND organization_id=?",(job['id'],org))
            else:second.execute("UPDATE intent_monitors SET status='Paused',revision=revision+1 WHERE id=? AND organization_id=?",(m['id'],org))
            second.commit();second.close()
        original_fence=discovery.fence
        def fence(*args,**kwargs):
            if boundary=='persistence':revoke()
            return original_fence(*args,**kwargs)
        monkeypatch.setattr(discovery,'fence',fence)
        async def fetch(c,q,key,permit):
            if boundary=='response':await asyncio.to_thread(revoke)
            # Exercise the actual adapter cache fence, not just the final signal fence.
            connectors.cache_fence(permit)
            c.execute('INSERT INTO intent_source_cache VALUES(?,?,?,?)',(org,'must-not-persist','[]','2100-01-01'));c.commit()
            return source_result()
        monkeypatch.setattr(connectors,'fetch',fetch)
        jobs.execute(job['id'],path)
        assert revoked
        for table in ('intent_signals','intent_alerts','intent_monitor_signals','intent_source_cache'):
            assert c.execute('SELECT COUNT(*) FROM '+table+' WHERE organization_id=?',(org,)).fetchone()[0]==0
        assert service.get(c,'monitors',m['id'])['last_checked'] is None

def test_foreign_feed_id_does_not_authorize_collection(radar):
    from fastapi import HTTPException
    c,_,org,other=radar;feed=str(uuid.uuid4())
    body=models.SourceConfig(name='Foreign feed',family='rss',endpoint='https://example.com/feed',policy_reference='Fixture only permission',attribution='Publisher',enabled=True)
    c.execute('INSERT INTO intent_source_configs VALUES(?,?,?,?)',(other,feed,body.model_dump_json(),'2026-11-10'));c.commit()
    with workspace_scope(c,'controlled@example.test',org):
        with pytest.raises(HTTPException) as denied:discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'],sources=['rss'],feed_ids=[feed])))
        assert denied.value.status_code in (404,409)
        assert c.execute('SELECT COUNT(*) FROM intent_discoveries WHERE organization_id=?',(org,)).fetchone()[0]==0

@pytest.mark.parametrize('change',['membership','product'])
def test_atomic_authorization_fence_denies_a_revocation_after_context_lookup(radar,monkeypatch,change):
    from app.intent_radar import permissions
    from fastapi import HTTPException
    c,path,org,_=radar
    original=permissions.context
    def stale_context(c,*args,**kwargs):
        old=original(c,*args,**kwargs);other=get_connection(path)
        if change=='membership':other.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=?",(org,))
        else:other.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=? AND product='INTENT_RADAR'",(org,))
        other.commit();other.close();return old
    with workspace_scope(c,'controlled@example.test',org):
        monkeypatch.setattr(permissions,'context',stale_context)
        with pytest.raises(HTTPException):permissions.persistence_context(c)
        c.rollback()
        assert c.execute('SELECT COUNT(*) FROM intent_signals WHERE organization_id=?',(org,)).fetchone()[0]==0

def test_new_mcp_reads_require_grants_and_workspace_ownership(radar,monkeypatch):
    from app.config.settings import get_settings
    from app.developer import keys
    from app.developer.mcp_server import invoke
    from app.intent_radar import providers
    c,path,org,other=radar
    monkeypatch.setattr(get_settings(),'heysow_developer_api_enabled',True);monkeypatch.setattr(get_settings(),'heysow_mcp_enabled',True)
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'controlled@example.test',org):
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'])));c.commit();jobs.execute(job['id'],path)
        signal=service.listing(c,'signals')['items'][0]
        allowed=keys.create(c,keys.Create(name='Intent reader',scopes=['mcp:use','intent:read']))
        denied=keys.create(c,keys.Create(name='No intent grant',scopes=['mcp:use','companies:read']));c.commit()
    headers={'authorization':'Bearer '+allowed['token']}
    assert len(invoke(headers,'list_intent_sources',{},['intent:read'])['items'])==4
    assert invoke(headers,'get_intent_analysis',{'id':signal['id']},['intent:read'])['items']==[]
    assert invoke(headers,'get_intent_run',{'id':job['id']},['intent:read'])['id']==job['id']
    with pytest.raises(Exception):invoke({'authorization':'Bearer '+denied['token']},'list_intent_sources',{},['intent:read'])
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(other,));c.commit()
    with workspace_scope(c,'foreign@example.test',other):foreign=keys.create(c,keys.Create(name='Foreign reader',scopes=['mcp:use','intent:read']));c.commit()
    for name,key in [('get_intent_analysis',signal['id']),('get_intent_run',job['id'])]:
        with pytest.raises(Exception):invoke({'authorization':'Bearer '+foreign['token']},name,{'id':key},['intent:read'])
