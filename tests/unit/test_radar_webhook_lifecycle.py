import asyncio,json,time
from unittest.mock import AsyncMock
import httpx,pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from test_intent_radar import radar,owned,run,source_result
from app.platform.context import workspace_scope
from app.intent_radar import service,models,providers
from app.webhooks import service as hooks,worker
from app.config.settings import get_settings

def test_committed_radar_events_are_minimal_stable_and_revocable(radar,monkeypatch):
    c,path,org,other=radar;s=get_settings();monkeypatch.setattr(s,'heysow_webhooks_enabled',True);monkeypatch.setattr(s,'heysow_integration_encryption_key',Fernet.generate_key().decode());monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    monkeypatch.setattr(s,'radar_webhook_events_enabled',True)
    with workspace_scope(c,'controlled@example.test',org):
        config=hooks.Endpoint(name='Test receiver',url='https://receiver.example.test/events',topics=list(hooks.RADAR_TOPICS));registered=hooks.save(c,config);endpoint=registered['endpoint']['id'];c.commit()
        for _ in range(2):run(c,path,models.Search(keywords=['website']))
        sig=service.listing(c,'signals')['items'][0];sid=sig['id'];service.review(c,sid,models.SignalUpdate(status='In Review',revision=sig['revision']));opp=service.opportunity(c,sid);service.opportunity(c,sid);service.opportunity(c,opp['id'],models.OpportunityUpdate(status='Reviewing',priority='Medium',revision=opp['revision']));c.commit()
        events=[dict(r) for r in c.execute('SELECT * FROM webhook_deliveries WHERE endpoint_id=?',(endpoint,)).fetchall()];assert sorted(e['topic'] for e in events)==sorted(hooks.RADAR_TOPICS)
        def receive(req):
            payload=json.loads(req.content);stamp=req.headers['X-PlaneByte-Timestamp'];assert abs(time.time()-int(stamp))<300
            assert req.headers['X-PlaneByte-Signature']==hooks.signature(registered['signing_secret'],stamp,req.content)
            assert payload['schema_version']==1 and len(payload['data'])==1 and payload['resource'].startswith('/api/v1/intent-radar/') and sig['title'] not in str(payload)
            return httpx.Response(204)
        assert asyncio.run(worker.deliver(c,endpoint,events[0]['id'],httpx.MockTransport(receive)))=='DELIVERED'
        c.execute('UPDATE intent_signals SET available=0 WHERE id=?',(sid,));c.commit()
        assert asyncio.run(worker.deliver(c,endpoint,events[1]['id'],httpx.MockTransport(lambda _:pytest.fail('revoked evidence sent'))))=='FAILED'
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):hooks.save(c,config)
