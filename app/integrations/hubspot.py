"""Workspace CRM connection. Portal identity is verified by HubSpot before saving or rotating credentials."""
import json
import re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from urllib.parse import urlencode
from fastapi import HTTPException
import httpx
from app.acquisition.sheets import SheetsUnavailable
from app.config.settings import get_settings
from app.database.prospects import now
from app.integrations import service
from app.intent_radar.permissions import context

CALLBACK='https://app.planebyte.com/intent-radar/integrations/hubspot/callback'
SCOPES='oauth crm.objects.contacts.read crm.objects.contacts.write crm.objects.companies.read crm.objects.companies.write crm.objects.deals.read crm.objects.deals.write'

def enabled(c):
    ctx=context(c,True,True);service.manager(c);s=get_settings()
    if not s.radar_hubspot_enabled or (s.app_env=='production' and ctx.organization_id not in {w.strip() for w in s.radar_hubspot_workspaces.split(',')}):raise HTTPException(403,'CRM connections are restricted to approved workspaces.')
    return ctx

def configured():
    s=get_settings();service.cipher()
    return bool(s.radar_hubspot_client_id and s.radar_hubspot_client_secret.get_secret_value() and s.radar_hubspot_redirect_uri==CALLBACK)

def authorization_url(state,scope):
    return 'https://app.hubspot.com/oauth/authorize?'+urlencode({'client_id':get_settings().radar_hubspot_client_id,'redirect_uri':CALLBACK,'state':state,'scope':scope})

async def token_request(path,data):
    if get_settings().app_env=='test':raise SheetsUnavailable('External CRM access is disabled in offline tests.')
    if path not in ('token','token/introspect'):raise ValueError('Unsupported OAuth operation')
    try:
        async with httpx.AsyncClient(timeout=8,trust_env=False,follow_redirects=False) as client:
            async with client.stream('POST','https://api.hubapi.com/oauth/v3/'+path,data=data) as r:
                if r.status_code in (400,401,403):raise HTTPException(409,'HubSpot authorization was rejected. Reconnect to continue.')
                if r.status_code!=200:raise SheetsUnavailable('HubSpot is temporarily unavailable.')
                raw=bytearray()
                async for chunk in r.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>65536:raise ValueError()
                body=json.loads(raw)
                if not isinstance(body,dict):raise ValueError()
                return body
    except (httpx.HTTPError,ValueError):raise SheetsUnavailable('HubSpot could not verify the request.') from None

async def exchange(payload):
    s=get_settings();client={'client_id':s.radar_hubspot_client_id,'client_secret':s.radar_hubspot_client_secret.get_secret_value()}
    data={k:v for k,v in payload.items() if k in ('grant_type','code','refresh_token','redirect_uri')}
    result=await token_request('token',client|data);access=result.get('access_token')
    if not isinstance(access,str) or not 1<=len(access)<=8192:raise HTTPException(409,'HubSpot returned an invalid token.')
    check=await token_request('token/introspect',client|{'access_token':access,'token_type_hint':'access_token'})
    portal=check.get('hub_id');scopes=check.get('scopes')
    if (check.get('active') is not True or check.get('app_id')!=62975250 or check.get('client_id')!=client['client_id'] or type(portal) is not int or portal<=0 or result.get('hub_id')!=portal or not isinstance(scopes,list) or not all(isinstance(v,str) for v in scopes) or set(scopes)!=set(SCOPES.split())):raise HTTPException(409,'CRM portal, application or granted scopes could not be verified.')
    return result|{'scope':' '.join(scopes),'portal_id':str(portal)}

def connected(c,row,value):
    if row['portal_id'] and row['portal_id']!=value['portal_id']:raise HTTPException(409,'Reconnect the original HubSpot portal.')
    c.execute('UPDATE radar_crm_connections SET portal_id=?,last_success_at=? WHERE id=? AND organization_id=?',(value['portal_id'],now(),row['id'],row['organization_id']))

def spec():
    return service.ProviderSpec(provider='HUBSPOT',table='radar_crm_connections',states='radar_crm_oauth_states',scope=SCOPES,redirect_uri=CALLBACK,authorize_url=authorization_url,setup_check=configured,exchange=exchange,connected=connected)

def status(c):
    ctx=enabled(c);row=c.execute("SELECT * FROM radar_crm_connections WHERE organization_id=? AND provider='HUBSPOT'",(ctx.organization_id,)).fetchone()
    return {'configured':configured(),'connection':service.view(dict(row))|{'portal_id':row['portal_id']} if row else None}


class Match(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    kind:Literal['contacts','companies','deals']
    value:str=Field(min_length=1,max_length=254)

async def crm_json(method,path,token,body=None):
    if not re.fullmatch(r'/crm/v3/(pipelines/deals|objects/(contacts|companies|deals)/(search|[1-9][0-9]{0,20}))',path):raise ValueError('Unsupported CRM path')
    if get_settings().app_env=='test':raise HTTPException(503,'CRM network access is disabled in offline tests.')
    try:
        async with httpx.AsyncClient(timeout=10,trust_env=False,follow_redirects=False) as client:
            async with client.stream(method,'https://api.hubapi.com'+path,headers={'Authorization':'Bearer '+token},json=body) as r:
                if r.status_code in (401,403):raise HTTPException(409,'HubSpot denied access. Check the installed grant and reconnect.')
                if r.status_code==404:raise HTTPException(404,'CRM record not found.')
                if r.status_code==429:raise HTTPException(429,'HubSpot rate limit reached. Retry later.')
                if r.status_code!=200:raise HTTPException(503,'HubSpot is unavailable.')
                raw=bytearray()
                async for part in r.aiter_bytes():
                    raw.extend(part)
                    if len(raw)>256000:raise ValueError()
                data=json.loads(raw)
                if not isinstance(data,dict):raise ValueError()
                return data
    except (httpx.HTTPError,ValueError):raise HTTPException(503,'Could not read a bounded HubSpot response.') from None

async def read(c,key,method,path,body=None):
    enabled(c);token,rev=await service.access_token(c,key,spec=spec());c.commit()
    result=await crm_json(method,path,token,body);enabled(c);service.lock(c);row=service.owned(c,key,spec=spec())
    if row['status']!='CONNECTED' or row['revision']!=rev:raise HTTPException(409,'Connection changed. Refresh the workspace.')
    c.execute('UPDATE radar_crm_connections SET last_success_at=?,last_error_code=NULL WHERE organization_id=? AND id=? AND revision=?',(now(),row['organization_id'],key,rev));return result

async def pipelines(c,key):
    data=await read(c,key,'GET','/crm/v3/pipelines/deals');return {'items':[{'id':str(p['id']),'label':str(p['label'])[:160],'stages':[{'id':str(s['id']),'label':str(s['label'])[:160]} for s in p.get('stages',[])[:100] if not s.get('archived')]} for p in data.get('results',[])[:100] if not p.get('archived')]}

async def match(c,key,query):
    field={'contacts':'email','companies':'domain','deals':'hs_object_id'}[query.kind];v=query.value.lower()
    if field=='email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v) or field=='domain' and not re.fullmatch(r'(?:[a-z0-9-]+\.)+[a-z]{2,63}',v) or field=='hs_object_id' and not re.fullmatch(r'[1-9][0-9]{0,20}',v):raise HTTPException(422,'Provide an exact known identifier.')
    fields={'contacts':['email','firstname','lastname'],'companies':['domain','name'],'deals':['dealname','pipeline','dealstage']}[query.kind];data=await read(c,key,'POST',f'/crm/v3/objects/{query.kind}/search',{'filterGroups':[{'filters':[{'propertyName':field,'operator':'EQ','value':v}]}],'properties':fields,'limit':5})
    return {'items':[{'id':str(item['id']),'properties':{k:str(item['properties'].get(k) or '')[:300] for k in fields}} for item in data.get('results',[])[:5]],'more':bool(data.get('paging',{}).get('next'))}
