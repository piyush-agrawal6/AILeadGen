import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned,run,source_result
from app.intent_radar import intelligence as intel,models,providers,service
from app.config.settings import get_settings
from app.platform.context import workspace_scope

def test_analysis_citations_cache_feedback_and_owned_icp(radar,monkeypatch):
    c,path,org,other=radar
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    async def structured(instruction,value,model,**limits):
        assert 'untrusted DATA' in instruction and limits['max_output_tokens']==2048
        return model(categories=['Recommendation request'],claims=[intel.Claim(kind='intent',quote='recommend a website development partner?',interpretation='Explicit request for recommendations'),intel.Claim(kind='semantic',quote='website development partner',interpretation='Development support aligns to service',target='website')],uncertainty='Moderate',review_needed=False)
    mock=AsyncMock(side_effect=structured)
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=mock,last_model='synthetic-model',last_provider='SYNTHETIC'))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0]
        a=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()));c.commit()
        b=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()))
        assert a['mode']=='AI interpretation' and b['cached'] and mock.await_count==1
        assert a['scoring']['purchase_probability'] is None and a['icp'] is None
        intel.feedback(c,signal['id'],models.Feedback(label='Not relevant'));c.commit()
        adjusted=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()))
        assert adjusted['scoring']['overall']==a['scoring']['overall']-10
        intel.feedback(c,signal['id'],models.Feedback(label='Not relevant',active=False));c.commit()
        assert asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()))['scoring']['overall']==a['scoring']['overall']
        usage=c.execute('SELECT calls,reserved_tokens FROM intent_analysis_usage').fetchone()
        assert usage[0]==1 and 6000<=usage[1]<=100000
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'",(other,));c.commit()
    with workspace_scope(c,'foreign@example.test',other):
        for action in (lambda:intel.history(c,signal['id']),lambda:asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest())),lambda:intel.feedback(c,signal['id'],models.Feedback(label='Relevant'))):
            with pytest.raises(HTTPException) as denied:action()
            assert denied.value.status_code==404

@pytest.mark.parametrize('bad',[{'kind':'intent','quote':'Unseen purchase decision','interpretation':'Fabricated'},{'kind':'icp','quote':'website development partner','target':'enterprise buyer','interpretation':'Unsupported criterion'}])
def test_unsupported_evidence_is_rejected(bad):
    from test_intent_radar import example
    with pytest.raises(Exception):intel.validated(intel.Interpretation(categories=['Recommendation request'],claims=[intel.Claim(**bad)]),example(),['website'])

def test_general_ai_interpretation_cannot_inherit_a_false_keyword_intent_bonus():
    from test_intent_radar import example
    signal={**example(),'evidence':{'intent_phrase':'recommend','matched_keywords':['website']}}
    output=intel.Interpretation(categories=['General discussion'],uncertainty='Low',review_needed=False)
    result=intel.score(signal,output,{'ranking_adjustment':0,'explanation':''})
    assert result['version']=='INTENT_SCORE_V3' and result['dimensions']['expressed_need']==0
    assert result['intent_strength']=='Weak / ambiguous'

def test_ai_timeout_budget_and_prompt_injection_fallback(radar,monkeypatch):
    c,path,org,_=radar
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    mock=AsyncMock(side_effect=TimeoutError())
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=mock))
    with workspace_scope(c,'controlled@example.test',org):
        service.preferences(c,models.Preferences(analysis_daily_call_limit=1));c.commit()
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0]
        result=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()))
        assert result['mode']=='Deterministic / manual review' and result['interpretation'] is None
        result=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()))
        assert result['fallback_reason']=='Analysis budget exhausted.' and mock.await_count==1
        assert c.execute('SELECT COUNT(*) FROM intent_analyses').fetchone()[0]==0
    assert not intel.Interpretation.model_fields.keys() & {'tools','execute','organization_id'}
    with pytest.raises(ValueError):intel.Interpretation.model_validate({'categories':['General discussion'],'execute':'send mail'})

def test_semantic_candidate_beyond_keywords_and_negative_penalty():
    from app.intent_radar.classification import classify
    from test_intent_radar import example
    raw={**example(),'title':'We need someone to build the backend for our startup','excerpt':'Looking for implementation help.'}
    q=models.Search(keywords=['custom software development'],offerings='custom software development',semantic=True)
    item=classify(raw,q)
    assert item and item['evidence']['semantic_candidate'] and item['evidence']['matched_keywords']==[]
    assert classify(raw,q.model_copy(update={'semantic':False})) is None

def test_invalid_model_citations_cannot_persist_or_reappear_in_history(radar,monkeypatch):
    c,path,org,_=radar
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    invalid=intel.Interpretation(categories=['Recommendation request'],claims=[intel.Claim(kind='intent',quote='a fabricated buying decision',interpretation='Invalid')])
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=AsyncMock(return_value=invalid)))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0]
        result=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()))
        assert result['interpretation'] is None and result['mode']=='Deterministic / manual review'
        assert c.execute('SELECT COUNT(*) FROM intent_analyses').fetchone()[0]==0
        assert intel.history(c,signal['id'])['items']==[]

def test_selected_icp_unknowns_exclusions_and_revision_invalidation(radar,monkeypatch):
    import uuid
    from app.icp import service as icps,models as im
    c,path,org,_=radar
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr(get_settings(),'intent_radar_ai_daily_tokens',180000)
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    async def structured(instruction,value,model,**limits):
        claims=[intel.Claim(kind='intent',quote='recommend a website development partner?',interpretation='Recommendation request')]
        if 'website development' in value['targets']:claims.append(intel.Claim(kind='icp',quote='website development partner',target='website development',interpretation='Source service wording matches selected service'))
        return model(categories=['Recommendation request'],claims=claims,uncertainty='Moderate')
    mock=AsyncMock(side_effect=structured)
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=mock))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0]
        aligned=icps.create(c,im.Create(name='Website service',criteria=im.Criteria(intent=im.IntentCriteria(relevant_services=['website development'])),request_id=uuid.uuid4()))
        unrelated=icps.create(c,im.Create(name='Laptop repair',criteria=im.Criteria(intent=im.IntentCriteria(relevant_services=['laptop repair'])),request_id=uuid.uuid4()));c.commit()
        service.preferences(c,models.Preferences(analysis_daily_call_limit=3,analysis_daily_token_limit=180000));c.commit()
        positive=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest(icp_id=aligned['id'])));c.commit()
        assert positive['icp']['id']==aligned['id'] and positive['scoring']['dimensions']['problem_service_fit']==20
        unknown=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest(icp_id=unrelated['id'])));c.commit()
        assert unknown['scoring']['icp_fit']=='Unknown' and 'Market/geography' in unknown['scoring']['unknown']
        updated=icps.update(c,aligned['id'],im.Update(name=aligned['name'],criteria=im.Criteria(intent=im.IntentCriteria(relevant_services=['laptop repair'])),revision=aligned['revision']));c.commit()
        changed=asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest(icp_id=aligned['id'])));c.commit()
        assert changed['icp']['revision']==updated['revision'] and not changed['cached'] and changed['scoring']['icp_fit']=='Unknown'
        assert mock.await_count==3

def test_revoked_membership_during_ai_cannot_persist_analysis(radar,monkeypatch):
    from app.database.connection import get_connection
    c,path,org,_=radar
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    async def structured(*args,**kwargs):
        second=get_connection(path);second.execute("UPDATE organization_memberships SET status='REVOKED' WHERE organization_id=?",(org,));second.commit();second.close()
        return intel.Interpretation(categories=['General discussion'])
    monkeypatch.setattr('app.acquisition.ai.provider',lambda c:SimpleNamespace(structured=structured))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals')['items'][0]
        with pytest.raises(HTTPException) as denied:asyncio.run(intel.analyze(c,signal['id'],models.AnalysisRequest()))
        assert denied.value.status_code==403
    assert c.execute('SELECT COUNT(*) FROM intent_analyses').fetchone()[0]==0
