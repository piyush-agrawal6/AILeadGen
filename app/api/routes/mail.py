import json,uuid
from typing import Literal
from fastapi import APIRouter,Depends,Request,HTTPException,Query,Response
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.api.routes.workflow import require_prospect
from app.mail import service,tracking
from app.mail.config import mail_settings
from app.mail.providers import provider
from app.mail.templates import seed,render,VARIABLES
from app.database.prospects import now
from app.config.settings import get_settings

def private_mail_response(response:Response):response.headers['Cache-Control']='private, no-store'
router=APIRouter(prefix='/email',tags=['Reviewed email'],dependencies=[Depends(private_mail_response)])
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Message(Strict):
    account_id:str|None=Field(None,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
    outreach_strategy:Literal['WORKSPACE','FIXED_5']|None=None
    template_version:str|None=Field(None,max_length=20)
    pdf_asset_id:str|None=Field(None,max_length=60)
    pdf_version:str|None=Field(None,max_length=20)
    campaign_id:str|None=Field(default=None,max_length=36)
    pitch_types:list[Literal['WEBSITE','SEO','SECURITY']]=Field(default_factory=list,max_length=3)
    preview_nonce:str=Field(default='',max_length=36)
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
def email_account(request:Request,conn=Depends(get_db,scope='function')):
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    if request.state.organization_id!=PLANEBYTE_ORGANIZATION_ID:
        if not get_settings().heysow_customer_gmail_enabled:
            return {'status':'NOT_CONFIGURED','provider':None,'email_address':None,'display_name':None,'sending_enabled':False,'can_send':False,'sync_enabled':False,'gmail_status':'Not configured for this workspace'}
        acc=service.account(conn,request.state.user_email);s=service.settings_for(conn,acc)
        return {**acc,'sending_enabled':s.sending_enabled,'can_send':s.sending_enabled and acc['connection_status']=='CONNECTED',
            'sync_enabled':True,'send_mode':s.mode,'test_recipient':s.test_recipient or None,'max_per_hour':s.max_hour,'max_per_day':s.max_day,'live_approved':s.live_approved}
    s=mail_settings();acc=service.account(conn,request.state.user_email)
    return {**acc,'send_mode':s.mode,'test_recipient':s.test_recipient if s.mode=='test' else None,'sync_enabled':s.sync_enabled,'sync_interval_minutes':s.sync_interval,'max_per_hour':s.max_hour,'max_per_day':s.max_day,'gmail_status':'Configured; acceptance required' if s.provider=='gmail' else 'Inactive','sending_enabled':s.sending_enabled,'can_send':s.sending_enabled and ((s.mode=='test' and not s.live_approved) or (s.mode=='production' and s.live_approved)),'live_approved':s.live_approved,'tracking':tracking.preferences(conn),'tracking_base_url':s.tracking_base_url}
@router.post('/health')
def health(request:Request,conn=Depends(get_db,scope='function')):
    acc=service.account(conn,request.state.user_email)
    try:result=service.transport_for(conn,acc).health_check()
    except Exception:result={'smtp':'UNAVAILABLE','imap':'UNAVAILABLE'}
    conn.execute('UPDATE email_accounts SET smtp_health=?,imap_health=?,health_checked_at=? WHERE id=? AND organization_id=?',(result['smtp'],result['imap'],now(),acc['id'],request.state.organization_id))
    return result
@router.post('/account/{action}')
def account_action(action:Literal['connect','disconnect','default'],request:Request,conn=Depends(get_db,scope='function')):
    acc=service.account(conn,request.state.user_email)
    if acc['provider']=='gmail_oauth':
        if action=='connect':raise HTTPException(409,'Use the customer Gmail OAuth connection flow to reconnect.')
        if action=='disconnect':
            from app.integrations.gmail import disconnect
            return disconnect(conn,acc['connection_id'])
        return {'saved':True}
    if action=='default':conn.execute('UPDATE email_accounts SET is_default=1 WHERE id=?',(service.ACCOUNT,))
    else:conn.execute('UPDATE email_accounts SET status=?,updated_at=? WHERE id=?',('CONNECTED' if action=='connect' else 'DISCONNECTED',now(),service.ACCOUNT))
    return {'saved':True}
@router.post('/sync')
def sync(request:Request,conn=Depends(get_db,scope='function')):
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    account_id=None if request.state.organization_id==PLANEBYTE_ORGANIZATION_ID else service.account(conn,request.state.user_email)['id']
    try:return service.sync_mailbox(account_id=account_id)
    except Exception:raise HTTPException(503,'Inbox synchronization is temporarily unavailable. No credentials or message bodies are included in this error.') from None
@router.get('/leads/{lead_id}/compose')
def compose(lead_id:int,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization)
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    acc=None
    if organization==PLANEBYTE_ORGANIZATION_ID:s=mail_settings()
    else:
        try:acc=service.account(conn,request.state.user_email);s=service.settings_for(conn,acc)
        except HTTPException as exc:
            if exc.status_code not in (403,404,503):raise
            from app.mail.config import MailSettings
            company=conn.execute('SELECT name FROM organizations WHERE id=?',(organization,)).fetchone()[0]
            s=MailSettings.model_construct(from_address='',from_name=company,company=company,website='',sending_enabled=False,tracking_enabled=False,test_recipient='')
    from app.platform.modules import legacy_enabled
    if legacy_enabled():seed(conn)
    reports=[dict(r) for r in conn.execute("SELECT id,version,created_at FROM client_reports WHERE prospect_id=? AND status='READY' AND organization_id=? ORDER BY version DESC LIMIT 20",(pid,organization)).fetchall()]
    from app.mail.templates import render_client_template,LEGACY_SEEDS
    from app.mail.workspace_templates import archived_template
    templates=[render_client_template(conn,lead_id,t[0],s) for t in conn.execute('SELECT id FROM email_templates WHERE enabled=1 AND organization_id=? AND (vertical IS NULL OR vertical=(SELECT vertical FROM businesses WHERE id=?)) ORDER BY name',(organization,lead_id)).fetchall() if (legacy_enabled() or not archived_template(t[0]))]
    templates.sort(key=lambda t:not t.get('recommended',False))
    blocked=service.suppressed(conn,pid)
    return {'account_id':acc['id'] if acc else None,'recipients':[] if blocked else service.recipients(conn,pid),'reports':reports,'templates':[] if blocked else templates,'suppressed':blocked,'from_address':s.from_address or None,'from_name':s.from_name,'test_mode':s.mode=='test','effective_test_recipient':s.test_recipient if s.mode=='test' else None,'sending_enabled':s.sending_enabled,'can_send':s.sending_enabled and ((s.mode=='test' and not s.live_approved) or (s.mode=='production' and s.live_approved)),'tracking':tracking.preferences(conn),'draft':(lambda r:json.loads(r[0]) if r else None)(conn.execute('SELECT payload_json FROM email_drafts WHERE prospect_id=? AND actor=? AND organization_id=?',(pid,request.state.user_email,organization)).fetchone())}

from app.integrations import gmail as customer_gmail,service as connection_service
from app.api.routes.integrations import Code
from app.mail.customer import PolicyUpdate

@router.get('/gmail',dependencies=[Depends(customer_gmail.require_enabled)])
def gmail_accounts(response:Response,conn=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='private, no-store'
    return customer_gmail.listing(conn)

@router.post('/gmail/authorize',dependencies=[Depends(customer_gmail.require_enabled)])
def gmail_authorize(response:Response,conn=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='private, no-store'
    return connection_service.authorize(conn,spec=customer_gmail.spec())

@router.post('/gmail/connect',dependencies=[Depends(customer_gmail.require_enabled)])
async def gmail_connect(body:Code,response:Response,conn=Depends(get_db,scope='function')):
    response.headers['Cache-Control']='private, no-store'
    result=await connection_service.connect(conn,body.state,body.code,spec=customer_gmail.spec())
    return customer_gmail.view(connection_service.owned(conn,result['id'],spec=customer_gmail.spec()))

@router.delete('/gmail/{connection_id}',dependencies=[Depends(customer_gmail.require_enabled)])
def gmail_disconnect(connection_id:uuid.UUID,conn=Depends(get_db,scope='function')):return customer_gmail.disconnect(conn,str(connection_id))

@router.post('/gmail/{connection_id}/health',dependencies=[Depends(customer_gmail.require_enabled)])
async def gmail_health(connection_id:uuid.UUID,conn=Depends(get_db,scope='function')):return await customer_gmail.health(conn,str(connection_id))

class SyncRetry(Strict):
    revision:int=Field(ge=1)
    confirmation:Literal['RETRY_SYNC']

@router.post('/gmail/{connection_id}/sync-retry',dependencies=[Depends(customer_gmail.require_enabled)])
def gmail_sync_retry(connection_id:uuid.UUID,body:SyncRetry,conn=Depends(get_db,scope='function')):
    from app.mail.customer import retry_sync
    return retry_sync(conn,str(connection_id),body.revision)

@router.get('/gmail/policy',dependencies=[Depends(customer_gmail.require_enabled)])
def gmail_policy(conn=Depends(get_db,scope='function')):
    from app.mail.customer import policy
    from app.api.organization import membership_role
    from app.platform.context import current
    context=current()
    return {**policy(conn),'can_approve':membership_role(conn,context.actor,context.organization_id)=='OWNER'}

@router.put('/gmail/policy',dependencies=[Depends(customer_gmail.require_enabled)])
def gmail_approve(body:PolicyUpdate,conn=Depends(get_db,scope='function')):
    from app.mail.customer import save_policy
    return save_policy(conn,body)

class MailboxRoute(Strict):account_id:str=Field(max_length=100,pattern=r'^[A-Za-z0-9_-]+$')

@router.put('/campaigns/{campaign_id}/mailbox',dependencies=[Depends(customer_gmail.require_enabled)])
def campaign_mailbox(campaign_id:uuid.UUID,body:MailboxRoute,conn=Depends(get_db,scope='function')):
    from app.mail.customer import route_campaign
    return route_campaign(conn,str(campaign_id),body.account_id)
@router.post('/leads/{lead_id}/preview')
def preview(lead_id:int,body:Message,request:Request,conn=Depends(get_db,scope='function')):
    pid=require_prospect(conn,lead_id,request.state.user_email,organization=request.state.organization_id);return service.preview(conn,pid,request.state.user_email,body.model_dump(),allow_disabled=True)
@router.post('/leads/{lead_id}/send')
def send(lead_id:int,body:Send,request:Request,conn=Depends(get_db,scope='function')):
    pid=require_prospect(conn,lead_id,request.state.user_email,organization=request.state.organization_id);return service.send(conn,pid,request.state.user_email,body.model_dump())
@router.get('/leads/{lead_id}/threads/{thread_id}')
def thread(lead_id:int,thread_id:str,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization)
    if not conn.execute('SELECT 1 FROM email_threads WHERE id=? AND prospect_id=? AND organization_id=?',(thread_id,pid,organization)).fetchone():raise HTTPException(404,'Conversation not found.')
    conn.execute('UPDATE prospect_sales SET unread_replies=0 WHERE prospect_id=? AND organization_id=?',(pid,organization))
    return [{**dict(r),'engagement':tracking.message_summary(conn,r['id']),'verified_reply':bool(conn.execute('SELECT 1 FROM activities WHERE dedup_key=?',('reply-'+r['id'],)).fetchone())} for r in conn.execute('SELECT id,direction,status,from_address,to_address,subject,body_text,sent_at,received_at,report_id,test_mode,created_at,template_id,message_type FROM email_messages WHERE prospect_id=? AND thread_id=? AND organization_id=? ORDER BY created_at',(pid,thread_id,organization)).fetchall()]
@router.get('/templates')
def templates(request:Request,conn=Depends(get_db,scope='function')):
    from app.platform.modules import legacy_enabled
    legacy=legacy_enabled()
    if legacy:seed(conn)
    rows=conn.execute('SELECT * FROM email_templates WHERE organization_id=? ORDER BY name',(request.state.organization_id,)).fetchall()
    from app.mail.templates import LEGACY_SEEDS,COMMERCIAL_IDS
    archived={r[0] for r in LEGACY_SEEDS}|set(COMMERCIAL_IDS)
    return [dict(r) for r in rows if legacy or (r['id'] not in archived and not r['id'].startswith('PB_INTRO_') and r['category']!='Experiment')]
def save_template(conn,key,body,organization=None):
    if not organization:raise HTTPException(403,'A workspace is required.')
    prior=conn.execute('SELECT organization_id FROM email_templates WHERE id=?',(key,)).fetchone()
    if prior and prior['organization_id']!=organization:raise HTTPException(404,'Template not found.')
    from app.mail.templates import COMMERCIAL_IDS
    if key in COMMERCIAL_IDS:
        required=('business_name','opening','observations','business_impact','solution','included_value','cta','signature')
        if any('{{'+v+'}}' not in body.body_text for v in required):raise HTTPException(422,'Approved outreach templates must retain personalization, observations, business impact, solution, included value, CTA and signature variables.')
        if '{{business_name}}' not in body.subject and '{{opportunity_subject}}' not in body.subject:raise HTTPException(422,'The subject must personalize the company or evidence-led opportunity.')
    try:render(body.subject,{});render(body.body_text,{})
    except ValueError:raise HTTPException(422,'Use only supported template variables.')
    service.header(body.subject)
    changed=conn.execute('INSERT INTO email_templates(id,name,category,vertical,subject,body_text,enabled,updated_at,organization_id) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,category=excluded.category,vertical=excluded.vertical,subject=excluded.subject,body_text=excluded.body_text,enabled=excluded.enabled,updated_at=excluded.updated_at WHERE email_templates.organization_id=excluded.organization_id',(key,body.name,body.category,body.vertical,body.subject,body.body_text,int(body.enabled),now(),organization)).rowcount
    if not changed:raise HTTPException(404,'Template not found.')
    return {'id':key}
@router.post('/templates',status_code=201)
def create_template(body:Template,request:Request,conn=Depends(get_db,scope='function')):return save_template(conn,str(uuid.uuid4()),body,request.state.organization_id)
@router.put('/templates/{template_id}')
def update_template(template_id:str,body:Template,request:Request,conn=Depends(get_db,scope='function')):
    if not conn.execute('SELECT 1 FROM email_templates WHERE id=? AND organization_id=?',(template_id,request.state.organization_id)).fetchone():raise HTTPException(404,'Template not found.')
    return save_template(conn,template_id,body,request.state.organization_id)

class ResetTemplate(Strict):confirmation:Literal['RESET']
@router.post('/templates/{template_id}/reset')
def reset_template(template_id:str,body:ResetTemplate,request:Request,conn=Depends(get_db,scope='function')):
    from app.mail.templates import COMMERCIAL_SEEDS
    row=next((r for r in COMMERCIAL_SEEDS if r[0]==template_id),None)
    if not row:raise HTTPException(422,'Reset is available for the four approved outreach variants.')
    key,name,category,subject,text=row
    conn.execute('UPDATE email_templates SET name=?,category=?,subject=?,body_text=?,enabled=1,updated_at=? WHERE id=? AND organization_id=?',(name,category,subject,text,now(),key,request.state.organization_id))
    return {'reset':True}


class TrackingPreferences(Strict):
    track_opens:bool
    track_clicks:bool
    track_replies:Literal[True]=True
    track_bounces:Literal[True]=True

@router.patch('/tracking')
def update_tracking(body:TrackingPreferences,conn=Depends(get_db,scope='function')):
    from app.platform.context import organization
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    org=organization()
    if org!=PLANEBYTE_ORGANIZATION_ID:
        customer_gmail.require_enabled()
        conn.execute('''INSERT INTO customer_mail_tracking_preferences(organization_id,track_opens,track_clicks,track_replies,track_bounces)
            VALUES(?,?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET track_opens=excluded.track_opens,track_clicks=excluded.track_clicks,
            track_replies=excluded.track_replies,track_bounces=excluded.track_bounces''',(org,*tuple(int(v) for v in body.model_dump().values())))
        return tracking.preferences(conn)
    conn.execute('UPDATE email_tracking_preferences SET track_opens=?,track_clicks=?,track_replies=?,track_bounces=? WHERE id=1',tuple(int(v) for v in body.model_dump().values()))
    return tracking.preferences(conn)

@router.put('/leads/{lead_id}/draft')
def draft(lead_id:int,body:Message,request:Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id;pid=require_prospect(conn,lead_id,request.state.user_email,organization=organization)
    if service.suppressed(conn,pid):raise HTTPException(409,'This prospect is marked Do Not Contact.')
    conn.execute('INSERT INTO email_drafts(id,prospect_id,actor,payload_json,updated_at,organization_id) VALUES(?,?,?,?,?,?) ON CONFLICT(prospect_id,actor) DO UPDATE SET payload_json=excluded.payload_json,updated_at=excluded.updated_at WHERE email_drafts.organization_id=excluded.organization_id',(str(uuid.uuid4()),pid,request.state.user_email,json.dumps(body.model_dump()),now(),organization))
    return {'status':'DRAFT'}

@router.get('/activity-summary')
def activity_summary(request:Request,days:Literal[1,7,30]=30,tz:str=Query('Asia/Kolkata',max_length=80),conn=Depends(get_db,scope='function')):
    from datetime import datetime,timedelta,timezone
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    try:local=datetime.now(ZoneInfo(tz))
    except ZoneInfoNotFoundError:raise HTTPException(422,'Choose a valid timezone.')
    organization=request.state.organization_id
    start=(local.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=days-1)).astimezone(timezone.utc).isoformat()
    # Test signals stay separate from actual prospect engagement.
    counts=[dict(r) for r in conn.execute('SELECT e.event_type,m.test_mode,COUNT(DISTINCT e.message_id) AS count FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.occurred_at>=? AND e.suspected_bot=0 AND m.organization_id=? GROUP BY e.event_type,m.test_mode',(start,organization)).fetchall()]
    automated=conn.execute('SELECT COUNT(*) FROM email_engagement_events WHERE occurred_at>=? AND suspected_bot=1',(start,)).fetchone()[0]
    templates=[dict(r) for r in conn.execute("SELECT t.id,t.name,e.event_type,m.test_mode,COUNT(DISTINCT m.id) AS count FROM email_templates t JOIN email_messages m ON m.template_id=t.id JOIN email_engagement_events e ON e.message_id=m.id WHERE e.occurred_at>=? AND e.suspected_bot=0 AND m.organization_id=? GROUP BY t.id,t.name,e.event_type,m.test_mode",(start,organization)).fetchall()]
    return {'days':days,'counts':counts,'automated_signals':automated,'templates':templates}


@router.get('/company-pdf/{version}')
def company_pdf(version:str,conn=Depends(get_db,scope='function')):
    from app.outreach.fixed import attachment,ASSET_ID
    from fastapi.responses import Response
    raw,name=attachment(conn,{'pdf_asset_id':ASSET_ID,'pdf_version':version})
    return Response(raw,media_type='application/pdf',headers={'Content-Disposition':'inline; filename="PlaneByte Capabilities & Services.pdf"','Cache-Control':'private, no-store'})

@router.get('/intro-analytics')
def intro_analytics(conn=Depends(get_db,scope='function')):
    from app.outreach.analytics import summary
    return summary(conn)
