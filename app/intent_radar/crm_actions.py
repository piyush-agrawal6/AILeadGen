"""Single-record CRM approval. Once a write may have left the process, only GET reconciliation is allowed."""
import hashlib,json,re,uuid
from datetime import datetime,timedelta,timezone
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.config.settings import get_settings
from app.database.prospects import now
from app.integrations import hubspot,service
from app.intent_radar import actions
from app.developer.keys import lock

class Draft(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    opportunity_id:uuid.UUID
    connection_id:uuid.UUID
    request_id:uuid.UUID
    kind:Literal['companies','contacts']
    identifier:str=Field(min_length=1,max_length=254)
    fields:dict[str,str]=Field(max_length=3)
    operation:Literal['create','link','update']

def authority(c,key):
    ctx=actions.scope(c,True);hubspot.enabled(c);row=service.owned(c,key,spec=hubspot.spec());portal=row['portal_id']
    if row['status']!='CONNECTED' or not portal or portal not in {p.strip() for p in get_settings().radar_hubspot_write_portals.split(',')}:raise HTTPException(403,'This portal is not approved for Action Center operations.')
    return ctx,row

def fields(body):
    allowed={'companies':{'name','city'},'contacts':{'firstname','lastname'}}[body.kind]
    if set(body.fields)-allowed or any(not v.strip() or len(v)>160 or any(ord(x)<32 for x in v) for v in body.fields.values()):raise HTTPException(422,'Supply only supported, nonempty CRM properties.')
    if body.operation=='link' and body.fields or body.operation=='update' and not body.fields:raise HTTPException(422,'Choose fields only for a create or update.')
    if body.kind=='companies' and body.operation=='create' and not body.fields.get('name'):raise HTTPException(422,'Provide the verified company name.')
    return {k:v.strip() for k,v in body.fields.items()}

def receipt(c,org,key):
    r=c.execute('SELECT * FROM radar_destination_receipts WHERE organization_id=? AND action_id=?',(org,key)).fetchone()
    if not r:raise HTTPException(404,'CRM action not found.')
    return dict(r)

def result(c,org,key):
    r=receipt(c,org,key);return {'id':key,'execution':r['state'],'external_id':r['external_id'],'error':r['error_code'],'attempts':r['attempts']}

async def observe(c,key,kind,identifier,operation,values):
    hits=await hubspot.match(c,key,hubspot.Match(kind=kind,value=identifier));items=hits['items']
    if hits['more'] or len(items)>1:raise HTTPException(409,'Ambiguous CRM match. No operation permitted.')
    if bool(items)!=(operation!='create'):raise HTTPException(409,'The CRM match differs from the requested operation. Review again.')
    if not items:return None
    obj=items[0];rid=str(obj['id']);identity='domain' if kind=='companies' else 'email'
    if not re.fullmatch('[1-9][0-9]{0,20}',rid):raise HTTPException(502,'Invalid CRM record identity.')
    token,rev=await service.access_token(c,key,spec=hubspot.spec());props=sorted({identity,*values})
    data=await hubspot.crm_json('GET',f'/crm/objects/2026-09/{kind}/{rid}',token,params={'properties':','.join(props)})
    _,conn=authority(c,key)
    if conn['revision']!=rev or str(data.get('id'))!=rid or data.get('archived') or data.get('properties',{}).get(identity,'').lower()!=identifier:raise HTTPException(409,'CRM target changed before review.')
    return {'id':rid,'properties':{k:data['properties'].get(k) for k in props}}

async def prepare(c,body):
    key=str(body.connection_id);ctx,conn=authority(c,key);org=ctx.organization_id;op=actions.source(c,str(body.opportunity_id));values=fields(body);ident=body.identifier.strip().lower();match=await observe(c,key,body.kind,ident,body.operation,values)
    ctx,latest=authority(c,key);lock(c,org)
    if latest['revision']!=conn['revision']:raise HTTPException(409,'Connection changed during review.')
    field='domain' if body.kind=='companies' else 'email';payload={'title':f'{body.operation.title()} HubSpot {body.kind}', 'operation':body.operation,'kind':body.kind,'identifier':ident,'match':match,'fields':({field:ident}|values if body.operation=='create' else values),'connection_id':key,'connection_revision':conn['revision'],'portal_id':conn['portal_id']}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'));digest=hashlib.sha256(json.dumps([org,ctx.actor,op['id'],op['revision'],raw]).encode()).hexdigest();req=str(body.request_id);old=c.execute('SELECT id,digest,created_by FROM radar_actions WHERE organization_id=? AND request_id=?',(org,req)).fetchone()
    if old:
        if old['digest']!=digest or old['created_by']!=ctx.actor:raise HTTPException(409,'Request already used for a different review.')
        return actions.view(actions.owned(c,org,old['id']))
    stamp=now();cutoff=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    if c.execute("SELECT count(*) FROM radar_actions WHERE organization_id=? AND kind='hubspot' AND created_at>=?",(org,cutoff)).fetchone()[0]>=20:raise HTTPException(429,'Workspace CRM review limit reached.')
    aid=str(uuid.uuid4());c.execute("INSERT INTO radar_actions(id,organization_id,request_id,created_by,opportunity_id,kind,payload_json,digest,opportunity_revision,status,created_at,updated_at) VALUES(?,?,?,?,?,'hubspot',?,?,?,'NEEDS_REVIEW',?,?)",(aid,org,req,ctx.actor,op['id'],raw,digest,op['revision'],stamp,stamp));target=hashlib.sha256(f'{body.kind}:{ident}'.encode()).hexdigest();c.execute("INSERT INTO radar_destination_receipts(organization_id,action_id,connection_id,portal_id,connection_revision,target_key,state,updated_at) VALUES(?,?,?,?,?,?,'REVIEW',?)",(org,aid,key,conn['portal_id'],conn['revision'],target,stamp));actions.audit(c,ctx,aid,'PREPARED');return actions.view(actions.owned(c,org,aid))

def owned(c,aid):
    ctx=actions.scope(c,True);org=ctx.organization_id;row=actions.owned(c,org,aid)
    if row['kind']!='hubspot' or row['created_by']!=ctx.actor:raise HTTPException(404,'CRM action not found.')
    r=receipt(c,org,aid);_,conn=authority(c,r['connection_id'])
    if conn['revision']!=r['connection_revision'] or conn['portal_id']!=r['portal_id']:raise HTTPException(409,'Portal authorization changed; create a new review.')
    op=actions.source(c,row['opportunity_id'])
    if op['revision']!=row['opportunity_revision']:raise HTTPException(409,'Opportunity changed. Review again.')
    return ctx,row,r,json.loads(row['payload_json'])

async def approve(c,aid,approval):
    ctx,row,r,p=owned(c,aid);org=ctx.organization_id;key=r['connection_id'];operation=p['operation']
    if approval.digest!=row['digest']:raise HTTPException(409,'The exact preview must be approved.')
    if r['state']=='EXECUTING' and datetime.fromisoformat(r['updated_at'])<datetime.now(timezone.utc)-timedelta(minutes=2):
        c.execute("UPDATE radar_destination_receipts SET state='UNCERTAIN',error_code='WORKER_INTERRUPTED',updated_at=? WHERE organization_id=? AND action_id=? AND state='EXECUTING' AND updated_at=?",(now(),org,aid,r['updated_at']));return result(c,org,aid)
    if r['state'] in ('CONFIRMED','UNCERTAIN','EXECUTING','REVIEW_AGAIN','CANCELED'):return result(c,org,aid)
    if r['state']=='REVIEW':
        if (datetime.now(timezone.utc)-datetime.fromisoformat(row['created_at'])).total_seconds()>900:raise HTTPException(409,'Review expired.')
        observed=await observe(c,key,p['kind'],p['identifier'],operation,p['fields'])
        if observed!=p['match']:raise HTTPException(409,'Target properties changed; review again.')
    token,revision=await service.access_token(c,key,spec=hubspot.spec());lock(c,org);ctx,row,r,p=owned(c,aid)
    if revision!=r['connection_revision']:raise HTTPException(409,'Token authority changed.')
    path='/crm/objects/2026-09/'+p['kind'];stamp=now()
    if r['state']=='REVIEW':
        collision=c.execute("SELECT 1 FROM radar_destination_receipts WHERE connection_id=? AND organization_id=? AND action_id<>? AND target_key=? AND (state IN ('EXECUTING','VERIFY','UNCERTAIN') OR (state='CONFIRMED' AND ?='create')) LIMIT 1",(key,org,aid,r['target_key'],operation)).fetchone()
        if collision:raise HTTPException(409,'This identifier has a pending or verified action. Reconcile it before creating another.')
        changed=c.execute("UPDATE radar_destination_receipts SET state='EXECUTING',attempts=attempts+1,updated_at=? WHERE organization_id=? AND action_id=? AND state='REVIEW'",(stamp,org,aid)).rowcount
        if not changed:raise HTTPException(409,'Another execution holds this action.')
        c.execute('UPDATE radar_actions SET approved_by=?,approved_at=?,updated_at=? WHERE id=? AND organization_id=?',(ctx.actor,stamp,stamp,aid,org));actions.audit(c,ctx,aid,'APPROVED');c.commit()
        try:
            if operation=='link':external=p['match']['id']
            else:
                response=await hubspot.crm_json('POST' if operation=='create' else 'PATCH',path if operation=='create' else path+'/'+p['match']['id'],token,{'properties':p['fields']});external=str(response.get('id',''))
            if not re.fullmatch('[1-9][0-9]{0,20}',external) or operation!='create' and external!=p['match']['id']:raise ValueError('Invalid record identity')
        except Exception:
            c.execute("UPDATE radar_destination_receipts SET state='UNCERTAIN',error_code='PROVIDER_WRITE_UNCONFIRMED',updated_at=? WHERE organization_id=? AND action_id=? AND state='EXECUTING'",(now(),org,aid));c.commit();return result(c,org,aid)
        c.execute("UPDATE radar_destination_receipts SET state='VERIFY',external_id=?,updated_at=? WHERE organization_id=? AND action_id=? AND state='EXECUTING'",(external,now(),org,aid));c.commit()
    elif r['state']=='VERIFY':external=r['external_id'];c.commit()
    else:return result(c,org,aid)
    expected=p['fields']|{('domain' if p['kind']=='companies' else 'email'):p['identifier']};ctx,row,r,p=owned(c,aid)
    try:remote=await hubspot.crm_json('GET',path+'/'+external,token,params={'properties':','.join(sorted(expected))})
    except HTTPException:return result(c,org,aid)  # independent GET can be retried without replaying the write
    if str(remote.get('id'))!=external or remote.get('archived') or any(remote.get('properties',{}).get(k)!=v for k,v in expected.items()):return result(c,org,aid)
    lock(c,org);ctx,row,r,p=owned(c,aid);stamp=now()
    if c.execute("UPDATE radar_destination_receipts SET state='CONFIRMED',error_code=NULL,updated_at=? WHERE organization_id=? AND action_id=? AND state='VERIFY'",(stamp,org,aid)).rowcount:
        c.execute("UPDATE radar_actions SET status='SUCCEEDED',updated_at=? WHERE organization_id=? AND id=?",(stamp,org,aid));actions.audit(c,ctx,aid,'PROVIDER_CONFIRMED')
    return result(c,org,aid)
