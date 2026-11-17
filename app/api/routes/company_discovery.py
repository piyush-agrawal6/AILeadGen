from typing import Literal,Any
from uuid import UUID
from pydantic import BaseModel,ConfigDict
from fastapi import APIRouter,Depends,BackgroundTasks
from app.api.dependencies import get_db
from app.platform import company_discovery as discovery
from app.platform.company_discovery_dispatch import launch
from app.platform.company_profiles import CompanyProfile

router=APIRouter(prefix='/organization/website-reviews',tags=['Company website setup'],dependencies=[Depends(discovery.require_enabled)])

class Review(BaseModel):
    id:UUID
    website:str
    status:Literal['QUEUED','RUNNING','READY','FAILED','CANCELLED']
    error_code:str|None
    created_at:str
    updated_at:str
    preview:dict[str,Any]|None
    can_retry:bool
    source_kind:Literal['WEBSITE','DESCRIPTION','ICP_RECOMMENDATIONS','ONBOARDING_ADVICE']='WEBSITE'
    progress_stage:str=''
    attempt_history:list[dict[str,Any]]=[]

class Control(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['CANCEL','RETRY']

@router.post('',response_model=Review,status_code=201)
def create(body:discovery.DiscoveryCreate,tasks:BackgroundTasks,c=Depends(get_db,scope='function')):
    result=discovery.create(c,body)
    if result['status']=='QUEUED':tasks.add_task(launch,result['id'])
    return result

@router.get('/capabilities')
def capabilities(c=Depends(get_db,scope='function')):
    from app.platform.company_autofill import capabilities
    return capabilities(c)

@router.get('/{review_id}',response_model=Review)
def detail(review_id:UUID,c=Depends(get_db,scope='function')):
    return discovery.detail(c,str(review_id))

@router.post('/{review_id}/control',response_model=Review)
def control(review_id:UUID,body:Control,tasks:BackgroundTasks,c=Depends(get_db,scope='function')):
    result=discovery.control(c,str(review_id),body.action)
    if result['status']=='QUEUED':tasks.add_task(launch,str(review_id))
    return result

@router.post('/{review_id}/confirm',response_model=CompanyProfile)
def confirm(review_id:UUID,body:discovery.PreviewApply,c=Depends(get_db,scope='function')):
    return discovery.confirm(c,str(review_id),body)
