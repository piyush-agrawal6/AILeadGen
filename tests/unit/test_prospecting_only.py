"""New Lead Engine contract: company evidence and owned targeting, no assessments."""
import asyncio,json,uuid
from unittest.mock import AsyncMock,Mock
import pytest
from fastapi import HTTPException
from app.database.connection import get_connection,db_session
from app.database.migrations import run_migrations
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.prospecting.intake import process,match_icp
from app.prospecting.policy import configuration
from app.enrichment.crawler import CrawlResult
from app.acquisition.models import ProcessingOptions
from app.pipeline.runner import PipelineRunner
from app.acquisition.pipeline import CandidateCoordinator

@pytest.fixture
def owned(tmp_path,monkeypatch):
 path=tmp_path/'companies.db';c=get_connection(path);run_migrations(c)
 org=create_organization(c,'controlled@example.test','Controlled company')['organization_id'];other=create_organization(c,'foreign@example.test','Foreign company')['organization_id']
 # These fixtures represent previously authorized Lead Engine customers. New
 # customer creation intentionally does not enroll them in Lead Engine.
 c.execute("UPDATE organization_products SET enabled=1 WHERE product='LEADGEN' AND organization_id IN (?,?)",(org,other))
 monkeypatch.setenv('ARTIFACT_LOCAL_ROOT',str(tmp_path/'artifacts'));c.commit();yield c,path,org,other;c.close()

def batch(c,org,source='FILE_IMPORT'):
 cid=str(uuid.uuid4());stamp='2026-11-06T00:00:00+00:00';c.execute("INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,organization_id) VALUES(?,?,?,?,?,?)",(cid,'controlled@example.test','{}',stamp,2,org))
 run=PipelineRun(market='Bristol, United Kingdom',vertical='dentists',target=2,status='RUNNING',run_configuration=configuration({'target':2,'source_type':source,'max_candidates':5,'created_by':'controlled@example.test','lighthouse_enabled':True,'opportunities':['SEO','SECURITY']}));PipelineRunRepository(c).create(run,organization=org);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run.id));c.commit();return cid,run

def company(run,n=1,email=True):return Business(run_id=run.id,name='Controlled Dentistry '+str(n),normalized_name='controlled dentistry '+str(n),vertical='dentists',city='Bristol',country='United Kingdom',website='https://controlled'+str(n)+'.example.com',domain='controlled'+str(n)+'.example.com',public_email='contact@controlled'+str(n)+'.example.com' if email else None,source_tags=json.dumps({'field_sources':{'email':{'url':'https://controlled'+str(n)+'.example.com/contact','value':'contact@controlled'+str(n)+'.example.com','verification':'PUBLICLY_PUBLISHED','dns_validated':True}}}))

async def crawl(url):
 value=CrawlResult(url);value.pages_crawled=1;value.homepage_html='<title>Controlled Dentistry</title><meta name="description" content="Dental services in Bristol."><p>Public company information.</p>';value.all_htmls={url:value.homepage_html};return value

def test_historical_flags_cannot_reenable_assessments_and_runner_exports_general_companies(owned,tmp_path,monkeypatch):
 c,path,org,_=owned
 with workspace_scope(c,'controlled@example.test',org):
  cid,run=batch(c,org);businesses=[company(run),company(run,2,False)]
  crawler=AsyncMock(side_effect=crawl);monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',lambda self,url: crawler(url))
  from importlib.util import find_spec
  assert find_spec('app.audit.lighthouse') is None
  monkeypatch.setattr('app.audit.quick.perform_quick_audit',Mock(side_effect=AssertionError('No audit may run')))
  runner=PipelineRunner(db_path=path,output_dir=tmp_path/'exports',discovery_coordinator=CandidateCoordinator(businesses,ProcessingOptions(),__import__('app.acquisition.policy',fromlist=['policy']).policy('FILE_IMPORT')))
  result=asyncio.run(runner.run(run.market,run.vertical,run.target,run_id=run.id,enable_lighthouse=True,run_configuration=run.run_configuration))
  assert result.status=='COMPLETED' and result.qualified==2 and result.exported==2
  assert c.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==2
  for table in ('lighthouse_results','opportunity_scores','findings','website_profiles','client_reports'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
  assert crawler.await_count==2
  from pathlib import Path
  assert Path(result.output_file).exists();text=Path(result.output_file).with_suffix('.csv').read_text();assert 'qualification' in text and 'security_score' not in text
  tags=json.loads(c.execute('SELECT source_tags_json FROM businesses ORDER BY id LIMIT 1').fetchone()[0]);assert tags['company_intelligence']['summary']=='Dental services in Bristol.'
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

def test_import_analysis_failure_and_suppression_never_change_company_qualification(owned):
 c,path,org,_=owned
 with workspace_scope(c,'controlled@example.test',org):
  cid,run=batch(c,org);b=company(run,email=False);BusinessRepository(c).insert(b);c.commit()
  counts=asyncio.run(process(c,[b],cid,run.run_configuration,Mock(crawl=AsyncMock(side_effect=RuntimeError('unreachable'))),lambda:None,lambda **kw:None))
  assert counts['qualified']==1 and counts['manual_contact']==1
  assert BusinessRepository(c).get_by_id(b.id).processing_status=='QUALIFIED'

def test_firecrawl_without_published_email_never_crawls_or_counts(owned):
 c,path,org,_=owned
 with workspace_scope(c,'controlled@example.test',org):
  cid,run=batch(c,org,'FIRECRAWL');b=company(run,email=False);BusinessRepository(c).insert(b);c.commit();crawler=Mock(crawl=AsyncMock())
  counts=asyncio.run(process(c,[b],cid,run.run_configuration,crawler,lambda:None,lambda **kw:None));assert counts['qualified']==0;crawler.crawl.assert_not_called()

def test_icp_ownership_is_verified_and_unmeasured_criteria_are_unknown(owned):
 from app.icp.models import Create
 from app.icp.service import create
 c,path,org,other=owned
 with workspace_scope(c,'foreign@example.test',other):foreign=create(c,Create(name='Foreign ICP',status='ACTIVE',criteria={'company':{'countries':['India']}},request_id=uuid.uuid4()))
 with workspace_scope(c,'controlled@example.test',org):
  _,run=batch(c,org);b=company(run)
  with pytest.raises(HTTPException) as denied:match_icp(c,b,{}, {'icp_id':foreign['id']})
  assert denied.value.status_code==404
  own=create(c,Create(name='Owned ICP',status='ACTIVE',criteria={'company':{'countries':['United Kingdom'],'employee_min':10}},request_id=uuid.uuid4()))
  result=match_icp(c,b,{}, {'icp_id':own['id']});assert result['status']=='PARTIAL';assert any(item['field']=='company.employee_min' and item['status']=='UNKNOWN' for item in result['criteria'])


def test_old_flags_and_report_dispatch_are_fail_closed_before_cloud_access():
 result=configuration({'lighthouse_enabled':True,'analyze_seo':True,'analyze_security':True,'vapt_enabled':True,'deep_audit_budget':100})
 assert not any(result[key] for key in ('lighthouse_enabled','analyze_seo','analyze_security','vapt_enabled','client_specific_pdf_enabled','static_company_pdf_enabled'))
 from app.api.services.cloud_executor import run_job
 cloud=Mock()
 with pytest.raises(HTTPException):run_job(None,cloud,report_id=str(uuid.uuid4()))
 cloud.post.assert_not_called()


def test_cleanup_preserves_historical_assessments_and_contact_safety_ledgers(owned):
 from app.database.models import WebsiteProfile,LighthouseResult,Finding,LeadScore
 from app.database.repositories import WebsiteProfileRepository,LighthouseRepository,FindingRepository,LeadScoreRepository
 from app.database.prospects import ProspectRepository
 from app.mail import contacted
 c,path,org,_=owned
 with workspace_scope(c,'controlled@example.test',org):
  cid,run=batch(c,org);b=company(run);BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,cid,organization=org)
  WebsiteProfileRepository(c).upsert(WebsiteProfile(business_id=b.id,requested_url=b.website,html_title='Historical measured page',reachable=True))
  LighthouseRepository(c).upsert(LighthouseResult(business_id=b.id,performance_score=67))
  FindingRepository(c).insert_batch([Finding(business_id=b.id,finding_code='HISTORICAL',category='SEO',severity='LOW',title='Historical observation',description='Preserve recorded evidence.')])
  LeadScoreRepository(c).upsert(LeadScore(business_id=b.id,total_score=42,tier='B'))
  contacted.record(c,message_id='historical-controlled',email=b.public_email,sent_at='2026-11-01T00:00:00+00:00',flags={'unsubscribed':True,'do_not_contact':True})
  tables=('website_profiles','lighthouse_results','findings','lead_scores','contacted_recipients','contacted_recipient_sends','schema_migrations')
  before={table:[dict(row) for row in c.execute('SELECT * FROM '+table).fetchall()] for table in tables};c.commit()
  result=asyncio.run(process(c,[b],cid,run.run_configuration,Mock(crawl=AsyncMock(side_effect=crawl)),lambda:None,lambda **kw:None))
  assert result['qualified']==1
  assert {table:[dict(row) for row in c.execute('SELECT * FROM '+table).fetchall()] for table in tables}==before
  assert contacted.lookup(c,b.public_email)['unsubscribed']==1


def test_artifact_reads_require_owned_context_and_pure_visibility_parser_is_preserved(owned,tmp_path,monkeypatch):
 from app.storage import publish_artifact,download_artifact
 from app.audit.structured_data import analyze_structured_data as compatibility
 from app.search_visibility.structured_data import analyze_structured_data
 c,path,org,other=owned
 assert compatibility is analyze_structured_data
 assert analyze_structured_data('<script type="application/ld+json">{"@type":"Hotel"}</script>','hospitality')==(True,['Hotel'],True)
 with workspace_scope(c,'controlled@example.test',org):
  cid,run=batch(c,org);b=company(run);BusinessRepository(c).insert(b);c.commit()
  file=tmp_path/'history.html';file.write_text('<p>Historical company report</p>');publish_artifact(c,'audits/controlled/history.html',file,business_id=b.id,kind='html');c.commit()
  response=download_artifact(c,business_id=b.id,kind='html');assert response.headers['content-security-policy'].startswith('sandbox;')
 with workspace_scope(c,'foreign@example.test',other):
  with pytest.raises(HTTPException) as denied:download_artifact(c,business_id=b.id,kind='html')
  assert denied.value.status_code==404
 with pytest.raises(HTTPException) as missing:download_artifact(c,business_id=b.id,kind='html')
 assert missing.value.status_code==403


def test_maps_company_fit_is_independent_of_email_or_website_availability(owned):
 c,path,org,_=owned
 with workspace_scope(c,'controlled@example.test',org):
  cid,run=batch(c,org,'OVERTURE');b=company(run,email=False);b.website=None;BusinessRepository(c).insert(b);c.commit()
  crawler=Mock(crawl=AsyncMock(side_effect=AssertionError('No website must not crawl')))
  result=asyncio.run(process(c,[b],cid,run.run_configuration,crawler,lambda:None,lambda **kw:None))
  assert result['qualified']==1 and result['manual_contact']==1
  saved=BusinessRepository(c).get_by_id(b.id);assert saved.processing_status=='QUALIFIED' and saved.public_email is None
  tags=json.loads(saved.source_tags);assert tags['contact_availability']['status']=='NO_USABLE_PUBLIC_EMAIL'
  assert tags['icp_match']['status']=='NOT_CONFIGURED'
  crawler.crawl.assert_not_called()
  for table in ('findings','opportunity_scores','lighthouse_results','email_messages'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
