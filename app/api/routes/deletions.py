from typing import Literal
from fastapi import APIRouter,Depends,Request
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.api.services.deletion import preview,delete

router=APIRouter(prefix='/deletions',tags=['Permanent deletion'])
Kind=Literal['campaign','scan','lead']

class ConfirmDeletion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    confirmation:str=Field(max_length=10)
    preview_token:str=Field(pattern='^[0-9a-f]{64}$')

@router.get('/{kind}/{identifier}/preview')
def deletion_preview(kind:Kind,identifier:str,conn=Depends(get_db)):
    return preview(conn,kind,identifier)

@router.delete('/{kind}/{identifier}')
def permanently_delete(kind:Kind,identifier:str,body:ConfirmDeletion,request:Request,conn=Depends(get_db)):
    return delete(conn,kind,identifier,body.confirmation,body.preview_token,request.state.user_email)
