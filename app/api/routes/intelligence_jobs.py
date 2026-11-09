from fastapi import APIRouter,Depends,Query
from app.api.dependencies import get_db
from app.intelligence import jobs
router=APIRouter(prefix='/intelligence/jobs',tags=['Company and contact enrichment'])
@router.get('/capabilities')
def capabilities(c=Depends(get_db,scope='function')):
    from app.people.service import ctx
    from app.config.settings import get_settings
    from app.api.organization import membership_role
    context=ctx(c)
    return {'company_summary_enabled':get_settings().heysow_company_ai_enabled,'can_generate_summary':membership_role(c,context.actor,context.organization_id) in ('OWNER','ADMIN'),'summary_type':'AI_SELECTED_PUBLIC_EXCERPTS'}

@router.get('')
def listing(status:str=Query('',max_length=30),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):return jobs.listing(c,status,page,page_size)
@router.post('',status_code=202)
async def start(body:jobs.Start,c=Depends(get_db,scope='function')):
    result=jobs.create(c,body);c.commit()
    from app.intelligence.dispatch import launch
    await launch(result['id']);return jobs.detail(c,result['id'])
@router.get('/{key}')
def detail(key:str,page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):return jobs.detail(c,key,page,page_size)
@router.post('/{key}/{action}')
async def control(key:str,action:str,c=Depends(get_db,scope='function')):
    from fastapi import HTTPException
    if action not in ('cancel','retry'):raise HTTPException(404,'Action not found.')
    result=jobs.control(c,key,action);c.commit()
    if action=='retry':
        from app.intelligence.dispatch import launch
        await launch(key)
    return result
