"""Workspace statistics are deterministic, private, idempotent and AI-free."""
import json
import pytest
from fastapi import HTTPException
from test_growth_intelligence import growth,radar,owned,run,source_result
from app.intent_radar import assistant,assistant_reads,service,models
from app.platform.context import workspace_scope
from app.config.settings import get_settings

@pytest.mark.parametrize('prompt,kind',[('How many signals have I generated yet?','signals'),('How many active monitors do I have?','monitors'),('Which sources are available?','sources'),('What is my remaining AI allowance?','usage'),('How many searches were requested today?','searches'),('How many opportunities do we have?','opportunities'),('How many saved signals?','saved')])
def test_read_routing_uses_finite_operations(prompt,kind):
    assert assistant_reads.route(prompt)['kind']==kind
    assert assistant_reads.route('Interpret this discussion about a potential migration partner.') is None

def test_real_counts_idempotent_snapshot_history_and_no_ai_or_jobs(growth,monkeypatch):
    c,path,org,other=growth
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',False)
    monkeypatch.setattr(assistant.ai,'provider',lambda _:(_ for _ in ()).throw(AssertionError('No model for counts')))
    with workspace_scope(c,'controlled@example.test',org):
        before_jobs=c.execute('SELECT COUNT(*) FROM intelligence_jobs').fetchone()[0]
        before_ai=c.execute('SELECT COUNT(*) FROM intent_analysis_usage').fetchone()[0]
        body=assistant.Turn(prompt='How many signals have I generated yet?')
        result=assistant.start(c,body)
        actual=c.execute('SELECT COUNT(*) FROM intent_signals WHERE organization_id=?',(org,)).fetchone()[0]
        assert result['status']=='COMPLETE' and result['job_id'] is None
        assert result['output']['mode']=='Workspace data — no AI used'
        assert result['snapshot']['facts']['stored_conversations']==actual
        assert str(actual) in result['output']['assistant']['blocks'][0]['text']
        assert assistant.start(c,body)['id']==result['id']
        followup=assistant.start(c,assistant.Turn(prompt='And today?',thread_id=result['id']))
        assert followup['snapshot']['workspace_read']=={'kind':'signals','period':'today'}
        assert any('publication dates' in x for x in followup['output']['assistant']['limitations'])
        assert len(assistant.history(c,result['id'])['turns'])==2
        assert c.execute('SELECT COUNT(*) FROM intelligence_jobs').fetchone()[0]==before_jobs
        assert c.execute('SELECT COUNT(*) FROM intent_analysis_usage').fetchone()[0]==before_ai
        with pytest.raises(HTTPException):assistant.start(c,body.model_copy(update={'prompt':'How many active monitors?'}))
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException):assistant.start(c,assistant.Turn(prompt='And today?',thread_id=result['id']))
        with pytest.raises(HTTPException) as denied:assistant.listing(c)
        assert denied.value.status_code==404
    with pytest.raises(HTTPException):assistant.start(c,assistant.Turn(prompt='How many signals?'))

def test_usage_sources_monitors_answers_without_generation(growth,monkeypatch):
    c,_,org,_=growth
    monkeypatch.setattr(assistant.ai,'provider',lambda _:(_ for _ in ()).throw(AssertionError('No provider')))
    with workspace_scope(c,'controlled@example.test',org):
        for question in ['Which sources are available?','How many active monitors?','What is my remaining AI allowance?']:
            r=assistant.start(c,assistant.Turn(prompt=question))
            assert r['status']=='COMPLETE' and r['job_id'] is None
            assert 'Documentation fallback' not in r['output']['mode']
            assert r['output']['assistant']['blocks'][0]['citations']

def test_unknown_or_ambiguous_followups_do_not_guess_tool_or_time_window():
    assert assistant_reads.route('Explain this competitor comparison') is None
    assert assistant_reads.route('And today?',{'kind':'signals'})=={'kind':'signals','period':'today'}
    assert assistant_reads.route('And what do you think?',{'kind':'signals'}) is None
    for question in ('What do these signals imply for my company?','Which signals should I review?','Show me how to review signals','What is the problem described by this discussion?'):
        assert assistant_reads.route(question) is None
