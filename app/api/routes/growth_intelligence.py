"""Growth routes inherit the existing signed workspace and Intent Radar gate."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query,HTTPException
from fastapi.responses import Response
from app.api.dependencies import get_db
from app.growth_intelligence import analytics,models,service,exports

router=APIRouter(prefix='/intent-radar/growth',tags=['Growth Intelligence'])

@router.get('/context')
def context(c=Depends(get_db,scope='function')):
    org=analytics.access(c).organization_id
    rows=c.execute("SELECT id,name,revision FROM ideal_customer_profiles WHERE organization_id=? AND status<>'DELETED' ORDER BY updated_at DESC,id LIMIT 100",(org,)).fetchall()
    return {'icps':[dict(row) for row in rows],'basis':'Reviewed workspace profile and explicitly selected ICP; not inferred buyer attributes.'}

def scope(days:int=Query(0,ge=0,le=90),source:list[str]=Query(default=[],max_length=4),search:str=Query('',max_length=160),min_score:int=Query(0,ge=0,le=100),language:Literal['any','en','es','fr','de','pt','hi','ja']='any',theme_id:list[UUID]=Query(default=[],max_length=5),competitor_id:UUID|None=None,icp_id:UUID|None=None):
    if days not in (0,7,30,90):raise HTTPException(422,'Choose available evidence or a supported 7, 30 or 90 day window.')
    return models.Scope(days=days,sources=source,search=search,min_score=min_score,language=language,theme_ids=theme_id,competitor_id=competitor_id,icp_id=icp_id)

@router.get('/overview')
def overview(filters=Depends(scope),c=Depends(get_db,scope='function')):return analytics.overview(c,filters)

@router.post('/research',status_code=202)
async def start(body:models.Start,c=Depends(get_db,scope='function')):
    result=service.start(c,body);c.commit()
    from app.intelligence.dispatch import launch
    await launch(result['job_id'])
    return service.detail(c,result['id'])

@router.get('/research')
def research(kind:Literal['','THEMES','RESEARCH','REPORT']='',saved:bool=False,search:str=Query('',max_length=120),page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):return service.listing(c,kind,page,page_size,saved,search)

@router.get('/research/{key}')
def detail(key:UUID,c=Depends(get_db,scope='function')):return service.detail(c,str(key))

@router.patch('/research/{key}')
def save(key:UUID,body:models.Save,c=Depends(get_db,scope='function')):return service.save(c,str(key),body)

async def control(key:UUID,action:Literal['cancel','retry'],c):
    row=service.owned(c,str(key));analytics.access(c,True,True)
    from app.intelligence import jobs
    jobs.control(c,row['job_id'],action);c.commit()
    if action=='retry':
        from app.intelligence.dispatch import launch
        await launch(row['job_id'])
    return service.detail(c,str(key))

@router.post('/research/{key}/cancel')
async def cancel(key:UUID,c=Depends(get_db,scope='function')):
    return await control(key,'cancel',c)

@router.post('/research/{key}/retry')
async def retry(key:UUID,c=Depends(get_db,scope='function')):
    return await control(key,'retry',c)

@router.get('/research/{key}/export/{format}')
def export(key:UUID,format:Literal['md','csv','json'],c=Depends(get_db,scope='function')):
    body,mime=exports.render(c,str(key),format)
    return Response(body,media_type=mime,headers={'Content-Disposition':'attachment; filename="planebyte-market-review-'+str(key)[:8]+'.'+format+'"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.get('/themes')
def themes(search:str=Query('',max_length=120),saved:bool=False,page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):return service.themes(c,search,saved,page,page_size)

@router.get('/themes/{key}')
def theme(key:UUID,c=Depends(get_db,scope='function')):return service.theme(c,str(key))

@router.patch('/themes/{key}')
def theme_update(key:UUID,body:models.ThemeUpdate,c=Depends(get_db,scope='function')):return service.update_theme(c,str(key),body)

@router.get('/competitors')
def competitors(c=Depends(get_db,scope='function')):return service.competitors(c)

@router.post('/competitors',status_code=201)
def competitor(body:models.Competitor,c=Depends(get_db,scope='function')):return service.competitor(c,body)

@router.put('/competitors/{key}')
def competitor_update(key:UUID,body:models.Competitor,c=Depends(get_db,scope='function')):return service.competitor(c,body,str(key))

@router.get('/watchlists')
def watchlists(c=Depends(get_db,scope='function')):return service.watchlists(c)

@router.post('/watchlists',status_code=201)
def watchlist(body:models.Watchlist,c=Depends(get_db,scope='function')):return service.watchlist(c,body)

@router.get('/{kind}/{key}/notes')
def notes(kind:Literal['theme','research','opportunity','competitor'],key:UUID,c=Depends(get_db,scope='function')):return service.notes(c,kind,str(key))

@router.post('/{kind}/{key}/notes',status_code=201)
def note(kind:Literal['theme','research','opportunity','competitor'],key:UUID,body:models.Note,c=Depends(get_db,scope='function')):return service.note(c,kind,str(key),body)

@router.patch('/{kind}/{key}/notes/{note_id}')
def note_update(kind:Literal['theme','research','opportunity','competitor'],key:UUID,note_id:UUID,body:models.Note,c=Depends(get_db,scope='function')):return service.note(c,kind,str(key),body,str(note_id))

@router.post('/opportunities/{key}/companies',status_code=201)
def company_link(key:UUID,body:models.LinkCompany,c=Depends(get_db,scope='function')):return service.link_company(c,str(key),body)
