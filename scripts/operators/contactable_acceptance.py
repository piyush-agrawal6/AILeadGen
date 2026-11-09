"""Bounded live-source acceptance, with no prospect outreach or auto-scan activation."""
import argparse,json,os,uuid
from pathlib import Path
os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.config.settings import get_settings
from app.acquisition import service
from app.acquisition.models import SearchIntent,ProcessingOptions,Budgets
from scripts.stage_acquisition_release import command,REGION
STATE=Path('docs/contactable-source-acceptance.json')

def stage():
 assert not STATE.exists(),'Inspect existing acceptance checkpoint; do not duplicate jobs.'
 reset=json.loads(Path('docs/contactable-clean-reset.json').read_text());assert reset['backup_verified']
 intent=SearchIntent(targetQualifiedLeads=10,verticals=['dentists'],countries=['United Kingdom'],cities=['Bristol'],queries=['dentists Bristol official website contact email','dental clinics Bristol contact email'])
 budget=Budgets(max_searches=6,max_scraped_pages=50,max_crawl_pages=0,max_runtime_seconds=900,max_candidates=100,max_credits=80)
 with db_session() as c:
  r=service.create_job(c,'FIRECRAWL',get_settings().allowed_emails[0],str(uuid.uuid4()),{'intent':intent.model_dump(),'processing':ProcessingOptions(default_vertical='dentists',default_city='Bristol').model_dump(),'budgets':budget.model_dump()},{'original_prompt':'Find 10 new Bristol dental businesses with publicly evidenced business emails','controlled_acquisition':True,'no_outreach':True})
  cid=service.create_campaign(c,r['id'],'Bristol dental businesses · Contactable-only',target=10)
 state={'job_id':r['id'],'campaign_id':cid,'target':10,'no_prospect_outreach':True,'executions':[]};STATE.write_text(json.dumps(state,indent=2));print(json.dumps(state))

def launch():
 state=json.loads(STATE.read_text())
 with db_session() as c:
  r=service.job(c,state['job_id']);assert r['status']=='QUEUED' and not r['execution_name']
 result=command(['run','jobs','execute','leadengine-acquisition','--region='+REGION,'--update-env-vars=LEADENGINE_ACQUISITION_JOB_ID='+state['job_id'],'--async','--quiet'])
 state['executions'].append(result['metadata']['name']);STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'execution':result['metadata']['name'],'no_outreach':True}))

def inspect():
 state=json.loads(STATE.read_text())
 with db_session() as c:
  r=service.job(c,state['job_id']);counts=service.refresh_counts(c,r['id'])
  no_work={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('opportunity_scores','lighthouse_results','client_reports','analysis_operations','workflow_runs')}
  no_work['prospect_emails']=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND message_type<>'OWNER_CONTROLLED_REDIRECT'").fetchone()[0]
  result={'status':r['status'],'error_code':r['error_code'],'stop_reason':r['error_message'],'counts':counts,'forbidden_automatic_work':no_work}
  assert not any(no_work.values()),'No analysis, copy generation, report, run or SMTP is allowed during source acceptance.'
 state['latest']=result;STATE.write_text(json.dumps(state,indent=2));print(json.dumps(result))

def extend():
 state=json.loads(STATE.read_text());assert state['target']==10
 with db_session() as c:
  r=service.job(c,state['job_id']);counts=service.refresh_counts(c,r['id']);assert r['status']=='COMPLETED' and counts['qualified']==10
  state['target10_result']={'status':r['status'],'counts':counts};cfg=json.loads(r['configuration_json']);cfg['intent']['targetQualifiedLeads']=50
  cfg['budgets']=Budgets(max_searches=16,max_scraped_pages=160,max_crawl_pages=0,max_runtime_seconds=1800,max_candidates=400,max_credits=250).model_dump()
  c.execute("UPDATE acquisition_jobs SET configuration_json=?,status='QUEUED',execution_name=NULL,finished_at=NULL WHERE id=?",(service.encoded(cfg),r['id']))
  campaign=c.execute('SELECT configuration_json FROM scan_campaigns WHERE id=?',(r['campaign_id'],)).fetchone();cc=json.loads(campaign[0]);cc['target']=50
  c.execute("UPDATE scan_campaigns SET target_total=50,configuration_json=?,status='RUNNING' WHERE id=?",(service.encoded(cc),r['campaign_id']))
  service.event(c,r['id'],'RESUME_TO_TARGET','10-contact acceptance passed. Continuing the same checkpoint to50; already qualified contacts and cached requests are reused.')
 state['target']=50;STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'target':50,'existing_10_preserved':True,'no_outreach':True}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','launch','inspect','extend']);a=p.parse_args();globals()[a.action]()
