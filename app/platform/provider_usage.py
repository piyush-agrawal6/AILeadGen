"""Shared provider-reported accounting. Missing usage/pricing stays unknown."""
import json
import time
import uuid
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException
from app.database.connection import db_session
from app.database.prospects import now

_operation=ContextVar('ai_usage_operation',default='STRUCTURED_INFERENCE')
@contextmanager
def operation(name,*,operation_id=None):
    token=_operation.set(name)
    try:
        from app.billing.ai_accounting import operation as paid_operation
        with paid_operation(operation_id):yield
    finally:_operation.reset(token)

def reported(data):
    metadata=data.get('usageMetadata') or {}
    mapping={'input_tokens':'promptTokenCount','output_tokens':'candidatesTokenCount','cached_tokens':'cachedContentTokenCount','thinking_tokens':'thoughtsTokenCount'}
    return {key:value if type(value:=metadata.get(native)) is int and value>=0 else None for key,native in mapping.items()}

def price(config,model,usage):
    try:
        entry=json.loads(config.model_pricing_json).get(model)
        if not entry or entry.get('approved') is not True or not str(entry.get('reference','')).startswith('https://'):return None,None
        if any(usage.get(key) is None for key in ('input_tokens','output_tokens','cached_tokens','thinking_tokens')):return None,entry['reference']
        rates={key:Decimal(str(entry[key])) for key in ('input_per_million_usd','output_per_million_usd','cached_per_million_usd')}
        if any(not v.is_finite() or v<0 for v in rates.values()):return None,None
        cached=usage['cached_tokens'] or 0
        if cached>usage['input_tokens']:return None,None
        total=((usage['input_tokens']-cached)*rates['input_per_million_usd']+cached*rates['cached_per_million_usd']+(usage['output_tokens']+(usage['thinking_tokens'] or 0))*rates['output_per_million_usd'])/Decimal(1000000)
        return str(total),entry['reference']
    except (ValueError,KeyError,TypeError,InvalidOperation):return None,None

def record(provider,usage,status,start):
    provider.last_usage={**usage,'basis':'PROVIDER_REPORTED' if any(v is not None for v in usage.values()) else 'NOT_REPORTED'}
    from app.platform.context import current
    try:ctx=current()
    except HTTPException:return
    from app.api.organization import membership_role
    cost,reference=price(provider.config,provider.model,usage)
    connection=getattr(provider,'usage_connection',None)
    with nullcontext(connection) if connection is not None else db_session() as c:
        if not membership_role(c,ctx.actor,ctx.organization_id):raise HTTPException(403,'AI usage membership was revoked.')
        c.execute('INSERT INTO ai_request_usage(id,organization_id,actor,operation,provider,model,status,input_tokens,output_tokens,cached_tokens,thinking_tokens,usage_basis,estimated_cost_usd,pricing_reference,fallback,duration_ms,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (str(uuid.uuid4()),ctx.organization_id,ctx.actor,_operation.get(),provider.provider_name,provider.model,status,usage['input_tokens'],usage['output_tokens'],usage['cached_tokens'],usage['thinking_tokens'],provider.last_usage['basis'],cost,reference,int(provider.provider_name=='GEMINI_API' and provider.config.primary_provider=='vertex'),round((time.monotonic()-start)*1000),now()))

def summary(c):
    from app.platform.context import current
    from app.api.organization import membership_role
    ctx=current()
    if not membership_role(c,ctx.actor,ctx.organization_id):raise HTTPException(403,'Active membership required.')
    month=now()[:7]
    rows=[dict(r) for r in c.execute('SELECT operation,provider,model,status,input_tokens,output_tokens,cached_tokens,thinking_tokens,usage_basis,estimated_cost_usd,fallback,duration_ms,created_at FROM ai_request_usage WHERE organization_id=? AND created_at>=? ORDER BY created_at DESC,id DESC LIMIT 50',(ctx.organization_id,month)).fetchall()]
    totals=dict(c.execute("SELECT COUNT(*) requests, SUM(CASE WHEN created_at>=? THEN 1 ELSE 0 END) requests_today, COALESCE(SUM(input_tokens),0) input_tokens_reported, COALESCE(SUM(output_tokens),0) output_tokens_reported, COALESCE(SUM(cached_tokens),0) cached_tokens_reported, COALESCE(SUM(thinking_tokens),0) thinking_tokens_reported, COALESCE(SUM(CASE WHEN usage_basis='NOT_REPORTED' THEN 1 ELSE 0 END),0) unreported_requests, COALESCE(SUM(CASE WHEN input_tokens IS NULL OR output_tokens IS NULL OR cached_tokens IS NULL OR thinking_tokens IS NULL THEN 1 ELSE 0 END),0) incomplete_usage_requests, COUNT(estimated_cost_usd) priced_requests, SUM(CAST(estimated_cost_usd AS NUMERIC)) estimated_cost FROM ai_request_usage WHERE organization_id=? AND created_at>=?",(now()[:10],ctx.organization_id,month)).fetchone())
    cost=totals.pop('estimated_cost');priced=totals.pop('priced_requests')
    totals['requests_today']=totals['requests_today'] or 0
    return {'month':month,**totals,'estimated_cost_usd':str(cost) if totals['requests'] and priced==totals['requests'] else None,'complete':True,'items':rows,'basis':'All workspace monthly requests aggregated server-side; latest 50 details. Actual provider tokens. Currency estimated only from operator-reviewed configured model pricing.'}
