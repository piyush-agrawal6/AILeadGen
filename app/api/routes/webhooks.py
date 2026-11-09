from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query,Response
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.webhooks import service
router=APIRouter(prefix='/organization/webhooks',tags=['Signed outgoing webhooks'])
@router.get('')
def listing(c=Depends(get_db,scope='function')):return service.listing(c)
@router.post('',status_code=201)
def create(body:service.Endpoint,response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store';return service.save(c,body)
@router.put('/{key}')
def update(key:UUID,body:service.Endpoint,c=Depends(get_db,scope='function')):return service.save(c,body,str(key))
class Control(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['pause','resume','archive','rotate']
    revision:int=Field(ge=1)
@router.post('/{key}/control')
def control(key:UUID,body:Control,response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store';return service.control(c,str(key),body.action,body.revision)
@router.get('/{key}/deliveries')
def history(key:UUID,page:int=Query(1,ge=1,le=10000),c=Depends(get_db,scope='function')):return service.history(c,str(key),page)
@router.post('/{key}/deliveries/{delivery_id}/retry')
def retry(key:UUID,delivery_id:UUID,c=Depends(get_db,scope='function')):return service.retry(c,str(key),str(delivery_id))
