"""Signed account preferences do not accept a user or organization selector."""
from fastapi import APIRouter,Depends,Request
from app.api.dependencies import get_db
from app.platform.workspaces import require_management_enabled as require_enabled
from app.platform.account_profiles import AccountProfile,AccountUpdate,read,save

router=APIRouter(prefix='/profile',tags=['Account'])

@router.get('',response_model=AccountProfile)
def profile(request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    return read(c,request.state.user_email)

@router.put('',response_model=AccountProfile)
def update_profile(body:AccountUpdate,request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    return save(c,request.state.user_email,body)
