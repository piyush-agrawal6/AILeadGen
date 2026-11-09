"""Contact lifecycle over existing contact_people and canonical companies."""
import json,uuid,hashlib
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from fastapi import HTTPException
from app.database.prospects import now
from app.platform.context import current
from app.api.permissions import role,authorize

class Person(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    name:str=Field(min_length=2,max_length=150)
    role:str=Field('',max_length=150)
    department:str=Field('',max_length=100)
    seniority:str=Field('',max_length=100)
    job_function:str=Field('',max_length=100)
    profile_url:str=Field('',max_length=1000)
    work_email:str=Field('',max_length=254)
    phone:str=Field('',max_length=80)
    source_url:str=Field('manual://owner',max_length=1000)
    confidence:Literal['UNKNOWN','LOW','MEDIUM','HIGH']='UNKNOWN'
    evidence:str=Field('',max_length=3000)
    revision:int|None=Field(None,ge=1)
    request_id:uuid.UUID=Field(default_factory=uuid.uuid4)
    @field_validator('source_url','profile_url')
    @classmethod
    def public_url(cls,value,info):
        if value=='':return value
        if info.field_name=='source_url' and (value=='manual://owner' or value.startswith('import://')):return value
        from app.utils.urls import is_safe_url,sanitize_url
        value=sanitize_url(value)
        if not value or not is_safe_url(value,check_dns=False):raise ValueError('Use a public HTTP/HTTPS source or professional profile URL.')
        return value
    @field_validator('work_email')
    @classmethod
    def email(cls,value):
        if value:
            from app.mail.service import address
            try:return address(value)
            except HTTPException:raise ValueError('Use a valid business email or leave it empty.') from None
        return ''

def ctx(c,write=False):
    context=current();role(c,context.actor,context.organization_id)
    if write:authorize(c,context.actor,'POST','/api/people',{},context.organization_id)
    return context

def company(c,business_id):
    org=ctx(c).organization_id
    row=c.execute('SELECT b.id,b.prospect_id,b.name,b.website,b.vertical,b.source_tags_json FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id JOIN prospects p ON p.id=b.prospect_id WHERE b.id=? AND r.organization_id=? AND p.organization_id=?',(business_id,org,org)).fetchone()
    if not row:raise HTTPException(404,'Company not found.')
    return dict(row)

def get(c,key):
    context=ctx(c)
    row=c.execute('SELECT x.* FROM contact_people x JOIN prospects p ON p.id=x.prospect_id AND p.organization_id=x.organization_id WHERE x.id=? AND x.organization_id=?',(key,context.organization_id)).fetchone()
    if not row:raise HTTPException(404,'Contact not found.')
    result=dict(row);result['evidence']=json.loads(result.pop('evidence_json'));result['recipient_delivery_verified']=result['verification_state']=='PROVIDER_VERIFIED'
    company_row=c.execute('SELECT b.id,b.name FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.prospect_id=? AND r.organization_id=? ORDER BY b.id DESC LIMIT 1',(row['prospect_id'],context.organization_id)).fetchone();result['business_id']=company_row[0] if company_row else None;result['company_name']=company_row[1] if company_row else 'Company record'
    result.pop('creation_fingerprint',None);result.pop('request_id',None)
    result['notes']=[dict(r) for r in c.execute('SELECT id,body,created_by,created_at FROM contact_person_notes WHERE contact_id=? AND organization_id=? ORDER BY created_at DESC LIMIT 100',(key,context.organization_id)).fetchall()]
    result['lists']=[dict(r) for r in c.execute('SELECT l.id,l.name,l.archived_at FROM lead_lists l JOIN contact_list_members m ON m.list_id=l.id WHERE m.contact_id=? AND m.organization_id=? AND l.organization_id=?',(key,context.organization_id,context.organization_id)).fetchall()]
    return result

def listing(c,search='',business_id=None,job_role='',state='',page=1,page_size=25):
    context=ctx(c);where=['x.organization_id=?','x.archived_at IS NULL'];args=[context.organization_id]
    if business_id:where.append('x.prospect_id=?');args.append(company(c,business_id)['prospect_id'])
    if search:where.append('(LOWER(x.name) LIKE ? OR LOWER(x.work_email) LIKE ? OR LOWER(x.role) LIKE ?)');args.extend(['%'+search.casefold()+'%']*3)
    if job_role:where.append('LOWER(x.role) LIKE ?');args.append('%'+job_role.casefold()+'%')
    if state:where.append('x.discovery_state=?');args.append(state)
    base=' FROM contact_people x JOIN prospects p ON p.id=x.prospect_id AND p.organization_id=x.organization_id WHERE '+' AND '.join(where)
    total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
    rows=c.execute("SELECT x.*,(SELECT b.name FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.prospect_id=x.prospect_id AND r.organization_id=x.organization_id ORDER BY b.id DESC LIMIT 1) company_name"+base+' ORDER BY COALESCE(x.updated_at,x.created_at) DESC,x.id LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall()
    items=[]
    for row in rows:
        item=dict(row);item['evidence']=json.loads(item.pop('evidence_json'));item.pop('creation_fingerprint',None);item.pop('request_id',None);item['recipient_delivery_verified']=item['verification_state']=='PROVIDER_VERIFIED';items.append(item)
    return {'items':items,'total':total,'page':page,'page_size':page_size}

def audit(c,action,key):
    context=ctx(c);c.execute('INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),context.actor,action,'person:'+key,'SUCCESS','{}',context.organization_id,now()))

def save(c,business_id,body,key=None,*,origin=None):
    context=ctx(c,True);parent=company(c,business_id);stamp=now();is_new=key is None
    if key:
        old=get(c,key)
        if old['prospect_id']!=parent['prospect_id']:raise HTTPException(409,'A contact cannot silently move to another company.')
        if old['archived_at']:raise HTTPException(409,'This contact is archived.')
        if body.revision!=old['revision']:raise HTTPException(409,'Contact changed. Reload before saving.')
    from app.workflows.service import lock
    lock(c)
    fingerprint=hashlib.sha256(json.dumps([parent['prospect_id'],body.model_dump(mode='json',exclude={'request_id','revision'})],sort_keys=True).encode()).hexdigest()
    if not key:
        previous=c.execute('SELECT id,creation_fingerprint FROM contact_people WHERE organization_id=? AND request_id=?',(context.organization_id,str(body.request_id))).fetchone()
        if previous:
            if previous['creation_fingerprint']!=fingerprint:raise HTTPException(409,'Contact request ID already belongs to different content.')
            return get(c,previous['id'])
    # A shared name is not enough to merge two people at unrelated companies.
    duplicate=c.execute("SELECT id FROM contact_people WHERE organization_id=? AND prospect_id=? AND archived_at IS NULL AND id<>? AND ((?<>'' AND LOWER(work_email)=?) OR (?<>'' AND profile_url=?)) LIMIT 1",(context.organization_id,parent['prospect_id'],key or '',body.work_email,body.work_email,body.profile_url,body.profile_url)).fetchone()
    if duplicate:
        if key:raise HTTPException(409,'This email or profile already belongs to a company contact.')
        return get(c,duplicate[0])
    evidence={'value':body.evidence,'source_url':body.source_url,'retrieved_at':stamp,'origin':origin or ('OWNER_PROVIDED' if body.source_url.startswith(('manual:','import:')) else 'MANUALLY_RECORDED_PUBLIC_SOURCE'),'employment_verified':False}
    if key and old.get('work_email')==body.work_email and old.get('evidence',{}).get('verification'):evidence['verification']=old['evidence']['verification']
    if not key:
        key=str(uuid.uuid4());c.execute('INSERT INTO contact_people(id,prospect_id,name,role,department,seniority,job_function,profile_url,work_email,phone,confidence,source_url,evidence_json,created_at,updated_at,created_by,organization_id,request_id,creation_fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,parent['prospect_id'],body.name,body.role,body.department,body.seniority,body.job_function,body.profile_url or None,body.work_email or None,body.phone,body.confidence,body.source_url,json.dumps(evidence),stamp,stamp,context.actor,context.organization_id,str(body.request_id),fingerprint))
    else:
        changed=c.execute("UPDATE contact_people SET name=?,role=?,department=?,seniority=?,job_function=?,profile_url=?,work_email=?,phone=?,confidence=?,source_url=?,evidence_json=?,updated_at=?,revision=revision+1,verification_state=CASE WHEN COALESCE(work_email,'')=? THEN verification_state ELSE 'UNKNOWN' END,checked_at=CASE WHEN COALESCE(work_email,'')=? THEN checked_at ELSE NULL END WHERE id=? AND organization_id=? AND revision=?",(body.name,body.role,body.department,body.seniority,body.job_function,body.profile_url or None,body.work_email or None,body.phone,body.confidence,body.source_url,json.dumps(evidence),stamp,body.work_email,body.work_email,key,context.organization_id,body.revision)).rowcount
        if not changed:raise HTTPException(409,'Contact changed. Reload before saving.')
    audit(c,'CONTACT_SAVED',key)
    result=get(c,key)
    from app.webhooks.service import emit
    emit(c,'contact.created' if is_new else 'contact.updated',key+':'+str(result['revision']),{'contact_id':key,'prospect_id':parent['prospect_id'],'business_id':business_id})
    return result

def archive(c,key,revision):
    context=ctx(c,True);get(c,key)
    if not c.execute('UPDATE contact_people SET archived_at=?,updated_at=?,revision=revision+1 WHERE id=? AND organization_id=? AND revision=? AND archived_at IS NULL',(now(),now(),key,context.organization_id,revision)).rowcount:raise HTTPException(409,'Contact changed. Reload before archiving.')
    audit(c,'CONTACT_ARCHIVED',key);return get(c,key)

def note(c,key,text):
    context=ctx(c,True);get(c,key);c.execute('INSERT INTO contact_person_notes(id,contact_id,organization_id,body,created_by,created_at) VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),key,context.organization_id,text,context.actor,now()));audit(c,'CONTACT_NOTE_ADDED',key);return get(c,key)

def membership(c,key,list_id,add=True):
    context=ctx(c,True);get(c,key)
    if not c.execute('SELECT id FROM lead_lists WHERE id=? AND organization_id=? AND archived_at IS NULL',(list_id,context.organization_id)).fetchone():raise HTTPException(404,'List not found.')
    if add:c.execute('INSERT INTO contact_list_members(list_id,contact_id,organization_id,added_at) VALUES(?,?,?,?) ON CONFLICT(list_id,contact_id) DO NOTHING',(list_id,key,context.organization_id,now()))
    else:c.execute('DELETE FROM contact_list_members WHERE list_id=? AND contact_id=? AND organization_id=?',(list_id,key,context.organization_id))
    audit(c,'CONTACT_LIST_CHANGED',key);return get(c,key)
