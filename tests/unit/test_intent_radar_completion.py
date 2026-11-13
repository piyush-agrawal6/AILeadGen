"""Phase 2/3 completion behavior, grounded AI, rank effects and usage integrity."""
import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_intent_radar import radar,owned,run,source_result,example
from app.config.settings import get_settings
from app.intent_radar import models,providers,service,intelligence
from app.platform.context import workspace_scope

def test_source_grounded_summary_contradictions_languages_and_translation():
    signal={**example(),'title':'Necesitamos un CRM para nuestro negocio','excerpt':'No queremos comprar todavía. Estamos investigando alternativas.','_summary_language':'en','_exclusions':['research only']}
    output=intelligence.Interpretation(categories=['General discussion'],summary=intelligence.Claim(kind='summary',quote='Necesitamos un CRM',interpretation='The post discusses CRM needs',translation='We need a CRM'),claims=[intelligence.Claim(kind='contradiction',quote='No queremos comprar todavía.',interpretation='Explicitly not buying yet'),intelligence.Claim(kind='exclusion',quote='Estamos investigando alternativas.',interpretation='Research-only context',target='research only')],detected_language='es',language_evidence='Necesitamos un CRM')
    assert intelligence.validated(output,signal,[])==output
    score=intelligence.score(signal,output,{'ranking_adjustment':0,'explanation':''})
    assert score['overall']<=60 and score['dimensions']['contradictory_evidence']==-30
    for corrupt in [output.model_copy(update={'language_evidence':'Invented Spanish quotation'}),output.model_copy(update={'summary':intelligence.Claim(kind='summary',quote='Invented quote',interpretation='Unknown purchase')})]:
        with pytest.raises(Exception):intelligence.validated(corrupt,signal,[])
    with pytest.raises(Exception):intelligence.validated(output,{**signal,'_summary_language':None},[])

def test_rank_feedback_changes_threshold_and_reversal_without_cross_tenant_effect(radar,monkeypatch):
    c,path,org,other=radar
    monkeypatch.setattr(providers.HackerNews,'fetch',AsyncMock(return_value=source_result()))
    with workspace_scope(c,'controlled@example.test',org):
        run(c,path,models.Search(keywords=['website']));signal=service.listing(c,'signals',sort='score')['items'][0];original=signal['score']
        intelligence.feedback(c,signal['id'],models.Feedback(label='Not relevant'))
        assert service.get(c,'signals',signal['id'])['score']==original-10
        assert service.listing(c,'signals',min_score=original)['total']==0
        intelligence.feedback(c,signal['id'],models.Feedback(label='Not relevant',active=False))
        assert service.listing(c,'signals',min_score=original)['total']==1
        c.commit()
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):service.get(c,'signals',signal['id'])

def test_actual_usage_metadata_and_unknown_price_are_not_fabricated():
    from app.platform.provider_usage import reported,price
    usage=reported({'usageMetadata':{'promptTokenCount':125,'candidatesTokenCount':32,'cachedContentTokenCount':50,'thoughtsTokenCount':8}})
    assert usage=={'input_tokens':125,'output_tokens':32,'cached_tokens':50,'thinking_tokens':8}
    assert all(v is None for v in reported({}).values())
    assert reported({'usageMetadata':{'promptTokenCount':True}})['input_tokens'] is None
    assert price(SimpleNamespace(model_pricing_json='{}'),'approved-model',usage)==(None,None)
    config=SimpleNamespace(model_pricing_json=json.dumps({'approved-model':{'approved':True,'reference':'https://cloud.google.com/vertex-ai/generative-ai/pricing','input_per_million_usd':'1','output_per_million_usd':'2','cached_per_million_usd':'.5'}}))
    from decimal import Decimal
    assert Decimal(price(config,'approved-model',usage)[0])==Decimal('0.00018')

def test_provider_usage_persists_owned_actual_counts_and_does_not_leak(radar):
    from app.platform.provider_usage import record,reported,summary,operation
    c,path,org,other=radar
    provider=SimpleNamespace(config=SimpleNamespace(model_pricing_json='{}',primary_provider='vertex'),model='owned-model',provider_name='VERTEX_AI',usage_connection=c)
    with workspace_scope(c,'controlled@example.test',org):
        with operation('INTENT_ANALYSIS'):record(provider,reported({'usageMetadata':{'promptTokenCount':25,'candidatesTokenCount':7}}),'SUCCEEDED',time.monotonic())
        c.commit();data=summary(c)
        assert data['requests']==1 and data['input_tokens_reported']==25 and data['output_tokens_reported']==7 and data['estimated_cost_usd'] is None
    with workspace_scope(c,'foreign@example.test',other):assert summary(c)['requests']==0
