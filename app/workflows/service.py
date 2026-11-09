"""Manual/scheduled orchestration over the existing scan and reviewed-mail engines."""
import json,uuid
from datetime import datetime,timezone
from fastapi import HTTPException
from app.database.prospects import now
from app.automation.service import reconcile,eligible_markets
from app.mail.config import mail_settings
from app.config.settings import get_settings

def lock(c):
 if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944511)')
 elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')

def row(c,rid,organization=None):
 from app.platform.context import organization as active_organization
 organization=active_organization(organization)
 r=c.execute('SELECT * FROM workflow_runs WHERE id=?'+(' AND organization_id=?' if organization else ''),(rid,)+((organization,) if organization else ())).fetchone()
 if not r:raise HTTPException(404,'Run not found.')
 return dict(r)

def config(run):return json.loads(run['configuration_json'])

def create(c,body,actor,request_key=None,schedule_id=None,organization=None):
 from app.platform.context import organization as active_organization
 organization=active_organization(organization)
 from app.workflows.campaigns import audience
 from app.prospecting.policy import configuration as prospecting_configuration
 body=prospecting_configuration(body)
 lock(c);key=request_key or body['request_id']
 old=c.execute('SELECT id,configuration_json,created_by FROM workflow_runs WHERE request_key=?'+(' AND organization_id=?' if organization else ''),(key,)+((organization,) if organization else ())).fetchone()
 if old:
  previous=json.loads(old['configuration_json']);previous.pop('icp_snapshot',None)
  if previous!=body or old['created_by']!=actor:raise HTTPException(409,'Run request key belongs to different content.')
  return row(c,old['id'])
 cid=body.get('campaign_id') if body['kind']=='OUTREACH' else None
 snapshot=None
 if body['kind']=='OUTREACH':
  if not cid:raise HTTPException(422,'A campaign is required for every outreach run.')
  if body.get('outreach_mode','UNCONTACTED')=='RECONTACT' and not body.get('confirm_recontact'):raise HTTPException(422,'Explicitly confirm re-contact before creating this run.')
  snapshot=audience(c,cid,body.get('pitch_types'),body.get('outreach_mode','UNCONTACTED'),require_complete=True,organization=organization)
 if body.get('email_strategy')=='FIXED_5' or body.get('experiment_id'):
  from app.prospecting.policy import unavailable
  unavailable()
 if body['kind']=='OUTREACH':
  from app.mail.workspace_templates import require_template
  require_template(c,body.get('template_id'))
  from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
  if organization!=PLANEBYTE_ORGANIZATION_ID:
   from app.mail.customer import owned_account,validate_campaign
   if not body.get('account_id'):raise HTTPException(422,'Choose your workspace Gmail mailbox for this outreach run.')
   acc=owned_account(c,actor,body['account_id']);validate_campaign(c,cid,acc['id'])
 if body.get('icp_id'):
  from app.icp.service import get
  selected=get(c,str(body['icp_id']))
  if selected['status']!='ACTIVE':raise HTTPException(422,'Choose an active ideal customer profile.')
  body['icp_snapshot']=selected
 rid=str(uuid.uuid4());name=body.get('name')
 if not name:name=(snapshot['campaign']['name']+' · Outreach'+' · '+datetime.now(timezone.utc).strftime('%b %d')) if snapshot else ' / '.join(body.get('cities') or body['countries'])+' · '+' + '.join(body['verticals'])+' · '+datetime.now(timezone.utc).strftime('%b %d')
 name=name[:120]
 c.execute("INSERT INTO workflow_runs(id,name,kind,configuration_json,created_by,created_at,requested,request_key,schedule_id,campaign_id,organization_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(rid,name,body['kind'],json.dumps(body),actor,now(),snapshot['will_queue'] if snapshot else body['target'],key,schedule_id,cid,organization))
 if snapshot:select_items(c,rid,snapshot)
 return row(c,rid)

def candidates(c,options):
 from app.workflows.campaigns import audience
 if not options.get('campaign_id'):raise HTTPException(422,'Select a campaign before choosing outreach.')
 return [b for b in audience(c,options['campaign_id'],options.get('pitch_types'),options.get('outreach_mode','UNCONTACTED'),require_complete=True)['items'] if b['disposition']=='READY']

def select_items(c,rid,snapshot=None):
 from app.workflows.campaigns import audience
 run=row(c,rid);options=config(run);organization=run.get('organization_id')
 snapshot=snapshot or audience(c,run['campaign_id'],options.get('pitch_types'),options.get('outreach_mode','UNCONTACTED'),run_id=rid,require_complete=True,organization=organization)
 for b in snapshot['items']:
  stamp=now();iid=str(uuid.uuid4());payload={'campaign_id':run['campaign_id'],'pitch_types':b['pitch_types']}
  c.execute('INSERT INTO outreach_run_items(id,run_id,prospect_id,business_id,status,payload_json,idempotency_key,error,created_at,updated_at,organization_id) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id,prospect_id) DO NOTHING',(iid,rid,b['prospect_id'],b['business_id'],'QUEUED' if b['disposition']=='READY' else b['disposition'],json.dumps(payload),'run-item-'+iid,b['reason'],stamp,stamp,organization))
 return snapshot

TERMINAL_ITEMS=('SENT','SKIPPED','MANUAL_CONTACT','SUPPRESSED','REPLIED','ALREADY_CONTACTED','QUEUED_ELSEWHERE')

def prepare(c,rid):
 from app.mail.workspace_templates import render_template,require_template
 from app.mail.service import preview
 run=row(c,rid);options=config(run)
 if options.get('email_strategy')=='FIXED_5' or options.get('experiment_id'):
  raise HTTPException(409,'This experiment is archived. Create a new run with a workspace-owned template.')
 if not options.get('template_id'):
  c.execute("UPDATE workflow_runs SET status='NEEDS_REVIEW',error='Choose a workspace-owned template in a new outreach run; historical content is preserved.' WHERE id=? AND organization_id=?",(rid,run['organization_id']));return
 require_template(c,options['template_id'])
 organization=run.get('organization_id')
 if any(k in options for k in ('emails','emails_to_send','selected_ids')) or options.get('needs_owner_review'):raise HTTPException(409,'Legacy audience requires owner review. Create a new campaign-linked email run; the historical limit will not be broadened.')
 if run['status'] not in ('DRAFT','NEEDS_REVIEW','PREPARING'):return
 if not run['campaign_id']:raise HTTPException(409,'This legacy run needs campaign review; create a campaign-linked run.')
 org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
 current=select_items(c,rid);by_id={b['prospect_id']:b for b in current['items']}
 items=c.execute("SELECT * FROM outreach_run_items WHERE run_id=? AND status IN ('QUEUED','PREPARING') ORDER BY CASE status WHEN 'QUEUED' THEN 0 ELSE 1 END,created_at LIMIT 8",(rid,)).fetchall()
 for item in items:
  b=by_id.get(item['prospect_id'])
  if not b or b['disposition']!='READY':
   c.execute('UPDATE outreach_run_items SET status=?,error=?,updated_at=? WHERE id=?'+org_sql,(b['disposition'] if b else 'NEEDS_REVIEW',b['reason'] if b else 'Campaign membership requires review.',now(),item['id'])+org_args);continue
  template=render_template(c,item['business_id'],options['template_id'])
  saved=json.loads(item['payload_json']) if item['payload_json'] else {}
  payload=saved if saved.get('body_text') else {'to_address':b['recipient'],'subject':template['rendered_subject'],'body_text':template['rendered_body'],'template_id':options['template_id'],'outreach_strategy':'WORKSPACE','message_type':'FIRST_CONTACT','followup_days':mail_settings().followup_days,'track_opens':True,'track_clicks':True,'preview_nonce':item['id'],'idempotency_key':item['idempotency_key'],'confirmation':'SEND'}
  if options.get('account_id'):payload['account_id']=options['account_id']
  payload.update(report_id=None,campaign_id=run['campaign_id'],pitch_types=[],outreach_strategy='WORKSPACE')
  try:
   reviewed=preview(c,item['prospect_id'],run['created_by'] if options.get('account_id') else 'system',payload,allow_disabled=True)
   from app.mail.quality import issues
   problems=issues(c,item['prospect_id'],payload,settings=mail_settings())
   payload['preview_token']=reviewed['preview_token'];status='NEEDS_REVIEW' if problems else 'READY';error=' '.join(problems) or None
   c.execute('UPDATE outreach_run_items SET status=?,payload_json=?,preview_json=?,report_id=?,error=?,updated_at=? WHERE id=?'+org_sql,(status,json.dumps(payload),json.dumps(reviewed),None,error,now(),item['id'])+org_args)
  except Exception:c.execute("UPDATE outreach_run_items SET status='NEEDS_REVIEW',error='Content or recipient requires review.' WHERE id=?"+org_sql,(item['id'],)+org_args)
 counts={r['status']:r['n'] for r in c.execute('SELECT status,COUNT(*) n FROM outreach_run_items WHERE run_id=? GROUP BY status',(rid,)).fetchall()}
 pending=bool(counts.get('QUEUED') or counts.get('PREPARING'))
 status='PREPARING' if pending else 'DRAFT' if counts.get('READY') else 'NEEDS_REVIEW' if counts.get('NEEDS_REVIEW') else 'COMPLETED'
 error=None if pending or counts.get('READY') else f"No sendable emails: {counts.get('MANUAL_CONTACT',0)} manual-contact leads, {counts.get('NEEDS_REVIEW',0)} needing review. Review contact evidence and the workspace template; no email was sent."
 c.execute('UPDATE workflow_runs SET status=?,requested=?,error=?,completed_at=? WHERE id=?'+org_sql,(status,counts.get('READY',0),error,now() if status=='COMPLETED' else None,rid)+org_args)

def start(c,rid):
 lock(c);run=row(c,rid);options=config(run);organization=run.get('organization_id');org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
 if options.get('experiment_id') or options.get('email_strategy')=='FIXED_5':raise HTTPException(409,'Internal experiment execution is archived.')
 if run['status']=='RUNNING':return run
 if run['status'] not in ('DRAFT','PAUSED','NEEDS_REVIEW'):raise HTTPException(409,'Prepare and review every email before starting.')
 from app.workflows.controls import require_unpaused
 require_unpaused(c,'email' if run['kind']=='OUTREACH' else 'scan')
 if run['kind']=='OUTREACH':
  if any(k in options for k in ('emails','emails_to_send','selected_ids')) or options.get('needs_owner_review'):raise HTTPException(409,'Create a new campaign-linked run after reviewing the legacy audience.')
  if options.get('account_id'):
   from app.mail import service as mail
   s=mail.settings_for(c,mail.account(c,run['created_by'],options['account_id']))
  else:s=mail_settings()
  if not run['campaign_id']:raise HTTPException(409,'A campaign is required.')
  if run['schedule_id'] and not s.auto_email_enabled:raise HTTPException(503,'Scheduled sending capability is disabled.')
  if not s.sending_enabled:raise HTTPException(503,'Sending is disabled by the owner.')
  if options.get('outreach_mode')=='RECONTACT' and not options.get('confirm_recontact'):raise HTTPException(422,'Explicit re-contact confirmation is required.')
  snapshot=select_items(c,rid);by_id={b['prospect_id']:b for b in snapshot['items']}
  items=c.execute('SELECT * FROM outreach_run_items WHERE run_id=?',(rid,)).fetchall()
  if any(i['status'] in ('QUEUED','PREPARING') for i in items):raise HTTPException(409,'The audience has unprepared emails. Refresh and review before starting.')
  ready=[]
  for i in items:
   if i['status']!='READY':continue
   b=by_id.get(i['prospect_id'])
   if not b or b['disposition']!='READY':
    c.execute('UPDATE outreach_run_items SET status=?,error=? WHERE id=?',(b['disposition'] if b else 'NEEDS_REVIEW',b['reason'] if b else 'Campaign membership changed.',i['id']));continue
   from app.mail.quality import issues
   payload=json.loads(i['payload_json']);problems=issues(c,i['prospect_id'],payload,settings=s)
   if problems:c.execute("UPDATE outreach_run_items SET status='NEEDS_REVIEW',error=? WHERE id=?",(' '.join(problems),i['id']));continue
   ready.append(i)
  if not ready:raise HTTPException(409,'No reviewed, currently eligible campaign emails remain.')
  for i in ready:
   payload=json.loads(i['payload_json'])
   if options.get('account_id'):
    from app.mail import service as mail
    reviewed=mail.preview(c,i['prospect_id'],run['created_by'],payload)
    import hmac
    if not hmac.compare_digest(reviewed['preview_token'],payload.get('preview_token','')):raise HTTPException(409,'Review a fresh preview after the mailbox or policy change.')
    continue
   c.execute("INSERT INTO automation_email_queue(prospect_id,recipient,priority,queued_at,idempotency_key) VALUES(?,?,100,?,?) ON CONFLICT(prospect_id) DO UPDATE SET recipient=excluded.recipient,status='QUEUED',message_id=NULL,attempted_at=NULL,error_code=NULL,idempotency_key=excluded.idempotency_key",(i['prospect_id'],payload['to_address'],now(),i['idempotency_key']))
  c.execute('UPDATE workflow_runs SET requested=? WHERE id=?'+org_sql,(len(ready)+sum(i['status']=='SENT' for i in items),rid)+org_args)
 if run['kind'] in ('SCAN','COMBINED') and not c.execute('SELECT 1 FROM scan_campaigns WHERE id=?',(rid,)).fetchone():
  from app.database.acquisition_schema import ready as source_ready
  if source_ready(c):
   from app.acquisition.policy import policy
   source=options.get('scan_source','OVERTURE');campaign_options={**options,'source_type':source,'processing_policy':policy(source).mode.value}
   if options.get('qualification_mode')=='CONTACTABLE_ONLY':
    from app.prospecting.policy import configuration as defaults
    campaign_options.update(defaults())
   c.execute("INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,source_type,source_metadata,original_prompt,organization_id) VALUES(?,?,?,?,?,?,?,?,?)",(rid,run['created_by'],json.dumps(campaign_options),now(),options['target'],source,json.dumps({'workflow_run_id':rid,'schedule_id':run['schedule_id'],'processing_policy':policy(source).mode.value}),options.get('ai_prompt') or None,organization))
  else:c.execute("INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,organization_id) VALUES(?,?,?,?,?,?)",(rid,run['created_by'],run['configuration_json'],now(),options['target'],organization))
  c.execute('UPDATE workflow_runs SET campaign_id=? WHERE id=?'+org_sql,(rid,rid)+org_args)
 if run['kind'] in ('SCAN','COMBINED'):
  if options.get('locations'):
   from app.config.locations import seed_selected
   seed_selected(c,options['locations'],options['verticals'])
  from app.workflows.history import capture_settings
  capture_settings(c,rid,options,run['schedule_id'])
 c.execute("UPDATE workflow_runs SET status='RUNNING',started_at=COALESCE(started_at,?) WHERE id=?",(now(),rid));return row(c,rid)

async def advance_scan(c,rid):
 from app.database.models import PipelineRun
 from app.database.repositories import PipelineRunRepository
 from app.api.services.scan_manager import scan_manager
 lock(c);run=row(c,rid)
 if run['status']!='RUNNING':return
 options=config(run);organization=run.get('organization_id');org_sql=(' AND r.organization_id=?' if organization else '');org_args=(organization,) if organization else ()
 if options.get('scan_source','OVERTURE')=='FIRECRAWL':
  from app.acquisition.scheduling import advance
  return await advance(c,run,options)
 reconcile(c)
 count=c.execute("SELECT COUNT(DISTINCT p.id) FROM prospects p JOIN businesses b ON b.prospect_id=p.id JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=?"+org_sql+" AND b.processing_status='QUALIFIED'",(rid,)+org_args).fetchone()[0]
 c.execute('UPDATE workflow_runs SET result_count=? WHERE id=?'+(' AND organization_id=?' if organization else ''),(count,rid)+org_args)
 child=c.execute('SELECT * FROM pipeline_runs WHERE id=?',(run['scan_run_id'],)).fetchone() if run['scan_run_id'] else None
 if child and child['status'] in ('QUEUED','RUNNING'):return
 if child and child['status'] in ('FAILED','INTERRUPTED'):
  c.execute("UPDATE workflow_runs SET status='NEEDS_REVIEW',error='Scan interrupted. Review and resume the saved run.' WHERE id=?",(rid,));return
 if count>=options['target']:
  c.execute("UPDATE workflow_runs SET status='COMPLETED',completed_at=? WHERE id=?"+(' AND organization_id=?' if organization else ''),(now(),rid)+org_args);return
 used={r[0] for r in c.execute('SELECT market||\'|\'||vertical FROM pipeline_runs WHERE campaign_id=?'+(' AND organization_id=?' if organization else ''),((rid,)+org_args)).fetchall()}
 markets=eligible_markets(c)
 allowed=[m for m in markets if m['country'] in options['countries'] and m['vertical'] in options['verticals'] and (not options.get('cities') or m['city'] in options['cities']) and m['city']+', '+m['country']+'|'+m['vertical'] not in used]
 if not options.get('rotate_locations',True):
  first=c.execute('SELECT market FROM pipeline_runs WHERE campaign_id=?'+(' AND organization_id=?' if organization else '')+' ORDER BY id LIMIT 1',(rid,)+org_args).fetchone()
  if first:allowed=[m for m in allowed if m['city']+', '+m['country']==first[0]]
 if not options.get('rotate_verticals',True):allowed=[m for m in allowed if m['vertical']==options['verticals'][0]]
 if not allowed:
  c.execute("UPDATE workflow_runs SET status='COMPLETED',completed_at=?,error=? WHERE id=?"+(' AND organization_id=?' if organization else ''),(now(),f'Qualified target shortfall: {max(0,options["target"]-count)}. No additional configured markets are eligible.',rid)+org_args);return
 controls=c.execute('SELECT scan_paused FROM automation_controls WHERE id=1').fetchone()
 if not controls or controls['scan_paused']:return
 allowed.sort(key=lambda market:(sum(item.split('|')[0].endswith(', '+market['country']) for item in used),options['countries'].index(market['country'])))
 m=allowed[0];remaining=options['target']-count
 country_slots=max(1,len({market['country'] for market in allowed}))
 child_target=max(1,(remaining+country_slots-1)//country_slots)
 settings={'target':child_target,'request_id':rid,'quality':'high_intent','opportunities':options['opportunities'],'business_scales':options['business_scales'],'results':'new','commercial_fit':options['commercial_fit'],'exclude_chains':True,'lighthouse_enabled':False,'workflow_run_id':rid,'icp_id':options.get('icp_id'),'icp_snapshot':options.get('icp_snapshot'),'search_criteria':options.get('search_criteria',{})}
 if 'scan_source' in options:
  settings.update(source_type='OVERTURE',processing_policy='DISCOVERY_QUALIFIED',qualification_flow_version=1)
  for key in ('qualification_mode','preliminary_opportunity_threshold','qualified_score_threshold','deep_audit_budget','lighthouse_budget','email_enrichment_reuse_days','max_candidates','max_runtime_seconds','analysis_reuse_days'):settings[key]=options.get(key)
 if settings.get('qualification_flow_version')==1:
  used_candidates=c.execute('SELECT COALESCE(SUM(raw_found),0) FROM pipeline_runs WHERE campaign_id=?'+(' AND organization_id=?' if organization else ''),(rid,)+org_args).fetchone()[0]
  settings['max_candidates']=max(0,(options.get('max_candidates') or 300)-used_candidates)
  settings['raw_budget']=settings['max_candidates']
  if not settings['max_candidates']:
   c.execute("UPDATE workflow_runs SET status='COMPLETED',completed_at=?,error=? WHERE id=?"+(' AND organization_id=?' if organization else ''),(now(),f'Qualified target shortfall: {remaining}. Campaign resource budget exhausted.',rid)+org_args);return
 from app.database.foundation_schema import ready
 if ready(c):
  from app.workflows.history import capture_settings
  frozen=capture_settings(c,rid,options,run['schedule_id'],organization=organization)
  for key in ('crawler','auditing','analysis_mode','social','locations','reuse_windows'):settings[key]=frozen.get(key)
 if settings.get('qualification_flow_version')==1:
  settings['reuse_windows']={**(settings.get('reuse_windows') or {}),**{key:options.get('analysis_reuse_days',7) for key in ('crawl','website','seo','security')},'contacts':options.get('email_enrichment_reuse_days',7)}
 from app.prospecting.policy import configuration as prospecting_configuration
 settings=prospecting_configuration(settings)
 scan=PipelineRun(market=m['city']+', '+m['country'],vertical=m['vertical'],target=child_target,status='QUEUED',started_at=now(),run_configuration=settings);PipelineRunRepository(c).create(scan,organization=organization)
 c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?'+(' AND organization_id=?' if organization else ''),(rid,scan.id)+org_args);c.execute('UPDATE workflow_runs SET scan_run_id=? WHERE id=?'+(' AND organization_id=?' if organization else ''),(scan.id,rid)+org_args);c.execute('UPDATE scan_markets SET last_scanned_at=?,updated_at=? WHERE id=?',(now(),now(),m['id']));c.commit()
 await scan_manager.executor.start(scan.id,scan.market,scan.vertical,scan.target,settings)

def detail(c,rid,page=1,page_size=25,status="",search=""):
 r=row(c,rid);r['configuration']=json.loads(r.pop('configuration_json'))
 where=['i.run_id=?'];args=[rid]
 if status:where.append('i.status=?');args.append(status)
 if search:where.append('LOWER(b.name) LIKE ?');args.append('%'+search.lower()+'%')
 base=' FROM outreach_run_items i JOIN businesses b ON b.id=i.business_id WHERE '+' AND '.join(where)
 r['items_total']=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
 r['page']=page;r['page_size']=page_size
 r['items']=[{**dict(i),'payload':json.loads(i['payload_json']) if i['payload_json'] else None,'preview':json.loads(i['preview_json']) if i['preview_json'] else None} for i in c.execute('SELECT i.*,b.name'+base+' ORDER BY i.created_at,i.id LIMIT ? OFFSET ?',[*args,page_size,(page-1)*page_size]).fetchall()]
 for i in r['items']:
  i.pop('payload_json',None);i.pop('preview_json',None)
  if i['message_id']:
   from app.mail.tracking import message_summary
   i['engagement']=message_summary(c,i['message_id'])
 r['counts']={x['status']:x['n'] for x in c.execute('SELECT status,COUNT(*) n FROM outreach_run_items WHERE run_id=? GROUP BY status',(rid,)).fetchall()}
 r['scans']=[dict(x) for x in c.execute('SELECT id,market,vertical,status,raw_found,websites_processed,filtered,qualified FROM pipeline_runs WHERE campaign_id=? ORDER BY id',(rid,)).fetchall()]
 r['leads']=[dict(x) for x in c.execute("SELECT DISTINCT b.id,b.name,b.city,b.vertical,b.public_email,b.phone,b.processing_status,i.commercial_fit,o.primary_opportunity,o.website_opportunity_score,o.seo_opportunity_score,o.security_opportunity_score FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id LEFT JOIN business_intelligence i ON i.business_id=b.id LEFT JOIN opportunity_scores o ON o.business_id=b.id WHERE r.campaign_id=? ORDER BY b.id DESC LIMIT 100",(rid,)).fetchall()]
 r['scan_summary']=dict(c.execute("SELECT COUNT(*) total,SUM(CASE WHEN b.processing_status='QUALIFIED' THEN 1 ELSE 0 END) qualified,SUM(CASE WHEN b.processing_status='QUALIFIED' AND b.public_email IS NOT NULL THEN 1 ELSE 0 END) email_available,SUM(CASE WHEN b.processing_status='QUALIFIED' AND b.public_email IS NULL THEN 1 ELSE 0 END) manual_contact,SUM(CASE WHEN b.processing_status='QUALIFIED' AND i.commercial_fit='HIGH' THEN 1 ELSE 0 END) high_fit,SUM(CASE WHEN b.processing_status='QUALIFIED' AND i.commercial_fit='MEDIUM' THEN 1 ELSE 0 END) medium_fit,SUM(CASE WHEN b.is_rejected=1 THEN 1 ELSE 0 END) rejected FROM businesses b JOIN pipeline_runs s ON s.id=b.run_id LEFT JOIN business_intelligence i ON i.business_id=b.id WHERE s.campaign_id=?",(rid,)).fetchone())
 r['current_stage']=(lambda e:dict(e) if e else None)(c.execute('SELECT stage,message FROM pipeline_run_events WHERE run_id=? ORDER BY id DESC LIMIT 1',(r['scan_run_id'],)).fetchone()) if r['scan_run_id'] else None

 return r

async def dispatch(c):
 from app.platform.context import current,workspace_scope
 try:context=current()
 except HTTPException:context=None
 if context:return await _dispatch_workspace(c)
 from app.api.organization import membership_role
 started=[]
 for workspace in c.execute("SELECT id,created_by_user_id FROM organizations WHERE status='ACTIVE' ORDER BY id LIMIT 100").fetchall():
  if not membership_role(c,workspace['created_by_user_id'],workspace['id']):continue
  with workspace_scope(c,workspace['created_by_user_id'],workspace['id']):
   result=await _dispatch_workspace(c);started.extend(result['scheduled_runs_started'])
 return {'scheduled_runs_started':started}

async def _dispatch_workspace(c):
 from app.platform.context import organization
 org=organization()
 from app.workflows.calendar import next_due
 lock(c);stamp=now();s=mail_settings();started=[]
 # A Cloud Run retry may finish a child after the parent observed its failed
 # attempt. Reconcile that exact automatic-review state without rerunning work
 # or overriding an owner pause/cancellation.
 c.execute("UPDATE workflow_runs SET status='RUNNING',error=NULL WHERE organization_id=? AND kind IN ('SCAN','COMBINED') AND status='NEEDS_REVIEW' AND error='Scan interrupted. Review and resume the saved run.' AND scan_run_id IN (SELECT id FROM pipeline_runs WHERE organization_id=? AND status='COMPLETED')",(org,org))
 for schedule in c.execute('SELECT * FROM automation_schedules WHERE organization_id=? AND enabled=1 AND deleted_at IS NULL AND next_run_at<=? ORDER BY next_run_at LIMIT 10',(org,stamp)).fetchall():
  from app.api.organization import membership_role
  if not membership_role(c,schedule['created_by'],org):continue
  if schedule['kind'] in ('SCAN','COMBINED') and not s.auto_scan_enabled:continue
  scheduled_config=json.loads(schedule['configuration_json'])
  if scheduled_config.get('experiment_id') or scheduled_config.get('email_strategy')=='FIXED_5':continue # Owned by the gated bounded experiment dispatcher.
  if schedule['kind']=='OUTREACH' and scheduled_config.get('account_id'):
   from app.platform.context import workspace_scope
   from app.mail import service as mail
   with workspace_scope(c,schedule['created_by'],org):
    configured=mail.settings_for(c,mail.account(c,schedule['created_by'],scheduled_config['account_id']))
    if not configured.automatic_sending_enabled:continue
  elif schedule['kind']=='OUTREACH' and not s.automatic_sending_enabled:continue
  controls=c.execute('SELECT * FROM automation_controls WHERE id=1').fetchone()
  if (schedule['kind'] in ('SCAN','COMBINED') and controls['scan_paused']) or (schedule['kind']=='OUTREACH' and controls['email_paused']):continue
  slot=schedule['next_run_at'];sid=str(uuid.uuid4())
  if c.execute("SELECT 1 FROM workflow_runs WHERE schedule_id=? AND status IN ('RUNNING','PREPARING','PAUSED','NEEDS_REVIEW')",(schedule['id'],)).fetchone():
   next_at=next_due(dict(schedule),datetime.now(timezone.utc));c.execute('UPDATE automation_schedules SET next_run_at=? WHERE id=?',(next_at,schedule['id']));continue
  if c.execute('SELECT 1 FROM automation_schedule_runs WHERE schedule_id=? AND due_at=?',(schedule['id'],slot)).fetchone():continue
  settings=json.loads(schedule['configuration_json'])
  if settings.get('needs_owner_review'):continue
  settings['request_id']=str(uuid.uuid5(uuid.NAMESPACE_URL,schedule['id']+slot))
  from app.platform.context import workspace_scope
  with workspace_scope(c,schedule['created_by'],org):
   run=create(c,settings,schedule['created_by'],schedule['id']+':'+slot,schedule['id'],organization=schedule['organization_id'])
   if run['kind']=='OUTREACH':prepare(c,run['id'])
   else:start(c,run['id'])
  c.execute("INSERT INTO automation_schedule_runs(id,schedule_id,workflow_run_id,due_at,status,started_at) VALUES(?,?,?,?,'RUNNING',?)",(sid,schedule['id'],run['id'],slot,stamp))
  next_at=next_due(dict(schedule),datetime.now(timezone.utc));c.execute('UPDATE automation_schedules SET next_run_at=?,last_run_at=?,enabled=? WHERE id=?',(next_at,stamp,1,schedule['id']))
  started.append(run['id'])
 c.commit()
 for run in c.execute("SELECT * FROM workflow_runs WHERE organization_id=? AND (status IN ('RUNNING','PREPARING') OR (schedule_id IS NOT NULL AND status='DRAFT')) ORDER BY CASE WHEN status='RUNNING' THEN 0 ELSE 1 END,created_at LIMIT 50",(org,)).fetchall():
  from app.api.organization import membership_role
  if not membership_role(c,run['created_by'],org):continue
  if config(run).get('experiment_id') or config(run).get('email_strategy')=='FIXED_5':continue
  if run['schedule_id'] and config(run).get('_schedule_trigger')!='RUN_NOW':
   enabled=c.execute('SELECT enabled,deleted_at FROM automation_schedules WHERE id=?',(run['schedule_id'],)).fetchone()
   if not enabled or not enabled['enabled'] or enabled['deleted_at']:continue
   if run['kind'] in ('SCAN','COMBINED') and not s.auto_scan_enabled:continue
  if run['kind']=='OUTREACH' and config(run).get('account_id'):
   from app.mail.customer import advance_run
   advance_run(c,dict(run));continue
  if run['kind'] in ('SCAN','COMBINED') and run['status']=='RUNNING':
   await advance_scan(c,run['id']);updated=row(c,run['id'])
   if updated['status']=='COMPLETED' and run['kind']=='COMBINED' and config(run).get('email_all_eligible') and not config(run).get('needs_owner_review'):
    if not config(run).get('template_id'):
     c.execute("UPDATE workflow_runs SET status='NEEDS_REVIEW',error='Discovery completed. Choose a workspace-owned template in a new campaign outreach run.' WHERE id=? AND organization_id=?",(run['id'],org));continue
    options=config(run);options.update(kind='OUTREACH',campaign_id=run['id'],name=run['name']+' · Outreach',request_id=str(uuid.uuid5(uuid.NAMESPACE_URL,run['id']+':outreach')))
    child=create(c,options,run['created_by'],run['id']+':outreach',run['schedule_id'],organization=run['organization_id']);prepare(c,child['id'])
    # Scheduled delegation can start only ready, quality-gated items.
    if run['schedule_id'] and row(c,child['id'])['status']=='DRAFT':
     try:start(c,child['id'])
     except HTTPException:pass
  elif run['kind']=='OUTREACH':
   controls=c.execute('SELECT email_paused FROM automation_controls WHERE id=1').fetchone()
   if controls['email_paused']:continue
   if run['schedule_id'] and not s.automatic_sending_enabled:continue
   if run['status']!='RUNNING':
    if run['schedule_id'] or run['status']=='PREPARING':prepare(c,run['id'])
    if run['schedule_id'] and row(c,run['id'])['status']=='DRAFT':
     try:start(c,run['id'])
     except HTTPException:pass
   if row(c,run['id'])['status']=='RUNNING':
    from app.automation.service import outreach_tick
    c.commit()
    if config(run).get('account_id'):
     from app.mail.customer import outreach_tick as customer_tick
     customer_tick(c,run['id'])
    else:outreach_tick(c,execution_id=run['id'])
    for item in c.execute("SELECT * FROM outreach_run_items WHERE run_id=? AND status='READY'",(run['id'],)).fetchall():
     message=c.execute('SELECT id,status,error_code FROM email_messages WHERE idempotency_key=?'+(' AND organization_id=?' if run['organization_id'] else ''),(item['idempotency_key'],)+((run['organization_id'],) if run['organization_id'] else ())).fetchone()
     if message:c.execute('UPDATE outreach_run_items SET status=?,message_id=?,error=?,updated_at=? WHERE id=?'+(' AND organization_id=?' if run['organization_id'] else ''),('SENT' if message['status']=='SENT' else 'NEEDS_REVIEW',message['id'],message['error_code'],now(),item['id'])+((run['organization_id'],) if run['organization_id'] else ()))
    org_sql=(' AND organization_id=?' if run['organization_id'] else '');org_args=(run['organization_id'],) if run['organization_id'] else ()
    pending=c.execute("SELECT COUNT(*) FROM outreach_run_items WHERE run_id=?"+org_sql+" AND status IN ('READY','QUEUED','PREPARING')",(run['id'],)+org_args).fetchone()[0]
    sent=c.execute("SELECT COUNT(*) FROM outreach_run_items WHERE run_id=?"+org_sql+" AND status='SENT'",(run['id'],)+org_args).fetchone()[0]
    failed=c.execute("SELECT COUNT(*) FROM outreach_run_items WHERE run_id=?"+org_sql+" AND status='NEEDS_REVIEW'",(run['id'],)+org_args).fetchone()[0]
    c.execute('UPDATE workflow_runs SET result_count=?,status=?,completed_at=? WHERE id=?'+org_sql,(sent,'NEEDS_REVIEW' if c.execute('SELECT email_paused FROM automation_controls WHERE id=1').fetchone()[0] and failed else 'RUNNING' if pending else 'NEEDS_REVIEW' if failed else 'COMPLETED',None if pending or failed else now(),run['id'])+org_args)
 for history in c.execute("SELECT h.id,r.status,r.completed_at FROM automation_schedule_runs h JOIN workflow_runs r ON r.id=h.workflow_run_id WHERE r.organization_id=? AND h.status='RUNNING'",(org,)).fetchall():
  if history['status'] in ('COMPLETED','FAILED','CANCELLED','NEEDS_REVIEW'):c.execute('UPDATE automation_schedule_runs SET status=?,completed_at=? WHERE id=?',(history['status'],history['completed_at'] or now(),history['id']))
 c.commit()
 if get_settings().app_env=='production':
  from app.api.services.cloud_executor import dispatch_queued
  dispatch_queued()
 from app.intelligence.dispatch import dispatch_owned
 await dispatch_owned(c)
 return {'scheduled_runs_started':started}
