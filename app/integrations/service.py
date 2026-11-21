"""Shared customer connection ownership and encrypted credential lifecycle."""
import asyncio
import hashlib
import json
import secrets
import logging,re
import uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode,urlsplit
from fastapi import HTTPException
from app.api.organization import require_role,membership_role
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import organization,current
from app.platform.workspaces import require_management_enabled
from app.integrations.crypto import cipher,seal,open_envelope
from app.acquisition import sheets
from dataclasses import dataclass

PROVIDER='GOOGLE_SHEETS'
WRITE_SCOPE='https://www.googleapis.com/auth/spreadsheets'

@dataclass(frozen=True)
class ProviderSpec:
    provider:str=PROVIDER
    table:str='organization_integrations'
    states:str='integration_oauth_states'
    scope:str=sheets.SCOPE
    redirect_uri:str|None=None
    user_owned:bool=False
    exchange:object=None
    connected:object=None
    revoked:object=None
    authorize_url:object=None
    setup_check:object=None

SHEETS=ProviderSpec()

class DestinationLogFilter(logging.Filter):
    """Keep the transport outcome; receiver paths and sheet IDs are customer data."""
    def filter(self,record):
        message=record.getMessage()
        if message.startswith('HTTP Request: '):
            record.msg=re.sub(r'https?://\S+', '[destination]', message);record.args=()
        return True

logging.getLogger('httpx').addFilter(DestinationLogFilter())

def require_spec(spec):
    require_enabled()
    if spec.provider=='GMAIL' and not get_settings().heysow_customer_gmail_enabled:
        raise HTTPException(503,'Customer Gmail is not enabled.')


def require_enabled():
    require_management_enabled()
    if not get_settings().heysow_customer_integrations_enabled:
        raise HTTPException(503,'Customer integrations are not enabled.')


def reader(c):
    require_enabled();org=organization()
    if not membership_role(c,current().actor,org):raise HTTPException(403,'Active workspace membership is required.')
    if current().actor not in get_settings().allowed_emails:
        from app.platform.admission import access
        if not access(c,current().actor):raise HTTPException(403,'The customer account is unavailable.')
    return org

def manager(c):
    org=reader(c)
    require_role(c,current().actor,org,('OWNER','ADMIN'))
    return org


def lock(c):
    org=manager(c)
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM organizations WHERE id=? FOR UPDATE',(org,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    manager(c)
    return org


def owned(c,key,*,spec=SHEETS):
    require_spec(spec)
    reader(c)
    row=c.execute(f'SELECT * FROM {spec.table} WHERE id=? AND organization_id=? AND provider=?',(key,organization(),spec.provider)).fetchone()
    if not row:raise HTTPException(404,'Connection not found.')
    if spec.user_owned and row['owner_user_id']!=current().actor:raise HTTPException(404,'Connection not found.')
    return dict(row)


def context(row,purpose):
    return {'organization_id':row['organization_id'],'connection_id':row['id'],'provider':row['provider'],'purpose':purpose}


def view(row):
    return {name:row[name] for name in ('id','provider','status','revision','connected_by','connected_at','last_success_at','last_error_code')}|{'scopes':json.loads(row['scopes_json'])}


def audit(c,key,action):
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',
        (str(uuid.uuid4()),current().actor,action,'integration:'+key,'SUCCESS',organization(),now()))


def configured():
    from app.acquisition.config import settings
    config=settings()
    try:cipher()
    except HTTPException:return False
    return bool(config.google_id and config.google_secret.get_secret_value())


def listing(c):
    org=reader(c)
    rows=c.execute('SELECT * FROM organization_integrations WHERE organization_id=? ORDER BY provider LIMIT 25',(org,)).fetchall()
    from app.acquisition.config import settings
    from app.acquisition.preferences import load
    enabled=load(c).get('enabled',{})
    importing=settings().enable_sheets and settings().enable_import and enabled.get('sheets',True) and enabled.get('import',True)
    return {'google_sheets_import_enabled':importing,'items':[view(dict(row)) for row in rows],'can_manage':membership_role(c,current().actor,org) in ('OWNER','ADMIN'),'google_sheets_configured':configured(),'google_sheets_scope':sheets.SCOPE}


def authorize(c,*,write=False,spec=SHEETS):
    from app.acquisition.config import settings
    require_spec(spec);org=manager(c);cipher();config=settings()
    if not (spec.setup_check or configured)():raise HTTPException(503,'The connection needs server configuration.')
    redirect_uri=spec.redirect_uri if spec.redirect_uri is not None else config.sheets_redirect_uri
    redirect=urlsplit(redirect_uri)
    if redirect.scheme!='https' and not (get_settings().app_env!='production' and redirect.scheme=='http' and redirect.hostname in ('localhost','127.0.0.1')):
        raise HTTPException(503,'Google Sheets needs a secure approved callback URL.')
    lock(c);actor=current().actor;scope=WRITE_SCOPE if write else spec.scope
    cutoff=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    if c.execute(f'SELECT COUNT(*) FROM {spec.states} WHERE organization_id=? AND created_at>=?',(org,cutoff)).fetchone()[0]>=10:
        raise HTTPException(429,'This workspace has reached its connection-attempt limit for this hour.')
    existing=c.execute(f'SELECT * FROM {spec.table} WHERE organization_id=? AND provider=?',(org,spec.provider)).fetchone()
    if existing and spec.user_owned and existing['owner_user_id']!=actor:raise HTTPException(403,'This mailbox belongs to another workspace member.')
    key=existing['id'] if existing else str(uuid.uuid4());revision=existing['revision']+1 if existing else 1;stamp=now()
    owner_column=',owner_user_id' if spec.user_owned else '';owner_value=',?' if spec.user_owned else ''
    c.execute(f'''INSERT INTO {spec.table}(id,organization_id,provider,revision,created_at,updated_at{owner_column})
        VALUES(?,?,?,?,?,?{owner_value}) ON CONFLICT(organization_id,provider) DO UPDATE SET
        revision=excluded.revision,status=CASE WHEN {spec.table}.status='DISCONNECTED' THEN 'NOT_CONNECTED' ELSE {spec.table}.status END,
        refresh_lease_id=NULL,refresh_lease_until=NULL,updated_at=excluded.updated_at''',(key,org,spec.provider,revision,stamp,stamp)+((actor,) if spec.user_owned else ()))
    c.execute(f"UPDATE {spec.states} SET status='CANCELLED',verifier_ciphertext=NULL WHERE organization_id=? AND connection_id=? AND status='PENDING'",(org,key))
    row=owned(c,key,spec=spec);state='hsw_'+secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
    import base64
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    c.execute(f"INSERT INTO {spec.states}(state_hash,organization_id,connection_id,actor,connection_revision,verifier_ciphertext,status,expires_at,created_at,requested_scope) VALUES(?,?,?,?,?,?,'PENDING',?,?,?)",
        (hashlib.sha256(state.encode()).hexdigest(),org,key,actor,revision,seal({'verifier':verifier},**context(row,'OAUTH_STATE')),(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),stamp,scope))
    audit(c,key,'INTEGRATION_AUTHORIZATION_STARTED')
    if spec.authorize_url:return {'authorization_url':spec.authorize_url(state,scope),'scope':scope}
    return {'authorization_url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':config.google_id,'redirect_uri':redirect_uri,'response_type':'code','scope':scope,'access_type':'offline','prompt':'consent','state':state,'code_challenge':challenge,'code_challenge_method':'S256'}),'scope':scope}


def token_value(result,previous=None,*,expected_scope=None,spec=SHEETS):
    if not isinstance(result,dict):raise HTTPException(409,'Google Sheets returned an invalid connection response.')
    previous=previous or {}
    scopes=result.get('scope',previous.get('scope',''))
    expected_scope=expected_scope or previous.get('scope',spec.scope)
    accepted=(sheets.SCOPE,WRITE_SCOPE) if spec.provider==PROVIDER else (spec.scope,)
    if expected_scope not in accepted or not isinstance(scopes,str) or set(scopes.split())!=set(expected_scope.split()):
        raise HTTPException(409,'Google Sheets must grant exactly the permission explicitly requested for this connection.')
    access=result.get('access_token');refresh=result.get('refresh_token') or previous.get('refresh_token')
    if not isinstance(access,str) or not access or len(access)>8192 or not isinstance(refresh,str) or not refresh or len(refresh)>8192:
        raise HTTPException(409,'Google Sheets needs a new read-only connection with offline access.')
    try:ttl=int(result.get('expires_in',3600))
    except (ValueError,TypeError,OverflowError):raise HTTPException(409,'Google Sheets returned an invalid token lifetime.') from None
    if ttl<60 or ttl>86400:raise HTTPException(409,'Google Sheets returned an invalid token lifetime.')
    value={'access_token':access,'refresh_token':refresh,'scope':expected_scope,'expires_at':(datetime.now(timezone.utc)+timedelta(seconds=ttl-30)).isoformat()}
    if spec.user_owned:value['identity']=previous.get('identity') if previous else result.get('identity')
    if spec.provider=='HUBSPOT':
        portal=result.get('portal_id')
        if not isinstance(portal,str) or not portal.isascii() or not portal.isdecimal() or previous and portal!=previous.get('portal_id'):raise HTTPException(409,'The CRM portal identity changed.')
        value['portal_id']=portal
    return value


async def exchange(payload,*,spec=SHEETS):
    try:return await asyncio.wait_for((spec.exchange or sheets.token_request)(payload),timeout=25)
    except TimeoutError:raise sheets.SheetsUnavailable('Connection request timed out.') from None


def provider_error(c,row,code,lease=None,reauth=False,*,spec=SHEETS):
    changed=c.execute(f'''UPDATE {spec.table} SET last_error_code=?,updated_at=?,
        status=CASE WHEN ?=1 THEN 'REAUTH_REQUIRED' ELSE status END,
        credentials_ciphertext=CASE WHEN ?=1 THEN NULL ELSE credentials_ciphertext END,
        refresh_lease_id=CASE WHEN CAST(? AS TEXT) IS NULL THEN NULL ELSE refresh_lease_id END,
        refresh_lease_until=CASE WHEN CAST(? AS TEXT) IS NULL THEN NULL ELSE refresh_lease_until END
        WHERE id=? AND organization_id=? AND revision=? AND status<>'DISCONNECTED' AND (refresh_lease_id=? OR CAST(? AS TEXT) IS NULL)''',
        (code,now(),int(reauth),int(reauth),lease,lease,row['id'],organization(),row['revision'],lease,lease)).rowcount
    if changed and reauth and spec.revoked:spec.revoked(c,row)
    c.commit()


async def connect(c,state,code,*,spec=SHEETS):
    require_spec(spec);manager(c)
    digest=hashlib.sha256(state.encode()).hexdigest()
    claim=c.execute(f"SELECT * FROM {spec.states} WHERE state_hash=? AND organization_id=? AND actor=? AND status='PENDING' AND expires_at>?",(digest,organization(),current().actor,now())).fetchone()
    if not claim:raise HTTPException(409,'Connection request expired or is unavailable for this account and workspace.')
    row=owned(c,claim['connection_id'],spec=spec)
    if row['revision']!=claim['connection_revision']:raise HTTPException(409,'A newer connection request replaced this one.')
    verifier=open_envelope(claim['verifier_ciphertext'],**context(row,'OAUTH_STATE'))['verifier']
    changed=c.execute(f"UPDATE {spec.states} SET status='CONSUMED',verifier_ciphertext=NULL WHERE state_hash=? AND organization_id=? AND actor=? AND status='PENDING' AND expires_at>?",(digest,organization(),current().actor,now())).rowcount
    if changed!=1:raise HTTPException(409,'This connection request has already been used.')
    c.commit()
    from app.acquisition.config import settings
    try:
        result=await exchange({'grant_type':'authorization_code','code':code,'redirect_uri':spec.redirect_uri if spec.redirect_uri is not None else settings().sheets_redirect_uri,'code_verifier':verifier},spec=spec)
        value=token_value(result,expected_scope=claim['requested_scope'],spec=spec)
    except sheets.SheetsUnavailable:
        provider_error(c,row,'OAUTH_UNAVAILABLE',spec=spec)
        raise HTTPException(503,'Google Sheets could not connect. Start a new connection request and retry.') from None
    except HTTPException:
        provider_error(c,row,'OAUTH_RESPONSE_REJECTED',spec=spec)
        raise
    require_spec(spec);lock(c);latest=owned(c,row['id'],spec=spec)
    if latest['revision']!=row['revision'] or latest['status']=='DISCONNECTED':raise HTTPException(409,'Connection was cancelled or replaced before completion.')
    if spec.connected:spec.connected(c,latest,value)
    c.execute(f"UPDATE {spec.table} SET status='CONNECTED',credentials_ciphertext=?,scopes_json=?,connected_by=?,connected_at=?,last_error_code=NULL,updated_at=? WHERE id=? AND organization_id=? AND revision=?",
        (seal(value,**context(row,'CREDENTIALS')),json.dumps(value['scope'].split()),current().actor,now(),now(),row['id'],organization(),row['revision']))
    audit(c,row['id'],'INTEGRATION_CONNECTED')
    return view(owned(c,row['id'],spec=spec))


def disconnect(c,key,*,spec=SHEETS):
    require_spec(spec);lock(c);row=owned(c,key,spec=spec)
    if row['status']=='DISCONNECTED':return {'status':'DISCONNECTED','provider_access_revoked':False}
    c.execute(f"UPDATE {spec.table} SET status='DISCONNECTED',credentials_ciphertext=NULL,revision=revision+1,refresh_lease_id=NULL,refresh_lease_until=NULL,last_error_code=NULL,updated_at=? WHERE id=? AND organization_id=?",(now(),key,organization()))
    c.execute(f"UPDATE {spec.states} SET status='CANCELLED',verifier_ciphertext=NULL WHERE connection_id=? AND organization_id=? AND status='PENDING'",(key,organization()))
    audit(c,key,'INTEGRATION_DISCONNECTED')
    # Revoking a Google grant could also disrupt the existing internal connection
    # for the same Google client/account. Remove local authority and secrets only.
    return {'status':'DISCONNECTED','provider_access_revoked':False}


async def access_token(c,key,*,spec=SHEETS):
    require_spec(spec);manager(c);row=owned(c,key,spec=spec)
    if row['status']!='CONNECTED' or not row['credentials_ciphertext']:raise HTTPException(409,'Connect Google Sheets for this workspace first.')
    value=open_envelope(row['credentials_ciphertext'],**context(row,'CREDENTIALS'))
    if not isinstance(value.get('access_token'),str) or not isinstance(value.get('refresh_token'),str):raise HTTPException(409,'This workspace connection needs to be reconnected.')
    try:
        expires=datetime.fromisoformat(value['expires_at'])
        if expires.tzinfo is None or expires.utcoffset() is None:raise ValueError()
    except (ValueError,KeyError,TypeError):raise HTTPException(409,'This workspace connection needs to be reconnected.') from None
    if expires>datetime.now(timezone.utc):return value['access_token'],row['revision']
    lease=str(uuid.uuid4());stamp=now()
    updated=c.execute(f'''UPDATE {spec.table} SET refresh_lease_id=?,refresh_lease_until=? WHERE id=? AND organization_id=? AND revision=? AND status='CONNECTED'
        AND (refresh_lease_id IS NULL OR refresh_lease_until<=?)''',(lease,(datetime.now(timezone.utc)+timedelta(seconds=45)).isoformat(),key,organization(),row['revision'],stamp)).rowcount
    if updated!=1:raise HTTPException(429,'This connection is refreshing. Retry shortly.')
    c.commit()
    try:refreshed=token_value(await exchange({'grant_type':'refresh_token','refresh_token':value['refresh_token']},spec=spec),value,spec=spec)
    except sheets.SheetsUnavailable:
        provider_error(c,row,'TOKEN_REFRESH_UNAVAILABLE',lease,spec=spec)
        raise HTTPException(503,'Google Sheets is temporarily unavailable. Retry or reconnect.') from None
    except HTTPException:
        provider_error(c,row,'TOKEN_RESPONSE_REJECTED',lease,reauth=True,spec=spec)
        raise
    require_spec(spec);manager(c);owned(c,key,spec=spec)
    changed=c.execute(f"UPDATE {spec.table} SET credentials_ciphertext=?,refresh_lease_id=NULL,refresh_lease_until=NULL,last_error_code=NULL,updated_at=? WHERE id=? AND organization_id=? AND revision=? AND status='CONNECTED' AND refresh_lease_id=?",
        (seal(refreshed,**context(row,'CREDENTIALS')),now(),key,organization(),row['revision'],lease)).rowcount
    if changed!=1:raise HTTPException(409,'Connection was cancelled or replaced during refresh.')
    c.commit()
    return refreshed['access_token'],row['revision']
