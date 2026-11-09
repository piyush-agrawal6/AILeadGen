from fastapi import APIRouter,Depends
from typing import Literal
from pydantic import BaseModel
from app.api.dependencies import get_db
from app.platform.workspaces import require_management_enabled
from app.platform import onboarding as setup

router=APIRouter(prefix='/organization/onboarding',tags=['Company setup'],dependencies=[Depends(require_management_enabled)])

class Progress(setup.Setup):
    status:Literal['NOT_STARTED','IN_PROGRESS','COMPLETED','FAILED']
    can_edit:bool

class Result(BaseModel):
    status:Literal['COMPLETED']
    discovery_started:Literal[False]
    outreach_started:Literal[False]

@router.get('',response_model=Progress)
def read(c=Depends(get_db,scope='function')):
    return setup.read(c)

@router.get('/progress')
def progress(c=Depends(get_db,scope='function')):
    return setup.progress(c)

@router.put('',response_model=Progress)
def save(body:setup.Setup,c=Depends(get_db,scope='function')):
    return setup.save(c,body)

@router.post('/complete',response_model=Result)
def complete(body:setup.Completion,c=Depends(get_db,scope='function')):
    return setup.complete(c,body)
