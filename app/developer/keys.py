"""Hash-only random API keys. They bind a verified member to one fixed workspace."""
import hashlib,hmac,json,secrets,time,uuid
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from contextvars import ContextVar
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.prospects import now
from app.people.service import ctx
from app.api.organization import require_role,membership_role

Scope=Literal['companies:read','contacts:read','searches:read','searches:write','icps:read','lists:read','lists:write','tasks:read','tasks:write','enrichment:write','campaigns:read','mcp:use','intent:read']
SCOPES=['companies:read','contacts:read','searches:read','searches:write','icps:read','lists:read','lists:write','tasks:read','tasks:write','enrichment:write','campaigns:read','mcp:use','intent:read']
@dataclass(frozen=True)
class Grant:
    id:str
    organization_id:str
    actor:str
    scopes:tuple[str,...]
_grant=ContextVar('developer_credential',default=None)

class Create(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=100)
    scopes:list[Scope]=Field(min_length=1,max_length=12)
    lifetime_days:int=Field(90,ge=1,le=365)


def enabled():
    if not get_settings().heysow_developer_api_enabled:raise HTTPException(503,'The workspace developer API is disabled.')


def lock(c,organization_id):
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(organization_id,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')


def manager(c):
    enabled();context=ctx(c);require_role(c,context.actor,context.organization_id,('OWNER','ADMIN'))
    return context


def scope_access(c, organization_id, scopes):
    """Credentials cannot grant a product the workspace does not own."""
    from app.api.organization import products
    from app.intent_radar.permissions import availability
    leadgen = products(c, organization_id).get('LEADGEN', False)
    radar = availability(c, organization_id)['enabled']
    if set(scopes) - {'intent:read', 'mcp:use'} and not leadgen:
        raise HTTPException(404, 'Lead Engine is unavailable for these credential scopes.')
    if 'intent:read' in scopes and not radar:
        raise HTTPException(404, 'Intent Radar is unavailable for this workspace.')
    if not leadgen and not radar:
        raise HTTPException(404, 'No enabled product is available for this credential.')


def visible(row):
    result=dict(row);result.pop('token_hash',None);result['scopes']=json.loads(result.pop('scopes_json'));return result


def listing(c):
    context=manager(c)
    from app.intent_radar.permissions import availability
    from app.api.organization import products
    leadgen=products(c,context.organization_id).get('LEADGEN',False)
    radar=availability(c,context.organization_id)['enabled']
    available=[scope for scope in SCOPES if (scope=='mcp:use' and get_settings().heysow_mcp_enabled and (leadgen or radar)) or (scope=='intent:read' and radar) or (scope not in ('mcp:use','intent:read') and leadgen)]
    return {'items':[visible(row) for row in c.execute('SELECT * FROM workspace_api_keys WHERE organization_id=? ORDER BY created_at DESC LIMIT 100',(context.organization_id,)).fetchall()],'available_scopes':available,'rate_limit_per_minute':get_settings().developer_key_requests_per_minute}


def owned(c,key):
    context=manager(c);row=c.execute('SELECT * FROM workspace_api_keys WHERE id=? AND organization_id=?',(key,context.organization_id)).fetchone()
    if not row:raise HTTPException(404,'API key not found.')
    return dict(row)


def audit(c,key,action):
    context=manager(c);c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),context.actor,action,'api-key:'+key,'SUCCESS',context.organization_id,now()))


def create(c,body,rotated_from=None):
    if 'intent:read' in body.scopes:
        from app.intent_radar.permissions import context as radar_context
        radar_context(c)
    context=manager(c)
    lock(c,context.organization_id)
    scope_access(c,context.organization_id,body.scopes)
    if c.execute('SELECT COUNT(*) FROM workspace_api_keys WHERE organization_id=? AND revoked_at IS NULL AND expires_at>?',(context.organization_id,now())).fetchone()[0]>=20:raise HTTPException(429,'Revoke an unused API key before creating more.')
    key=str(uuid.uuid4());token='pbk_'+key+'.'+secrets.token_urlsafe(32);expires=(datetime.now(timezone.utc)+timedelta(days=body.lifetime_days)).isoformat()
    c.execute('INSERT INTO workspace_api_keys(id,organization_id,created_by,name,token_hash,scopes_json,created_at,expires_at,rotated_from) VALUES(?,?,?,?,?,?,?,?,?)',(key,context.organization_id,context.actor,body.name,hashlib.sha256(token.encode()).hexdigest(),json.dumps(sorted(set(body.scopes))),now(),expires,rotated_from));audit(c,key,'API_KEY_CREATED')
    return {'key':visible(owned(c,key)),'token':token,'shown_once':True}


def revoke(c,key):
    row=owned(c,key);c.execute('UPDATE workspace_api_keys SET revoked_at=COALESCE(revoked_at,?) WHERE id=? AND organization_id=?',(now(),key,row['organization_id']));audit(c,key,'API_KEY_REVOKED');return {'revoked':True}


def rotate(c,key):
    row=owned(c,key)
    if row['revoked_at'] or row['expires_at']<=now():raise HTTPException(409,'Create a new key; this credential has expired or was revoked.')
    revoke(c,key)
    result=create(c,Create(name=row['name'],scopes=json.loads(row['scopes_json'])),rotated_from=key)
    c.execute('UPDATE workspace_api_keys SET expires_at=? WHERE id=? AND organization_id=?',(row['expires_at'],result['key']['id'],row['organization_id']))
    result['key']=visible(owned(c,result['key']['id']));return result


def authenticate(c,authorization,*,consume=True):
    enabled()
    import re
    match=re.fullmatch(r'Bearer (pbk_([a-f0-9-]{36})\.[A-Za-z0-9_-]{43})',authorization or '')
    if not match:raise HTTPException(401,'A valid scoped API credential is required.')
    token,key=match.groups();row=c.execute('SELECT * FROM workspace_api_keys WHERE id=?',(key,)).fetchone()
    if not row or row['revoked_at'] or row['expires_at']<=now() or not hmac.compare_digest(row['token_hash'],hashlib.sha256(token.encode()).hexdigest()):raise HTTPException(401,'This API credential is invalid, expired or revoked.')
    from app.platform.context import workspace_scope
    with workspace_scope(c,row['created_by'],row['organization_id']):
        if not membership_role(c,row['created_by'],row['organization_id']):raise HTTPException(403,'Active workspace membership is required.')
        onboarded=c.execute("SELECT 1 FROM organization_onboarding WHERE organization_id=? AND status='COMPLETED'",(row['organization_id'],)).fetchone()
        if not onboarded:raise HTTPException(403,'Finish workspace onboarding before using the developer API.')
        scope_access(c,row['organization_id'],json.loads(row['scopes_json']))
    if not consume:return Grant(key,row['organization_id'],row['created_by'],tuple(json.loads(row['scopes_json'])))
    lock(c,row['organization_id'])
    current_row=c.execute('SELECT revoked_at,expires_at FROM workspace_api_keys WHERE id=?',(key,)).fetchone()
    if not current_row or current_row['revoked_at'] or current_row['expires_at']<=now():raise HTTPException(401,'This API credential is invalid, expired or revoked.')
    window=int(time.time())//60
    for bucket,limit in [('key:'+key,get_settings().developer_key_requests_per_minute),('workspace:'+row['organization_id'],get_settings().developer_workspace_requests_per_minute)]:
        counter=c.execute('SELECT requests FROM developer_request_windows WHERE owner_key=? AND window_start=?',(bucket,window)).fetchone()
        if counter and counter[0]>=limit:raise HTTPException(429,'API request limit reached. Retry after the current minute.')
        c.execute('INSERT INTO developer_request_windows(owner_key,window_start,requests) VALUES(?,?,1) ON CONFLICT(owner_key,window_start) DO UPDATE SET requests=developer_request_windows.requests+1',(bucket,window))
    from app.billing.usage import reserve
    with workspace_scope(c,row['created_by'],row['organization_id']):
        reserve(c,{'api_requests':1},str(uuid.uuid4()))
    c.execute('DELETE FROM developer_request_windows WHERE window_start<?',(window-10,));c.execute('UPDATE workspace_api_keys SET last_used_at=? WHERE id=? AND revoked_at IS NULL',(now(),key))
    return Grant(key,row['organization_id'],row['created_by'],tuple(json.loads(row['scopes_json'])))


def require(scope):
    grant=_grant.get()
    if grant is None or scope not in grant.scopes:raise HTTPException(403,'This API credential does not grant '+scope+'.')
    from app.platform.context import current
    context=current()
    if context.organization_id!=grant.organization_id or context.actor!=grant.actor:raise HTTPException(403,'The API credential does not match the verified workspace.')
    return grant


async def handle(request,call_next):
    from app.database.connection import db_session
    from app.platform.context import workspace_scope
    from fastapi.responses import JSONResponse
    try:
        # Reject URL credentials and browser workspace overrides; headers only.
        if any(key.casefold() in ('api_key','access_token','token') for key in request.query_params):raise HTTPException(401,'Provide API credentials only in the Authorization header.')
        if request.method not in ('GET','HEAD','OPTIONS'):
            body=bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body)>1048576:raise HTTPException(413,'Request exceeds the supported size.')
            request._body=bytes(body)
        with db_session() as c:grant=authenticate(c,request.headers.get('authorization',''))
        if request.url.path.rstrip('/')=='/api/v1/mcp':
            if not get_settings().heysow_mcp_enabled:raise HTTPException(503,'MCP is disabled.')
            if 'mcp:use' not in grant.scopes:raise HTTPException(403,'This API credential does not grant mcp:use.')
        marker=_grant.set(grant)
        try:
            with db_session() as c:
                with workspace_scope(c,grant.actor,grant.organization_id):
                    request.state.user_email=grant.actor;request.state.organization_id=grant.organization_id
                    response=await call_next(request)
        finally:_grant.reset(marker)
        response.headers['Cache-Control']='private, no-store';return response
    except HTTPException as exc:
        headers={'Cache-Control':'no-store'}
        if exc.status_code==401:headers['WWW-Authenticate']='Bearer'
        if exc.status_code==429:headers['Retry-After']=str(60-int(time.time())%60)
        return JSONResponse({'detail':exc.detail},status_code=exc.status_code,headers=headers)
