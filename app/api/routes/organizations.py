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
    plan_label:str|None=None
    access_state:str|None=None
    onboarding_status:str|None=None
    onboarding_completed_steps:int|None=None
    onboarding_total_steps:int|None=None
    member_count:int|None=None

class WorkspaceList(BaseModel):
    items:list[WorkspaceMembership]
    active_organization_id:UUID|None
    active_onboarding_status:Literal['NOT_STARTED','IN_PROGRESS','COMPLETED','FAILED']|None
    active_onboarding_deferred:bool=False
    active_is_internal:bool=False

@router.get('/workspaces',response_model=WorkspaceList)
def workspaces(request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    state=resolve(c,request.state.user_email)
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    from app.platform.workspaces import enrich_memberships
    if state:
        from app.billing.subscription_access import required,product_grant
        if required(c,state['organization_id']) and not product_grant(c,state['organization_id']):
            state={**state,'onboarding_status':'IN_PROGRESS'}
    return {'items':enrich_memberships(c,memberships(c,request.state.user_email)),'active_organization_id':state['organization_id'] if state else None,'active_onboarding_status':state['onboarding_status'] if state else None,'active_onboarding_deferred':bool(state and state.get('onboarding_deferred')),'active_is_internal':bool(state and state['organization_id']==PLANEBYTE_ORGANIZATION_ID)}

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
from app.platform.workspaces import WorkspaceCreate,WorkspaceCreated,WorkspaceRename,create_workspace,rename_workspace,leave_workspace

@router.post('/workspaces',status_code=201,response_model=WorkspaceCreated)
def workspace_create(body:WorkspaceCreate,request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    return create_workspace(c,request.state.user_email,body)

@router.patch('/workspaces/{workspace_id}')
def workspace_rename(workspace_id:UUID,body:WorkspaceRename,request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    return rename_workspace(c,request.state.user_email,str(workspace_id),body)

@router.post('/workspaces/{workspace_id}/leave')
def workspace_leave(workspace_id:UUID,request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    return leave_workspace(c,request.state.user_email,str(workspace_id))

@router.get('/members')
def member_list(request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.platform.memberships import list_members
    return list_members(c,request.state.user_email)

@router.delete('/members/{member_email:path}')
def member_remove(member_email:str,request:Request,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.platform.memberships import remove_member
    return remove_member(c,request.state.user_email,member_email)

@router.get('/invitations',response_model=invitations.InvitationPage)
def invitation_list(page:int=Query(default=1,ge=1,le=10000),c=Depends(get_db,scope='function')):
    require_enabled()
    return invitations.list_invitations(c,page)

@router.post('/invitations',status_code=201,response_model=invitations.InvitationCreated)
def invitation_create(body:invitations.InviteCreate,response:Response,c=Depends(get_db,scope='function')):
    require_enabled()
    response.headers['Cache-Control']='no-store'
    return invitations.create(c,body)

@router.post('/invitations/{invitation_id}/resend',response_model=invitations.InvitationCreated)
def invitation_resend(invitation_id:UUID,response:Response,c=Depends(get_db,scope='function')):
    require_enabled()
    response.headers['Cache-Control']='no-store'
    return invitations.resend(c,str(invitation_id))

@router.post('/invitations/respond',response_model=invitations.InvitationResult)
def invitation_respond(body:invitations.InviteRespond,request:Request,response:Response,c=Depends(get_db,scope='function')):
    require_enabled()
    response.headers['Cache-Control']='no-store'
    return invitations.respond(c,request.state.user_email,body)

@router.delete('/invitations/{invitation_id}',response_model=invitations.InvitationRevoked)
def invitation_revoke(invitation_id:UUID,c=Depends(get_db,scope='function')):
    require_enabled()
    return invitations.revoke(c,str(invitation_id))

@router.get('/notifications')
def notification_list(
    category:str|None=None,
    status:str='all',
    priority:str|None=None,
    severity:str|None=None,
    search:str='',
    from_date:str|None=None,
    to_date:str|None=None,
    page:int=1,
    page_size:int=20,
    c=Depends(get_db,scope='function'),
):
    require_enabled()
    from app.notifications import center
    return center.list_notifications(
        c,
        category=category,
        status=status,
        priority=priority,
        severity=severity,
        search=search,
        from_date=from_date,
        to_date=to_date,
        page=max(1,min(page,500)),
        page_size=max(1,min(page_size,100)),
    )

@router.post('/notifications/{notification_id}/read')
def notification_mark_read(notification_id:UUID,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.notifications import center
    return center.mark_read(c,str(notification_id))

@router.post('/notifications/{notification_id}/unread')
def notification_mark_unread(notification_id:UUID,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.notifications import center
    return center.mark_unread(c,str(notification_id))

from app.notifications.center import BulkNotificationAction
@router.post('/notifications/bulk')
def notification_bulk(body:BulkNotificationAction,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.notifications import center
    return center.bulk_update(c,body)

@router.post('/notifications/read-all')
def notification_mark_all_read(category:str|None=None,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.notifications import center
    return center.mark_all_read(c,category=category)

@router.get('/notifications/preferences')
def notification_preferences_get(c=Depends(get_db,scope='function')):
    require_enabled()
    from app.notifications import center
    return center.get_preferences(c)

from app.notifications.center import NotificationPreferencesUpdate
@router.put('/notifications/preferences')
def notification_preferences_put(body:NotificationPreferencesUpdate,c=Depends(get_db,scope='function')):
    require_enabled()
    from app.notifications import center
    return center.update_preferences(c,body)

@router.post('/notifications/test-email')
def notification_test_email(c=Depends(get_db,scope='function')):
    require_enabled()
    from app.notifications import center
    return center.send_test_email(c)

@router.get('/usage')
def usage_overview(c=Depends(get_db,scope='function')):
    from app.billing.overview import overview
    return overview(c)
