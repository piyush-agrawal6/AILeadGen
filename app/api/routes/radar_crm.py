from uuid import UUID
from fastapi import APIRouter,Depends
from app.api.dependencies import get_db
from app.api.routes.integrations import Code
from app.integrations import hubspot,service

router=APIRouter(prefix='/intent-radar/hubspot',tags=['Radar CRM'])
db=Depends(get_db,scope='function')

@router.get('')
def status(c=db):return hubspot.status(c)

@router.post('/authorize')
def authorize(c=db):
    hubspot.enabled(c);return service.authorize(c,spec=hubspot.spec())

@router.post('/connect')
async def connect(body:Code,c=db):
    hubspot.enabled(c);return await service.connect(c,body.state,body.code,spec=hubspot.spec())

@router.delete('/connections/{key}')
def disconnect(key:UUID,c=db):
    hubspot.enabled(c);return service.disconnect(c,str(key),spec=hubspot.spec())

@router.get('/connections/{key}/pipelines')
async def pipelines(key:UUID,c=db):return await hubspot.pipelines(c,str(key))

@router.post('/connections/{key}/match')
async def match(key:UUID,body:hubspot.Match,c=db):return await hubspot.match(c,str(key),body)
