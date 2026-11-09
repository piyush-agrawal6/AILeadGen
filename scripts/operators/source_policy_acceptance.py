"""Owner-authorized bounded acquisition QA. Never creates an outreach run."""
import asyncio,io,json,os,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
os.environ['DATABASE_BACKEND']='postgres'
os.environ['STORAGE_BACKEND']='r2'
from app.database.connection import db_session
from app.acquisition import service,sheets
from app.acquisition.models import ProcessingOptions,ColumnMapping,SearchIntent,Budgets
from app.config.settings import get_settings
from scripts.stage_acquisition_release import command,REGION
STATE=Path('docs/source-policy-controlled-acceptance.json')
SHEET='1ykaqduUYQv7kCWw2HasWKLlDsiGRO3DkdXEIBVZXckc'
MAPPING=ColumnMapping(company_name='Organisation',website='Site Address',email='Mail ID',phone='Telephone',city='Market',country='Country',vertical='Category',contact_name='Contact Person')

def stage():
 assert not STATE.exists(),'Acceptance jobs already staged; inspect existing checkpoints first.'
 actor=get_settings().allowed_emails[0];processing=ProcessingOptions();jobs={}
 with db_session() as c:
  staged=asyncio.run(sheets.stage(c,actor,SHEET,'Acceptance Leads',str(uuid.uuid4())))
  jid=staged['id'];service.approve_import(c,jid,actor,MAPPING,processing,'Owner QA · Trusted Sheets source policy',str(uuid.uuid4()));jobs['sheets']=jid
  # Reuse the controlled sample rows only; never retrieve prospect lists.
  source=service.job(c,jid);manifest=json.loads(source['manifest_json']);sample=manifest['sample'];headers=manifest['headers']
  import csv
  text=io.StringIO();writer=csv.writer(text);writer.writerow(headers);writer.writerows(sample[:3])
  csvjob=service.stage_file(c,actor,'Owner-controlled-source-policy.csv',text.getvalue().encode(),str(uuid.uuid4()));service.approve_import(c,csvjob['id'],actor,MAPPING,processing,'Owner QA · Trusted CSV source policy',str(uuid.uuid4()));jobs['csv']=csvjob['id']
  from openpyxl import Workbook
  wb=Workbook();ws=wb.active;ws.append(headers)
  for row in sample[:3]:ws.append(row)
  out=io.BytesIO();wb.save(out)
  excel=service.stage_file(c,actor,'Owner-controlled-source-policy.xlsx',out.getvalue(),str(uuid.uuid4()));service.approve_import(c,excel['id'],actor,MAPPING,processing,'Owner QA · Trusted Excel source policy',str(uuid.uuid4()));jobs['xlsx']=excel['id']
  intent=SearchIntent(targetQualifiedLeads=5,verticals=['dentists'],countries=['United Kingdom'],cities=['Bristol'],queries=['independent dentists Bristol official website contact email','dental clinics Bristol contact email'])
  budgets=Budgets(max_searches=2,max_scraped_pages=18,max_crawl_pages=0,max_runtime_seconds=300,max_candidates=30)
  r=service.create_job(c,'FIRECRAWL',actor,str(uuid.uuid4()),{'intent':intent.model_dump(),'processing':ProcessingOptions(default_vertical='dentists',default_city='Bristol').model_dump(),'budgets':budgets.model_dump()},{'original_prompt':'Owner QA · Find 5 dentists in Bristol with public business email','controlled_acquisition':True,'no_outreach':True})
  service.create_campaign(c,r['id'],'Owner QA · Email-contactable Firecrawl',target=5);jobs['firecrawl']=r['id']
 STATE.write_text(json.dumps({'status':'STAGED','jobs':jobs,'no_outreach_authorized':True,'no_prospect_mail_created':True},indent=2));print(json.dumps({'staged_jobs':jobs,'no_outreach_created':True}))

def launch(kind):
 state=json.loads(STATE.read_text());jid=state['jobs'][kind]
 assert kind not in state.get('executions',{}),'Already launched. Inspect checkpoint, never automatically repeat.'
 result=command(['run','jobs','execute','leadengine-acquisition','--region='+REGION,'--update-env-vars=LEADENGINE_ACQUISITION_JOB_ID='+jid+',ENABLE_AI_ACQUISITION=true,ENABLE_FIRECRAWL_ACQUISITION=true,ENABLE_LEAD_IMPORT=true,ENABLE_GOOGLE_SHEETS_IMPORT=true','--async','--quiet'])
 state.setdefault('executions',{})[kind]=result['metadata']['name'];STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'kind':kind,'execution':result['metadata']['name'],'global_source_flags_unchanged':True,'no_mail_capability_in_source_job':True}))

def inspect():
 state=json.loads(STATE.read_text());results={}
 with db_session() as c:
  for kind,jid in state['jobs'].items():
   job=service.job(c,jid);counts=service.refresh_counts(c,jid);cid=job['campaign_id']
   messages=c.execute('SELECT COUNT(*) FROM email_messages WHERE prospect_id IN (SELECT prospect_id FROM lead_source_evidence WHERE campaign_id=?)',(cid,)).fetchone()[0]
   outreach=c.execute("SELECT COUNT(*) FROM workflow_runs WHERE kind='OUTREACH' AND campaign_id=?",(cid,)).fetchone()[0]
   assert messages==outreach==0
   results[kind]={'job_id':jid,'campaign_id':cid,'status':job['status'],'counts':counts,'error_code':job['error_code'],'messages':messages,'outreach_runs':outreach}
 state['results']=results;state['status']='INSPECTED';STATE.write_text(json.dumps(state,indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','launch','inspect']);p.add_argument('--kind',choices=['sheets','csv','xlsx','xlsx_ten','firecrawl']);a=p.parse_args()
 if a.action=='stage':stage()
 elif a.action=='launch':launch(a.kind)
 else:inspect()
