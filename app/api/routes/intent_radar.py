from uuid import UUID
from typing import Literal
from datetime import date
from fastapi import APIRouter,Depends,Query,HTTPException
from pydantic import BaseModel
from app.api.dependencies import get_db
from app.intent_radar import models,service,discovery,providers,ai
from app.intent_radar.permissions import context,availability

router=APIRouter(prefix='/intent-radar',tags=['Intent Radar'])

@router.get('/capabilities')
def capabilities(c=Depends(get_db,scope='function')):
    ctx=context(c)
    from app.api.organization import membership_role
    return {**availability(c,ctx.organization_id),'sources':providers.catalog(c),'can_write':membership_role(c,ctx.actor,ctx.organization_id)!='VIEWER','can_manage':membership_role(c,ctx.actor,ctx.organization_id) in ('OWNER','ADMIN'),'usage':discovery.usage(c)}

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
    result=discovery.create(c,body);c.commit()
    from app.intelligence.dispatch import launch
    await launch(result['id'])
    return discovery.owned_job(c,result['id'])
@router.get('/jobs/{key}')
def job(key:UUID,c=Depends(get_db,scope='function')):return discovery.owned_job(c,str(key))
@router.get('/jobs')
def jobs(c=Depends(get_db,scope='function')):
    org=context(c).organization_id
    return {'items':[discovery.owned_job(c,row[0]) for row in c.execute("SELECT id FROM intelligence_jobs WHERE organization_id=? AND kind='INTENT_DISCOVER' ORDER BY created_at DESC LIMIT 25",(org,)).fetchall()]}
@router.post('/jobs/{key}/{action}')
async def control(key:UUID,action:Literal['cancel','retry'],c=Depends(get_db,scope='function')):
    context(c,True);discovery.owned_job(c,str(key))
    from app.intelligence import jobs
    result=jobs.control(c,str(key),action);c.commit()
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
