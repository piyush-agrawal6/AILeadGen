"""Integrated customer UI fixture. Source/AI transports are explicitly synthetic."""
import asyncio,json
from types import SimpleNamespace
from uuid import UUID
from fastapi import Depends
from tests.intent_radar_fixture_server import app,path,settings
from app.api.dependencies import get_db
from app.database.connection import get_connection
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
from app.platform.context import workspace_scope
from app.intent_radar import connectors,models,providers,service,schedules,intelligence
from app.acquisition import ai

settings.intent_radar_stackexchange_enabled=True
settings.intent_radar_schedules_enabled=True
settings.intent_radar_ai_enabled=True
c=get_connection(path)
with workspace_scope(c,'founder@leadengine.example',PLANEBYTE_ORGANIZATION_ID):
    feed_id='4d9b8735-807d-4a7f-8ef4-2bcb1e96c8a1'
    config=models.SourceConfig(name='Synthetic approved RSS',family='rss',endpoint='https://www.w3.org/news/feed/',policy_reference='Synthetic test policy; not live approval',attribution='Synthetic publisher',enabled=True)
    c.execute('INSERT INTO intent_source_configs(organization_id,id,configuration_json,updated_at) VALUES(?,?,?,?)',(PLANEBYTE_ORGANIZATION_ID,feed_id,config.model_dump_json(),'2026-11-10'))
    c.commit()
c.close()
original=connectors.fetch
async def fetch(c,q,key,permit):
    if key=='hacker_news':return await original(c,q,key,permit)
    permit();await asyncio.sleep(.2);permit()
    item=providers.normalize({'id':999124 if key=='stack_exchange' else 999125,'type':'story','time':int(__import__('time').time()),'title':'Recommend a website development agency?','text':'Looking for a website development partner for our business.'})
    item.update(source='Stack Exchange' if key=='stack_exchange' else 'RSS / Atom',source_url='https://stackoverflow.com/questions/999124' if key=='stack_exchange' else 'https://example.com/research-request')
    return {'items':[item],'requests':1,'scanned':1,'next_offset':None,'synthetic':True,'coverage':'Synthetic '+key+' source transport for browser contract checks; not live evidence.'}
connectors.fetch=fetch
async def structured(instruction,value,model,**limits):
    if model==models.SearchDraft:return models.SearchDraft(name='Synthetic AI criteria',configuration=models.Search(keywords=['website'],sources=['hacker_news','stack_exchange','rss'],feed_ids=[feed_id]))
    return intelligence.Interpretation(categories=['Recommendation request'],claims=[intelligence.Claim(kind='intent',quote='website development',interpretation='Synthetic grounded classification for UI testing')],uncertainty='Moderate',review_needed=True)
ai.provider=lambda c=None:SimpleNamespace(structured=structured,last_model='SYNTHETIC-browser-model',last_provider='SYNTHETIC')

@app.post('/api/intent-radar/_test-tick/{key}')
async def test_tick(key:UUID,c=Depends(get_db,scope='function')):
    # Test-only clock advancement on an owned monitor; never mounted by production app.
    old=service.get(c,'monitors',str(key))
    if old['status']=='Active':c.execute('UPDATE intent_monitors SET next_run_at=? WHERE id=? AND organization_id=?',('2000-01-01',old['id'],old['organization_id']));c.commit()
    pending=schedules.enqueue_due(c)
    from app.intelligence import jobs
    for job in pending:await asyncio.to_thread(jobs.execute,job['id'],path)
    return {'dispatched':len(pending)}
