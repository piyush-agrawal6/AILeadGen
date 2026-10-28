import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.models import Business, PipelineRun
from app.database.repositories import BusinessRepository, PipelineRunRepository
from app.database.prospects import ProspectRepository
from app.enrichment.social_intelligence import normalize_profile, discover_profiles, parse_activity, timestamp_status, presence_summary, store_social
from app.scoring.commercial import classify_scale_v2, commercial_fit
from app.api.services.deletion import preview, delete

@pytest.mark.parametrize('missing',[None,float('nan'),'null','nan','',[]])
def test_missing_source_metadata_does_not_discard_businesses(missing):
    from app.discovery.source_metadata import source_metadata
    tags=json.loads(source_metadata('{"primary":"dentist"}',missing))
    assert tags=={'primary':'dentist','socials':[]}

def test_source_metadata_preserves_social_array_and_taxonomy():
    from app.discovery.source_metadata import source_metadata
    assert json.loads(source_metadata('{"primary":"dentist"}','["https://youtube.com/@clinic"]'))=={'primary':'dentist','socials':['https://youtube.com/@clinic']}

@pytest.mark.parametrize('missing',[None,float('nan'),'NaN','null','<NA>'])
def test_missing_website_does_not_become_a_corporate_domain(missing):
    from app.discovery.source_metadata import optional_text
    from app.scoring.commercial import professional_domain,footprint_counts
    from app.reports.data import public_url
    assert optional_text(missing) is None
    assert not professional_domain('nan') and public_url('http://nan/')==''
    b=Business(name='Missing domain',normalized_name='missing domain',vertical='dentists',domain='nan',website='http://nan/')
    conn=Mock();assert footprint_counts(conn,b)==(1,1,1);conn.execute.assert_not_called()
    assert commercial_fit(b,'LOCAL','LOW')[0]=='UNKNOWN'

def test_worker_queue_handoff_does_not_initialize_scan_manager():
    import subprocess,sys,os
    result=subprocess.run([sys.executable,'-c',"import sys;import app.api.services.cloud_executor;assert 'app.api.services.scan_manager' not in sys.modules"],env={**os.environ,'APP_ENV':'test','SCAN_EXECUTOR':'gcp'},capture_output=True,text=True)
    assert result.returncode==0,result.stderr

@pytest.mark.parametrize('url,platform', [('https://instagram.com/clinic/?utm_source=x','INSTAGRAM'),('https://m.facebook.com/dentalcare','FACEBOOK'),('https://linkedin.com/company/dental-care','LINKEDIN'),('https://twitter.com/dentalcare','X'),('https://youtube.com/@dentalcare','YOUTUBE'),('https://tiktok.com/@dentalcare','TIKTOK'),('https://pinterest.com/dentalcare','PINTEREST'),('https://threads.net/@dentalcare','THREADS')])
def test_canonical_profiles(url,platform):
    p=normalize_profile(url);assert p and p['platform']==platform and '?' not in p['profile_url']

@pytest.mark.parametrize('url',['https://instagram.com.evil.com/clinic','https://instagram.com/p/123','https://facebook.com/sharer.php?u=x','https://youtube.com/watch?v=123','https://linkedin.com/in/employee','https://user:pass@instagram.com/clinic','https://instagram.com/accounts/login','javascript:alert(1)'])
def test_reject_non_business_social_urls(url):assert normalize_profile(url) is None

def test_activity_requires_owned_dated_post():
    p=normalize_profile('https://instagram.com/dentalcare');today=datetime(2026,10,26,tzinfo=timezone.utc)
    assert timestamp_status('2026-10-20',today).status=='RECENT'
    assert timestamp_status('2026-09-01',today).status=='ACTIVE'
    assert timestamp_status('2025-01-01',today).status=='STALE'
    assert timestamp_status('2027-01-01',today).status=='UNKNOWN'
    assert parse_activity('<title>Log in</title><time datetime="2025-01-01">Old</time>',p,today).status=='UNKNOWN'
    node={'@type':'SocialMediaPosting','author':{'url':p['profile_url']},'datePublished':'2026-10-20','url':'https://instagram.com/p/abc'}
    html='<script type="application/ld+json">'+json.dumps(node)+'</script>'
    assert parse_activity(html,p,today).status=='RECENT'
    node['author']['url']='https://instagram.com/another';assert parse_activity('<script type="application/ld+json">'+json.dumps(node)+'</script>',p,today).status=='UNKNOWN'
    assert presence_summary([{'activity_status':'UNKNOWN'}])=='UNKNOWN'
    assert presence_summary([{'activity_status':'STALE'},{'activity_status':'UNKNOWN'}])=='UNKNOWN'

def test_discovery_combines_same_as_footer_contact_and_source_lists():
    b=Business(name='Clinic',normalized_name='clinic',vertical='dentists',source_overture=True,source_tags=json.dumps({'socials':['https://youtube.com/@dentalcare']}))
    pages={'https://clinic.example':'<script type="application/ld+json">{"sameAs":["https://instagram.com/dentalcare/?utm_source=test"]}</script><footer><a href="https://instagram.com/dentalcare">IG</a></footer>', 'https://clinic.example/contact':'<a href="https://linkedin.com/company/dentalcare">LI</a>'}
    profiles=discover_profiles(pages,b);assert len(profiles)==3
    assert {p['platform'] for p in profiles}=={'INSTAGRAM','LINKEDIN','YOUTUBE'}
    assert next(p for p in profiles if p['platform']=='INSTAGRAM')['confidence']=='HIGH'

@pytest.mark.parametrize('locations,expected',[(1,'LOCAL'),(2,'SMALL_GROUP'),(5,'SMALL_GROUP'),(6,'MID_MARKET'),(15,'MID_MARKET'),(25,'MID_MARKET'),(26,'REGIONAL'),(100,'REGIONAL'),(101,'ENTERPRISE')])
def test_scale_bands_preserve_independent_groups(locations,expected):
    b=Business(name='Independent Dental',normalized_name='independent dental',vertical='dentists',domain='independent.example',website='https://independent.example')
    assert classify_scale_v2(b,locations,2 if locations>1 else 1)[0]==expected
    assert commercial_fit(b,'MID_MARKET','HIGH')[0]=='HIGH'

@pytest.fixture
def deletion_fixture(tmp_path):
    c=get_connection(tmp_path/'delete.db');run_migrations(c)
    c.execute("INSERT INTO scan_campaigns(id,created_by,status,configuration_json,target_total,created_at) VALUES('one','founder@example.com','COMPLETED',?,5,'2026-10-26')",(json.dumps({'cities':['London'],'verticals':['dentists']}),))
    runs=[];businesses=[]
    for campaign in ['one',None]:
        run=PipelineRun(market='London',vertical='dentists',target=5,status='COMPLETED');PipelineRunRepository(c).create(run);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(campaign,run.id));runs.append(run.id)
        b=Business(name='Shared Dental',normalized_name='shared dental',vertical='dentists',city='London',country='UK',website='https://shared.example',domain='shared.example',address='1 Street',run_id=run.id);BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,campaign);businesses.append(b)
    c.commit();yield c,runs,businesses;c.close()

def test_campaign_delete_preserves_other_observation_and_workflow(deletion_fixture,monkeypatch):
    c,runs,b=deletion_fixture;pid=c.execute('SELECT prospect_id FROM businesses WHERE id=?',(b[0].id,)).fetchone()[0]
    ProspectRepository(c).add_note(pid,'founder@example.com','Keep this note');c.commit()
    storage=Mock();monkeypatch.setattr('app.api.services.deletion.artifact_storage',lambda:storage)
    p=preview(c,'campaign','one');c.commit();assert p['shared_leads_retained']==1
    assert delete(c,'campaign','one','DELETE',p['token'],'founder@example.com')['deleted']
    assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM prospect_notes').fetchone()[0]==1
    assert c.execute('SELECT COUNT(*) FROM scan_campaigns').fetchone()[0]==0

def test_lead_delete_all_observations_and_retry_failed_storage(deletion_fixture,monkeypatch):
    c,runs,b=deletion_fixture;storage=Mock();storage.delete_many.side_effect=RuntimeError('unavailable');monkeypatch.setattr('app.api.services.deletion.artifact_storage',lambda:storage)
    p=preview(c,'lead',str(b[0].id));c.commit()
    with pytest.raises(HTTPException) as e:delete(c,'lead',str(b[0].id),'DELETE',p['token'],'founder@example.com')
    assert e.value.status_code==503 and c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==2
    assert c.execute('SELECT COUNT(*) FROM deletion_batches').fetchone()[0]==1
    storage.delete_many.side_effect=None
    assert delete(c,'lead',str(b[0].id),'DELETE',p['token'],'founder@example.com')['deleted']
    for table in ['businesses','prospects','business_identities','prospect_observations','deletion_batches']:assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==2

def test_delete_rejects_missing_confirmation_and_stale_preview(deletion_fixture):
    c,_,b=deletion_fixture
    with pytest.raises(HTTPException) as e:delete(c,'lead',str(b[0].id),'yes','bad','founder@example.com')
    assert e.value.status_code==422
    with pytest.raises(HTTPException) as e:delete(c,'lead',str(b[0].id),'DELETE','0'*64,'founder@example.com')
    assert e.value.status_code==409

def test_delete_removes_all_versions_private_files_and_derived_data(deletion_fixture,monkeypatch,tmp_path):
    from app.storage import publish_artifact, artifact_storage
    from app.database.prospects import now
    c,runs,b=deletion_fixture;pid=c.execute('SELECT prospect_id FROM businesses WHERE id=?',(b[0].id,)).fetchone()[0]
    file=tmp_path/'evidence.pdf';file.write_bytes(b'%PDF-QA')
    for i in (1,2):
        key=f'prospects/{pid}/reports/qa-{i}.pdf';artifact_storage().put(key,file,'application/pdf')
        c.execute("INSERT INTO client_reports(id,prospect_id,business_id,created_at,created_by,version,status,object_key,snapshot_json,updated_at) VALUES(?,?,?,?,?,?,'READY',?,'{}',?)",(f'report-{i}',pid,b[0].id,now(),'founder@example.com',i,key,now()))
    for run in runs:publish_artifact(c,f'campaigns/qa-{run}/leads.csv',file,run_id=run,kind='csv')
    publish_artifact(c,f'audits/{b[0].id}/capture.webp',file,run_id=runs[0],business_id=b[0].id,kind='website_desktop')
    profiles=discover_profiles({'https://shared.example':'<footer><a href="https://instagram.com/shareddental">Social</a></footer>'},b[0]);store_social(c,b[0],profiles)
    c.commit();p=preview(c,'lead',str(b[0].id));c.commit();assert p['files']==5 and p['reports']==2
    delete(c,'lead',str(b[0].id),'DELETE',p['token'],'founder@example.com')
    for table in ('client_reports','artifact_objects','social_profiles','social_profile_sources'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
    assert not list(artifact_storage().root.rglob('*.pdf')) and not list(artifact_storage().root.rglob('*.csv'))

@pytest.mark.asyncio
async def test_social_request_budget_and_unavailable_is_unknown(monkeypatch):
    from app.enrichment.social_intelligence import RequestBudget, enrich_social, PublicWebSocialActivityProvider
    from unittest.mock import AsyncMock
    budget=RequestBudget(maximum=1,timeout=1);client=Mock();client.get=AsyncMock(return_value=Mock(status_code=403))
    await budget.get(client,'https://instagram.com/clinic','instagram.com')
    with pytest.raises(TimeoutError):await budget.get(client,'https://instagram.com/clinic','instagram.com')
    assert client.get.await_count==1
    provider=PublicWebSocialActivityProvider();result=await provider.check(normalize_profile('https://x.com/clinic'),RequestBudget())
    assert result.status=='UNKNOWN'
    b=Business(name='No profiles',normalized_name='no profiles',vertical='dentists')
    profiles,metrics=await enrich_social({},b,enabled=False)
    assert profiles==[] and metrics['requests']==0

@pytest.mark.asyncio
async def test_blocked_profile_never_becomes_stale(monkeypatch):
    from app.enrichment.social_intelligence import PublicWebSocialActivityProvider,RequestBudget
    class BlockedClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):return Mock(status_code=200,text='User-agent: *\nAllow: /') if url.endswith('robots.txt') else Mock(status_code=403,text='<time datetime="2020-01-01">Old</time>')
    monkeypatch.setattr('app.enrichment.social_intelligence.SafeAsyncClient',BlockedClient)
    result=await PublicWebSocialActivityProvider().check(normalize_profile('https://instagram.com/dentalcare'),RequestBudget())
    assert result.status=='UNKNOWN' and result.last_activity_at is None

@pytest.mark.asyncio
async def test_screenshot_skips_unreachable_and_unpermitted_pages(deletion_fixture,monkeypatch):
    from app.enrichment.screenshot import capture_website
    from app.database.models import WebsiteProfile
    from app.enrichment.crawler import CrawlResult
    from unittest.mock import AsyncMock
    c,_,b=deletion_fixture
    process=AsyncMock();monkeypatch.setattr('app.enrichment.screenshot.asyncio.create_subprocess_exec',process)
    assert await capture_website(c,b[0],WebsiteProfile(business_id=b[0].id,requested_url=b[0].website,reachable=False),CrawlResult(b[0].website))=='UNAVAILABLE'
    process.assert_not_called()
