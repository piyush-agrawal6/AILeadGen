"""Gated targeting profiles; these routes never launch acquisition or outreach."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from app.api.dependencies import get_db
from app.platform.workspaces import require_management_enabled
from app.icp import service
from app.icp.models import Create,Update,Duplicate,Profile,ProfilePage,VersionPage
from app.icp import ai,builder
from pydantic import BaseModel,Field

router=APIRouter(prefix='/organization/icps',tags=['Ideal customer profiles'],dependencies=[Depends(require_management_enabled)])

class AIStatus(BaseModel):
    enabled:bool
    configured:bool
    can_generate:bool
    provider:str
    review_required:Literal[True]
    requests_used_today:int
    daily_limit:int
    period_timezone:Literal['UTC']

class AIProposal(BaseModel):
    draft:ai.Draft
    proposal_id:UUID|None=None
    cached:bool
    review_required:Literal[True]
    profile_created:Literal[False]
    discovery_started:Literal[False]

@router.get('/ai-status',response_model=AIStatus)
def ai_status(c=Depends(get_db,scope='function')):
    return ai.status(c)

@router.post('/interpret',response_model=AIProposal)
async def interpret(body:ai.Interpretation,c=Depends(get_db,scope='function')):
    return await ai.interpret(c,body)

@router.post('/suggest')
async def suggest(body:builder.Generate,c=Depends(get_db,scope='function')):
    return await builder.generate(c,body)

@router.post('/refine')
async def refine(body:builder.Refine,c=Depends(get_db,scope='function')):
    return await builder.refine(c,body)

@router.get('',response_model=ProfilePage)
def profiles(page:int=Query(1,ge=1,le=10000),status:Literal['ACTIVE','INACTIVE','ARCHIVED']|None=None,c=Depends(get_db,scope='function')):
    return service.listing(c,page,status)

@router.post('',response_model=Profile,status_code=201)
def create(body:Create,c=Depends(get_db,scope='function')):
    return service.create(c,body)

@router.get('/{profile_id}',response_model=Profile)
def get(profile_id:UUID,c=Depends(get_db,scope='function')):
    return service.get(c,str(profile_id))

@router.get('/{profile_id}/discovery-preview')
def discovery_preview(profile_id:UUID,c=Depends(get_db,scope='function')):
    from app.icp.discovery import preview
    return preview(c,str(profile_id))

class RefinementStart(ai.Strict):
    revision:int=Field(ge=1)

@router.post('/{profile_id}/prepare-refinement')
def prepare_refinement(profile_id:UUID,body:RefinementStart,c=Depends(get_db,scope='function')):
    return builder.prepare_refinement(c,str(profile_id),body.revision)

@router.put('/{profile_id}',response_model=Profile)
def update(profile_id:UUID,body:Update,c=Depends(get_db,scope='function')):
    return service.update(c,str(profile_id),body)

@router.post('/{profile_id}/duplicate',response_model=Profile,status_code=201)
def duplicate(profile_id:UUID,body:Duplicate,c=Depends(get_db,scope='function')):
    return service.duplicate(c,str(profile_id),body)

@router.get('/{profile_id}/versions',response_model=VersionPage)
def history(profile_id:UUID,page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    return service.history(c,str(profile_id),page)

@router.get('/{profile_id}/compare')
def compare(profile_id:UUID,before:int=Query(ge=1),after:int=Query(ge=1),c=Depends(get_db,scope='function')):
    return service.compare(c,str(profile_id),before,after)
