"""Release regressions cover rank consistency, finite cleanup, quotas and fallback."""
import asyncio
import json
import uuid
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned,run,source_result,example
from app.config.settings import get_settings
from app.intent_radar import models,providers,service,intelligence,discovery,operations
from app.platform.context import workspace_scope

def test_semantic_discovery_reranks_paraphrase_and_rejects_unverified_fallback(radar,monkeypatch):
    c,path,org,_=radar
    raw={**example(),'title':'Necesitamos cambiar nuestra plataforma','excerpt':'Nuestro negocio necesita ayuda con su sitio web.'}
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value={**source_result(),'items':[raw]}))
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    async def structured(instruction,value,model,**limits):
        return model(categories=['General discussion'],claims=[intelligence.Claim(kind='semantic',quote='ayuda con su sitio web',interpretation='Website support',target='website support')],detected_language='es',language_evidence='Nuestro negocio')
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=structured))
    with workspace_scope(c,'controlled@example.test',org):
        body=models.Search(keywords=['crm'],offerings='website support',semantic=True,language='es',min_relevance=20)
        job=run(c,path,body)
        assert job['status']=='COMPLETED'
        result=job['items'][0]['result']
        assert result['matched']==1 and result['sources'][0]['semantic_evaluations'][0]['accepted']
        assert service.listing(c,'signals')['items'][0]['ranking']['language']=='es'
        # A second run exhausts the independently committed workspace call cap.
        second=run(c,path,body)
        assert second['status']=='COMPLETED' # Valid cache reuse does not spend again.
        monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',False)
        body=models.Search(keywords=['crm'],offerings='website support',semantic=True,semantic_criteria=['different approved criterion'])
        third=run(c,path,body)
        assert third['items'][0]['result']['matched']==0
        assert not third['items'][0]['result']['sources'][0]['semantic_evaluations'][0]['accepted']

def test_source_reservations_survive_failure_and_are_workspace_scoped(radar,monkeypatch):
    c,path,org,other=radar
    monkeypatch.setattr(get_settings(),'intent_radar_daily_searches',1)
    with workspace_scope(c,'controlled@example.test',org):
        operations.reserve_source('hacker_news')
        with pytest.raises(HTTPException) as denied:operations.reserve_source('hacker_news')
        assert denied.value.status_code==429
        assert operations.source_health(c)['items'][0]['daily_requests_reserved']==22
    assert c.execute('SELECT COUNT(*) FROM intent_source_usage WHERE organization_id=?',(other,)).fetchone()[0]==0

def test_retention_rotates_past_nonexpiring_prefix_preserves_saved_notes_and_other_workspace(radar):
    c,path,org,other=radar
    with workspace_scope(c,'controlled@example.test',org):
        for n in range(1001):
            c.execute('INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(f'{n:08}',org,'Hacker News',str(n),'https://news.ycombinator.com/item?id='+str(n),'Public title','Public evidence','2000-01-01T00:00:00+00:00','2000-01-01T00:00:00+00:00' if n==1000 else datetime.now(timezone.utc).isoformat(),'General discussion',10,json.dumps({'provenance':{'retention_days':1}}) if n==1000 else '{}'))
        service.bookmark(c,'00001000')
        c.execute("UPDATE intent_saved_signals SET notes='Preserved owner research' WHERE organization_id=?",(org,));c.commit()
        first=service.expire_content(c);c.commit()
        assert first['scanned']==1000 and first['expired_source_items']==0
        second=service.expire_content(c);c.commit()
        assert second['expired_source_items']==1
        assert service.get(c,'signals','00001000')['excerpt']==''
        assert service.saved(c)['items'][0]['notes']=='Preserved owner research'
        assert c.execute('SELECT COUNT(*) FROM intent_retention_cursors WHERE organization_id=?',(other,)).fetchone()[0]==0

def test_monthly_provider_totals_are_complete_beyond_detail_window(radar):
    from app.platform.provider_usage import record,reported,summary
    c,path,org,_=radar
    provider=SimpleNamespace(config=SimpleNamespace(model_pricing_json='{}',primary_provider='vertex'),model='test',provider_name='VERTEX_AI',usage_connection=c)
    with workspace_scope(c,'controlled@example.test',org):
        import time
        for n in range(1001):record(provider,reported({'usageMetadata':{'promptTokenCount':2,'candidatesTokenCount':1}}),'SUCCEEDED',time.monotonic())
        c.commit();usage=summary(c)
        assert usage['requests']==1001 and usage['input_tokens_reported']==2002 and usage['output_tokens_reported']==1001 and usage['requests_today']==1001
        assert usage['complete'] and len(usage['items'])==50 and usage['estimated_cost_usd'] is None

def test_saved_global_page_filter_sort_and_workspace_profile_contract(radar,monkeypatch):
    c,path,org,_=radar
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0]
        service.bookmark(c,signal['id']);c.execute("UPDATE intent_saved_signals SET collection='Reviewed',tags_json='[\"tagged\"]' WHERE organization_id=?",(org,))
        found=service.saved(c,size=1,search='tagged',collection='Reviewed',sort='oldest')
        assert found['total']==1 and found['collections']==['Reviewed']
        assert service.saved(c,page=2,size=1)['items']==[]
        assert operations.workspace_context(c)['business_profile']['name']

@pytest.mark.parametrize('hosts,origins',[
    ('*.planebyte.com','https://app.planebyte.com'),
    ('app.planebyte.com','*'),
    ('app.planebyte.com','http://app.planebyte.com'),
    ('https://app.planebyte.com','https://app.planebyte.com'),
    ('','https://app.planebyte.com'),
])
def test_production_mcp_rejects_wildcard_or_malformed_policy(hosts,origins):
    from app.developer.mcp_server import transport_policy
    with pytest.raises(ValueError):transport_policy(SimpleNamespace(app_env='production',heysow_mcp_enabled=True,mcp_allowed_hosts=hosts,mcp_allowed_origins=origins))

def test_production_mcp_accepts_exact_host_and_origin():
    from app.developer.mcp_server import transport_policy
    policy=transport_policy(SimpleNamespace(app_env='production',heysow_mcp_enabled=True,mcp_allowed_hosts='leadengine-api-befca7xg4a-el.a.run.app',mcp_allowed_origins='https://app.planebyte.com'))
    assert policy.enable_dns_rebinding_protection

def test_adapter_rejects_invalid_identity_and_request_overflow():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):models.SourceResult.model_validate({**source_result(),'requests':100})
    with pytest.raises(ValidationError):models.SourceResult.model_validate({**source_result(),'items':[{'removed':False}]})
    malformed={**source_result()['items'][0],'source_url':'javascript:alert(1)'}
    with pytest.raises(ValidationError):models.SourceResult.model_validate({**source_result(),'items':[malformed]})

@pytest.mark.parametrize('category',['Promotion','Jobs / hiring','Security announcement','Unrelated discussion','Explicitly non-buying'])
def test_noncommercial_classifications_cannot_cross_high_intent_threshold(category):
    signal={**example(),'title':'Need help with our website. We are not buying.','excerpt':'','evidence':{}}
    output=intelligence.Interpretation(categories=[category],claims=[intelligence.Claim(kind='intent',quote='Need help',interpretation='Topic reference'),intelligence.Claim(kind='semantic',quote='website',interpretation='Website topic',target='website')],uncertainty='Low',review_needed=False)
    assert intelligence.score(signal,intelligence.validated(output,signal,['website']),{'ranking_adjustment':0,'explanation':''})['overall']<75

def test_semantic_monitor_does_not_alert_on_excluded_candidate(radar,monkeypatch):
    c,path,org,_=radar
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    async def structured(instruction,value,model,**limits):
        return model(categories=['Recommendation request'],claims=[intelligence.Claim(kind='intent',quote='website development',interpretation='Topic evidence'),intelligence.Claim(kind='semantic',quote='website development',interpretation='Website relevance',target='website'),intelligence.Claim(kind='exclusion',quote='website development',interpretation='Excluded service category',target='development services')])
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=structured))
    with workspace_scope(c,'controlled@example.test',org):
        q=models.Search(keywords=['website'],offerings='website',semantic=True,semantic_exclusions=['development services'])
        monitor=service.save_monitor(c,models.Monitor(name='Semantic exclusion monitor',configuration=q,status='Active'));c.commit()
        job=discovery.create(c,models.Discovery(configuration=q,monitor_id=monitor['id']));c.commit()
        from app.intelligence import jobs
        jobs.execute(job['id'],path)
        assert discovery.owned_job(c,job['id'])['status']=='COMPLETED'
        assert c.execute('SELECT COUNT(*) FROM intent_monitor_signals WHERE organization_id=?',(org,)).fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM intent_alerts WHERE organization_id=?',(org,)).fetchone()[0]==0

def test_shared_gateway_honors_radar_attempt_cap_without_changing_default():
    from app.acquisition.ai_router import AIProviderRouter
    from app.acquisition.ai import AiProviderError,AiUnavailable
    from app.acquisition.config import AcquisitionSettings
    async def fails(*args,**kwargs):raise AiProviderError(502)
    router=AIProviderRouter(AcquisitionSettings(vertex_enabled=False,gemini_enabled=False),providers=[])
    provider=SimpleNamespace(provider_name='VERTEX_AI',model='test',structured=AsyncMock(side_effect=fails))
    router.providers=[provider]
    with pytest.raises(AiUnavailable):asyncio.run(router.structured('instruction',{},intelligence.Interpretation,attempts_per_provider=1))
    assert provider.structured.await_count==1

def test_icp_industry_market_and_role_match_require_cited_unverified_context():
    signal={**example(),'title':'We operate a dental clinic in France','excerpt':'We are not a software company','_icp_criteria':{'company.industries':['software'],'company.countries':['France'],'contact.job_titles':['CEO']},'evidence':{}}
    output=intelligence.Interpretation(categories=['General discussion'],icp_assessments=[intelligence.CriterionAssessment(criterion='company.industries',status='MISMATCH',quote='not a software company',explanation='Explicit source contradiction'),intelligence.CriterionAssessment(criterion='company.countries',status='MATCH',quote='dental clinic in France',explanation='Self-reported location only'),intelligence.CriterionAssessment(criterion='contact.job_titles',status='UNKNOWN',explanation='No author role evidenced')])
    valid=intelligence.validated(output,signal,[])
    scored=intelligence.score(signal,valid,{'ranking_adjustment':0,'explanation':''})
    assert scored['dimensions']['icp_context_mismatch']==-20 and scored['purchase_probability'] is None
    assert scored['icp_criteria'][1]['basis'].startswith('Unverified')
    from app.acquisition.ai import AiOutputError
    invalid=output.model_copy(update={'icp_assessments':[intelligence.CriterionAssessment(criterion='contact.job_titles',status='MATCH',quote='invented CEO identity',explanation='Unverified claim')]})
    with pytest.raises(AiOutputError):intelligence.validated(invalid,signal,[])

def test_opportunity_pagination_uses_primary_feedback_rank(radar,monkeypatch):
    c,path,org,_=radar
    data=source_result();second={**data['items'][0],'source_record_id':'999456','source_url':'https://news.ycombinator.com/item?id=999456'}
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value={**data,'items':[data['items'][0],second],'scanned':2}))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']))
        for signal in service.listing(c,'signals')['items']:service.opportunity(c,signal['id'])
        before=service.listing(c,'opportunities',size=1)
        assert before['total']==2
        first=before['items'][0]
        intelligence.feedback(c,first['signal_id'],models.Feedback(label='Not relevant'))
        after=service.listing(c,'opportunities',size=1)
        assert after['items'][0]['id']!=first['id']
        assert service.listing(c,'opportunities',size=1,page=2)['items'][0]['id']==first['id']

def test_stack_exchange_watermark_and_cache_preserve_incremental_cursor(radar,monkeypatch):
    import httpx
    from urllib.parse import parse_qs,urlsplit
    from app.intent_radar import connectors
    from pydantic import SecretStr
    c,path,org,_=radar;calls=[]
    monkeypatch.setattr(get_settings(),'intent_radar_stackexchange_enabled',True)
    monkeypatch.setattr(get_settings(),'intent_radar_stackexchange_key',SecretStr('synthetic-test-key'))
    monkeypatch.setattr(connectors,'cooldown',lambda *args,**kwargs:None)
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,**kwargs):
            calls.append(parse_qs(urlsplit(url).query));page=int(calls[-1]['page'][0])
            return httpx.Response(200,json={'has_more':page==1,'quota_remaining':100,'items':[{'question_id':page,'title':'Website recommendation','link':'https://stackoverflow.com/questions/'+str(page),'body':'Website help','creation_date':2000 if page==1 else 1900,'owner':{},'content_license':'CC BY-SA 4.0'}]},request=httpx.Request('GET',url))
    monkeypatch.setattr(connectors,'SafeAsyncClient',Client)
    with workspace_scope(c,'controlled@example.test',org):
        q=models.Search(keywords=['website'],sources=['stack_exchange']);q._collection_cursor={'sites':{'stackoverflow':{'page':1,'since':1}}}
        first=asyncio.run(connectors.fetch(c,q,'stack_exchange',lambda:True));q._collection_cursor=first['cursor']
        assert isinstance(first,models.SourceResult)
        second=asyncio.run(connectors.fetch(c,q,'stack_exchange',lambda:True))
        assert second['cursor']['sites']['stackoverflow']['since']==1880
        cached=asyncio.run(connectors.fetch(c,q,'stack_exchange',lambda:True))
        assert cached['requests']==0 and cached['cursor']==second['cursor'] and len(calls)==2

def test_high_volume_signal_pages_are_stable_scoped_and_query_bounded(radar):
    import time
    c,path,org,other=radar
    with workspace_scope(c,'controlled@example.test',org):
        for n in range(10000):
            c.execute('INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(str(uuid.uuid5(uuid.NAMESPACE_URL,f'synthetic-performance:{n}')),org,'Hacker News',str(n+1),'https://news.ycombinator.com/item?id='+str(n+1),'Synthetic performance corpus','Synthetic public text','2026-11-11T00:00:00+00:00','2026-11-11T00:00:00+00:00','General discussion',n%100,'{}'))
        c.commit();queries=[];c.set_trace_callback(queries.append);started=time.monotonic()
        first=service.listing(c,'signals',size=20,min_score=90,sort='score');elapsed=time.monotonic()-started
        query_count=len(queries);c.set_trace_callback(None)
        second=service.listing(c,'signals',size=20,min_score=90,sort='score',page=2)
        assert first['total']==1000 and len(first['items'])==20 and len(second['items'])==20
        assert {row['id'] for row in first['items']}.isdisjoint(row['id'] for row in second['items'])
        assert all(row['organization_id']==org and row['score']>=90 for row in first['items']) and query_count<75
        print(json.dumps({'synthetic_rows':10000,'first_page_seconds':round(elapsed,4),'first_page_queries':query_count,'scope':'Isolated SQLite engineering measurement, not production scale acceptance'}))
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException) as denied:service.listing(c,'signals')
        assert denied.value.status_code==404

def test_cancelled_semantic_worker_cannot_persist_ai_analysis_or_rank(radar,monkeypatch):
    from app.database.connection import get_connection
    from app.intelligence import jobs
    c,path,org,_=radar
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    job_id=None
    async def structured(instruction,value,model,**limits):
        other=get_connection(path);other.execute("UPDATE intelligence_jobs SET status='CANCELED' WHERE id=?",(job_id,));other.commit();other.close()
        return model(categories=['Recommendation request'],claims=[intelligence.Claim(kind='intent',quote='website development partner',interpretation='Source request'),intelligence.Claim(kind='semantic',quote='website development partner',interpretation='Website topic',target='website')])
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=structured))
    with workspace_scope(c,'controlled@example.test',org):
        job=discovery.create(c,models.Discovery(configuration=models.Search(keywords=['website'],offerings='website',semantic=True)));job_id=job['id'];c.commit();jobs.execute(job_id,path)
        assert discovery.owned_job(c,job_id)['status']=='CANCELED'
        assert c.execute('SELECT COUNT(*) FROM intent_analyses WHERE organization_id=?',(org,)).fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM intent_rankings WHERE organization_id=?',(org,)).fetchone()[0]==0

def test_semantic_duplicate_urls_do_not_double_spend_or_inflate_matches(radar,monkeypatch):
    from app.intent_radar import connectors
    from app.intelligence import jobs
    c,path,org,_=radar
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr(connectors,'approved_endpoint',lambda url:url)
    raw=source_result()['items'][0]
    async def fetch(c,q,key,permit):
        return {**source_result(),'items':[{**raw,'source':'Hacker News' if key=='hacker_news' else 'RSS / Atom'}]}
    monkeypatch.setattr(connectors,'fetch',fetch)
    output=intelligence.Interpretation(categories=['Recommendation request'],claims=[intelligence.Claim(kind='intent',quote='website development partner',interpretation='Source request'),intelligence.Claim(kind='semantic',quote='website development partner',interpretation='Website support',target='website')])
    structured=AsyncMock(return_value=output)
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=structured))
    with workspace_scope(c,'controlled@example.test',org):
        feed=connectors.configure(c,models.SourceConfig(name='Synthetic permitted duplicate feed',family='rss',endpoint='https://example.com/feed',policy_reference='Synthetic publisher approval for isolated fixture',attribution='Synthetic fixture publisher',enabled=True));c.commit()
        q=models.Search(keywords=['website'],offerings='website',semantic=True,sources=['hacker_news','rss'],feed_ids=[feed['id']])
        job=discovery.create(c,models.Discovery(configuration=q));c.commit();jobs.execute(job['id'],path)
        completed=discovery.owned_job(c,job['id']);assert completed['status']=='COMPLETED'
        result=completed['items'][0]['result'];assert result['matched']==1 and result['new_signals']==1 and result['new_candidate_signals']==2
        assert structured.await_count==1 and sum(row['matched'] for row in completed['sources'])==1
        assert service.listing(c,'signals')['total']==2 # original family attribution is preserved

def test_disabled_monitor_history_cannot_starve_enabled_workspace_dispatch(radar,monkeypatch):
    from app.intent_radar import schedules
    c,path,org,other=radar
    monkeypatch.setattr(get_settings(),'intent_radar_schedules_enabled',True)
    monkeypatch.setattr(get_settings(),'intent_radar_monitor_limit',30)
    with workspace_scope(c,'controlled@example.test',org):
        for n in range(12):
            monitor=service.save_monitor(c,models.Monitor(name=f'Historical monitor {n}',status='Active',configuration=models.Search(keywords=['website'])))
            schedules.update(c,monitor['id'],models.Schedule(revision=monitor['revision'],frequency='6 hours'));c.commit()
    c.execute("UPDATE intent_monitors SET next_run_at='2000-01-01T00:00:00+00:00' WHERE organization_id=?",(org,))
    c.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=? AND product='INTENT_RADAR'",(org,))
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(other,));c.commit()
    with workspace_scope(c,'foreign@example.test',other):
        monitor=service.save_monitor(c,models.Monitor(name='Enabled monitor',status='Active',configuration=models.Search(keywords=['website'])))
        schedules.update(c,monitor['id'],models.Schedule(revision=monitor['revision'],frequency='6 hours'));c.commit()
    c.execute("UPDATE intent_monitors SET next_run_at='2001-01-01T00:00:00+00:00' WHERE organization_id=?",(other,));c.commit()
    pending=schedules.enqueue_due(c)
    assert len(pending)==1 and pending[0]['organization_id']==other
    assert c.execute('SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND last_job_id IS NULL AND next_run_at=?',(org,'2000-01-01T00:00:00+00:00')).fetchone()[0]==12

def test_workspace_retention_applies_to_hn_and_cannot_extend_publisher_limit():
    signal={'retrieved_at':'2000-01-01T00:00:00+00:00','evidence':{}}
    assert service.expired(signal,30)
    from datetime import datetime,timezone,timedelta
    recent={'retrieved_at':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),'evidence':{'provenance':{'retention_days':1}}}
    assert service.expired(recent,30)
    assert not service.expired({**recent,'evidence':{}},30)

def test_expired_evidence_cannot_leak_in_rank_analysis_or_filtered_counts(radar,monkeypatch):
    c,path,org,_=radar
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0]
        c.execute("UPDATE intent_signals SET retrieved_at='2000-01-01T00:00:00+00:00' WHERE organization_id=?",(org,));c.commit()
        assert service.listing(c,'signals')['total']==0
        expired=service.get(c,'signals',signal['id']);assert expired['score']==0 and expired['evidence']=={} and not expired['available']
        assert intelligence.history(c,signal['id'])['items']==[] and service.overview(c)['new_signals']==0
