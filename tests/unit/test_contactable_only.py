import json,asyncio
import pytest
from test_automation import db
from campaign_fixtures import campaign
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import now
from app.qualification.contactable import accept,defaults,maps
from app.mail.contacted import record
from app.workflows.campaigns import audience
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID

def candidate(c,cid,n=1,email='public@example.com'):
    r=PipelineRun(market='Bristol, United Kingdom',vertical='dentists',target=10,status='RUNNING');PipelineRunRepository(c).create(r, organization=PLANEBYTE_ORGANIZATION_ID);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,r.id))
    b=Business(name='Example Dental '+str(n),normalized_name='example dental '+str(n),vertical='dentists',country='United Kingdom',city='Bristol',website='https://example.com',domain='example.com',public_email=email,processing_status='NORMALIZED',run_id=r.id);BusinessRepository(c).insert(b);return b

def test_public_contact_qualifies_without_any_analysis_or_findings(db):
    cid=campaign(db);db.execute('UPDATE scan_campaigns SET configuration_json=? WHERE id=?',(json.dumps(defaults()),cid));b=candidate(db,cid)
    assert accept(db,b,cid,'FIRECRAWL',{'url':'https://example.com/contact','verification':'PUBLICLY_PUBLISHED','dns_validated':True})=='QUALIFIED'
    from app.automation.service import reconcile
    reconcile(db)
    for table in ('website_profiles','opportunity_scores','lighthouse_results','client_reports','analysis_operations'):assert db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
    a=audience(db,cid);assert a['will_queue']==1 and a['items'][0]['pitch_types']==['WORKSPACE']

def test_previously_sent_is_not_a_new_qualified_contact(db):
    cid=campaign(db);b=candidate(db,cid)
    record(db,message_id='historical',provider_message_id='<historical@smtp>',email='PUBLIC@example.com',sent_at=now())
    assert accept(db,b,cid,'FIRECRAWL',{'url':'https://example.com/contact','verification':'PUBLICLY_PUBLISHED'})=='ALREADY_CONTACTED'
    assert db.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==0

def test_no_email_does_not_analyze_or_prepare(db):
    cid=campaign(db);b=candidate(db,cid,email=None);b.website=None
    result=asyncio.run(maps(db,[b],cid,{'target':10},lambda:None))
    assert result['qualified']==0 and result['no_email']==1 and result['analyzed']==0
    assert db.execute('SELECT COUNT(*) FROM client_reports').fetchone()[0]==0

def test_dedupe_target_counts_only_one_exact_email(db):
    cid=campaign(db);a=candidate(db,cid);b=candidate(db,cid,2)
    proof={'url':'https://example.com/contact','verification':'PUBLICLY_PUBLISHED'}
    assert accept(db,a,cid,'FIRECRAWL',proof)=='QUALIFIED'
    assert accept(db,b,cid,'FIRECRAWL',proof)=='DUPLICATE_EMAIL'

def test_new_maps_defaults_do_not_inherit_old_analysis_mode(db):
    from app.qualification.configuration import new_scan_settings
    new=new_scan_settings(db,{'target':10})
    assert new['qualification_mode']=='CONTACTABLE_ONLY' and new['email_strategy']=='WORKSPACE'
    assert not new['analysis_enabled'] and not new['lighthouse_enabled']
    assert new_scan_settings(db,{'qualification_mode':'STRICT'})['qualification_mode']=='STRICT'

def test_published_maps_email_qualifies_without_website_or_rediscovery(db,monkeypatch):
    cid=campaign(db);b=candidate(db,cid,email='office@controlled-dental.test');b.website=None;b.source_osm=True;b.external_osm_id='node/123'
    monkeypatch.setattr('app.enrichment.dns.check_email_dns',lambda *a:('MX',True))
    result=asyncio.run(maps(db,[b],cid,{'target':1},lambda:None))
    assert result['qualified']==1 and result['contact_pages']==0 and result['analyzed']==0
    assert db.execute('SELECT COUNT(*) FROM client_reports').fetchone()[0]==0
