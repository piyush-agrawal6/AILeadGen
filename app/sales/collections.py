"""Workspace lists over existing company/contact membership tables; history retained."""
import hashlib,json,uuid
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.people.service import ctx,company
from app.database.prospects import now
from app.sales.service import member

class Named(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=1,max_length=100)
    description:str=Field('',max_length=1000)
    request_id:uuid.UUID=Field(default_factory=uuid.uuid4)
    revision:int|None=Field(None,ge=1)


def get(c,key):
    org=ctx(c).organization_id;row=c.execute('SELECT * FROM lead_lists WHERE id=? AND organization_id=?',(key,org)).fetchone()
    if not row:raise HTTPException(404,'List not found.')
    data=dict(row);data.pop('request_id',None);data.pop('creation_fingerprint',None);return data


def listing(c,search='',page=1,size=25,archived=False):
    org=ctx(c).organization_id;where='organization_id=? AND archived_at IS '+('NOT NULL' if archived else 'NULL');args=[org]
    if search:where+=' AND LOWER(name) LIKE ?';args.append('%'+search.casefold()+'%')
    total=c.execute('SELECT COUNT(*) FROM lead_lists WHERE '+where,args).fetchone()[0]
    rows=c.execute('SELECT l.*,(SELECT COUNT(*) FROM lead_list_members m JOIN prospects p ON p.id=m.prospect_id WHERE m.list_id=l.id AND p.organization_id=l.organization_id) member_count,(SELECT COUNT(*) FROM contact_list_members m WHERE m.list_id=l.id AND m.organization_id=l.organization_id) contact_count FROM lead_lists l WHERE '+where+' ORDER BY updated_at DESC,id LIMIT ? OFFSET ?',[*args,size,(page-1)*size]).fetchall()
    items=[]
    for row in rows:
        value=dict(row);value.pop('request_id',None);value.pop('creation_fingerprint',None);items.append(value)
    return {'items':items,'total':total,'page':page,'page_size':size}


def save(c,body,key=None):
    context=ctx(c,True)
    from app.workflows.service import lock
    lock(c);stamp=now();fingerprint=hashlib.sha256(json.dumps([body.name,body.description]).encode()).hexdigest()
    if key:
        previous=get(c,key)
        if previous['archived_at']:raise HTTPException(409,'This list is archived.')
        if not c.execute('UPDATE lead_lists SET name=?,description=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(body.name,body.description,stamp,key,context.organization_id,body.revision)).rowcount:raise HTTPException(409,'List changed. Reload before saving.')
    else:
        previous=c.execute('SELECT id,creation_fingerprint FROM lead_lists WHERE organization_id=? AND request_id=?',(context.organization_id,str(body.request_id))).fetchone()
        if previous:
            if previous['creation_fingerprint']!=fingerprint:raise HTTPException(409,'List request ID belongs to different content.')
            return get(c,previous['id'])
        if c.execute('SELECT COUNT(*) FROM lead_lists WHERE organization_id=? AND archived_at IS NULL',(context.organization_id,)).fetchone()[0]>=200:raise HTTPException(429,'Archive unused lists before creating more.')
        key=str(uuid.uuid4());c.execute('INSERT INTO lead_lists(id,name,description,created_by,created_at,updated_at,organization_id,request_id,creation_fingerprint) VALUES(?,?,?,?,?,?,?,?,?)',(key,body.name,body.description,context.actor,stamp,stamp,context.organization_id,str(body.request_id),fingerprint))
    return get(c,key)


def archive(c,key,revision):
    context=ctx(c,True);old=get(c,key)
    if old['archived_at']:return old
    if not c.execute('UPDATE lead_lists SET archived_at=?,updated_at=?,revision=revision+1 WHERE id=? AND organization_id=? AND revision=?',(now(),now(),key,context.organization_id,revision)).rowcount:raise HTTPException(409,'List changed. Reload before archiving.')
    return get(c,key)


def change_members(c,key,business_ids,remove=False):
    context=ctx(c,True);parent=get(c,key)
    if parent['archived_at']:raise HTTPException(409,'Archived list membership is preserved and cannot be changed.')
    parents=[company(c,bid) for bid in list(dict.fromkeys(business_ids))]
    for row in parents:member(c,row['prospect_id'],key,context.actor,remove,context.organization_id)
    c.execute('UPDATE lead_lists SET updated_at=?,revision=revision+1 WHERE id=? AND organization_id=?',(now(),key,context.organization_id))
    return {'updated':len(parents)}


def detail(c,key,page=1,size=25):
    result=get(c,key);org=ctx(c).organization_id
    companies=c.execute('SELECT b.id,b.name,b.website,b.country,b.city,p.lead_status FROM lead_list_members m JOIN prospects p ON p.id=m.prospect_id JOIN businesses b ON b.prospect_id=p.id JOIN pipeline_runs r ON r.id=b.run_id WHERE m.list_id=? AND p.organization_id=? AND r.organization_id=? AND b.id=(SELECT MAX(b2.id) FROM businesses b2 JOIN pipeline_runs r2 ON r2.id=b2.run_id WHERE b2.prospect_id=p.id AND r2.organization_id=?) ORDER BY b.name LIMIT ? OFFSET ?',(key,org,org,org,size,(page-1)*size)).fetchall()
    people=c.execute('SELECT p.id,p.name,p.role,p.verification_state,p.archived_at FROM contact_list_members m JOIN contact_people p ON p.id=m.contact_id AND p.organization_id=m.organization_id WHERE m.list_id=? AND m.organization_id=? ORDER BY p.name LIMIT ? OFFSET ?',(key,org,size,(page-1)*size)).fetchall()
    result.update(companies=[dict(row) for row in companies],contacts=[dict(row) for row in people],page=page,page_size=size,company_count=c.execute('SELECT COUNT(*) FROM lead_list_members m JOIN prospects p ON p.id=m.prospect_id WHERE m.list_id=? AND p.organization_id=?',(key,org)).fetchone()[0],contact_count=c.execute('SELECT COUNT(*) FROM contact_list_members WHERE list_id=? AND organization_id=?',(key,org)).fetchone()[0])
    return result
