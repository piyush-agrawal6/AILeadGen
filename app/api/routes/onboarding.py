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

@router.post('/skip',response_model=Progress)
def skip_onboarding(c=Depends(get_db,scope='function')):
    return setup.set_deferred(c,True)

@router.post('/resume',response_model=Progress)
def resume_onboarding(c=Depends(get_db,scope='function')):
    return setup.set_deferred(c,False)

# AI setup reuses the existing company worker and canonical profile/ICP stores.
from uuid import UUID
from fastapi import BackgroundTasks
from app.platform import onboarding_ai as assisted
from app.platform.company_discovery_dispatch import launch

@router.get('/assistant-context')
def assisted_state(c=Depends(get_db,scope='function')):
    return assisted.state(c)

@router.put('/private-draft')
def private_draft(body:assisted.PrivateDraft,c=Depends(get_db,scope='function')):
    return assisted.save_private_draft(c,body)

@router.post('/analyze',status_code=202)
def analyze(body:assisted.Start,tasks:BackgroundTasks,c=Depends(get_db,scope='function')):
    result=assisted.analyze(c,body)
    if result['review']['status']=='QUEUED':tasks.add_task(launch,result['review']['id'])
    return result

@router.put('/company')
def approve_company(body:assisted.SaveCompany,c=Depends(get_db,scope='function')):
    return assisted.company(c,body)

@router.post('/recommendations',status_code=202)
def recommend(body:assisted.Recommend,tasks:BackgroundTasks,c=Depends(get_db,scope='function')):
    result=assisted.recommendations(c,body)
    if result['review']['status']=='QUEUED':tasks.add_task(launch,result['review']['id'])
    return result

@router.post('/accept-profiles')
def accept_profiles(body:assisted.Accept,c=Depends(get_db,scope='function')):
    return assisted.accept(c,body)

@router.post('/finish',response_model=Result)
def finish(body:assisted.Finish,c=Depends(get_db,scope='function')):
    return assisted.finish(c,body)

@router.post('/assistant',status_code=202)
def guidance(body:assisted.Question,tasks:BackgroundTasks,c=Depends(get_db,scope='function')):
    result=assisted.ask(c,body)
    if (result.get('job') or {}).get('status')=='QUEUED':tasks.add_task(launch,result['job']['id'])
    return result

@router.get('/reviews/{key}')
def review(key:UUID,c=Depends(get_db,scope='function')):
    return assisted.detail(c,str(key))
