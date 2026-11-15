"""Blocking database phases must not freeze unrelated async HTTP requests."""
import asyncio,threading
import httpx
from test_growth_intelligence import growth,radar,owned
from app.intent_radar import assistant
from app.api.server import create_app
from app.platform.context import current

def test_slow_count_database_work_keeps_the_http_event_loop_responsive(growth,monkeypatch):
    c,_,org,_=growth;c.commit()
    entered=threading.Event();release=threading.Event();finished=[]
    original=assistant.start
    def blocking(db,body):
        assert current().organization_id==org and current().actor=='controlled@example.test'
        entered.set();finished.append(release.wait(timeout=2))
        return original(db,body)
    monkeypatch.setattr(assistant,'start',blocking)
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()),base_url='http://isolated.test') as client:
            task=asyncio.create_task(client.post('/api/intent-radar/assistant/turns',headers={'x-le-user':'controlled@example.test'},json={'prompt':'How many signals have I generated yet?'}))
            try:
                assert await asyncio.to_thread(entered.wait,1)
                assert (await asyncio.wait_for(client.get('/api/health'),timeout=1)).status_code==200
                assert not finished,'Database work blocked the unrelated health request until timeout.'
            finally:release.set()
            result=await task
            assert result.status_code==202 and result.json()['job_id'] is None
    asyncio.run(scenario())
    assert finished==[True]

def test_dispatch_preparation_is_offloaded_with_verified_context(growth,monkeypatch):
    from app.intelligence import dispatch
    from app.platform.context import workspace_scope
    c,_,org,_=growth;entered=threading.Event();release=threading.Event();finished=[]
    def claim(_):
        assert current().organization_id==org
        entered.set();finished.append(release.wait(timeout=2))
    monkeypatch.setattr(dispatch,'claim_dispatch',claim)
    async def scenario():
        task=asyncio.create_task(dispatch.launch('synthetic-no-dispatch'))
        try:
            assert await asyncio.to_thread(entered.wait,1)
            await asyncio.sleep(0)
            assert not finished,'Dispatcher blocked the event loop.'
        finally:release.set()
        await task
    with workspace_scope(c,'controlled@example.test',org):asyncio.run(scenario())
    assert finished==[True]
