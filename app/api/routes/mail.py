import json,uuid
from typing import Literal
from fastapi import APIRouter,Depends,Request,HTTPException,Query
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.api.routes.workflow import require_prospect
from app.mail import service,tracking
from app.mail.config import mail_settings
from app.mail.providers import provider
from app.mail.templates import seed,render,VARIABLES
from app.database.prospects import now

router=APIRouter(prefix='/email',tags=['Reviewed email'])
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Message(Strict):
    to_address:str=Field(max_length=254)
    subject:str=Field(min_length=1,max_length=200)
    body_text:str=Field(min_length=1,max_length=20000)
    report_id:str|None=Field(default=None,max_length=36)
    thread_id:str|None=Field(default=None,max_length=36)
    followup_days:int|None=Field(default=None,ge=1,le=30)
    override_declined:bool=False
    track_opens:bool=True
    track_clicks:bool=True
    template_id:str|None=Field(default=None,max_length=60)
    message_type:Literal['FIRST_CONTACT','FOLLOW_UP','MANUAL_REPLY']='FIRST_CONTACT'
class Send(Message):
    confirmation:Literal['SEND']
    preview_token:str=Field(pattern='^[a-f0-9]{64}$')
    idempotency_key:str=Field(pattern='^[a-f0-9-]{36}$')
class Template(Strict):
    name:str=Field(min_length=1,max_length=100)
    category:Literal['Website','SEO','Security','General']
    vertical:str|None=Field(default=None,max_length=60)
    subject:str=Field(min_length=1,max_length=200)
    body_text:str=Field(min_length=1,max_length=20000)
    enabled:bool=True

@router.get('/account')
def email_account(request:Request,conn=Depends(get_db)):
    s=mail_settings();acc=service.account(conn,request.state.user_email)
    return {**acc,'send_mode':s.mode,'test_recipient':s.test_recipient if s.mode=='test' else None,'sync_enabled':s.sync_enabled,'sync_interval_minutes':s.sync_interval,'max_per_hour':s.max_hour,'max_per_day':s.max_day,'gmail_status':'Optional; not configured','sending_enabled':s.sending_enabled,'can_send':s.sending_enabled and ((s.mode=='test' and not s.live_approved) or (s.mode=='production' and s.live_approved)),'live_approved':s.live_approved,'tracking':tracking.preferences(conn),'tracking_base_url':s.tracking_base_url}
@router.post('/health')
def health(request:Request,conn=Depends(get_db)):
    service.account(conn,request.state.user_email)
    try:result=provider().health_check()
    except Exception:result={'smtp':'UNAVAILABLE','imap':'UNAVAILABLE'}
    conn.execute('UPDATE email_accounts SET smtp_health=?,imap_health=?,health_checked_at=? WHERE id=?',(result['smtp'],result['imap'],now(),service.ACCOUNT))
    return result
@router.post('/account/{action}')
def account_action(action:Literal['connect','disconnect','default'],request:Request,conn=Depends(get_db)):
    service.account(conn,request.state.user_email)
    if action=='default':conn.execute('UPDATE email_accounts SET is_default=1 WHERE id=?',(service.ACCOUNT,))
    else:conn.execute('UPDATE email_accounts SET status=?,updated_at=? WHERE id=?',('CONNECTED' if action=='connect' else 'DISCONNECTED',now(),service.ACCOUNT))
    return {'saved':True}
@router.post('/sync')
def sync():
    try:return service.sync_mailbox()
    except Exception:raise HTTPException(503,'Inbox synchronization is temporarily unavailable. No credentials or message bodies are included in this error.') from None
@router.get('/leads/{lead_id}/compose')
def compose(lead_id:int,request:Request,conn=Depends(get_db)):
    pid=require_prospect(conn,lead_id,request.state.user_email);seed(conn);s=mail_settings()
    reports=[dict(r) for r in conn.execute("SELECT id,version,created_at FROM client_reports WHERE prospect_id=? AND status='READY' ORDER BY version DESC LIMIT 20",(pid,)).fetchall()]
    b=conn.execute('SELECT name,website,city,vertical FROM businesses WHERE id=?',(lead_id,)).fetchone();o=conn.execute('SELECT primary_opportunity,evidence_json FROM opportunity_scores WHERE business_id=?',(lead_id,)).fetchone();evidence=json.loads(o['evidence_json']) if o else {};kind=o['primary_opportunity'] if o else None
    items=evidence.get(kind,[]) if kind else [];finding=items[0].get('detail','') if items else 'A specific improvement has not yet been established from the stored evidence.'
    values={'business_name':b['name'],'website':b['website'],'city':b['city'],'vertical':b['vertical'],'primary_opportunity':kind,'top_finding':finding,'sender_name':s.signature_name,'sender_company':s.company}
    signature='\n'.join(v for v in [s.signature_name,s.signature_role,s.company,s.website,s.from_address] if v)
    templates=[{**dict(t),'rendered_subject':render(t['subject'],values),'rendered_body':render(t['body_text'],values)+'\n\n'+signature} for t in conn.execute('SELECT * FROM email_templates WHERE enabled=1 AND (vertical IS NULL OR vertical=?) ORDER BY name',(b['vertical'],)).fetchall()]
    blocked=service.suppressed(conn,pid)
    return {'recipients':[] if blocked else service.recipients(conn,pid),'reports':reports,'templates':[] if blocked else templates,'suppressed':blocked,'from_address':s.from_address,'test_mode':s.mode=='test','effective_test_recipient':s.test_recipient if s.mode=='test' else None,'sending_enabled':s.sending_enabled,'can_send':s.sending_enabled and ((s.mode=='test' and not s.live_approved) or (s.mode=='production' and s.live_approved)),'tracking':tracking.preferences(conn),'draft':(lambda r:json.loads(r[0]) if r else None)(conn.execute('SELECT payload_json FROM email_drafts WHERE prospect_id=? AND actor=?',(pid,request.state.user_email)).fetchone())}
@router.post('/leads/{lead_id}/preview')
def preview(lead_id:int,body:Message,request:Request,conn=Depends(get_db)):
    pid=require_prospect(conn,lead_id,request.state.user_email);return service.preview(conn,pid,request.state.user_email,body.model_dump())
@router.post('/leads/{lead_id}/send')
def send(lead_id:int,body:Send,request:Request,conn=Depends(get_db)):
    pid=require_prospect(conn,lead_id,request.state.user_email);return service.send(conn,pid,request.state.user_email,body.model_dump())
@router.get('/leads/{lead_id}/threads/{thread_id}')
def thread(lead_id:int,thread_id:str,request:Request,conn=Depends(get_db)):
    pid=require_prospect(conn,lead_id,request.state.user_email)
    if not conn.execute('SELECT 1 FROM email_threads WHERE id=? AND prospect_id=?',(thread_id,pid)).fetchone():raise HTTPException(404,'Conversation not found.')
    conn.execute('UPDATE prospect_sales SET unread_replies=0 WHERE prospect_id=?',(pid,))
    return [{**dict(r),'engagement':tracking.message_summary(conn,r['id']),'verified_reply':bool(conn.execute('SELECT 1 FROM activities WHERE dedup_key=?',('reply-'+r['id'],)).fetchone())} for r in conn.execute('SELECT id,direction,status,from_address,to_address,subject,body_text,sent_at,received_at,report_id,test_mode,created_at,template_id,message_type FROM email_messages WHERE prospect_id=? AND thread_id=? ORDER BY created_at',(pid,thread_id)).fetchall()]
@router.get('/templates')
def templates(conn=Depends(get_db)):seed(conn);return [dict(r) for r in conn.execute('SELECT * FROM email_templates ORDER BY name').fetchall()]
def save_template(conn,key,body):
    try:render(body.subject,{});render(body.body_text,{})
    except ValueError:raise HTTPException(422,'Use only supported template variables.')
    service.header(body.subject)
    conn.execute('INSERT INTO email_templates(id,name,category,vertical,subject,body_text,enabled,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,category=excluded.category,vertical=excluded.vertical,subject=excluded.subject,body_text=excluded.body_text,enabled=excluded.enabled,updated_at=excluded.updated_at',(key,body.name,body.category,body.vertical,body.subject,body.body_text,int(body.enabled),now()));return {'id':key}
@router.post('/templates',status_code=201)
def create_template(body:Template,conn=Depends(get_db)):return save_template(conn,str(uuid.uuid4()),body)
@router.put('/templates/{template_id}')
def update_template(template_id:str,body:Template,conn=Depends(get_db)):return save_template(conn,template_id,body)


class TrackingPreferences(Strict):
    track_opens:bool
    track_clicks:bool
    track_replies:Literal[True]=True
    track_bounces:Literal[True]=True

@router.patch('/tracking')
def update_tracking(body:TrackingPreferences,conn=Depends(get_db)):
    conn.execute('UPDATE email_tracking_preferences SET track_opens=?,track_clicks=?,track_replies=?,track_bounces=? WHERE id=1',tuple(int(v) for v in body.model_dump().values()))
    return tracking.preferences(conn)

@router.put('/leads/{lead_id}/draft')
def draft(lead_id:int,body:Message,request:Request,conn=Depends(get_db)):
    pid=require_prospect(conn,lead_id,request.state.user_email)
    if service.suppressed(conn,pid):raise HTTPException(409,'This prospect is marked Do Not Contact.')
    conn.execute('INSERT INTO email_drafts VALUES(?,?,?,?,?) ON CONFLICT(prospect_id,actor) DO UPDATE SET payload_json=excluded.payload_json,updated_at=excluded.updated_at',(str(uuid.uuid4()),pid,request.state.user_email,json.dumps(body.model_dump()),now()))
    return {'status':'DRAFT'}

@router.get('/activity-summary')
def activity_summary(days:Literal[1,7,30]=30,tz:str=Query('Asia/Kolkata',max_length=80),conn=Depends(get_db)):
    from datetime import datetime,timedelta,timezone
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    try:local=datetime.now(ZoneInfo(tz))
    except ZoneInfoNotFoundError:raise HTTPException(422,'Choose a valid timezone.')
    start=(local.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=days-1)).astimezone(timezone.utc).isoformat()
    # Test signals stay separate from actual prospect engagement.
    counts=[dict(r) for r in conn.execute('SELECT e.event_type,m.test_mode,COUNT(DISTINCT e.message_id) AS count FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.occurred_at>=? AND e.suspected_bot=0 GROUP BY e.event_type,m.test_mode',(start,)).fetchall()]
    automated=conn.execute('SELECT COUNT(*) FROM email_engagement_events WHERE occurred_at>=? AND suspected_bot=1',(start,)).fetchone()[0]
    templates=[dict(r) for r in conn.execute("SELECT t.id,t.name,e.event_type,m.test_mode,COUNT(DISTINCT m.id) AS count FROM email_templates t JOIN email_messages m ON m.template_id=t.id JOIN email_engagement_events e ON e.message_id=m.id WHERE e.occurred_at>=? AND e.suspected_bot=0 GROUP BY t.id,t.name,e.event_type,m.test_mode",(start,)).fetchall()]
    return {'days':days,'counts':counts,'automated_signals':automated,'templates':templates}
