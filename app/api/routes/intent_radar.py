from uuid import UUID
from typing import Literal
from datetime import date
from fastapi import APIRouter,Depends,Query,HTTPException,Request
from pydantic import BaseModel,Field
from starlette.concurrency import run_in_threadpool
from app.api.dependencies import get_db
from app.intent_radar import models,service,discovery,providers,ai
from app.intent_radar.permissions import context,availability

router=APIRouter(prefix='/intent-radar',tags=['Intent Radar'])

@router.get('/capabilities')
def capabilities(c=Depends(get_db,scope='function')):
    ctx=context(c)
    from app.api.organization import membership_role
    from app.config.settings import get_settings
    return {**availability(c,ctx.organization_id),'growth_enabled':get_settings().intent_radar_growth_enabled,'sources':providers.catalog(c),'can_write':membership_role(c,ctx.actor,ctx.organization_id)!='VIEWER','can_manage':membership_role(c,ctx.actor,ctx.organization_id) in ('OWNER','ADMIN'),'usage':discovery.usage(c)}

@router.get('/sources/configurations')
def source_configs(c=Depends(get_db,scope='function')):
    from app.intent_radar.connectors import configurations
    return {'items':configurations(c)}
@router.get('/sources/health')
def source_health(c=Depends(get_db,scope='function')):
    from app.intent_radar.operations import source_health
    return source_health(c)
@router.post('/sources/expire')
def expire_sources(c=Depends(get_db,scope='function')):
    context(c,True,True)
    return service.expire_content(c)
@router.post('/sources/configurations',status_code=201)
def source_create(body:models.SourceConfig,c=Depends(get_db,scope='function')):
    from app.intent_radar.connectors import configure
    return configure(c,body)
@router.put('/sources/configurations/{key}')
def source_update(key:UUID,body:models.SourceConfig,c=Depends(get_db,scope='function')):
    from app.intent_radar.connectors import configure
    return configure(c,body,str(key))
@router.get('/sources/presets')
def source_presets(c=Depends(get_db,scope='function')):
    context(c)
    from app.intent_radar.feeds import CURATED_FEED_PRESETS
    from app.intent_radar.connectors import configurations
    from app.config.settings import get_settings
    from urllib.parse import urlsplit
    approved=set(x for x in get_settings().intent_radar_approved_feed_hosts.split(';') if x)
    existing={x['endpoint']:x for x in configurations(c)}
    return {'items':[{**p,'host_approved':urlsplit(p['endpoint']).hostname in approved,'configured':p['endpoint'] in existing,'enabled':bool(existing.get(p['endpoint'],{}).get('enabled')),'config_id':existing.get(p['endpoint'],{}).get('id')} for p in CURATED_FEED_PRESETS]}
class PresetToggle(BaseModel):
    enabled:bool=True
@router.post('/sources/presets/{preset_id}/enable')
def source_enable_preset(preset_id:str,body:PresetToggle=PresetToggle(),c=Depends(get_db,scope='function')):
    from app.intent_radar.connectors import enable_preset
    return enable_preset(c,preset_id,enabled=body.enabled)

@router.get('/sources/github/status')
def github_status(c=Depends(get_db,scope='function')):
    from app.intent_radar.github_source import connection_status
    return connection_status(c)
@router.post('/sources/github/oauth/start')
def github_oauth_start(c=Depends(get_db,scope='function')):
    from app.intent_radar.github_source import start_oauth
    return start_oauth(c)
class GitHubOAuthCallback(BaseModel):
    code:str=Field(min_length=1,max_length=256)
    state:str=Field(min_length=1,max_length=256)
    installation_id:str|None=Field(None,max_length=40)
@router.post('/sources/github/oauth/callback')
async def github_oauth_callback(body:GitHubOAuthCallback,c=Depends(get_db,scope='function')):
    from app.intent_radar.github_source import complete_oauth
    return await complete_oauth(c,code=body.code,state=body.state,installation_id=body.installation_id)
class GitHubRepoSelection(BaseModel):
    repository_ids:list[int]=Field(default_factory=list,max_length=100)
@router.put('/sources/github/repositories')
def github_repositories(body:GitHubRepoSelection,c=Depends(get_db,scope='function')):
    from app.intent_radar.github_source import update_repositories
    return update_repositories(c,body.repository_ids)
@router.post('/sources/github/disconnect')
def github_disconnect(c=Depends(get_db,scope='function')):
    from app.intent_radar.github_source import disconnect
    return disconnect(c)
@router.post('/webhooks/github')
async def github_webhook(request:Request,c=Depends(get_db,scope='function')):
    from app.intent_radar.github_source import ingest_webhook, MAX_WEBHOOK_BYTES
    buf=bytearray()
    async for chunk in request.stream():
        buf.extend(chunk)
        if len(buf)>MAX_WEBHOOK_BYTES:
            raise HTTPException(413,'Webhook payload exceeds supported size.')
    return ingest_webhook(
        c,
        raw_body=bytes(buf),
        delivery_id=request.headers.get('x-github-delivery',''),
        event_type=request.headers.get('x-github-event',''),
        signature=request.headers.get('x-hub-signature-256',''),
    )
@router.get('/sources/bluesky/stream-health')
def bluesky_stream_health(c=Depends(get_db,scope='function')):
    context(c)
    from app.intent_radar.bluesky_source import stream_health
    return stream_health(c)
@router.post('/sources/bluesky/stream-poll')
async def bluesky_stream_poll(c=Depends(get_db,scope='function')):
    context(c,True,True)
    from app.intent_radar.bluesky_source import poll_jetstream
    return await poll_jetstream(max_seconds=6.0,max_events=200,reconnect_attempts=2)
@router.get('/sources/youtube/policy')
def youtube_policy(c=Depends(get_db,scope='function')):
    context(c)
    from app.intent_radar.youtube_source import policy_state
    return policy_state()
@router.put('/monitors/{key}/schedule')
def schedule(key:UUID,body:models.Schedule,c=Depends(get_db,scope='function')):
    from app.intent_radar.schedules import update
    return update(c,str(key),body)
@router.get('/monitors/{key}/runs')
def monitor_runs(key:UUID,c=Depends(get_db,scope='function')):
    service.get(c,'monitors',str(key));org=context(c).organization_id
    rows=c.execute('SELECT d.id,d.created_at,r.provider,r.status,r.result_json FROM intent_discoveries d LEFT JOIN intent_source_runs r ON r.discovery_id=d.id AND r.organization_id=d.organization_id WHERE d.organization_id=? AND d.monitor_id=? ORDER BY d.created_at DESC LIMIT 100',(org,str(key))).fetchall()
    import json
    return {'items':[{**dict(r),'result':json.loads(r['result_json'] or '{}')} for r in rows]}

@router.get('/profile-context')
def profile_context(c=Depends(get_db,scope='function')):
    context(c)
    from app.platform.company_profiles import read_profile
    return read_profile(c)

@router.get('/overview/summary')
def overview_summary(c=Depends(get_db,scope='function')):return service.overview(c,include_previews=False)

@router.get('/overview')
def overview(c=Depends(get_db,scope='function')):return service.overview(c)
@router.get('/usage')
def usage(c=Depends(get_db,scope='function')):return discovery.usage(c)
@router.get('/usage/provider')
def provider_usage(c=Depends(get_db,scope='function')):
    context(c)
    from app.platform.provider_usage import summary
    return summary(c)
@router.get('/monitors')
def monitors(page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),search:str=Query('',max_length=120),status:str=Query('',max_length=30),c=Depends(get_db,scope='function')):return service.listing(c,'monitors',page=page,size=page_size,search=search,status=status)
@router.post('/monitors',status_code=201)
def create_monitor(body:models.Monitor,c=Depends(get_db,scope='function')):return service.save_monitor(c,body)
@router.get('/monitors/{key}')
def monitor(key:UUID,c=Depends(get_db,scope='function')):return service.get(c,'monitors',str(key))
@router.put('/monitors/{key}')
def update_monitor(key:UUID,body:models.Monitor,c=Depends(get_db,scope='function')):return service.save_monitor(c,body,str(key))
@router.post('/monitors/{key}/duplicate',status_code=201)
def duplicate(key:UUID,body:models.RequestKey,c=Depends(get_db,scope='function')):
    old=service.get(c,'monitors',str(key))
    return service.save_monitor(c,models.Monitor(name=(old['name']+' (copy)')[:120],description=old['description'],goal=old['goal'],configuration=old['configuration'],request_id=body.request_id))

@router.post('/discover',status_code=202)
async def start(body:models.Discovery,c=Depends(get_db,scope='function')):
    def prepare():
        result=discovery.create(c,body);c.commit();return result
    result=await run_in_threadpool(prepare)
    from app.intelligence.dispatch import launch
    await launch(result['id'])
    return await run_in_threadpool(discovery.owned_job,c,result['id'])
@router.get('/jobs/{key}')
def job(key:UUID,c=Depends(get_db,scope='function')):return discovery.owned_job(c,str(key))
@router.get('/jobs')
def jobs(c=Depends(get_db,scope='function')):
    org=context(c).organization_id
    return {'items':[discovery.owned_job(c,row[0]) for row in c.execute("SELECT id FROM intelligence_jobs WHERE organization_id=? AND kind='INTENT_DISCOVER' ORDER BY created_at DESC LIMIT 25",(org,)).fetchall()]}
@router.post('/jobs/{key}/{action}')
async def control(key:UUID,action:Literal['cancel','retry'],c=Depends(get_db,scope='function')):
    from app.intelligence import jobs
    def prepare():
        context(c,True);discovery.owned_job(c,str(key))
        result=jobs.control(c,str(key),action);c.commit();return result
    result=await run_in_threadpool(prepare)
    if action=='retry':
        from app.intelligence.dispatch import launch
        await launch(str(key))
    return result

@router.get('/signals')
def signals(page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),search:str=Query('',max_length=120),status:str=Query('',max_length=30),category:str=Query('',max_length=50),source:str=Query('',max_length=40),min_score:int=Query(0,ge=0,le=100),monitor_id:UUID|None=None,saved:Literal['','saved','unsaved']='',from_date:date|None=None,to_date:date|None=None,sort:Literal['newest','score','title']='newest',c=Depends(get_db,scope='function')):
    return service.listing(c,'signals',page=page,size=page_size,search=search,status=status,category=category,source=source,min_score=min_score,monitor_id=str(monitor_id) if monitor_id else '',saved=saved,from_date=from_date.isoformat() if from_date else '',to_date=to_date.isoformat() if to_date else '',sort=sort)
@router.get('/signals/{key}')
def signal(key:UUID,c=Depends(get_db,scope='function')):return service.get(c,'signals',str(key))
@router.patch('/signals/{key}')
def review(key:UUID,body:models.SignalUpdate,c=Depends(get_db,scope='function')):return service.review(c,str(key),body)
@router.post('/signals/actions')
def bulk(body:models.Bulk,c=Depends(get_db,scope='function')):
    context(c,True)
    keys=list(dict.fromkeys(map(str,body.ids)))
    for key in keys:service.get(c,'signals',key)
    for key in keys:
        if body.action=='save':service.bookmark(c,key)
        elif body.action=='opportunity':service.opportunity(c,key)
        else:
            old=service.get(c,'signals',key);service.review(c,key,models.SignalUpdate(revision=old['revision'],status='Reviewed' if body.action=='review' else 'Dismissed'))
    return {'updated':len(keys)}
@router.get('/saved')
def saved(page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),search:str=Query('',max_length=120),collection:str=Query('',max_length=100),sort:Literal['newest','oldest','collection']='newest',c=Depends(get_db,scope='function')):return service.saved(c,page=page,size=page_size,search=search,collection=collection,sort=sort)
@router.post('/saved/{key}')
def save_signal(key:UUID,c=Depends(get_db,scope='function')):return service.bookmark(c,str(key))
@router.put('/saved/{key}')
def edit_saved(key:UUID,body:models.SavedUpdate,c=Depends(get_db,scope='function')):return service.bookmark(c,str(key),body)
@router.delete('/saved/{key}')
def unsave(key:UUID,c=Depends(get_db,scope='function')):return service.bookmark(c,str(key),remove=True)
@router.post('/opportunities/{signal_id}',status_code=201)
def select(signal_id:UUID,c=Depends(get_db,scope='function')):return service.opportunity(c,str(signal_id))
@router.get('/opportunities')
def opportunities(page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),status:str=Query('',max_length=30),c=Depends(get_db,scope='function')):return service.listing(c,'opportunities',page=page,size=page_size,status=status)
@router.get('/opportunities/{key}')
def opportunity_detail(key:UUID,c=Depends(get_db,scope='function')):return service.get(c,'opportunities',str(key))
@router.patch('/opportunities/{key}')
def update_opportunity(key:UUID,body:models.OpportunityUpdate,c=Depends(get_db,scope='function')):return service.opportunity(c,str(key),body)
@router.get('/alerts')
def alerts(page:int=Query(1,ge=1,le=10000),read_state:Literal['All','Unread','Read']='All',alert_kind:Literal['All','Source issues','Monitor activity']='All',c=Depends(get_db,scope='function')):return service.listing(c,'alerts',page=page,read_state=read_state,alert_kind=alert_kind)
class Read(BaseModel):read:bool
@router.patch('/alerts/{key}')
def read(key:UUID,body:Read,c=Depends(get_db,scope='function')):return service.mark_alert(c,str(key),body.read)
@router.get('/settings')
def settings(c=Depends(get_db,scope='function')):return service.preferences(c)
@router.put('/settings')
def update_settings(body:models.Preferences,c=Depends(get_db,scope='function')):return service.preferences(c,body)
@router.post('/draft')
async def draft(body:models.Prompt,c=Depends(get_db,scope='function')):return await ai.draft(c,body)

@router.post('/signals/{key}/analysis')
async def analyze(key:UUID,body:models.AnalysisRequest,c=Depends(get_db,scope='function')):
    from app.intent_radar.intelligence import analyze
    return await analyze(c,str(key),body)
@router.get('/signals/{key}/analysis')
def analysis_history(key:UUID,c=Depends(get_db,scope='function')):
    from app.intent_radar.intelligence import history
    return history(c,str(key))
@router.post('/signals/{key}/withdraw')
def withdraw(key:UUID,c=Depends(get_db,scope='function')):
    return service.remove_source(c,str(key))
@router.put('/signals/{key}/feedback')
def feedback(key:UUID,body:models.Feedback,c=Depends(get_db,scope='function')):
    from app.intent_radar.intelligence import feedback
    return feedback(c,str(key),body)
@router.get('/icps')
def icps(c=Depends(get_db,scope='function')):
    context(c)
    from app.icp.service import listing
    return listing(c)

# The global assistant reuses the existing asynchronous research/job pipeline.
from app.intent_radar import assistant
@router.get('/assistant/conversations')
def assistant_conversations(c=Depends(get_db,scope='function')):return assistant.listing(c)
@router.get('/assistant/conversations/{key}')
def assistant_conversation(key:UUID,c=Depends(get_db,scope='function')):return assistant.history(c,str(key))
@router.post('/assistant/turns',status_code=202)
async def assistant_turn(body:assistant.Turn,c=Depends(get_db,scope='function')):
    def prepare():
        result=assistant.start(c,body);c.commit();return result
    result=await run_in_threadpool(prepare)
    from app.intelligence.dispatch import launch
    if result.get('job_id'):await launch(result['job_id'])
    return result
