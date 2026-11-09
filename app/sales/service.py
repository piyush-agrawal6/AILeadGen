"""Small persisted sales workflow; no automatic outreach."""
import json,uuid
from datetime import datetime,timezone
from fastapi import HTTPException
from app.database.prospects import now
from app.database.phase4_schema import ready,STATUSES

def prospect_org(c,pid,expected=None):
    from app.platform.context import organization
    org=organization(expected)
    if not c.execute('SELECT 1 FROM prospects WHERE id=? AND organization_id=?',(pid,org)).fetchone():raise HTTPException(404,'Prospect not found in this workspace.')
    return org

def activity(c,pid,actor,event,metadata=None,dedup=None,event_at=None,organization=None):
    if not ready(c):return
    organization=prospect_org(c,pid,organization)
    key=str(uuid.uuid4())
    inserted=c.execute('INSERT INTO activities(id,prospect_id,actor_user_id,event_type,event_at,metadata_json,created_at,dedup_key,organization_id) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(dedup_key) DO NOTHING',(key,pid,actor,event,event_at or now(),json.dumps(metadata or {}),now(),dedup,organization)).rowcount
    topic={'LEAD_DISCOVERED':'company.created','SALES_TASK_CREATED':'task.created','SALES_TASK_UPDATED':'task.updated','EMAIL_SENT':'email.sent','REPLY_DETECTED':'reply.received'}.get(event)
    if inserted and topic:
        from app.webhooks.service import emit
        details={name:value for name,value in (metadata or {}).items() if name in ('business_id','task_id','message_id') and value is not None}
        emit(c,topic,key,{'prospect_id':pid,**details})

def ensure(c,pid,organization=None):
    organization=prospect_org(c,pid,organization)
    c.execute('INSERT INTO prospect_sales(prospect_id,organization_id) VALUES(?,?) ON CONFLICT DO NOTHING',(pid,organization))

def suppressed(c,pid,organization=None):
    organization=prospect_org(c,pid,organization)
    row=c.execute("SELECT p.lead_status,s.suppressed_at FROM prospects p LEFT JOIN prospect_sales s ON s.prospect_id=p.id WHERE p.id=?"+(' AND p.organization_id=?' if organization else ''),(pid,)+((organization,) if organization else ())).fetchone()
    return not row or row['lead_status']=='DO_NOT_CONTACT' or bool(row['suppressed_at'])

def status_event(c,pid,actor,status,previous,organization=None):
    organization=prospect_org(c,pid,organization)
    ensure(c,pid,organization)
    if status=='DO_NOT_CONTACT':
        c.execute('UPDATE prospect_sales SET suppressed_at=COALESCE(suppressed_at,?) WHERE prospect_id=?'+(' AND organization_id=?' if organization else ''),(now(),pid)+((organization,) if organization else ()))
        from app.mail.tracking import available
        if available(c):c.execute("UPDATE prospect_sales SET suppression_source=COALESCE(suppression_source,'MANUAL_DNC') WHERE prospect_id=?"+(' AND organization_id=?' if organization else ''),(pid,)+((organization,) if organization else ()))
        c.execute("UPDATE followups SET status='CANCELED',completed_at=? WHERE prospect_id=? AND status='OPEN'"+(' AND organization_id=?' if organization else ''),(now(),pid)+((organization,) if organization else ()))
    activity(c,pid,actor,status if status in ('WON','LOST','DO_NOT_CONTACT') else 'STATUS_CHANGED',{'from':previous,'to':status},organization=organization)

def schedule(c,pid,actor,due_at,note='',assigned_to=None,reason='Manual follow-up',organization=None):
    organization=prospect_org(c,pid,organization)
    if suppressed(c,pid,organization):raise HTTPException(409,'This prospect is marked Do Not Contact.')
    try:
        due=datetime.fromisoformat(due_at.replace('Z','+00:00'))
        if due.tzinfo is None:raise ValueError()
    except ValueError:raise HTTPException(422,'Use a follow-up date with an explicit timezone.')
    key=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO followups(id,prospect_id,assigned_to,due_at,status,reason,note,created_by,created_at,organization_id) VALUES(?,?,?,?,'OPEN',?,?,?,?,?)",(key,pid,assigned_to,due.astimezone(timezone.utc).isoformat(),reason,note,actor,stamp,organization))
    activity(c,pid,actor,'FOLLOW_UP_CREATED',{'followup_id':key,'due_at':due.astimezone(timezone.utc).isoformat()},organization=organization)
    return key

def dossier(c,pid,organization=None):
    organization=prospect_org(c,pid,organization)
    ensure(c,pid,organization)
    scope=' AND organization_id=?' if organization else ''
    args=(pid,organization) if organization else (pid,)
    result=dict(c.execute('SELECT * FROM prospect_sales WHERE prospect_id=?'+scope,args).fetchone())
    result['suppressed']=suppressed(c,pid,organization)
    result['followups']=[dict(r) for r in c.execute('SELECT * FROM followups WHERE prospect_id=?'+scope+' ORDER BY due_at DESC LIMIT 100',args).fetchall()]
    result['activities']=[{**dict(r),'metadata':json.loads(r['metadata_json'])} for r in c.execute('SELECT * FROM activities WHERE prospect_id=?'+scope+' ORDER BY event_at DESC,id DESC LIMIT 200',args).fetchall()]
    list_scope=' AND l.archived_at IS NULL AND l.organization_id=?' if organization else ''
    result['lists']=[dict(r) for r in c.execute('SELECT l.* FROM lead_lists l JOIN lead_list_members m ON m.list_id=l.id WHERE m.prospect_id=?'+list_scope+' ORDER BY l.name',args).fetchall()]
    from app.mail import tracking
    if tracking.available(c):result['engagement']=tracking.lead_summary(c,pid)
    result['threads']=[dict(r) for r in c.execute('SELECT * FROM email_threads WHERE prospect_id=?'+scope+' ORDER BY last_message_at DESC LIMIT 50',args).fetchall()]
    return result

def member(c,pid,list_id,actor,remove=False,organization=None):
    organization=prospect_org(c,pid,organization)
    if not c.execute('SELECT 1 FROM lead_lists WHERE archived_at IS NULL AND id=?'+(' AND organization_id=?' if organization else ''),(list_id,)+((organization,) if organization else ())).fetchone():raise HTTPException(404,'List not found.')
    if remove:changed=c.execute('DELETE FROM lead_list_members WHERE list_id=? AND prospect_id=?',(list_id,pid)).rowcount
    else:changed=c.execute('INSERT INTO lead_list_members(list_id,prospect_id,added_by,added_at) VALUES(?,?,?,?) ON CONFLICT DO NOTHING',(list_id,pid,actor,now())).rowcount
    if changed:activity(c,pid,actor,'LIST_REMOVED' if remove else 'LIST_ADDED',{'list_id':list_id},organization=organization)
