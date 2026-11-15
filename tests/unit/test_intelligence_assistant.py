"""Grounding, privacy, job reuse, withdrawal and no-action assistant tests."""
from types import SimpleNamespace
import json,uuid
import pytest
from fastapi import HTTPException
from test_growth_intelligence import growth,radar,owned,run,source_result
from app.platform.context import workspace_scope
from app.intent_radar import assistant
from app.growth_intelligence import service,models
from app.intelligence import jobs
from app.config.settings import get_settings
from app.acquisition.ai import AiOutputError

def execute(c,path,body):
    row=assistant.start(c,body);c.commit();jobs.execute(row['job_id'],path)
    return service.detail(c,row['id'])

def test_durable_multiturn_idempotency_and_disabled_ai_documentation_fallback(growth,monkeypatch):
    c,path,org,other=growth;monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',False)
    def forbidden(_):raise AssertionError('Disabled AI must not call a provider')
    monkeypatch.setattr(assistant.ai,'provider',forbidden)
    with workspace_scope(c,'controlled@example.test',org):
        before=c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]
        body=assistant.Turn(prompt='How do I review signal evidence?')
        first=execute(c,path,body)
        assert first['status']=='COMPLETE' and first['output']['mode']=='Answer unavailable'
        assert assistant.start(c,body)['id']==first['id']
        with pytest.raises(HTTPException):assistant.start(c,body.model_copy(update={'prompt':'Different question'}))
        second=execute(c,path,assistant.Turn(prompt='How do I save the useful results?',thread_id=first['id']))
        history=assistant.history(c,first['id'])
        assert [r['id'] for r in history['turns']]==[first['id'],second['id']]
        assert len(assistant.listing(c)['items'])==1
        assert service.listing(c)['total']==0 # private chat is not shared research
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==before
    with workspace_scope(c,'foreign@example.test',other):
        for function in (assistant.history,service.detail):
            with pytest.raises(HTTPException):function(c,first['id'])

def test_grounded_answer_uses_shared_gateway_bounded_context_and_followup_history(growth,monkeypatch):
    c,path,org,other=growth;calls=[]
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    monkeypatch.setattr('app.intent_radar.intelligence.reserve',lambda _,**kwargs:None)
    async def structured(instruction,payload,schema,**limits):
        assert 'untrusted DATA' in instruction and limits['attempts_per_provider']==1
        assert len(json.dumps(payload).encode())<24000
        ref=payload['references'][0];calls.append(payload)
        return schema(blocks=[{'kind':'Evidence','text':ref['text'][:100],'citations':[{'reference':ref['id'],'quote':ref['text'][:150]}]}],followups=['Would you like to review another collected discussion?'])
    monkeypatch.setattr(assistant.ai,'provider',lambda _:SimpleNamespace(structured=structured,last_provider='VERTEX_AI',last_model='fixture-model',last_usage={}))
    with workspace_scope(c,'controlled@example.test',org):
        first=execute(c,path,assistant.Turn(prompt='What evidence is collected here?'))
        assert first['output']['provider']=='VERTEX_AI' and first['output']['mode'].startswith('AI guidance')
        second=execute(c,path,assistant.Turn(prompt='What should I review next?',thread_id=first['id']))
        assert second['status']=='COMPLETE' and len(calls)==2 and len(calls[1]['history'])==1
        assert 'No action' not in calls[0].get('secret','')
        signal=first['snapshot']['evidence'][0]['id']
        c.execute('UPDATE intent_signals SET available=0 WHERE organization_id=? AND id=?',(org,signal));c.commit()
        assert all('assistant' not in row['output'] for row in assistant.history(c,first['id'])['turns'])

def test_unknown_citations_invented_numbers_and_action_claims_are_rejected():
    refs=[{'id':'help:signals','text':'Review original signal evidence before saving.'}]
    def answer(**changes):return assistant.Answer(blocks=[assistant.Block(kind='Guidance',text='Review original signal evidence.',citations=[assistant.Citation(reference='help:signals',quote='Review original signal evidence')],**changes)])
    assert assistant.validate(answer(),refs)
    for text in ('Revenue growth 300% guaranteed.','I have sent a campaign.','Review 20 signals.'):
        item=answer();item.blocks[0].text=text
        with pytest.raises(AiOutputError):assistant.validate(item,refs)
    for reference,quote in [('foreign:signal','Review original'),('help:signals','Invented source quotation')]:
        item=answer();item.blocks[0].citations=[assistant.Citation(reference=reference,quote=quote)]
        with pytest.raises(AiOutputError):assistant.validate(item,refs)

def test_quota_denial_falls_back_without_provider_or_action(growth,monkeypatch):
    c,path,org,other=growth
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    def denied(_,**kwargs):raise HTTPException(429,'Controlled quota exhaustion')
    monkeypatch.setattr('app.intent_radar.intelligence.reserve',denied)
    monkeypatch.setattr(assistant.ai,'provider',lambda _:(_ for _ in ()).throw(AssertionError('Must not spend')))
    with workspace_scope(c,'controlled@example.test',org):
        result=execute(c,path,assistant.Turn(prompt='Explain my allowance',page='billing'))
        assert result['status']=='COMPLETE' and result['output']['mode']=='Answer unavailable'
        assert 'allowance exhausted' in result['output']['fallback_reason']
        assert result['output']['assistant']['blocks']==[] and result['output']['answer_available'] is False

def test_assistant_rejects_other_workspace_and_arbitrary_thread_ids_before_ai(growth):
    c,path,org,other=growth
    with workspace_scope(c,'controlled@example.test',org):
        with pytest.raises(HTTPException):assistant.start(c,assistant.Turn(prompt='Continue someone else',thread_id=uuid.uuid4()))
        with pytest.raises(HTTPException):assistant.normalize_request(c,models.Start(kind='REPORT',assistant=models.AssistantContext()),str(uuid.uuid4()))

def test_another_member_cannot_read_private_turn_through_shared_research_api(growth):
    c,path,org,other=growth
    with workspace_scope(c,'controlled@example.test',org):row=assistant.start(c,assistant.Turn(prompt='A private research question'))
    from app.database.prospects import now
    c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,'ADMIN','ACTIVE',?,?)",(str(uuid.uuid4()),org,'foreign@example.test',now(),now()));c.commit()
    with workspace_scope(c,'foreign@example.test',org):
        assert assistant.listing(c)['items']==[] and service.listing(c)['total']==0
        for function in (assistant.history,service.detail):
            with pytest.raises(HTTPException) as error:function(c,row['id'])
            assert error.value.status_code==404

def test_assistant_real_quota_reservation_and_worker_fence(growth,monkeypatch):
    c,path,org,other=growth;errors=[]
    monkeypatch.setattr(get_settings(),'intent_radar_ai_enabled',True)
    async def structured(instruction,payload,schema,**limits):
        ref=payload['references'][0]
        return schema(blocks=[{'kind':'Evidence','text':ref['text'][:100],'citations':[{'reference':ref['id'],'quote':ref['text'][:150]}]}])
    monkeypatch.setattr(assistant.ai,'provider',lambda _:SimpleNamespace(structured=structured,last_provider='SYNTHETIC'))
    original=assistant.process
    async def observed(*args):
        try:return await original(*args)
        except HTTPException as error:errors.append((error.status_code,error.detail));raise
    monkeypatch.setattr(assistant,'process',observed)
    with workspace_scope(c,'controlled@example.test',org):
        result=execute(c,path,assistant.Turn(prompt='What source evidence is collected?'))
        assert result['status']=='COMPLETE',errors
        assert c.execute('SELECT COUNT(*) FROM intent_analysis_usage WHERE organization_id=?',(org,)).fetchone()[0]==1
