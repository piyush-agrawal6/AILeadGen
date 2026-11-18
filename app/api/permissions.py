"""Small workspace roles and redacted operational audit; no new auth system."""
import json,re,uuid
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.foundation_schema import ready
from app.database.prospects import now
ROLES=('OWNER','ADMIN','OPERATOR','VIEWER')

def role(c,email,organization_id=None):
    if organization_id is None:
        from app.platform.context import organization
        organization_id=organization()
    from app.api.organization import membership_role,ROLE_ALIASES
    member=membership_role(c,email,organization_id)
    if member:return ROLE_ALIASES.get(member,'VIEWER')
    raise HTTPException(403,'Active workspace membership is required.')

def require_owner(c,email,organization_id=None):
    if role(c,email,organization_id)!='OWNER':raise HTTPException(403,'This action requires the workspace owner.')

def authorize(c,email,method,path,body,organization_id=None):
    r=role(c,email,organization_id)
    if method in ('GET','HEAD','OPTIONS'):return r
    # Selecting one's own already-authorized workspace is an account preference,
    # not a mutation of the current organization's data. Viewers must be able to
    # leave a workspace; the selection service rechecks target membership.
    if method=='PUT' and path=='/api/organization/active':return r
    if method=='PUT' and path=='/api/profile':return r
    # Responding to one's own invitation uses the signed account and token,
    # independent of a viewer role in a different currently selected workspace.
    if method=='POST' and path=='/api/organization/invitations/respond':return r
    # This creates an independent workspace owned by the authenticated account;
    # it does not mutate the currently selected organization's data.
    if method=='POST' and path=='/api/organization/workspaces':return r
    # Leaving a workspace, updating personal notification preferences, or contacting support
    # are allowed for any authenticated workspace member regardless of viewer role.
    if method=='POST' and path.startswith('/api/organization/workspaces/') and path.endswith('/leave'):return r
    if method=='PUT' and path=='/api/organization/notifications/preferences':return r
    if method=='POST' and path=='/api/help/support':return r
    if r=='VIEWER':raise HTTPException(403,'Viewer access is read-only.')
    nested=body.get('configuration') if isinstance(body.get('configuration'),dict) else {}
    owner_only=('/automation/controls' in path or '/foundation/roles' in path or '/foundation/duplicates/merge' in path or '/unsuppress' in path or '/deletions/campaign/' in path or '/deletions/scan/' in path or body.get('confirm_recontact') is True or nested.get('confirm_recontact') is True)
    if owner_only and r!='OWNER':raise HTTPException(403,'This action requires the workspace owner.')
    if r=='OPERATOR' and (path.startswith('/api/settings') or '/email/templates' in path or '/automation/targets' in path or '/automation/markets' in path):raise HTTPException(403,'Settings changes require an administrator.')
    return r

def begin_in(c,email,method,path,body,organization_id=None):
    """Apply the same RBAC/audit contract on a caller-owned transaction."""
    r=authorize(c,email,method,path,body,organization_id)
    critical=method not in ('GET','HEAD','OPTIONS') and any(x in path for x in ('/deletions/','/unsuppress','/workflow/schedules','/automation/controls','/settings','/foundation/roles','/foundation/duplicates','/foundation/reviews','/foundation/emergency','/email/templates','/organization/webhooks'))
    if body.get('confirm_recontact') is True:critical=True
    if not critical or not ready(c):return r,None
    key=str(uuid.uuid4());action='RECONTACT_CONFIRMED' if body.get('confirm_recontact') else method+' '+path
    c.execute("INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)",(key,email,action,path,'ATTEMPTED',organization_id,now()))
    return r,key


def begin(email,method,path,body,organization_id=None):
    from app.database.connection import db_session
    with db_session() as c:return begin_in(c,email,method,path,body,organization_id)


def finish(key,status):
    if not key:return
    from app.database.connection import db_session
    with db_session() as c:c.execute('UPDATE audit_log SET result=? WHERE id=?',('SUCCESS' if status<400 else 'REJECTED_HTTP_'+str(status),key))

class AuditCompletionMiddleware:
    """Finalize after response dependencies commit and release database locks."""
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        import asyncio,logging
        status=500
        async def observed(message):
            nonlocal status
            if message['type']=='http.response.start':status=message['status']
            await send(message)
        try:await self.app(scope,receive,observed)
        finally:
            key=scope.get('state',{}).get('audit_id')
            if key:
                try:await asyncio.to_thread(finish,key,status)
                except Exception:logging.getLogger(__name__).warning('Audit completion unavailable; attempted action remains recorded')
