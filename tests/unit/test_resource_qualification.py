"""New Maps qualification gates: no contactable opportunity means no deep work."""
import asyncio,json
from unittest.mock import AsyncMock
import pytest
from test_automation import db
from campaign_fixtures import campaign
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository
from app.enrichment.http_probe import ProbeResult
from app.pipeline.reuse import AnalysisReuse
from app.qualification import resource_gate as gate
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID

OPTIONS={'qualification_flow_version':1,'qualification_mode':'BALANCED','opportunities':['WEBSITE','SEO','SECURITY'],'deep_audit_budget':2,'preliminary_opportunity_threshold':10,'qualified_score_threshold':35}

def candidate(c,n,html,cid=None):
 cid=cid or campaign(c,'Resource gate')
 run=PipelineRun(market='Bristol, United Kingdom',vertical='dentists',target=1,status='RUNNING');PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run.id))
 b=Business(name=f'Independent Dental {n}',normalized_name=f'independent dental {n}',vertical='dentists',subcategory='dental_clinic',country='United Kingdom',city='Bristol',website=f'https://dental{n}.test',domain=f'dental{n}.test',source_tags='{}',run_id=run.id)
 BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,cid,'owner', organization=PLANEBYTE_ORGANIZATION_ID);c.commit()
 probe=ProbeResult(requested_url=b.website,final_url=b.website,reachable=True,http_status=200,https_enabled=True,html_content=html,response_headers={})
 return b,probe,AnalysisReuse(c,run.id,OPTIONS)

def opportunity(points=25):return {'website_opportunity_score':points,'seo_opportunity_score':0,'security_opportunity_score':0,'evidence':{'WEBSITE':[{'code':'NO_VIEWPORT','points':points,'source_url':'https://dental1.test','observed_at':'2026-11-02'}]}}

@pytest.mark.parametrize('mode',['EXPLORATORY','BALANCED','STRICT'])
def test_no_email_blocks_every_mode_and_preserves_canonical(db,monkeypatch,mode):
 b,p,reuse=candidate(db,1,'<h1>Dental</h1>')
 contact=AsyncMock(return_value=[]);audit=AsyncMock(side_effect=AssertionError('No email must not reach opportunity/deep analysis'))
 monkeypatch.setattr(gate,'contact_pages',contact);monkeypatch.setattr(gate,'analyze_opportunities',audit)
 selected,counts=asyncio.run(gate.early_filter(db,[b],{b.id:p},reuse,{**OPTIONS,'qualification_mode':mode},'dentists'))
 assert selected==[] and counts['no_email']==1 and counts['deep_audits_skipped']==1
 saved=db.execute('SELECT * FROM businesses WHERE id=?',(b.id,)).fetchone();assert saved['rejection_reason']=='NO_EMAIL' and saved['processing_status']!='QUALIFIED'
 assert json.loads(saved['source_tags_json'])['qualification']['email_searched_at']
 assert db.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==1
 assert db.execute('SELECT COUNT(*) FROM lighthouse_results').fetchone()[0]==0
 assert not audit.called
 # Negative contact search is cached; the next identical scan does not refetch contact pages.
 reuse2=AnalysisReuse(db,b.run_id,OPTIONS)
 asyncio.run(gate.early_filter(db,[b],{b.id:p},reuse2,OPTIONS,'dentists'))
 assert contact.await_count==1


def test_email_plus_one_website_opportunity_is_sufficient(db,monkeypatch):
 b,p,reuse=candidate(db,2,'<h1>Dental</h1><a href="mailto:office@dental2.test">Contact</a>')
 monkeypatch.setattr(gate,'check_email_dns',lambda *a:('MX',True));monkeypatch.setattr(gate,'analyze_opportunities',lambda *a,**k:opportunity())
 selected,counts=asyncio.run(gate.early_filter(db,[b],{b.id:p},reuse,OPTIONS,'dentists'))
 assert selected==[b] and counts['email_valid']==1 and gate.meaningful(opportunity(),OPTIONS)
 assert b.public_email=='office@dental2.test'
 assert db.execute("SELECT source_type,is_public_business_contact FROM contacts WHERE business_id=?",(b.id,)).fetchone()[0]=='EARLY_EMAIL'
 assert not gate.meaningful(opportunity(0),OPTIONS)
 assert not gate.meaningful(opportunity(25),{**OPTIONS,'qualification_mode':'STRICT'})


def test_email_without_opportunity_and_invalid_domain_skip_deep(db,monkeypatch):
 b,p,reuse=candidate(db,3,'<h1>Dental</h1><a href="mailto:office@dental3.test">Contact</a>')
 monkeypatch.setattr(gate,'check_email_dns',lambda *a:('MX',True));monkeypatch.setattr(gate,'analyze_opportunities',lambda *a,**k:opportunity(0))
 selected,_=asyncio.run(gate.early_filter(db,[b],{b.id:p},reuse,OPTIONS,'dentists'))
 assert not selected and b.rejection_reason=='NO_MEANINGFUL_OPPORTUNITY'
 b,p,reuse=candidate(db,4,'<a href="mailto:office@dental4.test">Email</a>')
 monkeypatch.setattr(gate,'check_email_dns',lambda *a:('NXDOMAIN',False));monkeypatch.setattr(gate,'contact_pages',AsyncMock(return_value=[]))
 selected,counts=asyncio.run(gate.early_filter(db,[b],{b.id:p},reuse,OPTIONS,'dentists'))
 assert not selected and counts['invalid_email']==1 and b.rejection_reason=='INVALID_EMAIL'


def test_suppression_precedes_email_search(db,monkeypatch):
 b,p,reuse=candidate(db,5,'<a href="mailto:office@dental5.test">Email</a>')
 db.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT'")
 dns=AsyncMock(side_effect=AssertionError('Suppressed identity must stop early'));monkeypatch.setattr(gate,'check_email_dns',dns)
 selected,_=asyncio.run(gate.early_filter(db,[b],{b.id:p},reuse,OPTIONS,'dentists'))
 assert not selected and b.rejection_reason=='SUPPRESSED' and not dns.called


def test_lighthouse_requires_actual_performance_indicators():
 p=ProbeResult(requested_url='https://example.test',reachable=True,html_content='<h1>Small page</h1>')
 assert not gate.lighthouse_useful(p)
 p.html_content='<script></script>'*12
 assert gate.lighthouse_useful(p)


def test_new_schedule_requires_explicit_source_and_firecrawl_review():
 from app.api.routes.workflows import Run,Schedule
 from pydantic import ValidationError
 common={'name':'Daily','frequency':'daily','start_at':'2026-12-01T09:00:00+05:30'}
 with pytest.raises(ValidationError,match='Select the scan source'):Schedule(**common,configuration={'kind':'SCAN'})
 assert Schedule(**common,configuration={'kind':'SCAN','scan_source':'OVERTURE'}).configuration.scan_source=='OVERTURE'
 with pytest.raises(ValidationError,match='Interpret and review'):Run(kind='SCAN',scan_source='FIRECRAWL')


def test_maps_light_company_evidence_is_reused_without_assessments(tmp_path,monkeypatch,request):
 from app.database.connection import get_connection,db_session
 from app.database.migrations import run_migrations
 from app.acquisition.pipeline import CandidateCoordinator
 from app.acquisition.models import ProcessingOptions
 from app.acquisition.policy import DISCOVERY
 from app.pipeline.runner import PipelineRunner
 from app.enrichment.crawler import CrawlResult
 from app.enrichment.contacts import extract_contacts_from_html
 from tests.workspace_fixtures import bind_internal_workspace
 path=tmp_path/'maps.db';c=get_connection(path);run_migrations(c);bind_internal_workspace(c,request);c.close()
 crawled=[]
 async def crawl(self,url):
  crawled.append(url);r=CrawlResult(url);html='<title>Bristol Dental Clinic</title><p>Independent dental practice in Bristol.</p><a href="mailto:office@dental10.test">Contact</a>'
  r.all_htmls={url:html};r.homepage_html=html;r.pages_crawled=1;r.contacts=extract_contacts_from_html(html,url);return r
 monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',crawl)
 monkeypatch.setattr('app.prospecting.intake.check_email_dns',lambda *a:('MX',True))
 for attempt in range(2):
  b=Business(name='Independent Dental 10',normalized_name='independent dental 10',vertical='dentists',subcategory='dental_clinic',country='United Kingdom',city='Bristol',website='https://dental10.test',domain='dental10.test',source_overture=True)
  runner=PipelineRunner(db_path=path,output_dir=tmp_path/'out',discovery_coordinator=CandidateCoordinator([b],ProcessingOptions(default_vertical='dentists'),DISCOVERY))
  run=asyncio.run(runner.run('Bristol, United Kingdom','dentists',1,enable_lighthouse=True,run_configuration={**OPTIONS,'source_type':'OVERTURE','target':1,'results':'include_previous'}))
  assert run.status=='COMPLETED' and run.qualified==1
 with db_session(path) as c:
  for table in ('lighthouse_results','website_profiles','findings','opportunity_scores','client_reports','email_messages'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==1
 assert crawled==['https://dental10.test']


def test_deep_audit_budget_bounds_valid_promising_businesses(db,monkeypatch):
 businesses=[];probes={};reuse=None
 for n in (21,22,23):
  b,p,r=candidate(db,n,f'<a href="mailto:office@dental{n}.test">Email</a>');businesses.append(b);probes[b.id]=p;reuse=reuse or r
 monkeypatch.setattr(gate,'check_email_dns',lambda *a:('MX',True));monkeypatch.setattr(gate,'analyze_opportunities',lambda *a,**k:opportunity())
 selected,counts=asyncio.run(gate.early_filter(db,businesses,probes,reuse,{**OPTIONS,'deep_audit_budget':1},'dentists'))
 assert len(selected)==1 and counts['email_valid']==3 and counts['deep_audits_skipped']==2
 assert sum(b.rejection_reason=='DEEP_AUDIT_BUDGET' for b in businesses)==2


def test_no_email_pool_records_shortfall_with_bounded_company_crawling(tmp_path,monkeypatch,request):
 from app.database.connection import get_connection,db_session
 from app.database.migrations import run_migrations
 from app.acquisition.pipeline import CandidateCoordinator
 from app.acquisition.models import ProcessingOptions
 from app.acquisition.policy import DISCOVERY
 from app.pipeline.runner import PipelineRunner
 from app.enrichment.crawler import CrawlResult
 from tests.workspace_fixtures import bind_internal_workspace
 path=tmp_path/'shortfall.db';c=get_connection(path);run_migrations(c);bind_internal_workspace(c,request);c.close()
 businesses=[Business(name=f'Independent Dental {n}',normalized_name=f'independent dental {n}',vertical='dentists',subcategory='dental_clinic',website=f'https://anomaly{n}.test',domain=f'anomaly{n}.test',country='United Kingdom',city='Bristol',source_overture=True) for n in range(20)]
 async def crawl(self,url):
  value=CrawlResult(url);value.all_htmls={url:'<title>Bristol Dental Clinic</title>'};value.pages_crawled=1;return value
 fake=AsyncMock(side_effect=crawl);monkeypatch.setattr('app.enrichment.crawler.WebsiteCrawler.crawl',lambda self,url:fake(self,url))
 runner=PipelineRunner(db_path=path,output_dir=tmp_path/'out',discovery_coordinator=CandidateCoordinator(businesses,ProcessingOptions(default_vertical='dentists'),DISCOVERY))
 result=asyncio.run(runner.run('Bristol, United Kingdom','dentists',5,run_configuration={'source_type':'OVERTURE','target':5,'max_candidates':4}))
 assert result.status=='COMPLETED' and result.qualified==4 and 'TARGET_NOT_REACHED' in result.error_message
 assert fake.await_count==4
 with db_session(path) as c:
  assert c.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==4
  assert c.execute("SELECT COUNT(*) FROM contacts WHERE contact_type='email'").fetchone()[0]==0
  for table in ('lighthouse_results','opportunity_scores','website_profiles'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
