from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.people import service
router=APIRouter(prefix='/people',tags=['Professional contacts'])
class Revision(BaseModel):revision:int=Field(ge=1)
class Note(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    body:str=Field(min_length=1,max_length=5000)
@router.get('')
def listing(search:str=Query('',max_length=200),business_id:int|None=Query(None,ge=1),job_role:str=Query('',max_length=150),state:str=Query('',max_length=30),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):return service.listing(c,search,business_id,job_role,state,page,page_size)
@router.post('/companies/{business_id}',status_code=201)
def create(business_id:int,body:service.Person,c=Depends(get_db,scope='function')):return service.save(c,business_id,body)
@router.get('/{key}')
def detail(key:str,c=Depends(get_db,scope='function')):return service.get(c,key)
@router.put('/{key}/companies/{business_id}')
def update(key:str,business_id:int,body:service.Person,c=Depends(get_db,scope='function')):return service.save(c,business_id,body,key)
@router.post('/{key}/archive')
def archive(key:str,body:Revision,c=Depends(get_db,scope='function')):return service.archive(c,key,body.revision)
@router.post('/{key}/notes',status_code=201)
def note(key:str,body:Note,c=Depends(get_db,scope='function')):return service.note(c,key,body.body)
@router.post('/{key}/lists/{list_id}')
def add_list(key:str,list_id:str,c=Depends(get_db,scope='function')):return service.membership(c,key,list_id)
@router.delete('/{key}/lists/{list_id}')
def remove_list(key:str,list_id:str,c=Depends(get_db,scope='function')):return service.membership(c,key,list_id,False)
