"""Real shared HTTP provider + isolated paid ledger; no external API calls."""
import asyncio
from types import SimpleNamespace
import httpx,pytest
from fastapi import HTTPException
from test_commercial_usage import paid,radar,owned
from test_ai_router import config,Result
from app.acquisition.vertex import VertexAIProvider
from app.acquisition.ai import AiTransportError,AiRateLimited
from app.billing import commercial_usage as usage
from app.platform.context import workspace_scope
from app.platform.provider_usage import operation

def provider(c,transport):
    p=VertexAIProvider(config(),httpx.MockTransport(transport),credentials=SimpleNamespace(valid=True,token='synthetic-token'))
    p.usage_connection=c
    return p

def valid(_):
    return httpx.Response(200,json={'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':20,'thoughtsTokenCount':5},'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"answer":"valid"}'}]}}]})

def totals(c):return {r['dimension']:(r['reserved'],r['used']) for r in c.execute('SELECT * FROM subscription_usage')}

def invoke(c,p,key):
    usage.reserve(c,{'ai_calls':1},key);c.commit()
    with operation('CONTROLLED_CAPACITY_TEST',operation_id=key):
        return asyncio.run(p.structured('Use only supplied facts.',{'facts':['Controlled fixture']},Result,retry_transient=False))

def test_success_refunds_unused_tokens_and_idempotent_operation_is_one_call(paid):
    c,_,org,*_=paid
    with workspace_scope(c,'controlled@example.test',org):
        p=provider(c,valid)
        assert invoke(c,p,'one-logical-operation').answer=='valid'
        assert totals(c)=={'ai_calls':(0,1),'ai_tokens':(0,125)}
        assert invoke(c,p,'one-logical-operation').answer=='valid'
        assert totals(c)=={'ai_calls':(0,1),'ai_tokens':(0,250)}
        assert c.execute("SELECT COUNT(*) FROM subscription_reservations WHERE dimension='ai_tokens'").fetchone()[0]==2

def test_unknown_timeout_holds_capacity_and_worker_retry_reserves_more(paid):
    c,_,org,*_=paid
    def timeout(request):raise httpx.ReadTimeout('Synthetic uncertain delivery',request=request)
    with workspace_scope(c,'controlled@example.test',org):
        p=provider(c,timeout)
        for _ in range(2):
            with pytest.raises(AiTransportError):invoke(c,p,'recovered-job')
        rows=c.execute("SELECT * FROM subscription_reservations WHERE dimension='ai_tokens'").fetchall()
        assert len(rows)==2 and all(r['state']=='RESERVED' for r in rows)
        assert totals(c)['ai_tokens']==(sum(r['amount'] for r in rows),0)
        assert totals(c)['ai_calls']==(0,1)

def test_explicit_provider_rejection_releases_capacity_and_retry_can_succeed(paid):
    c,_,org,*_=paid
    with workspace_scope(c,'controlled@example.test',org):
        p=provider(c,lambda _:httpx.Response(429,json={'error':{'message':'Controlled quota rejection'}}))
        with pytest.raises(AiRateLimited):invoke(c,p,'known-rejection')
        assert totals(c)=={'ai_calls':(0,0),'ai_tokens':(0,0)}
        assert invoke(c,provider(c,valid),'known-rejection').answer=='valid'
        assert totals(c)=={'ai_calls':(0,1),'ai_tokens':(0,125)}

def test_exhausted_capacity_prevents_network_and_releases_unstarted_call(paid):
    c,_,org,*_=paid;calls=[]
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'ai_tokens':600000},'already-held');c.commit()
        with pytest.raises(HTTPException) as error:invoke(c,provider(c,lambda r:(calls.append(r) or valid(r))),'cannot-start')
        assert error.value.status_code==429 and calls==[]
        assert totals(c)=={'ai_calls':(0,0),'ai_tokens':(600000,0)}

def test_partial_settlement_keeps_pending_report_reserved(paid):
    c,_,org,*_=paid
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'reports':1,'ai_calls':1},'report:controlled');c.commit()
        invoke(c,provider(c,valid),'report:controlled')
        assert totals(c)['reports']==(1,0) and totals(c)['ai_calls']==(0,1)
        usage.settle(c,'report:controlled',dimensions=('reports',))
        assert totals(c)['reports']==(0,1)

def test_missing_operation_id_never_becomes_shared_none_reservation(paid):
    from app.billing.usage import reserve
    c,_,org,*_=paid
    with workspace_scope(c,'controlled@example.test',org):
        for key in (None,'', ' ',123):
            with pytest.raises(ValueError):reserve(c,{'ai_calls':1},key)
        assert totals(c)=={}

def test_crash_recovery_cannot_refund_a_previous_unknown_attempt(paid):
    import hashlib
    from app.billing.ai_accounting import finalize_operation
    c,_,org,*_=paid;key='crashed-before-finally'
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'ai_calls':1},key)
        attempt='ai-attempt:'+hashlib.sha256(key.encode()).hexdigest()[:32]+':crashed'
        usage.reserve(c,{'ai_tokens':600000},attempt);c.commit()
        # Simulate recovery finding a durable attempt but no response metadata.
        finalize_operation(c,key)
        assert totals(c)=={'ai_calls':(0,1),'ai_tokens':(600000,0)}
        with pytest.raises(HTTPException):invoke(c,provider(c,valid),key)
        assert totals(c)=={'ai_calls':(0,1),'ai_tokens':(600000,0)}

def test_reported_overrun_is_recorded_without_clipping_or_extra_charge(paid):
    from app.billing import ai_accounting
    c,_,org,*_=paid
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'ai_calls':1},'unexpected-usage');c.commit()
        p=provider(c,valid)
        with operation('CONTROLLED_CAPACITY_TEST',operation_id='unexpected-usage'):
            attempt=ai_accounting.begin_attempt(p,10)
            ai_accounting.complete_attempt(p,attempt,{'input_tokens':100,'output_tokens':20,'thinking_tokens':5})
        assert totals(c)=={'ai_calls':(0,1),'ai_tokens':(0,125)}

def test_incomplete_thinking_usage_remains_reserved_instead_of_becoming_zero(paid):
    from app.billing import ai_accounting
    c,_,org,*_=paid
    with workspace_scope(c,'controlled@example.test',org):
        usage.reserve(c,{'ai_calls':1},'partly-reported');c.commit()
        p=provider(c,valid)
        with operation('CONTROLLED_CAPACITY_TEST',operation_id='partly-reported'):
            attempt=ai_accounting.begin_attempt(p,1000)
            ai_accounting.complete_attempt(p,attempt,{'input_tokens':100,'output_tokens':20,'thinking_tokens':None})
        assert totals(c)=={'ai_calls':(0,1),'ai_tokens':(1000,0)}
