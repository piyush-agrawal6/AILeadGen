"""Workspace-owned, explicitly reviewed actions. Internal execution is atomic, not a simulated provider job."""
import hashlib
import json
import uuid
from datetime import datetime,timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field
from app.api.organization import membership_role
from app.config.settings import get_settings
from app.database.prospects import now
from app.intent_radar.permissions import context,persistence_context
from app.intent_radar.service import get
from app.developer.keys import lock


class Draft(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    request_id:uuid.UUID
    opportunity_id:uuid.UUID
    title:str=Field(min_length=1,max_length=140)
    description:str=Field('',max_length=1200)
    owner:str=Field(min_length=1,max_length=254)
    due_at:AwareDatetime
    priority:Literal['low','normal','high']='normal'


class Approval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    digest:str=Field(pattern='^[a-f0-9]{64}$')


class Outcome(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    note:str=Field(min_length=1,max_length=500)


def scope(c,write=False):
    if not get_settings().radar_actions_enabled:raise HTTPException(404,'Action Center is unavailable.')
    return persistence_context(c) if write else context(c)


def source(c,key):
    op=get(c,'opportunities',key)
    if not op['signal']['available'] or op['status']=='Dismissed':raise HTTPException(409,'This opportunity is no longer actionable.')
    return op


SELECT='''SELECT a.*,t.status AS task_status,t.completed_at,t.outcome,r.state AS execution,r.external_id,r.error_code FROM radar_actions a LEFT JOIN radar_followups t ON t.id=a.id AND t.organization_id=a.organization_id LEFT JOIN radar_destination_receipts r ON r.action_id=a.id AND r.organization_id=a.organization_id'''

def view(row):
    return {k:row[k] for k in ('id','opportunity_id','kind','status','approved_at','approved_by','created_at','updated_at','digest','task_status','outcome','completed_at','execution','external_id','error_code')}|{'preview':json.loads(row['payload_json'])}

def owned(c,org,key):
    row=c.execute(SELECT+' WHERE a.organization_id=? AND a.id=?',(org,key)).fetchone()
    if not row:raise HTTPException(404,'Action not found.')
    return row

def audit(c,ctx,key,event):
    c.execute("INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,'SUCCESS',?,?)",(str(uuid.uuid4()),ctx.actor,'RADAR_ACTION_'+event,'radar-action:'+key,ctx.organization_id,now()))

def listing(c,status,limit,offset):
    ctx=scope(c);manager=membership_role(c,ctx.actor,ctx.organization_id) in ('OWNER','ADMIN');query=SELECT+" WHERE a.organization_id=? AND (a.kind='internal_followup' OR (a.created_by=? AND ?=1))";args=[ctx.organization_id,ctx.actor,int(manager)]
    if status:query+=' AND (a.status=? OR t.status=?)';args.extend([status,status])
    rows=c.execute(query+' ORDER BY a.created_at DESC,a.id DESC LIMIT ? OFFSET ?',(*args,limit+1,offset)).fetchall()
    return {'items':[view(r) for r in rows[:limit]],'has_more':len(rows)>limit}

def prepare(c,body):
    ctx=scope(c,True);org=ctx.organization_id;lock(c,org)
    op_id=str(body.opportunity_id);op=source(c,op_id)
    if not membership_role(c,body.owner,org):raise HTTPException(404,'Choose an active workspace member.')
    payload={'title':body.title,'description':body.description,'owner':body.owner,'due_at':body.due_at.astimezone(timezone.utc).isoformat(),'priority':body.priority}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'));digest=hashlib.sha256(json.dumps([org,op_id,op['revision'],'internal_followup',raw]).encode()).hexdigest();request=str(body.request_id)
    old=c.execute('SELECT id,created_by,digest FROM radar_actions WHERE organization_id=? AND request_id=?',(org,request)).fetchone()
    if old:
        if old['created_by']!=ctx.actor or old['digest']!=digest:raise HTTPException(409,'Request already used for a different action.')
        return view(owned(c,org,old['id']))
    if c.execute("SELECT count(*) FROM radar_actions WHERE organization_id=? AND status='NEEDS_REVIEW'",(org,)).fetchone()[0]>=100:raise HTTPException(429,'Review outstanding actions first.')
    key=str(uuid.uuid4());stamp=now();c.execute("INSERT INTO radar_actions(id,organization_id,request_id,created_by,opportunity_id,kind,payload_json,digest,opportunity_revision,status,created_at,updated_at) VALUES(?,?,?,?,?,'internal_followup',?,?,?,'NEEDS_REVIEW',?,?)",(key,org,request,ctx.actor,op_id,raw,digest,op['revision'],stamp,stamp));audit(c,ctx,key,'PREPARED');return view(owned(c,org,key))

def decide(c,key,choice,body):
    ctx=scope(c,True);org=ctx.organization_id;lock(c,org);row=owned(c,org,key)
    if row['kind']!='internal_followup':raise HTTPException(409,'Use the approval flow for this destination.')
    if row['created_by']!=ctx.actor:raise HTTPException(403,'Only the reviewing author can approve or cancel this action.')
    if body.digest!=row['digest']:raise HTTPException(409,'Review the exact action first.')
    status='SUCCEEDED' if choice=='approve' else 'CANCELED'
    if row['status']==status:return view(row)
    if row['status']!='NEEDS_REVIEW':raise HTTPException(409,'This action has already been decided.')
    stamp=now();payload=json.loads(row['payload_json']);approve=choice=='approve'
    if approve:
        op=source(c,row['opportunity_id'])
        if op['revision']!=row['opportunity_revision'] or not membership_role(c,payload['owner'],org):raise HTTPException(409,'Opportunity or assignee changed. Prepare a new review.')
        c.execute("INSERT INTO radar_followups(id,organization_id,owner_id,due_at,priority,status) VALUES(?,?,?,?,?,'OPEN')",(key,org,payload['owner'],payload['due_at'],payload['priority']))
    c.execute('UPDATE radar_actions SET status=?,approved_at=?,approved_by=?,updated_at=? WHERE organization_id=? AND id=?',(status,stamp if approve else None,ctx.actor if approve else None,stamp,org,key));audit(c,ctx,key,status);return view(owned(c,org,key))

def complete(c,key,body):
    ctx=scope(c,True);org=ctx.organization_id;lock(c,org);row=owned(c,org,key)
    if row['kind']!='internal_followup':raise HTTPException(409,'External actions require provider confirmation.')
    if ctx.actor!=json.loads(row['payload_json'])['owner'] and membership_role(c,ctx.actor,org) not in ('OWNER','ADMIN'):raise HTTPException(403,'Only the assignee or an administrator can complete this task.')
    if row['task_status']=='DONE' and row['outcome']==body.note:return view(row)
    if row['task_status']!='OPEN':raise HTTPException(409,'No open follow-up for this action.')
    stamp=now();c.execute("UPDATE radar_followups SET status='DONE',outcome=?,completed_by=?,completed_at=? WHERE organization_id=? AND id=?",(body.note,ctx.actor,stamp,org,key));c.execute('UPDATE radar_actions SET updated_at=? WHERE organization_id=? AND id=?',(stamp,org,key));audit(c,ctx,key,'USER_REPORTED_OUTCOME');return view(owned(c,org,key))
