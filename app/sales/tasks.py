"""General sales tasks extend follow-ups; creating or completing a task sends nothing."""
import hashlib,json,uuid
from datetime import datetime,timezone,timedelta,time
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator
from app.people.service import ctx,company,get as person
from app.api.organization import membership_role
from app.sales.service import activity,suppressed
from app.database.prospects import now
class Task(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    business_id:int=Field(ge=1,le=9223372036854775807)
    title:str=Field(min_length=2,max_length=180)
    task_type:Literal['FOLLOW_UP','RESEARCH','REVIEW','OTHER']='FOLLOW_UP'
    priority:Literal['LOW','NORMAL','HIGH']='NORMAL'
    note:str=Field('',max_length=2000)
    due_at:str=Field(max_length=60)
    contact_id:uuid.UUID|None=None
    assigned_to:str|None=Field(None,max_length=254)
    request_id:uuid.UUID=Field(default_factory=uuid.uuid4)
    @field_validator('due_at')
    @classmethod
    def date(cls,value):
        date=datetime.fromisoformat(value.replace('Z','+00:00'))
        if date.tzinfo is None:raise ValueError('Choose a due date with an explicit timezone.')
        return date.astimezone(timezone.utc).isoformat()


def get(c,key):
    org=ctx(c).organization_id
    row=c.execute('SELECT f.* FROM followups f JOIN prospects p ON p.id=f.prospect_id AND p.organization_id=f.organization_id WHERE f.id=? AND f.organization_id=?',(key,org)).fetchone()
    if not row:raise HTTPException(404,'Task not found.')
    result=dict(row);result.pop('creation_fingerprint',None);result.pop('request_id',None);return result


def validate(c,body):
    context=ctx(c,True);parent=company(c,body.business_id)
    if body.contact_id and person(c,str(body.contact_id))['prospect_id']!=parent['prospect_id']:raise HTTPException(409,'Choose a contact from this company.')
    if body.assigned_to and not membership_role(c,body.assigned_to,context.organization_id):raise HTTPException(422,'Assign a current workspace member.')
    if body.task_type=='FOLLOW_UP' and suppressed(c,parent['prospect_id']):raise HTTPException(409,'This company is suppressed. An internal review task is allowed; outreach follow-ups are blocked.')
    return parent


def create(c,body):
    parent=validate(c,body);context=ctx(c,True)
    from app.workflows.service import lock
    lock(c);fingerprint=hashlib.sha256(body.model_dump_json(exclude={'request_id'}).encode()).hexdigest()
    old=c.execute('SELECT id,creation_fingerprint FROM followups WHERE organization_id=? AND request_id=?',(context.organization_id,str(body.request_id))).fetchone()
    if old:
        if old['creation_fingerprint']!=fingerprint:raise HTTPException(409,'Task request ID belongs to different content.')
        return get(c,old['id'])
    if c.execute("SELECT COUNT(*) FROM followups WHERE organization_id=? AND status='OPEN'",(context.organization_id,)).fetchone()[0]>=2000:raise HTTPException(429,'Complete or cancel an existing task before creating more.')
    key=str(uuid.uuid4());c.execute("INSERT INTO followups(id,prospect_id,assigned_to,due_at,status,reason,note,created_by,created_at,organization_id,title,task_type,priority,contact_id,request_id,creation_fingerprint) VALUES(?,?,?,?,'OPEN',?,?,?,?,?,?,?,?,?,?,?)",(key,parent['prospect_id'],body.assigned_to,body.due_at,body.task_type,body.note,context.actor,now(),context.organization_id,body.title,body.task_type,body.priority,str(body.contact_id) if body.contact_id else None,str(body.request_id),fingerprint))
    activity(c,parent['prospect_id'],context.actor,'SALES_TASK_CREATED',{'task_id':key,'task_type':body.task_type},organization=context.organization_id)
    return get(c,key)


def listing(c,status='OPEN',assigned_to='',task_type='',page=1,size=25,priority='',view='',tz='UTC'):
    org=ctx(c).organization_id;where=['f.organization_id=?','p.organization_id=?'];args=[org,org]
    if view=='MY':assigned_to=ctx(c).actor
    if view=='COMPLETED':status='COMPLETED'
    for field,value in [('status',status),('assigned_to',assigned_to),('task_type',task_type),('priority',priority)]:
        if value:where.append('f.'+field+'=?');args.append(value)
    if view in ('TODAY','UPCOMING','OVERDUE'):
        from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
        try:zone=ZoneInfo(tz)
        except (ZoneInfoNotFoundError,ValueError):raise HTTPException(422,'Choose a valid task-view timezone.') from None
        present=datetime.now(timezone.utc);today=present.astimezone(zone).date()
        start=datetime.combine(today,time.min,zone).astimezone(timezone.utc).isoformat()
        end=datetime.combine(today+timedelta(days=1),time.min,zone).astimezone(timezone.utc).isoformat()
        if view=='TODAY':where.extend(['f.due_at>=?','f.due_at<?']);args.extend([start,end])
        elif view=='UPCOMING':where.append('f.due_at>=?');args.append(end)
        else:where.extend(["f.status='OPEN'",'f.due_at<?']);args.append(present.isoformat())
    base=' FROM followups f JOIN prospects p ON p.id=f.prospect_id WHERE '+' AND '.join(where)
    total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
    rows=c.execute('SELECT f.id,f.prospect_id,f.title,f.task_type,f.priority,f.note,f.assigned_to,f.due_at,f.status,f.contact_id,f.revision,(SELECT b.name FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.prospect_id=f.prospect_id AND r.organization_id=f.organization_id ORDER BY b.id DESC LIMIT 1) company_name,(SELECT b.id FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.prospect_id=f.prospect_id AND r.organization_id=f.organization_id ORDER BY b.id DESC LIMIT 1) business_id'+base+' ORDER BY f.due_at,f.id LIMIT ? OFFSET ?',[*args,size,(page-1)*size]).fetchall()
    return {'items':[dict(row) for row in rows],'total':total,'page':page,'page_size':size}


def update(c,key,revision,status=None,changes=None):
    context=ctx(c,True);old=get(c,key)
    status=status or old['status'];changes=changes or {}
    allowed={'title','task_type','priority','note','due_at','assigned_to','contact_id'}
    if set(changes)-allowed:raise HTTPException(422,'Unsupported task edit.')
    if changes.get('assigned_to') and not membership_role(c,changes['assigned_to'],context.organization_id):raise HTTPException(422,'Assign a current workspace member.')
    if changes.get('contact_id') and person(c,str(changes['contact_id']))['prospect_id']!=old['prospect_id']:raise HTTPException(409,'Choose a contact from this company.')
    if status=='OPEN' and changes.get('task_type',old['task_type'])=='FOLLOW_UP' and suppressed(c,old['prospect_id']):raise HTTPException(409,'Suppressed companies cannot have outreach follow-ups reopened.')
    columns=['status=?','completed_at=?','revision=revision+1'];values=[status,None if status=='OPEN' else now()]
    for field,value in changes.items():
        columns.append(field+'=?');values.append(str(value) if field=='contact_id' and value else value)
    if not c.execute('UPDATE followups SET '+','.join(columns)+' WHERE id=? AND organization_id=? AND revision=?',(*values,key,context.organization_id,revision)).rowcount:raise HTTPException(409,'Task changed. Reload before saving.')
    activity(c,old['prospect_id'],context.actor,'SALES_TASK_UPDATED',{'task_id':key,'status':status},organization=context.organization_id);return get(c,key)
