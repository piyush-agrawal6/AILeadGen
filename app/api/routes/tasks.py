from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
from app.api.dependencies import get_db
from app.sales import tasks
router=APIRouter(prefix='/sales/tasks',tags=['Sales tasks'])
@router.get('')
def listing(status:Literal['','OPEN','COMPLETED','CANCELED']='OPEN',assigned_to:str=Query('',max_length=254),task_type:Literal['','FOLLOW_UP','RESEARCH','REVIEW','OTHER']='',page:int=Query(1,ge=1,le=10000),page_size:int=Query(25,ge=1,le=100),priority:Literal['','LOW','NORMAL','HIGH']='',view:Literal['','MY','TODAY','UPCOMING','OVERDUE','COMPLETED']='',timezone:str=Query('UTC',max_length=80),c=Depends(get_db,scope='function')):return tasks.listing(c,status,assigned_to,task_type,page,page_size,priority,view,timezone)
@router.post('',status_code=201)
def create(body:tasks.Task,c=Depends(get_db,scope='function')):return tasks.create(c,body)
@router.get('/{key}')
def get(key:UUID,c=Depends(get_db,scope='function')):return tasks.get(c,str(key))
class Change(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:int=Field(ge=1)
    status:Literal['OPEN','COMPLETED','CANCELED']|None=None
    title:str|None=Field(None,min_length=2,max_length=180)
    task_type:Literal['FOLLOW_UP','RESEARCH','REVIEW','OTHER']|None=None
    priority:Literal['LOW','NORMAL','HIGH']|None=None
    note:str|None=Field(None,max_length=2000)
    due_at:str|None=Field(None,max_length=60)
    assigned_to:str|None=Field(None,max_length=254)
    contact_id:UUID|None=None
    @field_validator('due_at')
    @classmethod
    def date(cls,value):return tasks.Task.date(value) if value is not None else value
    @model_validator(mode='after')
    def valid_edit(self):
        if any(getattr(self,key) is None for key in self.model_fields_set-{'assigned_to','contact_id'}):raise ValueError('Required task fields cannot be cleared.')
        if self.model_fields_set=={'revision'}:raise ValueError('Choose a task field to update.')
        return self
@router.patch('/{key}')
def change(key:UUID,body:Change,c=Depends(get_db,scope='function')):return tasks.update(c,str(key),body.revision,body.status,body.model_dump(exclude={'revision','status'},exclude_unset=True))
