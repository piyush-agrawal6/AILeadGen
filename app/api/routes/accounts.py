"""Exact, signed broker account endpoints; none inherits workspace authority."""
import re
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from app.api.dependencies import get_db
from app.accounts import models,service,sessions,google
from app.config.settings import get_settings

PREFIX='/api/organization/accounts'
PUBLIC=frozenset(PREFIX+'/'+p for p in ('signup','verify-email','resend-verification','login','exchange','recovery','reset-password'))
SESSION=frozenset(PREFIX+'/'+p for p in ('session','logout','link-google','set-password','terms'))
router=APIRouter(prefix='/organization/accounts',tags=['Account security'])

def broker(request:Request,response:Response):
    response.headers['Cache-Control']='private, no-store'
    if not get_settings().heysow_accounts_enabled:raise HTTPException(404,'Account service is unavailable.')
    if not getattr(request.state,'internal_verified',False):raise HTTPException(401,'Verified server authentication is required.')
    client=request.headers.get('x-le-client','')
    if not re.fullmatch(r'[a-f0-9]{64}',client):raise HTTPException(400,'A verified account request context is required.')
    return client

def identity(request,email):
    if request.state.user_email!=email:raise HTTPException(403,'Account request identity does not match.')

def challenge_identity(c,request,key):
    row=c.execute('SELECT email FROM account_verifications WHERE id=?',(str(key),)).fetchone()
    if row:identity(request,row['email'])

def state(request):return request.state.user_email,request.headers.get('x-le-session','')

@router.post('/signup')
def signup(body:models.Signup,request:Request,response:Response,client=Depends(broker)):
    identity(request,body.email);result=service.begin_signup(body,client)
    result.pop('notification_id',None)
    return result

@router.post('/verify-email')
def verify(body:models.Verify,request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    challenge_identity(c,request,body.challenge_id)
    result=service.verify_email(body,client)
    if not result['verified']:response.status_code=400
    return result

@router.post('/resend-verification')
def resend(body:models.Resend,request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    challenge_identity(c,request,body.challenge_id)
    result=service.resend_verification(body,client);result.pop('notification_id',None)
    return result

@router.post('/login')
def login(body:models.Login,request:Request,response:Response,client=Depends(broker)):
    identity(request,body.email);result=service.login(body,client)
    if not result['authenticated']:response.status_code=401
    return result

@router.post('/exchange')
def exchange(body:models.Exchange,request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    service.enabled()
    from app.accounts import security
    row=c.execute('SELECT user_id FROM account_login_tickets WHERE token_hash=?',(security.digest('exchange',body.token.get_secret_value()),)).fetchone()
    if row:identity(request,row['user_id'])
    return sessions.exchange(c,body.token.get_secret_value())

@router.post('/recovery')
def recovery(body:models.Recovery,request:Request,response:Response,client=Depends(broker)):
    identity(request,body.email);service.recover(body,client)
    return {'accepted':True,'message':'If this account supports password recovery, a reset link will be emailed shortly.'}

@router.post('/reset-password')
def reset(body:models.Reset,request:Request,response:Response,client=Depends(broker)):
    result=service.reset_password(body,client)
    if not result['reset']:response.status_code=400
    return result

@router.post('/session')
def session(request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    service.enabled();actor,token=state(request);value=sessions.validate(c,actor,token,require_current_terms=False)
    account=c.execute('SELECT password_hash,google_subject FROM customer_accounts WHERE user_id=?',(actor,)).fetchone()
    return {'email':value['email'],'name':value['name'],'expires_at':value['expires_at'],'terms_version':value['terms_version'],'requires_terms':value['terms_version']!=get_settings().heysow_terms_version,'password_enabled':bool(account['password_hash']),'google_linked':bool(account['google_subject'])}

@router.post('/logout')
def logout(request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    service.enabled();return sessions.revoke(c,*state(request))

@router.post('/link-google')
def link(request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    service.enabled();return google.begin_link(c,*state(request))

@router.post('/set-password')
def set_password(body:models.SetPassword,request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    from app.accounts import security
    security.throttle('set-password',request.state.user_email,client,email_limit=3,client_limit=10)
    return service.start_password(c,*state(request),body)

@router.post('/terms')
def terms(body:models.AcceptTerms,request:Request,response:Response,client=Depends(broker),c=Depends(get_db,scope='function')):
    return service.accept_terms(c,*state(request),body)
