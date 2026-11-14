"""Isolated signed frontend/worker fixture; never imported by production."""
from types import SimpleNamespace
from tests.intent_radar_fixture_server import app,settings,path
from app.acquisition import ai
from app.growth_intelligence import models

settings.intent_radar_growth_enabled=True
settings.intent_radar_ai_enabled=True

async def structured(instruction,payload,schema,**limits):
    from app.intent_radar.assistant import Answer
    if schema is Answer:
        ref=payload['references'][0]
        return Answer(blocks=[{'kind':'Evidence','text':ref['text'][:120],'citations':[{'reference':ref['id'],'quote':ref['text'][:150]}]}],limitations=['Synthetic browser provider, not real Vertex acceptance.'])
    if schema is models.Interpretation:
        signal=payload['evidence'][0]
        return models.Interpretation(themes=[models.Theme(name='Website partner comparisons',description='Synthetic browser fixture: one collected discussion about comparing website partners.',citations=[models.Citation(signal_id=signal['id'],quote=signal['excerpt'][:150])])],findings=[models.Finding(section='Customer problem',interpretation='Synthetic fixture: this discussion asks how to compare website options.',citations=[models.Citation(signal_id=signal['id'],quote=signal['excerpt'][:150])])],limitations=['Synthetic browser evidence, not independent acceptance or real market data.'])
    raise AssertionError('Unexpected provider task in isolated Growth acceptance')
ai.provider=lambda c=None:SimpleNamespace(structured=structured,last_provider='SYNTHETIC',last_model='SYNTHETIC-browser-fixture',last_usage={})
