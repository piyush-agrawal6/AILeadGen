"""Personal workspace selection; does not grant membership or alter permissions."""
import uuid
from fastapi import HTTPException
from app.api.organization import membership_role,ensure_user
from app.database.prospects import now
from pydantic import BaseModel,ConfigDict,Field,field_validator
from uuid import UUID


def require_management_enabled():
    from app.config.settings import get_settings
    if not get_settings().heysow_workspace_management_enabled:
        raise HTTPException(503,'Workspace management is not enabled.')


class WorkspaceCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=2,max_length=120)
    request_id:UUID

    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        value=value.strip()
        if len(value)<2 or any(ord(ch)<32 for ch in value):raise ValueError('Enter a company name of at least two characters without control characters.')
        return value


class WorkspaceCreated(BaseModel):
    organization_id:UUID
    reused:bool


def create_workspace(c,actor,body:WorkspaceCreate):
    """An authenticated account explicitly creates and selects its own workspace."""
    from app.api.organization import create_organization
    ensure_user(c,actor)
    if getattr(c,'backend',None)=='postgres':
        c.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(actor,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    prior=c.execute('SELECT organization_id,requested_name FROM workspace_creation_requests WHERE user_id=? AND request_id=?',(actor,str(body.request_id))).fetchone()
    if prior:
        if prior['requested_name']!=body.name:raise HTTPException(409,'This creation request was already used for a different company name.')
        if not membership_role(c,actor,prior['organization_id']):raise HTTPException(404,'Created workspace is no longer available to this account.')
        # Retrying an old request must not switch the user's current workspace.
        return {'organization_id':prior['organization_id'],'reused':True}
    owned=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE user_id=? AND role='OWNER' AND status='ACTIVE'",(actor,)).fetchone()[0]
    from app.config.settings import get_settings
    if owned>=get_settings().heysow_workspace_creation_limit:raise HTTPException(409,'The current workspace creation safety limit has been reached for this account.')
    created=create_organization(c,actor,body.name)
    org=created['organization_id']
    c.execute('INSERT INTO workspace_creation_requests(user_id,request_id,organization_id,requested_name,created_at) VALUES(?,?,?,?,?)',(actor,str(body.request_id),org,body.name,now()))
    select_workspace(c,actor,org)
    return {'organization_id':org,'reused':False}


def select_workspace(c,actor,organization_id):
    if not membership_role(c,actor,organization_id):
        raise HTTPException(404,'Workspace is unavailable for this account.')
    ensure_user(c,actor)
    stamp=now()
    c.execute('''INSERT INTO user_profiles(user_id,active_organization_id,created_at,updated_at)
        VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
        active_organization_id=excluded.active_organization_id,updated_at=excluded.updated_at''',
        (actor,organization_id,stamp,stamp))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,'WORKSPACE_SELECTED','organization:'+organization_id,'SUCCESS',organization_id,stamp))
    return {'organization_id':organization_id}
