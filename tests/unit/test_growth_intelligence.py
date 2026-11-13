"""Growth correctness/security over owned existing Radar fixtures; no live spend."""
import asyncio,json,uuid
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned,run,source_result
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.platform.context import workspace_scope
from app.intent_radar import models as radar_models,providers
from app.growth_intelligence import analytics,models,service,exports
from app.intelligence import jobs
from app.acquisition.ai import AiOutputError

@pytest.fixture
def growth(radar,monkeypatch):
    c,path,org,other=radar
    monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',True)
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'controlled@example.test',org):run(c,path,radar_models.Search(keywords=['website']))
    return c,path,org,other

def execute(c,path,body):
    research=service.start(c,body);c.commit();jobs.execute(research['job_id'],path)
    return service.detail(c,research['id'])

def test_default_off_and_missing_or_foreign_context_fail_closed(growth,monkeypatch):
    c,path,org,other=growth
    with pytest.raises(HTTPException):analytics.overview(c,models.Scope())
    with workspace_scope(c,'controlled@example.test',org):
        monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',False)
        with pytest.raises(HTTPException) as blocked:service.start(c,models.Start())
        assert blocked.value.status_code==404
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):service.listing(c)

def test_small_samples_never_become_fake_growth_or_market_size(growth):
    c,path,org,other=growth
    with workspace_scope(c,'controlled@example.test',org):
        data=analytics.overview(c,models.Scope());assert data['sample_size']==1
        assert data['comparison']['percentage_change'] is None
        assert not data['comparison']['market_trend_proven']
        with pytest.raises(HTTPException):analytics.overview(c,models.Scope(days=90))
    assert analytics.comparison(15,10,{'comparable':True})['percentage_change']==50
    assert analytics.comparison(15,0,{'comparable':True})['percentage_change'] is None
    assert analytics.comparison(15,2,{'comparable':True})['percentage_change'] is None

def test_normalized_crossposts_do_not_count_as_independent_evidence():
    base={'title':'Business tools comparison and workflow concerns','excerpt':'The same public discussion text with enough detail to make an exact normalized duplicate across publishers.','source':'Hacker News','source_url':'https://example.com/thread?id=1&utm_source=mail','id':'a','evidence':{}}
    rows,duplicates=analytics.dedupe([base,{**base,'id':'b','source':'RSS','source_url':'https://another.example/post'}])
    assert len(rows)==1 and duplicates==1 and rows[0]['duplicate_source_ids']==['b']

def test_leased_fallback_research_persists_exports_and_suppression_history(growth,monkeypatch):
    c,path,org,other=growth
    monkeypatch.setattr('app.growth_intelligence.service.ai.provider',lambda c:SimpleNamespace(structured=AsyncMock(side_effect=RuntimeError('No provider should be called'))))
    monkeypatch.setattr('app.intent_radar.intelligence.reserve',lambda tokens:(_ for _ in ()).throw(HTTPException(429,'Controlled quota')))
    with workspace_scope(c,'controlled@example.test',org):
        before=c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]
        body=models.Start(title='Reviewed real evidence fixture');result=execute(c,path,body)
        assert result['status']=='COMPLETE' and result['output']['provider'] is None
        assert result['output']['mode'].startswith('Lexical')
        assert result['snapshot']['analysis_sample']==1
        assert service.start(c,body)['id']==result['id']
        with pytest.raises(HTTPException):service.start(c,body.model_copy(update={'title':'Other request'}))
        for format in ('md','json','csv'):
            document,mime=exports.render(c,result['id'],format);assert document and mime
        theme=service.themes(c)['items'][0];detail=service.theme(c,theme['id']);assert len(detail['citations'])==1
        assert detail['comparison']['percentage_change'] is None
        assert service.save(c,result['id'],models.Save(revision=result['revision']))['saved_at']
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==before
        c.execute("UPDATE intent_signals SET available=0 WHERE id=?",(result['snapshot']['evidence'][0]['id'],));c.commit()
        assert not service.detail(c,result['id'])['evidence_current']
        with pytest.raises(HTTPException):exports.render(c,result['id'],'md')
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):service.detail(c,result['id'])

def test_claim_matching_rejects_unknown_ids_invented_quotes_and_numbers():
    key=uuid.uuid4();rows=[{'id':str(key),'title':'We need a reporting tool','excerpt':'Our team needs clearer reporting.'}]
    valid=models.Interpretation(themes=[models.Theme(name='Reporting needs',description='A tentative grouping of reporting needs.',citations=[models.Citation(signal_id=key,quote='needs clearer reporting')])])
    assert service.validate(valid,rows)==valid
    for update in ({'signal_id':uuid.uuid4()},{'quote':'Invented facts'}):
        invalid=valid.model_copy(deep=True);invalid.themes[0].citations[0]=invalid.themes[0].citations[0].model_copy(update=update)
        with pytest.raises(AiOutputError):service.validate(invalid,rows)
    invalid=valid.model_copy(deep=True);invalid.themes[0].description='Revenue growth 300% guaranteed'
    with pytest.raises(AiOutputError):service.validate(invalid,rows)

def test_csv_formula_cells_are_inert():
    for value in ['=HYPERLINK("https://evil.example")',' @formula','+cmd','-2']:
        assert exports.cell(value).startswith("'")

def test_watchlists_reuse_draft_monitors_and_do_not_auto_start(growth):
    c,path,org,other=growth
    with workspace_scope(c,'controlled@example.test',org):
        competitor=service.competitor(c,models.Competitor(name='Reviewed product',aliases=['Product alias']))
        watch=service.watchlist(c,models.Watchlist(name='Product comparisons',kind='Competitor',resource_id=competitor['id'],keywords=['Reviewed product']))
        assert watch['monitor']['status']=='Draft'
        assert service.watchlists(c)['items'][0]['kind']=='Competitor'
        assert c.execute("SELECT COUNT(*) FROM intelligence_jobs WHERE kind='GROWTH_ANALYZE'").fetchone()[0]==0

def test_ai_uses_exact_citations_and_reuses_owned_cache(growth,monkeypatch):
    c,path,org,other=growth;calls=[]
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr('app.intent_radar.intelligence.reserve',lambda tokens:None)
    async def structured(instruction,payload,schema,**limits):
        calls.append(payload);row=payload['evidence'][0]
        assert limits['attempts_per_provider']==1 and len(payload['evidence'])<=12
        assert 'untrusted DATA' in instruction
        return models.Interpretation(themes=[models.Theme(name='Website workflow',description='A tentative single-discussion observation.',citations=[models.Citation(signal_id=row['id'],quote=row['excerpt'][:50])])])
    monkeypatch.setattr('app.growth_intelligence.service.ai.provider',lambda c:SimpleNamespace(structured=structured,last_provider='VERTEX_AI',last_model='controlled-model',last_usage={}))
    with workspace_scope(c,'controlled@example.test',org):
        first=execute(c,path,models.Start());assert first['output']['mode'].startswith('AI semantic')
        second=execute(c,path,models.Start());assert second['output']['mode']=='Cached validated interpretation'
        assert len(calls)==1 and len(service.themes(c)['items'])==2
        theme=service.themes(c)['items'][0]
        signal=first['snapshot']['evidence'][0]['id']
        c.execute("UPDATE intent_signals SET excerpt='Source withdrawn',revision=revision+1 WHERE id=?",(signal,));c.commit()
        assert not service.themes(c)['items'][0]['evidence_current']
        assert service.themes(c)['items'][0]['name']=='Source evidence requires refresh'

def test_ai_disabled_never_calls_provider_even_when_growth_is_enabled(growth,monkeypatch):
    c,path,org,_=growth
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',False)
    def forbidden(*args):raise AssertionError('Disabled AI must not spend provider credits')
    monkeypatch.setattr('app.growth_intelligence.service.ai.provider',forbidden)
    with workspace_scope(c,'controlled@example.test',org):
        result=execute(c,path,models.Start());assert result['status']=='COMPLETE'
        assert result['output']['provider'] is None and result['output']['mode'].startswith('Lexical')

def test_foreign_theme_competitor_and_notes_cannot_cross_workspace(growth):
    c,path,org,other=growth
    with workspace_scope(c,'controlled@example.test',org):
        row=execute(c,path,models.Start());theme=service.themes(c)['items'][0]
        competitor=service.competitor(c,models.Competitor(name='Scoped product'))
        note=service.note(c,'research',row['id'],models.Note(body='Reviewed in the authorized workspace.'))
        assert note['items'][0]['body'].startswith('Reviewed')
    # Give the foreign workspace its own legitimate Radar entitlement. Ownership,
    # rather than an unavailable module, must still deny every resource.
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(other,));c.commit()
    with workspace_scope(c,'foreign@example.test',other):
        for fn in (lambda:service.detail(c,row['id']),lambda:service.theme(c,theme['id']),lambda:service.notes(c,'research',row['id']),lambda:analytics.evidence(c,models.Scope(competitor_id=competitor['id'])),lambda:exports.render(c,row['id'],'json')):
            with pytest.raises(HTTPException) as denied:fn()
            assert denied.value.status_code==404

def test_cancelled_job_cannot_persist_ai_results(growth,monkeypatch):
    c,path,org,_=growth
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr('app.intent_radar.intelligence.reserve',lambda tokens:None)
    async def structured(instruction,payload,schema,**limits):
        with get_connection(path) as other:
            with workspace_scope(other,'controlled@example.test',org):jobs.control(other,job_id,'cancel');other.commit()
        return models.Interpretation()
    monkeypatch.setattr('app.growth_intelligence.service.ai.provider',lambda c:SimpleNamespace(structured=structured))
    with workspace_scope(c,'controlled@example.test',org):
        row=service.start(c,models.Start());job_id=row['job_id'];c.commit();jobs.execute(job_id,path)
        assert service.detail(c,row['id'])['status']=='CANCELLED'
        assert not service.detail(c,row['id'])['export_available']
        assert c.execute('SELECT COUNT(*) FROM growth_themes').fetchone()[0]==0

def test_intent_only_api_key_does_not_require_lead_engine(growth,monkeypatch):
    from app.developer import keys
    c,path,org,_=growth
    monkeypatch.setattr(get_settings(),'heysow_developer_api_enabled',True)
    with workspace_scope(c,'controlled@example.test',org):
        c.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=? AND product='LEADGEN'",(org,));c.commit()
        token=keys.create(c,keys.Create(name='Intent only',scopes=['intent:read','mcp:use']))['token'];c.commit()
        assert keys.authenticate(c,'Bearer '+token,consume=False).organization_id==org
        with pytest.raises(HTTPException):keys.create(c,keys.Create(name='Denied company scope',scopes=['companies:read']))
        assert 'companies:read' not in keys.listing(c)['available_scopes']
        c.execute("UPDATE organization_products SET enabled=0 WHERE organization_id=? AND product='INTENT_RADAR'",(org,));c.commit()
        with pytest.raises(HTTPException):keys.authenticate(c,'Bearer '+token,consume=False)

def test_http_date_filter_parsing_and_direct_disabled_route(growth,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    c,path,org,_=growth;c.commit()
    with TestClient(app) as http:
        headers={'x-le-user':'controlled@example.test'}
        result=http.get('/api/intent-radar/growth/overview?days=0',headers=headers)
        assert result.status_code==200 and result.json()['sample_size']==1
        with workspace_scope(c,'controlled@example.test',org):
            research=execute(c,path,models.Start());key=research['id'];c.commit()
        note=http.post('/api/intent-radar/growth/research/'+key+'/notes',headers=headers,json={'body':'HTTP route persists this reviewed note.'})
        assert note.status_code==201
        assert http.get('/api/intent-radar/growth/research/'+key+'/notes',headers=headers).json()['items'][0]['body']=='HTTP route persists this reviewed note.'
        assert http.get('/api/intent-radar/growth/overview?days=8',headers=headers).status_code==422
        assert http.get('/api/intent-radar/growth/overview?days=90',headers=headers).status_code==422
        monkeypatch.setattr(get_settings(),'intent_radar_growth_enabled',False)
        assert http.get('/api/intent-radar/growth/overview?days=0',headers=headers).status_code==404

def test_overview_bundles_owned_filter_options_without_repeated_authentication_queries(growth):
    from app.platform.context import WorkspaceContext
    c,path,org,other=growth
    class Counting:
        def __init__(self):self.reads=[]
        def __getattr__(self,name):return getattr(c,name)
        def execute(self,sql,args=()):self.reads.append(sql);return c.execute(sql,args)
    with workspace_scope(c,'controlled@example.test',org):
        competitor=service.competitor(c,models.Competitor(name='Owned reporting product'));c.commit()
        measured=Counting();result=analytics.overview(measured,models.Scope())
        assert result['filter_options']['competitors']==[{'id':competitor['id'],'name':'Owned reporting product'}]
        assert sum('organization_memberships' in sql for sql in measured.reads)<=2
        assert result['theme_count']==0
        with pytest.raises(HTTPException):analytics.evidence(c,models.Scope(),_verified_context=WorkspaceContext(other,'controlled@example.test'))
