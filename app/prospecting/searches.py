"""Owned saved searches. Loading/duplicating never starts discovery or outreach."""
import hashlib,json,uuid
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,ValidationError
from app.platform.context import current
from app.api.permissions import role,authorize
from app.database.prospects import now
class SaveSearch(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=1,max_length=120)
    configuration:dict
    request_id:uuid.UUID=Field(default_factory=uuid.uuid4)
    revision:int|None=Field(None,ge=1)

def context(c,write=False):
    ctx=current();role(c,ctx.actor,ctx.organization_id)
    if write:authorize(c,ctx.actor,'POST','/api/discovery/searches',{},ctx.organization_id)
    return ctx

def configuration(c,value):
    from app.api.routes.workflows import Run
    from app.prospecting.policy import configuration as policy
    if value.get('kind','SCAN')!='SCAN':raise HTTPException(422,'Save a discovery search, not an outreach operation.')
    from app.prospecting.policy import configuration as effective_policy
    metadata=set(effective_policy())-set(Run.model_fields)
    try:value=Run.model_validate({**{key:item for key,item in value.items() if key not in metadata},'kind':'SCAN'})
    except ValidationError as exc:raise HTTPException(422,'Review discovery criteria: '+'; '.join(issue['msg'] for issue in exc.errors(include_input=False,include_context=False))[:500]) from None
    if value.icp_id:
        from app.icp.service import get
        get(c,str(value.icp_id))
    result=policy(value.model_dump(mode='json'))
    for key in ('request_id','name'):result.pop(key,None)
    result['email_all_eligible']=False
    return result

def get(c,key):
    ctx=context(c);row=c.execute('SELECT * FROM discovery_searches WHERE id=? AND organization_id=?',(key,ctx.organization_id)).fetchone()
    if not row:raise HTTPException(404,'Search not found.')
    result=dict(row);result['configuration']=json.loads(result.pop('configuration_json'));result.pop('fingerprint');return result

def list_searches(c,search='',page=1,page_size=25,archived=False):
    ctx=context(c);where='organization_id=? AND archived_at IS '+('NOT NULL' if archived else 'NULL');args=[ctx.organization_id]
    if search:where+=' AND LOWER(name) LIKE ?';args.append('%'+search.casefold()+'%')
    total=c.execute('SELECT COUNT(*) FROM discovery_searches WHERE '+where,args).fetchone()[0]
    rows=c.execute('SELECT id FROM discovery_searches WHERE '+where+' ORDER BY updated_at DESC,id LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall()
    return {'items':[get(c,row[0]) for row in rows],'total':total,'page':page,'page_size':page_size}

def save(c,body,key=None):
    ctx=context(c,True);cfg=configuration(c,body.configuration);encoded=json.dumps(cfg,sort_keys=True,separators=(',',':'));fingerprint=hashlib.sha256(json.dumps([body.name,cfg],sort_keys=True).encode()).hexdigest();stamp=now()
    if key:
        old=get(c,key)
        if old['archived_at']:raise HTTPException(409,'Archived searches cannot be edited.')
        if body.revision!=old['revision']:raise HTTPException(409,'Search changed. Reload before saving.')
        changed=c.execute('UPDATE discovery_searches SET name=?,configuration_json=?,fingerprint=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(body.name,encoded,fingerprint,stamp,key,ctx.organization_id,body.revision)).rowcount
        if not changed:raise HTTPException(409,'Search changed. Reload before saving.')
    else:
        from app.workflows.service import lock
        lock(c)
        old=c.execute('SELECT id,fingerprint FROM discovery_searches WHERE organization_id=? AND request_id=?',(ctx.organization_id,str(body.request_id))).fetchone()
        if old:
            if old['fingerprint']!=fingerprint:raise HTTPException(409,'Request ID already belongs to different search content.')
            return get(c,old['id'])
        # Use the existing per-workspace write lock to serialize the quota check.
        from app.workflows.service import lock
        lock(c)
        if c.execute('SELECT COUNT(*) FROM discovery_searches WHERE organization_id=? AND archived_at IS NULL',(ctx.organization_id,)).fetchone()[0]>=100:raise HTTPException(429,'Archive an unused search before saving another.')
        key=str(uuid.uuid4());c.execute('INSERT INTO discovery_searches(id,organization_id,name,configuration_json,request_id,fingerprint,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(key,ctx.organization_id,body.name,encoded,str(body.request_id),fingerprint,ctx.actor,stamp,stamp))
    return get(c,key)

def archive(c,key,revision):
    ctx=context(c,True);get(c,key)
    if not c.execute('UPDATE discovery_searches SET archived_at=?,updated_at=?,revision=revision+1 WHERE id=? AND organization_id=? AND revision=? AND archived_at IS NULL',(now(),now(),key,ctx.organization_id,revision)).rowcount:raise HTTPException(409,'Search changed. Reload before archiving.')
    return get(c,key)
