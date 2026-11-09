from typing import Literal
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter,Depends,Response
from app.api.dependencies import get_db
from app.platform.workspaces import require_management_enabled
from app.platform import domains

router=APIRouter(prefix='/organization/domains',tags=['Domain ownership'],dependencies=[Depends(require_management_enabled)])

class Domain(BaseModel):
    id:UUID
    domain:str
    status:Literal['PENDING','VERIFIED','REVOKED','EXPIRED']
    challenge_expires_at:str
    verified_at:str|None
    checked_at:str|None

class DomainPage(BaseModel):
    items:list[Domain]
    can_edit:bool

class Challenge(BaseModel):
    id:UUID
    domain:str
    record_type:Literal['TXT']
    record_name:str
    record_value:str
    expires_at:str

class Verification(BaseModel):
    status:Literal['VERIFIED','PENDING']
    verified_at:str|None

class Revoked(BaseModel):
    status:Literal['REVOKED']

@router.get('',response_model=DomainPage)
def listing(c=Depends(get_db,scope='function')):
    return domains.listing(c)

@router.post('',response_model=Challenge,status_code=201)
def challenge(body:domains.DomainCreate,response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='no-store'
    return domains.challenge(c,body)

@router.post('/{domain_id}/verify',response_model=Verification)
async def verify(domain_id:UUID,c=Depends(get_db,scope='function')):
    return await domains.verify(c,str(domain_id))

@router.delete('/{domain_id}',response_model=Revoked)
def revoke(domain_id:UUID,c=Depends(get_db,scope='function')):
    return domains.revoke(c,str(domain_id))
