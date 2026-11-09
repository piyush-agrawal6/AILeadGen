import json
from datetime import datetime,timedelta,timezone
from test_automation import db
from campaign_fixtures import campaign,lead
from app.workflows.history import signature,capture_settings,capture_business,compare,settings
from app.pipeline.reuse import AnalysisReuse,dump_crawl,load_crawl
from app.enrichment.http_probe import ProbeResult

def test_equivalent_signatures_ignore_order_not_effective_settings():
    a={'countries':['Canada','United States'],'verticals':['hospitality'],'crawler':{'max_pages':8}}
    b={**a,'countries':['United States','Canada'],'name':'Different title','target':500}
    assert signature(a)==signature(b)
    assert signature(a)!=signature({**b,'crawler':{'max_pages':12}})

def test_effective_settings_frozen_and_history_comparison(db):
    first=campaign(db,'First');b,pid=lead(db,first,27)
    options={'countries':['United Kingdom'],'cities':['London'],'verticals':['hospitality']}
    frozen=capture_settings(db,first,options)
    db.execute("INSERT INTO shared_settings(id,configuration_json,updated_by,updated_at) VALUES(1,?,'owner','2026')",(json.dumps({'crawler':{'max_pages':23}}),))
    assert capture_settings(db,first,options)==frozen
    capture_business(db,first,b.id)
    second=campaign(db,'Second');other,pid2=lead(db,second,27)
    assert pid==pid2
    # Explicitly use the original effective configuration to create an equivalent run.
    capture_settings(db,second,frozen)
    db.execute("INSERT INTO findings(business_id,finding_code,category,severity,title,description,score_points) VALUES(?,'NEW_CTA','WEBSITE','MEDIUM','CTA','Observed',10)",(other.id,))
    capture_business(db,second,other.id)
    result=compare(db,second,first)
    assert result['businesses'][0]['state']=='CHANGED'
    assert result['businesses'][0]['new_findings']==['NEW_CTA']
    assert 'NEW_CTA' not in db.execute('SELECT snapshot_json FROM campaign_business_snapshots WHERE business_id=?',(b.id,)).fetchone()[0]
    # Later observation edits cannot mutate either frozen campaign snapshot.
    db.execute('DELETE FROM findings WHERE business_id=?',(other.id,));capture_business(db,second,other.id)
    assert compare(db,second,first)['businesses'][0]['new_findings']==['NEW_CTA']

def test_reuse_requires_same_evidence_freshness_settings_and_mode(db):
    cid=campaign(db);b,pid=lead(db,cid,17);run=db.execute('SELECT run_id FROM businesses WHERE id=?',(b.id,)).fetchone()[0]
    probe=ProbeResult(requested_url=b.website,final_url=b.website,reachable=True,http_status=200,html_content='<title>Hotel</title>',response_headers={'server':'nginx'})
    cache=AnalysisReuse(db,run,{'crawler':{'max_pages':8}})
    cache.put(b,'seo',probe,{'finding':'description missing'});cache.flush()
    hit=AnalysisReuse(db,run,{'crawler':{'max_pages':8}})
    assert hit.get(b,'seo',probe)=={'finding':'description missing'}
    assert hit.get(b,'seo',probe.model_copy(update={'html_content':'<title>Changed</title>'})) is None
    assert AnalysisReuse(db,run,{'crawler':{'max_pages':9}}).get(b,'seo',probe) is None
    assert AnalysisReuse(db,run,{'analysis_mode':'FULL','crawler':{'max_pages':8}}).get(b,'seo',probe) is None
    db.execute("UPDATE analysis_cache SET expires_at='2000-01-01T00:00:00+00:00'")
    assert AnalysisReuse(db,run,{'crawler':{'max_pages':8}}).get(b,'seo',probe) is None

def test_crawl_roundtrip_retains_contact_sources_and_evidence():
    from app.enrichment.crawler import CrawlResult
    cr=CrawlResult('https://hotel.example');cr.homepage_html='<h1>Hotel</h1>';cr.all_htmls={cr.start_url:cr.homepage_html};cr.all_links={'https://hotel.example/contact'}
    cr.contacts.emails=[('published@hotel.example',cr.start_url,.9)];cr.page_statuses={cr.start_url:200}
    restored=load_crawl(dump_crawl(cr))
    assert restored.all_htmls==cr.all_htmls and restored.all_links==cr.all_links
    assert restored.contacts.emails[0][1]==cr.start_url and restored.page_statuses==cr.page_statuses
