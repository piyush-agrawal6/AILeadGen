"""Paginated operational read models; execution stays in the existing services."""
import json,uuid
from typing import Literal
from fastapi import APIRouter,Depends,Query,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import get_db
from app.database.prospects import now
from app.workflows.campaigns import campaign_summary,audience
router=APIRouter(prefix='/operations',tags=['Operations UI'])

def page_result(items,total,page,size,**extra):return {'items':items,'total':total,'page':page,'page_size':size,'total_pages':max(1,(total+size-1)//size),**extra}

@router.get('/campaigns')
def campaigns(request:Request,source_type:Literal['','OVERTURE','FIRECRAWL','FILE_IMPORT','CSV','XLSX','GOOGLE_SHEETS']=Query(''),search:str=Query('',max_length=200),status:str=Query('',max_length=30),market:str=Query('',max_length=100),vertical:str=Query('',max_length=80),created_from:str=Query('',max_length=40),created_to:str=Query('',max_length=40),sort:Literal['newest','name','qualified']='newest',page:int=Query(1,ge=1),page_size:int=Query(15,ge=1,le=50),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 conditions=['s.organization_id=?'];args=[organization]
 from app.database.acquisition_schema import ready as source_ready
 if not isinstance(source_type,str):source_type=''
 if source_type:
  if source_ready(c):
   if source_type in ('CSV','XLSX'):
    conditions.append("s.source_type='FILE_IMPORT' AND s.id IN (SELECT campaign_id FROM acquisition_jobs WHERE source_type='FILE_IMPORT' AND REPLACE(manifest_json,' ','') LIKE ? AND organization_id=?)");args.extend(['%"file_format":"'+source_type+'"%',organization])
   else:conditions.append('s.source_type=?');args.append(source_type)
  elif source_type!='OVERTURE':conditions.append('1=0')
 if search:conditions.append("(LOWER(s.configuration_json) LIKE ? OR LOWER(s.id) LIKE ? OR LOWER(w.name) LIKE ?)");args.extend(['%'+search.lower()+'%']*3)
 if market:conditions.append("EXISTS(SELECT 1 FROM pipeline_runs r WHERE r.campaign_id=s.id AND r.organization_id=? AND LOWER(r.market) LIKE ?)");args.extend([organization,'%'+market.lower()+'%'])
 if vertical:conditions.append("EXISTS(SELECT 1 FROM pipeline_runs r WHERE r.campaign_id=s.id AND r.organization_id=? AND r.vertical=?)");args.extend([organization,vertical])
 if status:conditions.append('COALESCE(w.status,s.status)=?');args.append(status)
 for val,op in [(created_from,'>='),(created_to,'<=')]:
  if val:conditions.append('s.created_at'+op+'?');args.append(val+('T23:59:59+00:00' if op=='<=' and len(val)==10 else ''))
 base=" FROM scan_campaigns s LEFT JOIN workflow_runs w ON w.id=s.id AND w.kind IN ('SCAN','COMBINED') WHERE "+' AND '.join(conditions)
 total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
 order={'newest':'s.created_at DESC','name':'s.configuration_json','qualified':"(SELECT COUNT(DISTINCT b.prospect_id) FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=s.id AND r.organization_id=? AND b.processing_status='QUALIFIED') DESC"}[sort]
 ids=[r[0] for r in c.execute('SELECT s.id'+base+' ORDER BY '+order+' LIMIT ? OFFSET ?',[*args,*([organization] if sort=='qualified' else []),page_size,(page-1)*page_size]).fetchall()]
 from app.workflows.campaigns import batch_data
 batch=batch_data(c,ids)
 return page_result([campaign_summary(c,cid,_batch=batch) for cid in ids],total,page,page_size)

@router.get('/campaigns/{cid}')
def detail(cid:str,request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 if not c.execute('SELECT 1 FROM scan_campaigns WHERE id=? AND organization_id=?',(cid,organization)).fetchone():raise HTTPException(404,'Campaign not found')
 result=campaign_summary(c,cid)
 result['reports']=[dict(r) for r in c.execute('SELECT p.id,p.business_id,p.version,p.status,p.created_at,b.name FROM client_reports p JOIN businesses b ON b.id=p.business_id JOIN pipeline_runs s ON s.id=b.run_id WHERE s.campaign_id=? AND p.organization_id=? ORDER BY p.created_at DESC LIMIT 20',(cid,organization)).fetchall()]
 return result

@router.get('/campaigns/{cid}/leads')
def campaign_leads(cid:str,request:Request,search:str=Query('',max_length=200),status:str=Query('',max_length=40),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 if not c.execute('SELECT 1 FROM scan_campaigns WHERE id=? AND organization_id=?',(cid,organization)).fetchone():raise HTTPException(404,'Campaign not found')
 data=audience(c,cid);rows=[b for b in data['items'] if (not search or search.lower() in ' '.join(str(b.get(k) or '') for k in ('name','domain','public_email','phone')).lower()) and (not status or b['disposition']==status)]
 return page_result(rows[(page-1)*page_size:page*page_size],len(rows),page,page_size,accounting=data['accounting'],qualified=data['qualified'],total_accounted=data['total_accounted'])

@router.get('/runs')
def runs(request:Request,kind:str=Query('',max_length=20),campaign_id:str=Query('',max_length=36),status:str=Query('',max_length=30),search:str=Query('',max_length=200),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 where=['r.organization_id=?'];args=[organization]
 for value,column in [(kind,'r.kind'),(campaign_id,'r.campaign_id'),(status,'r.status')]:
  if value:where.append(column+'=?');args.append(value)
 if search:where.append('LOWER(r.name) LIKE ?');args.append('%'+search.lower()+'%')
 base=' FROM workflow_runs r LEFT JOIN scan_campaigns c ON c.id=r.campaign_id WHERE '+' AND '.join(where)
 total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
 rows=[]
 for r in c.execute('SELECT r.*,c.configuration_json campaign_configuration'+base+' ORDER BY r.created_at DESC LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall():
  item=dict(r);item['configuration']=json.loads(item.pop('configuration_json'));campaign=json.loads(item.pop('campaign_configuration') or '{}');item['campaign_name']=campaign.get('name') or ' / '.join(campaign.get('cities') or []) or 'Campaign';rows.append(item)
 return page_result(rows,total,page,page_size)

MESSAGE_BASE=""" FROM email_messages m
 JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=m.prospect_id)
 LEFT JOIN prospect_sales sales ON sales.prospect_id=m.prospect_id
 LEFT JOIN master_lead_state master ON master.prospect_id=m.prospect_id
 LEFT JOIN outreach_run_items i ON i.id=(SELECT ri.id FROM outreach_run_items ri JOIN email_messages source ON source.id=ri.message_id WHERE source.thread_id=m.thread_id ORDER BY source.created_at DESC,ri.id LIMIT 1) LEFT JOIN workflow_runs w ON w.id=i.run_id
 LEFT JOIN client_reports p ON p.id=COALESCE(m.report_id,(SELECT source.report_id FROM email_messages source WHERE source.thread_id=m.thread_id AND source.direction='OUTBOUND' AND source.report_id IS NOT NULL ORDER BY source.created_at DESC,source.id LIMIT 1)) LEFT JOIN businesses pb ON pb.id=p.business_id
 LEFT JOIN pipeline_runs ps ON ps.id=pb.run_id LEFT JOIN scan_campaigns sc ON sc.id=COALESCE(w.campaign_id,ps.campaign_id)
 """
@router.get('/messages')
def messages(request:Request,search:str=Query('',max_length=200),campaign_id:str=Query('',max_length=36),pitch:str=Query('',max_length=20),status:str=Query('',max_length=30),engagement:str=Query('',max_length=30),reply_state:Literal['','unread','awaiting','closed']='',sender:str=Query('',max_length=254),direction:Literal['OUTBOUND','INBOUND']='OUTBOUND',created_from:str=Query('',max_length=40),created_to:str=Query('',max_length=40),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 where=['m.organization_id=?','m.direction=?'];args=[organization,direction]
 if sender:where.append('LOWER(m.from_address)=?');args.append(sender.lower())
 if reply_state=='unread':where.append('COALESCE(sales.unread_replies,0)>0')
 elif reply_state=='awaiting':where.append("master.sales_state='REPLIED' AND COALESCE(sales.unread_replies,0)=0")
 elif reply_state=='closed':where.append("master.sales_state IN ('WON','LOST','REJECTED','NOT_INTERESTED')")
 if search:where.append('(LOWER(b.name) LIKE ? OR LOWER(m.subject) LIKE ? OR LOWER(m.to_address) LIKE ? OR LOWER(m.from_address) LIKE ?)');args.extend(['%'+search.lower()+'%']*4)
 if campaign_id:where.append('COALESCE(w.campaign_id,ps.campaign_id)=?');args.append(campaign_id)
 if status:where.append('m.status=?');args.append(status)
 if pitch:where.append('i.payload_json LIKE ?');args.append('%"'+pitch+'"%')
 if engagement:where.append('EXISTS(SELECT 1 FROM email_engagement_events e WHERE e.message_id=m.id AND e.event_type=?)');args.append(engagement)
 for val,op in [(created_from,'>='),(created_to,'<=')]:
  if val:where.append('m.created_at'+op+'?');args.append(val+('T23:59:59+00:00' if op=='<=' and len(val)==10 else ''))
 base=MESSAGE_BASE+' WHERE '+' AND '.join(where)
 total=c.execute('SELECT COUNT(DISTINCT m.id)'+base,args).fetchone()[0]
 rows=[]
 for r in c.execute('SELECT DISTINCT m.id,m.prospect_id,m.subject,m.to_address,m.from_address,m.status,m.created_at,m.sent_at,m.received_at,m.body_text,m.test_mode,m.report_id,m.thread_id,master.sales_state thread_state,COALESCE(sales.unread_replies,0) unread_replies,b.name,b.id business_id,COALESCE(w.campaign_id,ps.campaign_id) campaign_id,sc.configuration_json campaign_configuration,i.payload_json'+base+' ORDER BY m.created_at DESC LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall():
  item=dict(r);cfg=json.loads(item.pop('campaign_configuration') or '{}');item['campaign_name']=cfg.get('name') or ' / '.join(cfg.get('cities') or []) or 'Individual / legacy';payload=json.loads(item.pop('payload_json') or '{}');item['pitch_types']=payload.get('pitch_types',[])
  item['events']=[e[0] for e in c.execute('SELECT DISTINCT event_type FROM email_engagement_events WHERE message_id=?',(item['id'],)).fetchall()];rows.append(item)
 return page_result(rows,total,page,page_size)

@router.get('/schedules')
def schedules(request:Request,search:str=Query('',max_length=200),kind:str=Query('',max_length=20),enabled:Literal['','yes','no']='',frequency:str=Query('',max_length=20),owner:str=Query('',max_length=254),market:str=Query('',max_length=100),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 where=['s.organization_id=?','s.deleted_at IS NULL'];args=[organization]
 for value,column in [(kind,'s.kind'),(frequency,'s.frequency'),(owner,'s.created_by')]:
  if value:where.append(column+'=?');args.append(value)
 if enabled:where.append('s.enabled=?');args.append(int(enabled=='yes'))
 if search:where.append('LOWER(s.name) LIKE ?');args.append('%'+search.lower()+'%')
 if market:where.append('LOWER(s.configuration_json) LIKE ?');args.append('%'+market.lower()+'%')
 base=' FROM automation_schedules s WHERE '+' AND '.join(where);total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
 rows=[]
 from app.mail.config import mail_settings
 capability=mail_settings();controls=c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone()
 for r in c.execute('SELECT s.*'+base+' ORDER BY s.next_run_at,s.created_at DESC LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall():
  item=dict(r);item['configuration']=json.loads(item.pop('configuration_json'));last=c.execute('SELECT status,started_at,error FROM automation_schedule_runs WHERE schedule_id=? ORDER BY started_at DESC LIMIT 1',(item['id'],)).fetchone();item['last_result']=dict(last) if last else None;rows.append(item)
  reason=None
  if item['enabled']:
   if item['configuration'].get('needs_owner_review'):reason='Campaign audience requires owner review.'
   elif item['kind'] in ('SCAN','COMBINED') and controls['scan_paused']:reason='Scanning is paused by the owner.'
   elif item['kind'] in ('SCAN','COMBINED') and not capability.auto_scan_enabled:reason='Scheduled scanning capability is disabled.'
   elif item['kind']=='OUTREACH' and controls['email_paused']:reason='Outreach is paused by the owner.'
   elif item['kind']=='OUTREACH' and not capability.automatic_sending_enabled:reason='Scheduled sending capability is disabled.'
  item['blocked_reason']=reason
  item['outreach_hold_reason']='Acquisition can proceed; the email stage is held until outreach is enabled and unpaused.' if item['kind']=='COMBINED' and item['configuration'].get('email_all_eligible') and (controls['email_paused'] or not capability.automatic_sending_enabled) else None
 return page_result(rows,total,page,page_size)

@router.get('/reports')
def reports(request:Request,search:str=Query('',max_length=200),campaign_id:str=Query('',max_length=36),status:str=Query('',max_length=30),created_from:str=Query('',max_length=40),created_to:str=Query('',max_length=40),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 where=['p.organization_id=?'];args=[organization]
 if search:where.append('LOWER(b.name) LIKE ?');args.append('%'+search.lower()+'%')
 if campaign_id:where.append('s.campaign_id=?');args.append(campaign_id)
 if status:where.append('p.status=?');args.append(status)
 for val,op in [(created_from,'>='),(created_to,'<=')]:
  if val:where.append('p.created_at'+op+'?');args.append(val+('T23:59:59+00:00' if op=='<=' and len(val)==10 else ''))
 base=' FROM client_reports p JOIN businesses b ON b.id=p.business_id LEFT JOIN pipeline_runs s ON s.id=b.run_id WHERE '+' AND '.join(where);total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
 items=[dict(r) for r in c.execute('SELECT p.id,p.business_id,p.version,p.status,p.created_at,b.name business_name,s.campaign_id,s.market,s.vertical'+base+' ORDER BY p.created_at DESC LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall()]
 return page_result(items,total,page,page_size)

class SavedView(BaseModel):
 model_config=ConfigDict(extra='forbid')
 name:str=Field(min_length=1,max_length=100)
 filters:dict[str,str]=Field(default_factory=dict,max_length=30)
@router.get('/views')
def views(request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 return [{**dict(r),'filters':json.loads(r['filters_json'])} for r in c.execute("SELECT * FROM saved_views WHERE filters_json LIKE ? AND organization_id=? ORDER BY name",('%"operations_leads"%',organization)).fetchall()]
@router.post('/views',status_code=201)
def save_view(body:SavedView,request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 key=str(uuid.uuid4());filters={**body.filters,'surface':'operations_leads'};c.execute('INSERT INTO saved_views(id,name,filters_json,created_by,created_at,updated_at,organization_id) VALUES(?,?,?,?,?,?,?)',(key,body.name.strip(),json.dumps(filters),request.state.user_email,now(),now(),organization));return {'id':key}
@router.put('/views/{key}')
def edit_view(key:str,body:SavedView,request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 c.execute('UPDATE saved_views SET name=?,filters_json=?,updated_at=? WHERE id=? AND organization_id=?',(body.name.strip(),json.dumps({**body.filters,'surface':'operations_leads'}),now(),key,organization));return {'saved':True}
@router.delete('/views/{key}')
def delete_view(key:str,request:Request,c=Depends(get_db,scope='function')):organization=request.state.organization_id;c.execute('DELETE FROM saved_views WHERE id=? AND organization_id=?',(key,organization));return {'deleted':True}

@router.get('/dashboard')
def dashboard(request:Request,c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 from app.workflows.dashboard import summary as existing
 result=existing(c,organization);result['active_schedules']=c.execute('SELECT COUNT(*) FROM automation_schedules WHERE enabled=1 AND deleted_at IS NULL AND organization_id=?',(organization,)).fetchone()[0]
 result['open_runs']=c.execute("SELECT COUNT(*) FROM workflow_runs WHERE status IN ('RUNNING','PAUSED','PREPARING','NEEDS_REVIEW') AND organization_id=?",(organization,)).fetchone()[0]
 result['attention']={'manual_contact':result['manual'],'queued':result['queued'],'unread_replies':c.execute('SELECT COALESCE(SUM(unread_replies),0) FROM prospect_sales WHERE organization_id=?',(organization,)).fetchone()[0],'paused_schedules':c.execute('SELECT COUNT(*) FROM automation_schedules WHERE enabled=0 AND deleted_at IS NULL AND organization_id=?',(organization,)).fetchone()[0],'failed_reports':c.execute("SELECT COUNT(*) FROM client_reports WHERE status='FAILED' AND organization_id=?",(organization,)).fetchone()[0],'email_review':c.execute("SELECT COUNT(*) FROM outreach_run_items WHERE status='NEEDS_REVIEW' AND organization_id=?",(organization,)).fetchone()[0]}
 result['recent_activity']=[dict(r) for r in c.execute("SELECT a.id,a.event_type,a.event_at,b.name,b.id business_id FROM activities a JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=a.prospect_id) WHERE a.organization_id=? ORDER BY a.event_at DESC LIMIT 15",(organization,)).fetchall()]
 result['recent_campaigns']=[dict(r) for r in c.execute('SELECT id,configuration_json,created_at,status,target_total FROM scan_campaigns WHERE organization_id=? ORDER BY created_at DESC LIMIT 6',(organization,)).fetchall()]
 result['recent_leads']=[dict(r) for r in c.execute('SELECT b.id,b.name,b.city,b.vertical,m.contact_state,m.qualified_at FROM master_lead_state m JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=m.prospect_id) WHERE m.organization_id=? ORDER BY m.qualified_at DESC LIMIT 6',(organization,)).fetchall()]
 result['outreach']={}
 for kind in ('OPEN_SIGNAL','CLICK_SIGNAL','REPLIED_VERIFIED','BOUNCED_HARD','BOUNCED_SOFT'):
  result['outreach'][kind]=c.execute('SELECT COUNT(DISTINCT e.message_id) FROM email_engagement_events e JOIN email_messages m ON m.id=e.message_id WHERE e.event_type=? AND m.test_mode=0 AND e.suspected_bot=0 AND m.organization_id=?',(kind,organization)).fetchone()[0]
 return result

@router.get('/exports')
def exports(request:Request,search:str=Query('',max_length=200),campaign_id:str=Query('',max_length=36),status:str=Query('',max_length=30),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 where=['r.organization_id=?'];args=[organization]
 if search:where.append('(LOWER(r.market) LIKE ? OR LOWER(r.vertical) LIKE ?)');args.extend(['%'+search.lower()+'%']*2)
 if campaign_id:where.append('r.campaign_id=?');args.append(campaign_id)
 if status:where.append('r.status=?');args.append(status)
 base=' FROM pipeline_runs r WHERE '+' AND '.join(where);total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
 rows=[]
 for r in c.execute('SELECT r.id run_id,r.market,r.vertical,r.qualified,r.status,r.campaign_id,r.started_at,r.output_file'+base+' ORDER BY r.id DESC LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall():
  item=dict(r);objects={o[0] for o in c.execute('SELECT kind FROM artifact_objects WHERE run_id=?',(item['run_id'],)).fetchall()}
  from pathlib import Path
  legacy=Path(item.pop('output_file') or '/nonexistent')
  for kind,key in [('xlsx','excel'),('csv','csv')]:
   exists=kind in objects or (legacy.with_suffix('.'+kind).is_file() if str(legacy)!='/nonexistent' else False)
   item['has_'+key]=exists;item[key+'_url']='/api/scans/'+str(item['run_id'])+'/export/'+kind if exists else None
  rows.append(item)
 return page_result(rows,total,page,page_size)

@router.get('/files')
def files(request:Request,search:str=Query('',max_length=200),campaign_id:str=Query('',max_length=36),kind:str=Query('',max_length=20),status:str=Query('',max_length=30),page:int=Query(1,ge=1),page_size:int=Query(25,ge=1,le=100),c=Depends(get_db,scope='function')):
 organization=request.state.organization_id
 union="""SELECT p.id,b.name,p.business_id,r.campaign_id,r.market,'pdf' kind,p.status,p.created_at,p.version,p.id report_id,NULL run_id FROM client_reports p JOIN businesses b ON b.id=p.business_id LEFT JOIN pipeline_runs r ON r.id=b.run_id WHERE p.organization_id=?
 UNION ALL SELECT a.object_key,COALESCE(b.name,r.market),a.business_id,r.campaign_id,r.market,a.kind,'READY',a.created_at,0,NULL,a.run_id FROM artifact_objects a LEFT JOIN businesses b ON b.id=a.business_id LEFT JOIN pipeline_runs r ON r.id=a.run_id WHERE r.organization_id=?"""
 where=['1=1'];args=[organization,organization]
 if search:where.append('(LOWER(f.name) LIKE ? OR LOWER(f.kind) LIKE ?)');args.extend(['%'+search.lower()+'%']*2)
 for val,col in [(campaign_id,'campaign_id'),(kind,'kind'),(status,'status')]:
  if val:where.append('f.'+col+'=?');args.append(val)
 base=' FROM ('+union+') f WHERE '+' AND '.join(where);total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
 rows=[]
 for r in c.execute('SELECT *'+base+' ORDER BY f.created_at DESC LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall():
  item=dict(r);item['download_url']=('/api/client-reports/'+item['report_id']+'/download') if item['report_id'] else ('/api/scans/'+str(item['run_id'])+'/export/'+item['kind']) if item['run_id'] and item['kind'] in ('xlsx','csv') else None;rows.append(item)
 return page_result(rows,total,page,page_size)
