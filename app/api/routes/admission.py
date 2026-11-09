"""Only the signed Google authentication broker may create an admitted account."""
from fastapi import APIRouter,Depends,Request,Response
from app.api.dependencies import get_db
from app.platform.admission import GoogleAdmission,admit

router=APIRouter(prefix='/organization/admission',tags=['Account admission'])

@router.post('/google')
def google_account(body:GoogleAdmission,request:Request,response:Response,c=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='private, no-store'
    return admit(c,body,actor=request.state.user_email,broker_verified=getattr(request.state,'internal_verified',False))
