from app.platform.context import current
import asyncio,json,uuid
from pathlib import Path
from unittest.mock import AsyncMock,Mock
import pytest
from app.database.connection import get_connection,db_session
from app.database.migrations import run_migrations
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,now
from app.acquisition import service
from app.acquisition.models import ProcessingOptions,SearchIntent
from app.acquisition.imports import normalize_row
from app.acquisition.pipeline import analyze_batch
from app.enrichment.crawler import CrawlResult
from app.enrichment.contacts import extract_contacts_from_html
from app.enrichment.http_probe import ProbeResult
from test_acquisition_sources import INTENT
from test_automation import db
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID

HTML='''<html><head><title>Acme Dental Bristol</title></head><body><h1>Acme Dental</h1><p>Bristol independent dental clinic. United Kingdom.</p><a href="mailto:info@acme.test">Contact</a><p>Call +44 117 555 1234</p></body></html>'''
@pytest.fixture
def pipeline(tmp_path,monkeypatch,request):
 path=tmp_path/'source.db';c=get_connection(path);run_migrations(c)
 from tests.workspace_fixtures import bind_internal_workspace
 bind_internal_workspace(c,request);c.close()
 async def probe(url,**kw):return ProbeResult(requested_url=url,final_url=url,reachable=True,http_status=200,https_enabled=False,html_content=HTML,response_headers={})
 async def crawl(self,start_url,**kw):
  r=CrawlResult(start_url);r.homepage_html=HTML;r.all_htmls={start_url:HTML};r.pages_crawled=1;r.contacts=extract_contacts_from_html(HTML,start_url);r.contact_page_url=start_url+'/contact';return r
 monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',crawl)
 monkeypatch.setattr('app.prospecting.intake.check_email_dns',lambda *a,**kw:('MX',True));monkeypatch.setattr('app.enrichment.screenshot.capture_website',AsyncMock(return_value=None))
 monkeypatch.setenv('SOCIAL_ENRICHMENT_ENABLED','false');monkeypatch.setenv('SOCIAL_ACTIVITY_ENABLED','false')
 return path

def make_source(c,source,name='Source QA'):
 processing=ProcessingOptions(qualification_mode='ANALYZED',analyze_websites=True,analyze_seo=True,analyze_security=True,default_vertical='dentists',default_city='Bristol')
 config={'processing':processing.model_dump(),'intent':INTENT} if source=='FIRECRAWL' else {'processing':processing.model_dump()}
 r=service.create_job(c,source,current().actor,str(uuid.uuid4()),config,{'filename':'controlled.xlsx'});cid=service.create_campaign(c,r['id'],name,target=5)
 return r['id'],cid,processing

def business():return normalize_row({'company_name':'Acme Dental','website':'http://acme.test','email':'info@acme.test','phone':'+441175551234','city':'Bristol','country':'United Kingdom','vertical':'Dental'},ProcessingOptions(default_vertical='dentists'),'FILE_IMPORT')

def test_shared_pipeline_cross_source_dedupe_reuse_and_history(pipeline,monkeypatch):
 path=pipeline;jobs=[]
 with db_session(path) as c:
  from campaign_fixtures import campaign,qualify
  baseline=campaign(c,'Existing Overture campaign');run=PipelineRun(market='Bristol, United Kingdom',vertical='dentists',target=1,status='COMPLETED');PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(baseline,run.id))
  old=business();old.source_overture=True;old.run_id=run.id;old.processing_status='QUALIFIED';BusinessRepository(c).insert(old);pid=ProspectRepository(c).observe(old,baseline,'owner', organization=PLANEBYTE_ORGANIZATION_ID);qualify(c,old)
  for source in ('FILE_IMPORT','FIRECRAWL','GOOGLE_SHEETS'):jobs.append(make_source(c,source))
 for index,(jid,cid,processing) in enumerate(jobs):
  b=business();b.source_tags=json.dumps({'field_sources':{'email':{'source':['FILE_IMPORT','FIRECRAWL','GOOGLE_SHEETS'][index],'verification':'PUBLICLY_PUBLISHED' if index==1 else 'OWNER_PROVIDED','url':'http://acme.test','value':'info@acme.test'}},'row_number':2})
  asyncio.run(analyze_batch(jid,'controlled', [b],processing,target=1,db_path=path))
  with db_session(path) as c:
   assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==1
   assert c.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==index+2
   if index==0:
    pid=c.execute('SELECT id FROM prospects').fetchone()[0]
    ProspectRepository(c).workflow(pid,'owner',lead_status='DO_NOT_CONTACT')
 with db_session(path) as c:
  assert c.execute('SELECT COUNT(*) FROM prospect_observations').fetchone()[0]==4
  assert c.execute('SELECT COUNT(DISTINCT campaign_id) FROM lead_source_evidence').fetchone()[0]==3
  assert c.execute('SELECT COUNT(*) FROM lead_source_evidence WHERE organization_id=?',(PLANEBYTE_ORGANIZATION_ID,)).fetchone()[0]==3
  assert c.execute('SELECT COUNT(*) FROM analysis_operations').fetchone()[0]==0
  assert c.execute("SELECT lead_status FROM prospects").fetchone()[0]=='DO_NOT_CONTACT'
  from app.workflows.campaigns import audience
  for _,cid,_ in jobs:assert audience(c,cid)['suppressed']==1
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM automation_email_queue').fetchone()[0]==0
  assert c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE execution_name IS NOT NULL OR lease_owner IS NOT NULL").fetchone()[0]==0
 # A duplicate source worker resumes the same completed batch without another observation.
 jid,cid,p=jobs[-1];asyncio.run(analyze_batch(jid,'controlled',[business()],p,target=1,db_path=path))
 with db_session(path) as c:assert c.execute('SELECT COUNT(*) FROM prospect_observations').fetchone()[0]==4

def test_trusted_missing_website_stays_qualified_without_invented_findings(pipeline,monkeypatch):
 with db_session(pipeline) as c:jid,cid,p=make_source(c,'FILE_IMPORT')
 b=business();b.website=None;b.domain=None
 asyncio.run(analyze_batch(jid,'missing-website',[b],p,target=1,db_path=pipeline))
 with db_session(pipeline) as c:
  assert c.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==1
  assert c.execute('SELECT COUNT(*) FROM review_cases').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM findings').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM opportunity_scores').fetchone()[0]==0
  fields=json.loads(c.execute('SELECT field_sources_json FROM lead_source_evidence').fetchone()[0]);assert fields['_processing']['analysis_status']=='EXCLUDED_FROM_LEAD_ENGINE';assert fields['_processing']['company_information_status']=='NOT_AVAILABLE'
  assert service.detail(c,jid)['counts']['qualified']==1
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

@pytest.mark.parametrize('source',['OVERTURE','FIRECRAWL','FILE_IMPORT','GOOGLE_SHEETS'])
def test_source_agnostic_report_and_email_preparation(db,source,monkeypatch,tmp_path):
 monkeypatch.setattr('app.platform.modules.legacy_enabled',lambda:True)  # Retained historical report workflow.
 from campaign_fixtures import campaign,lead
 from app.reports.service import create_report,execute_report
 from app.workflows import service as workflow
 from app.api.routes.workflows import Run
 from app.mail.config import MailSettings
 from app.mail import service as mail
 cid=campaign(db,'Source '+source);db.execute('UPDATE scan_campaigns SET source_type=? WHERE id=?',(source,cid));b,pid=lead(db,cid,200)
 # Existing fixtures provide public-source/domain evidence; no imported email is promoted by source type.
 settings=MailSettings(_env_file=None,EMAIL_SENDING_ENABLED=True,EMAIL_SEND_MODE='test',EMAIL_PROVIDER='hostinger',EMAIL_TEST_RECIPIENT='contact@planebyte.com')
 monkeypatch.setattr(workflow,'mail_settings',lambda:settings);monkeypatch.setattr(mail,'mail_settings',lambda:settings)
 called=[]
 monkeypatch.setattr('app.mail.service.provider',lambda:called.append(1))
 from tests.workspace_fixtures import workspace_template
 template_id=workspace_template(db)
 r=workflow.create(db,Run(kind='OUTREACH',campaign_id=cid,template_id=template_id).model_dump(),'owner');workflow.prepare(db,r['id'])
 detail=workflow.detail(db,r['id']);assert detail['items_total']==1
 assert detail['items'][0]['status']=='READY',detail['items'][0].get('error')
 assert detail['items'][0]['preview']['rendered_html'] and detail['items'][0]['preview']['report_id'] is None
 assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0 and not called

def test_acquisition_does_not_consume_maps_dispatch_capacity(pipeline,monkeypatch):
 from app.api.services import cloud_executor
 from app.config.settings import get_settings
 with db_session(pipeline) as c:
  jid,cid,p=make_source(c,'FILE_IMPORT')
  acq=PipelineRun(market='Acquisition batch',vertical='dentists',target=1,status='RUNNING');PipelineRunRepository(c).create(acq, organization=PLANEBYTE_ORGANIZATION_ID);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,acq.id));c.execute('INSERT INTO acquisition_batches(job_id,batch_key,run_id) VALUES(?,?,?)',(jid,'capacity',acq.id))
  normal=PipelineRun(market='Bristol',vertical='dentists',target=1,status='QUEUED');PipelineRunRepository(c).create(normal, organization=PLANEBYTE_ORGANIZATION_ID);c.execute('UPDATE automation_controls SET scan_paused=0')
 monkeypatch.setattr(get_settings(),'database_path',str(pipeline));monkeypatch.setattr(get_settings(),'max_active_scans',1)
 called=[];monkeypatch.setattr(cloud_executor,'run_job',lambda rid,**kw:called.append(rid) or 'test-operation')
 assert cloud_executor.dispatch_queued()==[normal.id]
 assert called==[normal.id]
 with db_session(pipeline) as c:
  row=c.execute('SELECT status,execution_name,lease_owner FROM pipeline_runs WHERE id=?',(acq.id,)).fetchone();assert row['status']=='RUNNING' and row['execution_name'] is None and row['lease_owner'] is None


def test_mixed_vertical_batches_share_one_execution_deadline(pipeline,monkeypatch):
 import time
 from types import SimpleNamespace
 from app.acquisition import pipeline as module
 original=module.analyze_batch
 seen=[]
 async def leaf(*args,timeout=None,**kwargs):
  seen.append(timeout)
  await asyncio.wait_for(asyncio.sleep(0.04),timeout=timeout)
 monkeypatch.setattr(module,'analyze_batch',leaf)
 businesses=[SimpleNamespace(vertical='dentists'),SimpleNamespace(vertical='hospitality')]
 with db_session(pipeline) as c:jid,_,_=make_source(c,'FIRECRAWL')
 started=time.monotonic()
 with pytest.raises(asyncio.TimeoutError):asyncio.run(original(jid,'batch',businesses,ProcessingOptions(qualification_mode='ANALYZED',analyze_websites=True),timeout=0.06,db_path=pipeline))
 assert len(seen)==2 and seen[1]<seen[0]/2
 assert time.monotonic()-started<0.12


def test_trusted_analysis_failure_preserves_qualification(pipeline,monkeypatch):
 with db_session(pipeline) as c:jid,cid,p=make_source(c,'FILE_IMPORT')
 async def failed(*args,**kwargs):raise RuntimeError('controlled website failure')
 monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',failed)
 asyncio.run(analyze_batch(jid,'failed-analysis',[business()],p,target=1,db_path=pipeline))
 with db_session(pipeline) as c:
  assert c.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==1
  fields=json.loads(c.execute('SELECT field_sources_json FROM lead_source_evidence').fetchone()[0]);assert fields['_processing']['company_information_status']=='FAILED'
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_firecrawl_without_public_email_never_runs_deep_analysis(pipeline,monkeypatch):
 with db_session(pipeline) as c:jid,cid,p=make_source(c,'FIRECRAWL')
 b=business();b.public_email=None
 probe=AsyncMock(side_effect=AssertionError('No-email discovery must not be analyzed'))
 monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',probe)
 asyncio.run(analyze_batch(jid,'no-email',[b],p,target=1,db_path=pipeline))
 with db_session(pipeline) as c:
  assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM opportunity_scores').fetchone()[0]==0
 assert probe.await_count==0


def test_all_ten_trusted_rows_persist_before_failed_analysis_and_keep_owner_provenance(pipeline,monkeypatch):
 from app.acquisition.worker import import_job
 from app.acquisition.models import ColumnMapping
 from app.acquisition.firecrawl import SourceUnavailable
 from app.acquisition import pipeline as module
 names=['Northstar','Harbour','Maple','Brightline','Cedar','Riverside','Juniper','Oakridge','Silverline','Willow']
 raw=('Company,Website,Email,Industry\n'+''.join(f'{name} Advisory,https://{name.lower()}.test,office@{name.lower()}.test,Specialist consultancy\n' for name in names)).encode()
 with db_session(pipeline) as c:
  staged=service.stage_file(c,current().actor,'Controlled-ten.csv',raw,str(uuid.uuid4()));jid=staged['id']
  service.approve_import(c,jid,current().actor,ColumnMapping(company_name='Company',website='Website',email='Email',vertical='Industry'),ProcessingOptions(), 'Trusted ten',str(uuid.uuid4()))
  configuration=json.loads(service.job(c,jid)['configuration_json'])
 async def analysis_fails(*args,**kwargs):
  with db_session(pipeline) as c:
   assert c.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==10
   assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==10
  raise RuntimeError('controlled analysis failure')
 monkeypatch.setattr('app.acquisition.worker.analyze_batch',analysis_fails)
 with pytest.raises(SourceUnavailable,match='remain qualified'):asyncio.run(import_job(jid,configuration,pipeline))
 with db_session(pipeline) as c:
  assert service.refresh_counts(c,jid)['qualified_imported']==10
  assert c.execute("SELECT COUNT(*) FROM contacts WHERE source_type='OWNER_IMPORT' AND is_public_business_contact=0").fetchone()[0]==10
  assert c.execute('SELECT COUNT(*) FROM acquisition_requests').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM automation_email_queue').fetchone()[0]==0


def test_owner_import_email_can_be_ready_without_claiming_public_evidence(db):
 from campaign_fixtures import campaign,lead
 from app.workflows.campaigns import audience
 cid=campaign(db,'Owner-provided list');b,pid=lead(db,cid,987)
 db.execute('UPDATE scan_campaigns SET source_type=? WHERE id=?',('FILE_IMPORT',cid));db.execute("DELETE FROM contacts WHERE business_id=?",(b.id,))
 fields={'email':{'verification':'OWNER_PROVIDED','value':b.public_email},'_processing':{'policy':'TRUSTED_IMPORT'}}
 db.execute('INSERT INTO lead_source_evidence(id,prospect_id,business_id,campaign_id,source_type,field_sources_json,was_existing,observed_at,organization_id) VALUES(?,?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),pid,b.id,cid,'FILE_IMPORT',json.dumps(fields),0,now(),current().organization_id))
 assert audience(db,cid)['will_queue']==1
 from app.automation.service import reconcile
 reconcile(db)
 assert db.execute('SELECT contact_state FROM master_lead_state WHERE prospect_id=?',(pid,)).fetchone()[0]=='READY_TO_EMAIL'
 db.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT' WHERE id=?",(pid,))
 a=audience(db,cid);assert a['qualified']==1 and a['suppressed']==1 and a['will_queue']==0
 assert db.execute('SELECT COUNT(*) FROM contacts WHERE is_public_business_contact=1').fetchone()[0]==0


def test_firecrawl_search_counts_only_email_contactable_businesses_before_analysis(pipeline,monkeypatch):
 from app.acquisition import worker
 config={'intent':{**INTENT,'targetQualifiedLeads':2},'processing':ProcessingOptions(default_vertical='dentists',default_city='Bristol').model_dump(),'budgets':{'max_searches':1,'max_scraped_pages':6,'max_candidates':6,'max_runtime_seconds':120,'max_crawl_pages':0}}
 with db_session(pipeline) as c:
  r=service.create_job(c,'FIRECRAWL',current().actor,str(uuid.uuid4()),config,{});jid=r['id'];cid=service.create_campaign(c,jid,'Contactable controlled sample',target=2)
 class Source:
  async def search(self,*a,**kw):return {'items':[{'url':f'https://practice{n}.test'} for n in range(5)]}
  async def scrape(self,url):return {'url':url}
  def candidate(self,url,page):
   n=int(url.split('practice')[1].split('.')[0]);email=None if n<2 else f'office@practice{n}.test'
   return {'company_name':f'Practice {n} Dental','website':url,'email':email,'city':'Bristol','country':'United Kingdom','source_url':url,'evidence_text':'independent dental practice Bristol'.lower(),'field_sources':{'email':{'url':url,'verification':'PUBLICLY_PUBLISHED'}}},None
 monkeypatch.setattr(worker,'FirecrawlLeadSource',Source);monkeypatch.setattr('app.enrichment.dns.check_email_dns',lambda *a:('MX',True))
 original=worker.analyze_batch;analyzed=[]
 async def checked(jid,key,businesses,*args,**kw):
  assert all(b.public_email and b.website for b in businesses);analyzed.extend(b.domain for b in businesses)
  return await original(jid,key,businesses,*args,**kw)
 monkeypatch.setattr(worker,'analyze_batch',checked)
 asyncio.run(worker.firecrawl_job(jid,config,pipeline))
 assert analyzed==['practice2.test','practice3.test']
 with db_session(pipeline) as c:
  counts=service.refresh_counts(c,jid);assert counts['qualified']==2 and counts['no_email']==2
  assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==2
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_source_worker_records_safe_failure_diagnostics(pipeline,monkeypatch,caplog):
 from app.acquisition import worker
 with db_session(pipeline) as c:jid,cid,_=make_source(c,'FILE_IMPORT')
 monkeypatch.setattr('app.acquisition.config.require',lambda *a:None)
 async def failed(*a,**kw):raise RuntimeError('private-provider-token-must-not-be-logged')
 monkeypatch.setattr(worker,'process',failed)
 worker.execute(jid,pipeline)
 with db_session(pipeline) as c:
  record=c.execute("SELECT message,counts_json FROM acquisition_events WHERE job_id=? AND stage='ERROR_DIAGNOSTIC'",(jid,)).fetchone()
  assert json.loads(record['counts_json'])['error_type']=='RuntimeError'
  assert 'private-provider-token' not in record['message']+record['counts_json']+caplog.text
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
  assert service.job(c,jid)['lease_owner'] is None


def test_firecrawl_resume_finishes_analysis_before_target_early_return(pipeline,monkeypatch):
 from app.acquisition import worker
 with db_session(pipeline) as c:
  jid,cid,p=make_source(c,'FIRECRAWL');configuration=json.loads(service.job(c,jid)['configuration_json']);configuration['intent']['targetQualifiedLeads']=1
 b=business();b.source_tags=json.dumps({'field_sources':{'email':{'verification':'PUBLICLY_PUBLISHED','url':b.website,'value':b.public_email,'dns_validated':True}}})
 original_probe=__import__('app.enrichment.crawler',fromlist=['WebsiteCrawler']).WebsiteCrawler.crawl
 async def failed(*a,**kw):raise RuntimeError('controlled interrupted analysis')
 monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',failed)
 asyncio.run(analyze_batch(jid,'saved-contactable',[b],p,target=1,db_path=pipeline))
 with db_session(pipeline) as c:assert service.refresh_counts(c,jid)['qualified']==1
 monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',original_probe)
 source=type('NoRediscovery',(),{'search':AsyncMock(side_effect=AssertionError('Do not rediscover a completed contactable target')),'scrape':AsyncMock(side_effect=AssertionError('Do not refetch paid discovery'))})()
 monkeypatch.setattr(worker,'FirecrawlLeadSource',lambda:source)
 asyncio.run(worker.firecrawl_job(jid,configuration,pipeline))
 with db_session(pipeline) as c:
  assert c.execute('SELECT status FROM pipeline_runs').fetchone()[0]=='COMPLETED'
  assert c.execute('SELECT COUNT(*) FROM website_profiles').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM opportunity_scores').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM prospect_observations').fetchone()[0]==1
  assert service.refresh_counts(c,jid)['qualified']==1
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 assert source.search.await_count==source.scrape.await_count==0


def test_firecrawl_retains_verified_public_email_when_analysis_cannot_rediscover_it(pipeline,monkeypatch):
 from app.enrichment.contacts import ExtractedContacts
 with db_session(pipeline) as c:jid,cid,p=make_source(c,'FIRECRAWL')
 b=business();b.source_tags=json.dumps({'field_sources':{'email':{'verification':'PUBLICLY_PUBLISHED','url':'http://acme.test/contact','value':b.public_email,'dns_validated':True}}})
 async def crawl(self,start_url,**kw):
  r=CrawlResult(start_url);r.homepage_html='<html><title>Acme Dental Bristol</title><h1>Acme Dental</h1><p>Bristol dental care</p></html>';r.all_htmls={start_url:r.homepage_html};r.pages_crawled=1;r.contacts=ExtractedContacts();return r
 monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',crawl)
 asyncio.run(analyze_batch(jid,'public-source-email',[b],p,target=1,db_path=pipeline))
 with db_session(pipeline) as c:
  contact=c.execute("SELECT * FROM contacts WHERE source_type='FIRECRAWL'").fetchone()
  assert contact['contact_value']=='info@acme.test' and contact['is_public_business_contact']==1 and contact['is_valid']==1 and contact['source_url']=='http://acme.test/contact'
  from app.workflows.campaigns import trusted_emails
  assert (c.execute('SELECT id FROM prospects').fetchone()[0],'info@acme.test') in trusted_emails(c,[cid])
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

def test_resume_skips_completed_queries_but_keeps_cumulative_search_results(pipeline,monkeypatch):
 from app.acquisition import worker
 config={'intent':{**INTENT,'queries':['first contact query','second contact query'],'targetQualifiedLeads':1},'processing':ProcessingOptions(default_vertical='dentists',default_city='Bristol').model_dump(),'budgets':{'max_searches':2,'max_scraped_pages':2,'max_candidates':2,'max_runtime_seconds':120,'max_crawl_pages':0}}
 with db_session(pipeline) as c:
  r=service.create_job(c,'FIRECRAWL',current().actor,str(uuid.uuid4()),config,{});jid=r['id'];service.create_campaign(c,jid,'Resume controlled sample',target=1)
  c.execute("INSERT INTO acquisition_requests(job_id,request_key,kind,status,response_json,created_at) VALUES(?,'search:0','search','COMPLETED',?,?)",(jid,json.dumps({'items':[{'url':'https://no-contact.test'}]}),now()))
  service.event(c,jid,'QUERY_RESULT','First query fully processed.',{'query':'first contact query','results':1,'new_qualified':0})
 searched=[];scraped=[]
 class Source:
  async def search(self,query,**kw):searched.append(query);return {'items':[{'url':'https://new-practice.test'}]}
  async def scrape(self,url):scraped.append(url);return {}
  def candidate(self,url,page):return {'company_name':'New Practice Dental','website':url,'email':'office@new-practice.test','city':'Bristol','country':'United Kingdom','source_url':url,'evidence_text':'dental practice Bristol'.lower(),'field_sources':{'email':{'url':url,'verification':'PUBLICLY_PUBLISHED'}}},None
 monkeypatch.setattr(worker,'FirecrawlLeadSource',Source);monkeypatch.setattr('app.enrichment.dns.check_email_dns',lambda *a:('MX',True))
 asyncio.run(worker.firecrawl_job(jid,config,pipeline))
 assert searched==['second contact query'] and scraped==['https://new-practice.test']
 with db_session(pipeline) as c:
  counts=service.refresh_counts(c,jid);assert counts['qualified']==1 and counts['search_results']==2

def test_contact_page_records_reported_credits_even_without_email(pipeline):
 from app.acquisition.enrichment import contact_page_email
 from app.acquisition.models import Budgets
 config={'processing':ProcessingOptions().model_dump()}
 with db_session(pipeline) as c:
  jid=service.create_job(c,'FIRECRAWL',current().actor,str(uuid.uuid4()),config,{})['id']
 class Source:
  async def scrape(self,url):return {'html':'<html><title>Contact Example Dental</title><p>Please telephone reception.</p></html>','metadata':{'sourceURL':url},'_credits_used':1}
 data={'website':'https://example.test','contact_page':'https://example.test/contact','field_sources':{}}
 result=asyncio.run(contact_page_email(jid,data,Source(),Budgets(),pipeline));assert not result.get('email')
 with db_session(pipeline) as c:assert c.execute("SELECT credits FROM acquisition_requests WHERE job_id=? AND kind='scrape'",(jid,)).fetchone()[0]==1
