"""Feature-gated account workspace operations; existing authentication is retained."""
from fastapi import APIRouter,Depends,HTTPException,Request,Query,Response
from pydantic import BaseModel,ConfigDict
from typing import Literal
from uuid import UUID
from app.api.dependencies import get_db
from app.api.organization import memberships,resolve
from app.config.settings import get_settings

router=APIRouter(prefix='/organization',tags=['Workspaces'])

def require_enabled():
    from app.platform.workspaces import require_management_enabled
    require_management_enabled()

class Selection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    organization_id:UUID

class WorkspaceMembership(BaseModel):
    id:str
    organization_id:UUID
    role:Literal['OWNER','ADMIN','MEMBER','VIEWER']
    status:Literal['ACTIVE']
    name:str
    slug:str
    created_at:str

class WorkspaceList(BaseModel):
    items:list[WorkspaceMembership]
    active_organization_id:UUID|None
    active_onboarding_status:Literal['NOT_STARTED','IN_PROGRESS','COMPLETED','FAILED']|None
    active_is_internal:bool=False

@router.get('/workspaces',response_model=WorkspaceList)
def workspaces(request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    state=resolve(c,request.state.user_email)
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    if state:
        from app.billing.subscription_access import required,product_grant
        if required(c,state['organization_id']) and not product_grant(c,state['organization_id']):
            state={**state,'onboarding_status':'IN_PROGRESS'}
    return {'items':memberships(c,request.state.user_email),'active_organization_id':state['organization_id'] if state else None,'active_onboarding_status':state['onboarding_status'] if state else None,'active_is_internal':bool(state and state['organization_id']==PLANEBYTE_ORGANIZATION_ID)}

@router.get('/products')
def product_access(request:Request,c=Depends(get_db,scope='function')):
    # Middleware already resolved membership and reverified the workspace scope.
    # Never repeat that remote lookup or accept a browser-supplied workspace ID.
    state=getattr(request.state,'organization',None)
    from app.intent_radar.permissions import availability
    from app.api.organization import products
    from app.config.settings import get_settings
    org=state['organization_id'] if state else None
    radar=availability(c,org)
    return {'billing_enabled':bool(get_settings().billing_enabled),'organization_id':org,'lead_engine_available':get_settings().lead_engine_available,'lead_engine':bool(org and products(c,org).get('LEADGEN')),'intent_radar':{**radar,'growth_enabled':bool(radar['enabled'] and get_settings().intent_radar_growth_enabled)}}

@router.put('/active',response_model=Selection)
def active(body:Selection,request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.platform.workspaces import select_workspace
    return select_workspace(c,request.state.user_email,str(body.organization_id))

from app.platform.company_profiles import CompanyProfile,CompanyUpdate,read_profile,save_profile

@router.get('/profile',response_model=CompanyProfile)
def profile(c=Depends(get_db,scope='function')):
    require_enabled()
    return read_profile(c)

@router.put('/profile',response_model=CompanyProfile)
def update_profile(body:CompanyUpdate,c=Depends(get_db,scope='function')):
    require_enabled()
    return save_profile(c,body)

from app.platform import invitations
from app.platform.workspaces import WorkspaceCreate,WorkspaceCreated,create_workspace

@router.post('/workspaces',status_code=201,response_model=WorkspaceCreated)
def workspace_create(body:WorkspaceCreate,request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    return create_workspace(c,request.state.user_email,body)

@router.get('/invitations',response_model=invitations.InvitationPage)
def invitation_list(page:int=Query(default=1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    require_enabled()
    return invitations.list_invitations(c,page)

@router.post('/invitations',status_code=201,response_model=invitations.InvitationCreated)
def invitation_create(body:invitations.InviteCreate,response:Response,c=Depends(get_db,scope='function')):
    require_enabled()
    response.headers['Cache-Control']='no-store'
    return invitations.create(c,body)

@router.post('/invitations/respond',response_model=invitations.InvitationResult)
def invitation_respond(body:invitations.InviteRespond,request:Request,response:Response,c=Depends(get_db,scope='function')):
    require_enabled()
    response.headers['Cache-Control']='no-store'
    return invitations.respond(c,request.state.user_email,body)

@router.delete('/invitations/{invitation_id}',response_model=invitations.InvitationRevoked)
def invitation_revoke(invitation_id:UUID,c=Depends(get_db,scope='function')):
    require_enabled()
    return invitations.revoke(c,str(invitation_id))

@router.get('/notifications',response_model=invitations.NotificationPage)
def notification_list(c=Depends(get_db,scope='function')):
    require_enabled()
    return invitations.notifications(c)

@router.get('/usage')
def usage_overview(c=Depends(get_db,scope='function')):
    from app.billing.overview import overview
    return overview(c)
