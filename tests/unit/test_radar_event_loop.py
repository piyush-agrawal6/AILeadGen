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


def test_scheduler_database_phase_keeps_unrelated_http_reads_responsive(growth,monkeypatch):
    from app.intent_radar import schedules
    entered=threading.Event();release=threading.Event();finished=[]
    def slow_prepare():
        entered.set();finished.append(release.wait(timeout=2));return []
    monkeypatch.setattr(schedules,'_prepare_tick',slow_prepare)
    monkeypatch.setattr(schedules,'_record_tick',lambda count:None)
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()),base_url='http://isolated.test') as client:
            task=asyncio.create_task(schedules.tick())
            try:
                assert await asyncio.to_thread(entered.wait,1)
                assert (await asyncio.wait_for(client.get('/api/health'),timeout=1)).status_code==200
                assert not finished,'Scheduled database maintenance froze the HTTP event loop.'
            finally:release.set()
            await task
    asyncio.run(scenario());assert finished==[True]


def test_scheduler_releases_verified_scope_connection_before_cloud_dispatch(growth,monkeypatch):
    from app.intent_radar import schedules
    from app.intelligence import dispatch
    from contextlib import contextmanager
    c,_,org,_=growth;c.commit();active=[];seen=[]
    original=schedules.db_session
    @contextmanager
    def tracked():
        with original() as db:
            active.append(db)
            try:yield db
            finally:active.remove(db)
    monkeypatch.setattr(schedules,'db_session',tracked)
    monkeypatch.setattr(schedules,'_prepare_tick',lambda:[{'id':'controlled-job','organization_id':org,'actor':'controlled@example.test'}])
    async def launch(key):
        assert key=='controlled-job' and current().organization_id==org
        assert not active,'Do not retain a database connection across cloud dispatch.'
        seen.append(key)
    monkeypatch.setattr(dispatch,'launch',launch)
    asyncio.run(schedules.tick());assert seen==['controlled-job'] and not active

def test_revoked_dispatch_candidate_does_not_starve_other_workspaces(monkeypatch):
    import asyncio
    from contextvars import copy_context
    from fastapi import HTTPException
    from app.intent_radar import schedules
    from app.intelligence import dispatch
    from app.config.settings import get_settings
    monkeypatch.setattr(get_settings(),'intent_radar_stage','Beta')
    monkeypatch.setattr(get_settings(),'billing_enabled',False);monkeypatch.setattr(get_settings(),'payu_billing_enabled',False)
    monkeypatch.setattr(schedules,'_prepare_tick',lambda:[{'id':'revoked'},{'id':'authorized'}])
    def verified(item):
        if item['id']=='revoked':raise HTTPException(403,'Membership revoked')
        return copy_context()
    calls=[]
    async def launch(key):calls.append(key)
    monkeypatch.setattr(schedules,'_dispatch_context',verified);monkeypatch.setattr(dispatch,'launch',launch);monkeypatch.setattr(schedules,'_record_tick',lambda count:None)
    asyncio.run(schedules.tick());assert calls==['authorized']
