from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,Field
from app.api.dependencies import get_db
from app.prospecting import searches
router=APIRouter(prefix='/discovery',tags=['Discovery'])
class Revision(BaseModel):revision:int=Field(ge=1)
@router.get('/capabilities')
def capabilities():
    from app.prospecting.criteria import capabilities
    return capabilities()
@router.get('/searches')
def listing(search:str=Query('',max_length=120),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),archived:bool=False,c=Depends(get_db,scope='function')):return searches.list_searches(c,search,page,page_size,archived)
@router.post('/searches',status_code=201)
def create(body:searches.SaveSearch,c=Depends(get_db,scope='function')):return searches.save(c,body)
@router.get('/searches/{key}')
def get(key:str,c=Depends(get_db,scope='function')):return searches.get(c,key)
@router.put('/searches/{key}')
def update(key:str,body:searches.SaveSearch,c=Depends(get_db,scope='function')):return searches.save(c,body,key)
@router.post('/searches/{key}/archive')
def archive(key:str,body:Revision,c=Depends(get_db,scope='function')):return searches.archive(c,key,body.revision)
@router.post('/searches/{key}/duplicate',status_code=201)
def duplicate(key:str,body:searches.SaveSearch,c=Depends(get_db,scope='function')):
    original=searches.get(c,key)
    return searches.save(c,body.model_copy(update={'configuration':original['configuration'],'revision':None}))
