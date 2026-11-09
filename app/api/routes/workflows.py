"""Manual runs and explicitly enabled user schedules; no credential exposure."""
import json,uuid
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter,Depends,Request,HTTPException,Query
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.api.dependencies import get_db
from app.database.prospects import now
from app.workflows import service
from app.workflows.calendar import next_due,cron_fields
from app.config.locations import Location,country
from app.acquisition.models import SearchIntent,Budgets
router=APIRouter(prefix='/workflow',tags=['Manual workspace'])
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Filters(Strict):
 country:str=Field('',max_length=100)
 city:str=Field('',max_length=100)
 vertical:str=Field('',max_length=100)
 commercial_fit:Literal['','HIGH','MEDIUM','LOW','UNKNOWN']=''
 opportunity:Literal['','WEBSITE','SEO','SECURITY']=''
 email_availability:Literal['','yes','no']='yes'
 discovered_from:str=Field('',max_length=40)
 discovered_to:str=Field('',max_length=40)
from app.prospecting.criteria import SearchCriteria
class Run(Strict):
 account_id:str|None=Field(None,max_length=100,pattern=r'^[A-Za-z0-9_-]+$')
 search_criteria:SearchCriteria=Field(default_factory=SearchCriteria)
 request_id:str=Field(default_factory=lambda:str(uuid.uuid4()),pattern=r'^[a-f0-9-]{36}$')
 name:str=Field(default='',max_length=120)
 kind:Literal['SCAN','OUTREACH','COMBINED']
 scan_source:Literal['OVERTURE','FIRECRAWL']='OVERTURE'
 ai_prompt:str=Field('',max_length=2000)
 firecrawl_intent:SearchIntent|None=None
 firecrawl_reviewed:bool=False
 acquisition_budgets:Budgets=Field(default_factory=Budgets)
 qualification_mode:Literal['CONTACTABLE_ONLY','EXPLORATORY','BALANCED','STRICT']='CONTACTABLE_ONLY'
 preliminary_opportunity_threshold:int=Field(10,ge=1,le=100)
 qualified_score_threshold:int=Field(35,ge=1,le=100)
 max_candidates:int=Field(300,ge=1,le=1000)
 max_runtime_seconds:int=Field(1200,ge=60,le=3600)
 analysis_reuse_days:int=Field(7,ge=1,le=90)
 deep_audit_budget:int=Field(0,ge=0,le=200,deprecated=True)
 lighthouse_budget:int=Field(0,ge=0,le=50,deprecated=True)
 email_enrichment_reuse_days:int=Field(7,ge=1,le=90)
 target:int=Field(50,ge=1,le=1000)
 countries:list[str]=Field(default_factory=lambda:['United Kingdom'],min_length=1,max_length=10)
 cities:list[str]=Field(default_factory=list,max_length=10)
 locations:list[Location]=Field(default_factory=list,max_length=10)
 verticals:list[str]=Field(default_factory=lambda:['hospitality'],min_length=1,max_length=8)
 opportunities:list[Literal['WEBSITE','SEO','SECURITY']]=Field(default_factory=list,max_length=3,deprecated=True)
 business_scales:list[Literal['LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL']]=Field(default_factory=lambda:['LOCAL','SMALL_GROUP','MID_MARKET'],min_length=1,max_length=4)
 commercial_fit:list[Literal['HIGH','MEDIUM']]=Field(default_factory=lambda:['HIGH','MEDIUM'],min_length=1,max_length=2)
 rotate_locations:bool=True
 rotate_verticals:bool=True
 analysis_mode:Literal['INCREMENTAL','FULL']='INCREMENTAL'
 full_refresh_confirmed:bool=False
 campaign_id:str|None=Field(None,max_length=36)
 template_id:str|None=Field(None,max_length=60)
 icp_id:uuid.UUID|None=None
 pitch_types:list[Literal['WEBSITE','SEO','SECURITY']]=Field(default_factory=list,max_length=3,deprecated=True)
 outreach_mode:Literal['UNCONTACTED','RECONTACT']='UNCONTACTED'
 confirm_recontact:bool=False
 email_all_eligible:bool=False
 needs_owner_review:bool=False
 minimum_score:int=Field(0,ge=0,le=100)
 filters:Filters=Field(default_factory=Filters)
 max_hour:int=Field(5,ge=1,le=50)
 max_day:int=Field(100,ge=1,le=500)
 spacing_minutes:float=Field(1.2,ge=1.2,le=1440)
 window_start:str=Field('09:00',pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')
 window_end:str=Field('17:00',pattern=r'^(?:[01]\d|2[0-3]):[0-5]\d$')
 recipient_timezone:bool=True
 @model_validator(mode='after')
 def limits(self):

  from app.automation.service import CITIES
  from app.config.verticals import get_vertical_manager
  if any(not value.strip() or len(value)>100 or any(ord(ch)<32 for ch in value) for value in self.verticals):raise ValueError('Use a bounded industry name.')
  if self.kind!='OUTREACH' and self.scan_source=='OVERTURE' and any(value not in get_vertical_manager().verticals for value in self.verticals):raise ValueError('This industry needs reviewed web discovery. Maps currently supports the listed categories; choose AI discovery for another industry.')
  if self.kind!='OUTREACH' and self.scan_source=='FIRECRAWL':
   if not self.ai_prompt.strip() or not self.firecrawl_intent or not self.firecrawl_reviewed:raise ValueError('Interpret and review the AI + Firecrawl schedule instruction first.')
   if self.firecrawl_intent.targetQualifiedLeads!=self.target:raise ValueError('The reviewed AI target must match the scheduled contactable-lead target.')
   self.countries=self.firecrawl_intent.countries;self.cities=self.firecrawl_intent.cities;self.verticals=self.firecrawl_intent.verticals
   # Reviewed Firecrawl geography is authoritative. Coordinates belong only
   # to the Maps form and must not override a switched schedule's intent.
   self.locations=[]
  self.countries=list(dict.fromkeys(country(c).name for c in self.countries))
  if self.locations:
   self.countries=list(dict.fromkeys(x.country for x in self.locations))
   self.cities=list(dict.fromkeys(', '.join(dict.fromkeys(x for x in (loc.city,loc.region) if x)) for loc in self.locations))
  elif self.kind!='OUTREACH' and self.scan_source=='OVERTURE' and (any(c not in CITIES for c in self.countries) or self.cities and any(not any(city in CITIES[country] for country in self.countries) for city in self.cities)):
   raise ValueError('Select explicit city results for custom or global locations.')
  if self.window_start>=self.window_end:raise ValueError('Send window must end after it starts.')
  if self.kind=='OUTREACH' and not self.campaign_id:raise ValueError('Select Campaign is required.')
  if self.kind=='OUTREACH' and self.outreach_mode=='RECONTACT' and not self.confirm_recontact:raise ValueError('Confirm re-contact before proceeding.')
  return self
class Schedule(Strict):
 name:str=Field(min_length=1,max_length=120)
 configuration:Run
 enabled:bool=False
 timezone:str=Field('Asia/Kolkata',max_length=80)
 frequency:Literal['once','daily','weekdays','weekly','custom']='daily'
 cron_expression:str|None=Field(None,max_length=100)
 start_at:str=Field(max_length=40)
 @model_validator(mode='after')
 def calendar(self):
  if self.configuration.kind!='OUTREACH' and 'scan_source' not in self.configuration.model_fields_set:raise ValueError('Select the scan source explicitly: Overture / Maps or AI + Firecrawl.')
  try:ZoneInfo(self.timezone)
  except (KeyError,ValueError):raise ValueError('Choose a valid IANA timezone.')
  if datetime.fromisoformat(self.start_at.replace('Z','+00:00')).tzinfo is None:raise ValueError('Start time requires a timezone offset.')
  if self.frequency=='custom':cron_fields(self.cron_expression or '')
  return self
class ItemEdit(Strict):
 subject:str=Field(min_length=1,max_length=200)
 body_text:str=Field(min_length=1,max_length=20000)
class Confirm(Strict):confirmation:Literal['DELETE']

@router.get('/dashboard')
def dashboard(request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 from app.workflows.dashboard import summary
 return summary(c,organization)
@router.get('/runs')
def runs(request:Request,page:int=Query(1,ge=1),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 return {'items':[{**dict(r),'configuration':json.loads(r['configuration_json'])} for r in c.execute('SELECT * FROM workflow_runs WHERE organization_id=? ORDER BY created_at DESC LIMIT 25 OFFSET ?',(organization,(page-1)*25)).fetchall()],'total':c.execute('SELECT COUNT(*) FROM workflow_runs WHERE organization_id=?',(organization,)).fetchone()[0]}
@router.post('/eligible')
def eligible(body:Run,request:Request,c=Depends(get_db,scope='function')):
 from app.workflows.campaigns import audience
 data=audience(c,body.campaign_id,body.pitch_types,body.outreach_mode,require_complete=True,organization=request.state.organization_id)
 data['total']=data['will_queue'];data.pop('items');return data
@router.post('/runs',status_code=201)
def create(body:Run,request:Request,c=Depends(get_db,scope='function')):
 return service.create(c,body.model_dump(mode='json'),request.state.user_email,organization=request.state.organization_id)
@router.get('/runs/{rid}')
def detail(rid:str,page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),status:str=Query("",max_length=40),search:str=Query("",max_length=200),c=Depends(get_db,scope='function')):
 return service.detail(c,rid,page,page_size,status,search)
@router.post('/runs/{rid}/prepare')
def prepare(rid:str,c=Depends(get_db,scope='function')):
 service.prepare(c,rid);c.commit()
 return service.detail(c,rid)
@router.post('/runs/{rid}/start')
async def start(rid:str,c=Depends(get_db,scope='function')):
 r=service.start(c,rid);c.commit()
 if r['kind'] in ('SCAN','COMBINED'):await service.advance_scan(c,rid)
 return service.detail(c,rid)
@router.post('/runs/{rid}/{action}')
async def action(rid:str,action:Literal['pause','resume','stop'],request:Request,c=Depends(get_db,scope='function')):
 from app.api.services.scan_manager import scan_manager
 organization=request.state.organization_id
 service.lock(c);r=service.row(c,rid,organization=organization)
 if r['kind']!='OUTREACH' and json.loads(r['configuration_json']).get('scan_source')=='FIRECRAWL':
  from app.acquisition.scheduling import control
  await control(c,r,action)
  return service.detail(c,rid)
 if action=='resume':
  from app.workflows.controls import require_unpaused
  require_unpaused(c,'email' if r['kind']=='OUTREACH' else 'scan')
  if r['status'] not in ('PAUSED','NEEDS_REVIEW'):raise HTTPException(409,'Run is not paused.')
  if r['scan_run_id']:
   c.execute("UPDATE workflow_runs SET status='RUNNING',error=NULL WHERE id=? AND organization_id=?",(rid,organization));c.commit();await scan_manager.resume_scan(r['scan_run_id'])
  else:
   c.execute("UPDATE workflow_runs SET status='DRAFT' WHERE id=? AND organization_id=?",(rid,organization));service.start(c,rid)
 else:
  c.execute('UPDATE workflow_runs SET status=?,completed_at=? WHERE id=? AND organization_id=?',('PAUSED' if action=='pause' else 'CANCELLED',None if action=='pause' else now(),rid,organization))
  if action=='stop':
   c.execute("UPDATE outreach_run_items SET status='SKIPPED',error='Cancelled by owner.' WHERE run_id=? AND organization_id=? AND status IN ('QUEUED','READY','PREPARING')",(rid,organization))
   c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE status='QUEUED' AND prospect_id IN (SELECT prospect_id FROM outreach_run_items WHERE run_id=? AND organization_id=?)",(rid,organization))
  c.commit()
  if r['scan_run_id']:await scan_manager.cancel_scan(r['scan_run_id'])
 return service.detail(c,rid)
@router.put('/items/{iid}')
def edit_item(iid:str,body:ItemEdit,request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 i=c.execute('SELECT * FROM outreach_run_items WHERE id=? AND organization_id=?',(iid,organization)).fetchone()
 if not i:raise HTTPException(404,'Email item not found.')
 run=service.row(c,i['run_id'],organization=organization)
 if run['status']=='RUNNING' or i['message_id']:raise HTTPException(409,'Pause this run before editing unsent items.')
 payload=json.loads(i['payload_json'] or '{}')
 if not payload:raise HTTPException(409,'Prepare this report and email first.')
 payload.update(body.model_dump());payload.pop('preview_token',None)
 c.execute("UPDATE outreach_run_items SET payload_json=?,preview_json=NULL,status='QUEUED' WHERE id=? AND organization_id=?",(json.dumps(payload),iid,organization))
 c.execute("UPDATE workflow_runs SET status='DRAFT' WHERE id=? AND organization_id=?",(run['id'],organization));service.prepare(c,run['id']);return service.detail(c,run['id'])
@router.post('/items/{iid}/{action}')
def item_action(iid:str,action:Literal['cancel','retry'],request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 i=c.execute('SELECT * FROM outreach_run_items WHERE id=? AND organization_id=?',(iid,organization)).fetchone()
 if not i:raise HTTPException(404,'Email item not found.')
 if action=='retry':
  message=c.execute('SELECT status FROM email_messages WHERE idempotency_key=? AND organization_id=?',(i['idempotency_key'],organization)).fetchone()
  if message and message[0]!='FAILED':raise HTTPException(409,'Accepted or uncertain messages cannot be retried.')
  if message:raise HTTPException(409,'Review the failed message and create a new email run after confirming no delivery.')
  if service.row(c,i['run_id'],organization=organization)['status']=='RUNNING':raise HTTPException(409,'Pause before retrying this item.')
  c.execute("UPDATE outreach_run_items SET status='QUEUED',error=NULL WHERE id=? AND organization_id=?",(iid,organization));c.execute("UPDATE workflow_runs SET status='DRAFT' WHERE id=? AND organization_id=?",(i['run_id'],organization));service.prepare(c,i['run_id'])
 else:
  if i['message_id']:raise HTTPException(409,'A sent message cannot be cancelled.')
  c.execute("UPDATE outreach_run_items SET status='SKIPPED',error='Cancelled by owner.' WHERE id=? AND organization_id=?",(iid,organization));c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE status='QUEUED' AND prospect_id IN (SELECT id FROM prospects WHERE id=? AND organization_id=?)",(i['prospect_id'],organization))
 return service.detail(c,i['run_id'])
@router.get('/schedules')
def schedules(request:Request,c=Depends(get_db,scope='function')):
 return [{**dict(r),'configuration':json.loads(r['configuration_json'])} for r in c.execute('SELECT * FROM automation_schedules WHERE organization_id=? AND deleted_at IS NULL ORDER BY created_at DESC',(request.state.organization_id,)).fetchall()]
def save_schedule(c,body,actor,sid=None,organization=None):
 from app.platform.context import organization as active_organization
 organization=active_organization(organization)
 if sid:
  prior=c.execute('SELECT organization_id FROM automation_schedules WHERE id=?',(sid,)).fetchone()
  if prior and prior['organization_id']!=organization:raise HTTPException(404,'Schedule not found.')
 if body.configuration.needs_owner_review and body.enabled:raise HTTPException(409,'Review and save the audience before enabling.')
 if body.configuration.kind=='OUTREACH':
  from app.workflows.campaigns import campaign
  campaign(c,body.configuration.campaign_id,organization=organization)
 sid=sid or str(uuid.uuid4());d=body.model_dump(mode='json');due=next_due(d)
 if body.enabled and due is None:raise HTTPException(422,'Choose a future start time.')
 c.execute('INSERT INTO automation_schedules(id,name,kind,enabled,configuration_json,timezone,frequency,cron_expression,start_at,next_run_at,created_by,created_at,updated_at,organization_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,kind=excluded.kind,enabled=excluded.enabled,configuration_json=excluded.configuration_json,timezone=excluded.timezone,frequency=excluded.frequency,cron_expression=excluded.cron_expression,start_at=excluded.start_at,next_run_at=excluded.next_run_at,updated_at=excluded.updated_at WHERE automation_schedules.organization_id=excluded.organization_id',(sid,body.name,body.configuration.kind,int(body.enabled),json.dumps(body.configuration.model_dump(mode='json')),body.timezone,body.frequency,body.cron_expression,body.start_at,due,actor,now(),now(),organization));return {'id':sid}
@router.post('/schedules',status_code=201)
def create_schedule(body:Schedule,request:Request,c=Depends(get_db,scope='function')):return save_schedule(c,body,request.state.user_email,organization=request.state.organization_id)
@router.put('/schedules/{sid}')
def update_schedule(sid:str,body:Schedule,request:Request,c=Depends(get_db,scope='function')):
 if not c.execute('SELECT 1 FROM automation_schedules WHERE id=? AND organization_id=? AND deleted_at IS NULL',(sid,request.state.organization_id)).fetchone():raise HTTPException(404,'Schedule not found.')
 return save_schedule(c,body,request.state.user_email,sid,organization=request.state.organization_id)
@router.delete('/schedules/{sid}')
def delete_schedule(sid:str,body:Confirm,request:Request,c=Depends(get_db,scope='function')):
 c.execute('UPDATE automation_schedules SET enabled=0,deleted_at=?,updated_at=? WHERE id=? AND organization_id=?',(now(),now(),sid,request.state.organization_id));return {'deleted':True}
@router.get('/schedules/{sid}/history')
def history(sid:str,request:Request,c=Depends(get_db,scope='function')):
 if not c.execute('SELECT 1 FROM automation_schedules WHERE id=? AND organization_id=? AND deleted_at IS NULL',(sid,request.state.organization_id)).fetchone():raise HTTPException(404,'Schedule not found.')
 return [dict(r) for r in c.execute('SELECT h.*,r.name,r.kind,r.requested,r.result_count,r.scan_run_id FROM automation_schedule_runs h LEFT JOIN workflow_runs r ON r.id=h.workflow_run_id WHERE h.schedule_id=? ORDER BY h.started_at DESC LIMIT 100',(sid,)).fetchall()]
@router.post('/schedules/{sid}/{action}')
async def schedule_action(sid:str,action:Literal['enable','disable','pause','duplicate','run-now'],request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 s=c.execute('SELECT * FROM automation_schedules WHERE id=? AND organization_id=? AND deleted_at IS NULL',(sid,organization)).fetchone()
 if not s:raise HTTPException(404,'Schedule not found.')
 if json.loads(s['configuration_json']).get('experiment_id') and action not in ('disable','pause'):raise HTTPException(409,'Manage this fixed experiment schedule from the experiment controls; its date/source allocation is immutable.')
 if action in ('enable','run-now','duplicate') and json.loads(s['configuration_json']).get('needs_owner_review'):raise HTTPException(409,'Review and save the campaign audience configuration first; the legacy fixed email limit was not broadened.')
 if action in ('enable','disable','pause'):
  due=next_due(dict(s)) if action=='enable' else s['next_run_at']
  if action=='enable' and due is None:raise HTTPException(422,'Edit this once-only schedule to a future time.')
  c.execute('UPDATE automation_schedules SET enabled=?,next_run_at=?,updated_at=? WHERE id=? AND organization_id=?',(int(action=='enable'),due,now(),sid,organization));return {'saved':True}
 if action=='duplicate':
  saved=json.loads(s['configuration_json']);saved.setdefault('scan_source','OVERTURE')
  body=Schedule(name=s['name']+' copy',configuration=saved,enabled=False,timezone=s['timezone'],frequency=s['frequency'],cron_expression=s['cron_expression'],start_at=s['start_at']);return save_schedule(c,body,request.state.user_email,organization=organization)
 service.lock(c)
 active=c.execute("SELECT h.workflow_run_id FROM automation_schedule_runs h JOIN workflow_runs r ON r.id=h.workflow_run_id WHERE h.schedule_id=? AND r.organization_id=? AND r.status IN ('DRAFT','PREPARING','RUNNING','PAUSED','NEEDS_REVIEW') ORDER BY h.started_at DESC LIMIT 1",(sid,organization)).fetchone()
 if active:return {'run_id':active[0]}
 options=json.loads(s['configuration_json']);options['request_id']=str(uuid.uuid4());options['_schedule_trigger']='RUN_NOW';r=service.create(c,options,request.state.user_email,schedule_id=sid,organization=organization)
 c.execute("UPDATE automation_schedules SET last_run_at=?,next_run_at=CASE WHEN frequency='once' THEN NULL ELSE next_run_at END WHERE id=? AND organization_id=?",(now(),sid,organization))
 c.execute("INSERT INTO automation_schedule_runs(id,schedule_id,workflow_run_id,due_at,status,started_at) VALUES(?,?,?,?,'RUNNING',?)",(str(uuid.uuid4()),sid,r['id'],'manual:'+options['request_id'],now()))
 if r['kind']=='OUTREACH':service.prepare(c,r['id'])
 else:service.start(c,r['id']);c.commit();await service.advance_scan(c,r['id'])
 return {'run_id':r['id']}

@router.get('/messages/{mid}')
def message_detail(mid:str,request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 r=c.execute('SELECT m.*,b.id business_id,b.name FROM email_messages m JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=m.prospect_id) WHERE m.id=? AND m.organization_id=?',(mid,organization)).fetchone()
 if not r:raise HTTPException(404,'Email not found.')
 result=dict(r)
 from app.api.routes.operations import MESSAGE_BASE
 linkage=c.execute('SELECT COALESCE(w.campaign_id,ps.campaign_id) campaign_id,sc.configuration_json campaign_configuration,i.payload_json'+MESSAGE_BASE+' WHERE m.id=?',(mid,)).fetchone()
 result['campaign_id']=linkage['campaign_id'] if linkage else None
 result['campaign_name']=(json.loads(linkage['campaign_configuration'] or '{}').get('name') or 'Campaign') if linkage and linkage['campaign_id'] else 'Individual / legacy'
 result['pitch_types']=json.loads(linkage['payload_json'] or '{}').get('pitch_types',[]) if linkage else []
 if not result.get('rendered_html') and result['status']=='SENT' and result['direction']=='OUTBOUND':
  # Historical messages predate rendered-body persistence; read the exact Sent MIME.
  from app.mail.providers import provider
  from email import policy
  from email.parser import BytesParser
  p=provider();client=None
  try:
   client=p.imap();client.select(p.sent_mailbox(client),readonly=True)
   status,ids=client.uid('search',None,'HEADER','Message-ID','"'+result['provider_message_id']+'"')
   if status=='OK' and ids[0]:
    status,data=client.uid('fetch',ids[0].split()[-1],'(BODY.PEEK[])')
    message=BytesParser(policy=policy.default).parsebytes(next(x[1] for x in data if isinstance(x,tuple)))
    html=message.get_body(preferencelist=('html',));plain=message.get_body(preferencelist=('plain',))
    result['rendered_html']=html.get_content() if html else '';result['rendered_text']=plain.get_content() if plain else ''
    c.execute('UPDATE email_messages SET rendered_html=?,rendered_text=? WHERE id=? AND organization_id=?',(result['rendered_html'],result['rendered_text'],mid,organization))
  except Exception:result['content_notice']='Historical MIME is temporarily unavailable from Gmail. Stored original text is shown.'
  finally:
   if client:
    try:client.logout()
    except Exception:pass
 from app.mail.tracking import message_summary
 result['engagement']=message_summary(c,mid)
 result['timeline']=[dict(a) for a in c.execute('SELECT event_type,event_at,metadata_json FROM activities WHERE prospect_id=? AND organization_id=? ORDER BY event_at DESC LIMIT 100',(result['prospect_id'],organization)).fetchall() if json.loads(a['metadata_json']).get('message_id')==mid]
 result['smtp_result']='SMTP accepted' if result['status']=='SENT' else result.get('error_code') or result['status']
 result['attachments']=[{'filename':'PlaneByte digital review.pdf','report_id':result['report_id']}] if result['report_id'] else []
 return result

@router.get('/messages')
def messages(request:Request,direction:Literal['OUTBOUND','INBOUND']='OUTBOUND',page:int=Query(1,ge=1),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 return {'items':[dict(r) for r in c.execute('SELECT m.id,m.subject,m.to_address,m.from_address,m.status,m.created_at,m.sent_at,m.test_mode,m.thread_id,m.report_id,m.body_text,b.name,b.id business_id FROM email_messages m JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=m.prospect_id) WHERE m.organization_id=? AND m.direction=? ORDER BY m.created_at DESC LIMIT 25 OFFSET ?',(organization,direction,(page-1)*25)).fetchall()],'total':c.execute('SELECT COUNT(*) FROM email_messages WHERE organization_id=? AND direction=?',(organization,direction)).fetchone()[0]}

@router.get('/defaults')
def defaults(request:Request,c=Depends(get_db,scope='function')):
 from app.api.organization import workspace_settings
 return (workspace_settings(c,request.state.organization_id) or {}).get('manual_defaults')

@router.put('/defaults')
def save_defaults(body:Run,request:Request,c=Depends(get_db,scope='function')):
 from app.api.organization import workspace_settings,save_workspace_settings
 if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944520)')
 data=workspace_settings(c,request.state.organization_id) or {}
 data['manual_defaults']=body.model_dump(mode='json')
 save_workspace_settings(c,request.state.organization_id,data,request.state.user_email)
 return {'saved':True}

@router.get('/safety')
def safety(c=Depends(get_db,scope='function')):
 from app.automation.settings import effective_settings
 from app.mail.limits import MAX_PER_HOUR,MAX_PER_DAY,MIN_SPACING_SECONDS
 s=effective_settings(c)
 return {'max_hour':min(MAX_PER_HOUR,s.max_hour),'max_day':min(MAX_PER_DAY,s.max_day),'minimum_spacing_minutes':max(MIN_SPACING_SECONDS/60,60/min(MAX_PER_HOUR,s.max_hour)),'bounce_pause_threshold':s.high_bounce_rate,'bounce_min_sample':s.bounce_min_sample,'sending_enabled':s.sending_enabled}
