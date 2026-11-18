"""Invitation lifecycle over existing verified Google identities and memberships.

Creation returns a raw capability once for deliberate owner sharing. Only its
digest is persisted. Delivery is not coupled to the prospect SMTP pipeline.
"""
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime,timedelta,timezone
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.api.organization import ensure_user,membership_role
from app.database.prospects import now
from app.platform.context import current,organization


class InviteCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email:str=Field(min_length=3,max_length=254)
    role:Literal['ADMIN','MEMBER','VIEWER']='MEMBER'
    expires_in_days:int=Field(default=7,ge=1,le=30)

    @field_validator('email')
    @classmethod
    def valid_email(cls,value):
        value=value.strip().lower()
        if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',value):
            raise ValueError('Enter a valid email address.')
        return value


class InviteRespond(BaseModel):
    model_config=ConfigDict(extra='forbid')
    token:str=Field(min_length=40,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    action:Literal['ACCEPT','REJECT']


class InvitationItem(BaseModel):
    id:UUID
    email:str
    role:Literal['ADMIN','MEMBER','VIEWER']
    status:Literal['PENDING','ACCEPTED','REJECTED','REVOKED','EXPIRED']
    invited_by:str
    created_at:str
    expires_at:str
    responded_at:str|None


class InvitationPage(BaseModel):
    items:list[InvitationItem]
    total:int
    page:int
    page_size:int
    can_invite_admin:bool


class InvitationCreated(BaseModel):
    id:UUID
    email:str
    role:Literal['ADMIN','MEMBER','VIEWER']
    status:Literal['PENDING']
    expires_at:str
    token:str
    delivery:Literal['MANUAL_SHARE','EMAIL_QUEUED']


class InvitationResult(BaseModel):
    status:Literal['ACCEPTED','REJECTED']
    organization_id:UUID


class InvitationRevoked(BaseModel):
    status:Literal['REVOKED']


class NotificationItem(BaseModel):
    id:UUID
    kind:Literal['INVITATION_ACCEPTED','INVITATION_REJECTED','INTENT_RADAR']
    entity_id:UUID
    created_at:str
    read_at:str|None


class NotificationPage(BaseModel):
    items:list[NotificationItem]


def _lock(c,org):
    if getattr(c,'backend',None)=='postgres':
        c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')


def _manager(c,org,actor,invite_role=None):
    role=membership_role(c,actor,org)
    if role not in ('OWNER','ADMIN'):
        raise HTTPException(403,'Managing invitations requires an owner or administrator.')
    if invite_role=='ADMIN' and role!='OWNER':
        raise HTTPException(403,'Only an owner may invite an administrator.')


def _audit(c,org,actor,action,key,details=None):
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),actor,action,'invitation:'+key,'SUCCESS',json.dumps(details or {}),org,now()))


def _expire(c,org):
    c.execute("UPDATE workspace_invitations SET status='EXPIRED',responded_at=? WHERE organization_id=? AND status='PENDING' AND expires_at<=?",(now(),org,now()))


def create(c,body:InviteCreate):
    from app.accounts.policy import require_work_identity
    require_work_identity(body.email)
    org=organization();actor=current().actor
    _manager(c,org,actor,body.role)
    _lock(c,org)
    _manager(c,org,actor,body.role)
    _expire(c,org)
    if membership_role(c,body.email,org):
        raise HTTPException(409,'This account is already an active workspace member.')
    if c.execute("SELECT 1 FROM workspace_invitations WHERE organization_id=? AND email=? AND status='PENDING'",(org,body.email)).fetchone():
        raise HTTPException(409,'A pending invitation already exists. Revoke it before creating another.')
    from app.config.settings import get_settings
    if c.execute("SELECT COUNT(*) FROM workspace_invitations WHERE organization_id=? AND status='PENDING'",(org,)).fetchone()[0]>=get_settings().heysow_pending_invitation_limit:
        raise HTTPException(409,'This workspace has reached its pending invitation limit.')
    from app.billing.usage import capacity_for_workspace
    seats=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND status='ACTIVE'",(org,)).fetchone()[0]
    pending=c.execute("SELECT COUNT(*) FROM workspace_invitations WHERE organization_id=? AND status='PENDING'",(org,)).fetchone()[0]
    capacity_for_workspace(c,org,'team_members',seats+pending)
    if get_settings().heysow_accounts_enabled and body.email not in get_settings().allowed_emails and not c.execute('SELECT 1 FROM users WHERE id=?',(body.email,)).fetchone():
        from app.accounts.policy import work_email
        try:work_email(body.email)
        except ValueError:raise HTTPException(422,'Invite a teammate using their company email address.') from None
    key=str(uuid.uuid4());token=secrets.token_urlsafe(32);stamp=now()
    expiry=(datetime.now(timezone.utc)+timedelta(days=body.expires_in_days)).isoformat()
    c.execute("INSERT INTO workspace_invitations(id,organization_id,email,role,token_hash,status,invited_by,created_at,expires_at) VALUES(?,?,?,?,?,'PENDING',?,?,?)",
        (key,org,body.email,body.role,hashlib.sha256(token.encode()).hexdigest(),actor,stamp,expiry))
    _audit(c,org,actor,'INVITATION_CREATED',key,{'role':body.role})
    delivery='MANUAL_SHARE'
    nid=None
    from app.notifications import transactional as mail, dispatch
    if get_settings().transactional_mail_enabled and mail.configured():
        company=c.execute('SELECT name FROM organizations WHERE id=?',(org,)).fetchone()[0]
        nid=mail.queue(c,body.email,'TEAM_INVITATION',key,{'token':token,'company':company},dedupe_key='team-invitation:'+key,expires_at=int(datetime.fromisoformat(expiry).timestamp()),organization_id=org)
        delivery='EMAIL_QUEUED'
    if nid:
        c.commit()
        try:dispatch.enqueue_notification(nid)
        except Exception:pass
    return {'id':key,'email':body.email,'role':body.role,'status':'PENDING','expires_at':expiry,'token':token,'delivery':delivery}


def resend(c,key:str):
    org=organization();actor=current().actor
    _manager(c,org,actor);_lock(c,org);_manager(c,org,actor)
    _expire(c,org)
    row=c.execute('SELECT id,email,role,status,expires_at FROM workspace_invitations WHERE id=? AND organization_id=?',(key,org)).fetchone()
    if not row:raise HTTPException(404,'Invitation not found.')
    _manager(c,org,actor,row['role'])
    if row['status'] not in ('PENDING','EXPIRED'):
        raise HTTPException(409,'Only pending or expired invitations can be resent.')
    if membership_role(c,row['email'],org):
        raise HTTPException(409,'This account is already an active workspace member.')
    if row['status']=='EXPIRED':
        from app.billing.usage import capacity_for_workspace
        seats=c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND status='ACTIVE'",(org,)).fetchone()[0]
        pending=c.execute("SELECT COUNT(*) FROM workspace_invitations WHERE organization_id=? AND status='PENDING'",(org,)).fetchone()[0]
        capacity_for_workspace(c,org,'team_members',seats+pending)
    token=secrets.token_urlsafe(32);stamp=now()
    expiry=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat()
    c.execute(
        "UPDATE workspace_invitations SET token_hash=?,status='PENDING',invited_by=?,expires_at=?,responded_at=NULL WHERE id=? AND organization_id=?",
        (hashlib.sha256(token.encode()).hexdigest(),actor,expiry,key,org),
    )
    _audit(c,org,actor,'INVITATION_RESENT',key,{'role':row['role']})
    delivery='MANUAL_SHARE'
    nid=None
    from app.config.settings import get_settings
    from app.notifications import transactional as mail, dispatch
    if get_settings().transactional_mail_enabled and mail.configured():
        company=c.execute('SELECT name FROM organizations WHERE id=?',(org,)).fetchone()[0]
        nid=mail.queue(c,row['email'],'TEAM_INVITATION',key,{'token':token,'company':company},dedupe_key=f'team-invitation-resend:{key}:{int(datetime.now(timezone.utc).timestamp())}',expires_at=int(datetime.fromisoformat(expiry).timestamp()),organization_id=org)
        delivery='EMAIL_QUEUED'
    if nid:
        c.commit()
        try:dispatch.enqueue_notification(nid)
        except Exception:pass
    return {'id':key,'email':row['email'],'role':row['role'],'status':'PENDING','expires_at':expiry,'token':token,'delivery':delivery}


def list_invitations(c,page=1):
    org=organization();actor=current().actor
    _manager(c,org,actor)
    _expire(c,org)
    rows=c.execute('SELECT id,email,role,status,invited_by,created_at,expires_at,responded_at FROM workspace_invitations WHERE organization_id=? ORDER BY created_at DESC,id LIMIT 25 OFFSET ?',(org,(page-1)*25)).fetchall()
    total=c.execute('SELECT COUNT(*) FROM workspace_invitations WHERE organization_id=?',(org,)).fetchone()[0]
    return {'items':[dict(r) for r in rows],'total':total,'page':page,'page_size':25,'can_invite_admin':membership_role(c,actor,org)=='OWNER'}


def revoke(c,key):
    org=organization();actor=current().actor
    _manager(c,org,actor);_lock(c,org);_manager(c,org,actor)
    row=c.execute('SELECT role,status,expires_at FROM workspace_invitations WHERE id=? AND organization_id=?',(key,org)).fetchone()
    if not row:raise HTTPException(404,'Invitation not found.')
    _manager(c,org,actor,row['role'])
    if row['status']!='PENDING' or row['expires_at']<=now():raise HTTPException(409,'This invitation is no longer pending.')
    c.execute("UPDATE workspace_invitations SET status='REVOKED',responded_at=? WHERE id=? AND organization_id=? AND status='PENDING'",(now(),key,org))
    _audit(c,org,actor,'INVITATION_REVOKED',key)
    return {'status':'REVOKED'}


def pending_for_account(c,actor,token):
    """Validate a named invitation without consuming it or granting membership."""
    digest=hashlib.sha256(token.encode()).hexdigest()
    row=c.execute('SELECT * FROM workspace_invitations WHERE token_hash=?',(digest,)).fetchone()
    if not row or row['email']!=actor.strip().lower():
        raise HTTPException(404,'Invitation is unavailable for this account.')
    return pending_by_id(c,actor,row['id'])

def pending_by_id(c,actor,key):
    from app.accounts.policy import require_work_identity
    require_work_identity(actor)
    row=c.execute('SELECT * FROM workspace_invitations WHERE id=? AND email=?',(key,actor.strip().lower())).fetchone()
    if not row:raise HTTPException(404,'Invitation is unavailable for this account.')
    org=row['organization_id'];_lock(c,org)
    row=c.execute('SELECT * FROM workspace_invitations WHERE id=? AND email=?',(key,actor.strip().lower())).fetchone()
    if row['status']!='PENDING':raise HTTPException(409,'This invitation has already been used or revoked.')
    if row['expires_at']<=now():raise HTTPException(410,'This invitation has expired.')
    active=c.execute("SELECT 1 FROM organizations WHERE id=? AND status='ACTIVE'",(org,)).fetchone()
    if not active:raise HTTPException(409,'This workspace is unavailable.')
    # A revoked/demoted inviter cannot retain a latent grant capability.
    from app.config.settings import get_settings
    settings=get_settings()
    if settings.heysow_customer_access_enabled and row['invited_by'] not in settings.allowed_emails:
        from app.platform.admission import access
        if not access(c,row['invited_by']):raise HTTPException(403,'The inviting account is unavailable.')
    _manager(c,org,row['invited_by'],row['role'])
    return row

def respond(c,actor,body:InviteRespond):
    # The signed authenticated account is the recipient authority; current
    # workspace selection is deliberately irrelevant. Do not accept an org ID.
    row=pending_for_account(c,actor,body.token)
    org=row['organization_id']
    stamp=now();status='ACCEPTED' if body.action=='ACCEPT' else 'REJECTED'
    if body.action=='ACCEPT':
        if membership_role(c,actor,org):raise HTTPException(409,'You are already an active member of this workspace.')
        ensure_user(c,actor)
        from app.billing.usage import capacity_for_workspace
        capacity_for_workspace(c,org,'team_members',c.execute("SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND status='ACTIVE'",(org,)).fetchone()[0])
        c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,?,'ACTIVE',?,?) ON CONFLICT(organization_id,user_id) DO UPDATE SET role=excluded.role,status='ACTIVE',updated_at=excluded.updated_at",
            (str(uuid.uuid4()),org,actor,row['role'],stamp,stamp))
    c.execute("UPDATE workspace_invitations SET status=?,responded_at=? WHERE id=? AND status='PENDING'",(status,stamp,row['id']))
    _audit(c,org,actor,'INVITATION_'+status,row['id'])
    c.execute('INSERT INTO workspace_notifications(id,organization_id,user_id,kind,entity_id,created_at) VALUES(?,?,?,?,?,?)',
        (str(uuid.uuid4()),org,row['invited_by'],'INVITATION_'+status,row['id'],stamp))
    # Never switch an account's existing workspace silently on acceptance.
    return {'status':status,'organization_id':org}


def notifications(c):
    org=organization();actor=current().actor
    from app.intent_radar.permissions import availability
    enabled=availability(c,org)['enabled']
    where='' if enabled else " AND kind<>'INTENT_RADAR'"
    return {'items':[dict(r) for r in c.execute('SELECT id,kind,entity_id,created_at,read_at FROM workspace_notifications WHERE organization_id=? AND user_id=?'+where+' ORDER BY created_at DESC,id LIMIT 50',(org,actor)).fetchall()]}
