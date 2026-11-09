from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,ConfigDict
from app.api.dependencies import get_db
from app.assistant import service
router=APIRouter(prefix='/assistant',tags=['Lead Engine assistant'])
@router.get('/status')
def status(c=Depends(get_db,scope='function')):
    from app.config.settings import get_settings
    from app.api.organization import membership_role
    from app.acquisition.config import settings
    context=service.ctx(c);provider=settings()
    return {'enabled':get_settings().heysow_lead_assistant_enabled,'configured':bool(provider.vertex_enabled or provider.gemini_enabled and provider.gemini_key.get_secret_value()),'can_use':membership_role(c,context.actor,context.organization_id) in ('OWNER','ADMIN'),'writes_require_approval':True,'email_sending_supported':False}
@router.get('/conversations')
def listing(page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):return service.listing(c,page)
@router.get('/conversations/{key}')
def detail(key:UUID,c=Depends(get_db,scope='function')):return service.detail(c,str(key))
@router.post('/turns',status_code=202)
async def turn(body:service.Turn,c=Depends(get_db,scope='function')):
    result=service.create(c,body);c.commit()
    from app.intelligence.dispatch import launch
    await launch(result['job_id']);return result
class Decision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision:Literal['approve','decline']
@router.post('/actions/{key}')
async def action(key:UUID,body:Decision,c=Depends(get_db,scope='function')):
    result=service.action(c,str(key),body.decision);c.commit()
    job=result.get('result',{}).get('job')
    if job:
        from app.intelligence.dispatch import launch
        await launch(job['id'])
    return result
