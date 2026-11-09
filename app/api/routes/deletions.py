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
def deletion_preview(kind:Kind,identifier:str,request:Request,conn=Depends(get_db,scope='function')):
    return preview(conn,kind,identifier,organization=request.state.organization_id)

@router.delete('/{kind}/{identifier}')
def permanently_delete(kind:Kind,identifier:str,body:ConfirmDeletion,request:Request,conn=Depends(get_db,scope='function')):
    return delete(conn,kind,identifier,body.confirmation,body.preview_token,request.state.user_email,organization=request.state.organization_id)
