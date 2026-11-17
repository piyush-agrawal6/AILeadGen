"""Paid AI operations and inference attempts have different durable identities.

One logical operation consumes one shared AI operation. Every actual provider
attempt reserves its own token capacity before network I/O. Unknown outcomes
stay reserved across crashes; retries cannot reuse that unknown capacity.
The existing versioned reservation ledger is sufficient; no migration or paid
access is manufactured here. Operator daily budgets remain separate.
"""
import hashlib,uuid
from contextlib import contextmanager,nullcontext
from contextvars import ContextVar
from dataclasses import dataclass,field
from app.billing import commercial_usage as usage,access_periods
from app.config.settings import get_settings
from app.database.connection import db_session

@dataclass
class Scope:
    operation_id:str
    attempts:list=field(default_factory=list)
    connection:object=None

_scope=ContextVar('paid_ai_operation',default=None)

def finalize_operation(c,operation_id):
    """Settle the logical operation using durable attempts, including old leases."""
    from app.billing.contracts import verified_workspace
    org=verified_workspace(c)
    from app.developer.keys import lock
    lock(c,org)
    _,reservations_table=access_periods.ledgers(c,org)
    row=c.execute(f"SELECT state FROM {reservations_table} WHERE organization_id=? AND operation_id=? AND dimension='ai_calls'",(org,operation_id)).fetchone()
    if row and row['state']=='RESERVED':
        prefix='ai-attempt:'+hashlib.sha256(operation_id.encode()).hexdigest()[:32]+':%'
        attempted=c.execute(f"SELECT 1 FROM {reservations_table} WHERE organization_id=? AND operation_id LIKE ? AND dimension='ai_tokens' AND state<>'RELEASED' LIMIT 1",(org,prefix)).fetchone()
        usage.settle(c,operation_id,release=not bool(attempted),dimensions=('ai_calls',))

@contextmanager
def operation(operation_id):
    scope=Scope(operation_id) if operation_id and (get_settings().payu_billing_enabled or access_periods.enabled()) else None
    token=_scope.set(scope)
    try:yield
    finally:
        try:
            if scope:
                with nullcontext(scope.connection) if scope.connection is not None else db_session() as c:
                    # A previous successful worker attempt already consumed this
                    # logical operation. A retry cannot refund or consume it twice.
                    finalize_operation(c,scope.operation_id)
                    c.commit()
        finally:_scope.reset(token)

def begin_attempt(provider,capacity):
    scope=_scope.get()
    if scope is None:return None
    scope.connection=getattr(provider,'usage_connection',None)
    # The prefix supports an operator audit without storing prompts or secrets.
    prefix=hashlib.sha256(scope.operation_id.encode()).hexdigest()[:32]
    attempt={'id':'ai-attempt:'+prefix+':'+str(uuid.uuid4()),'capacity':capacity,'outcome':'UNKNOWN'}
    with nullcontext(scope.connection) if scope.connection is not None else db_session() as c:
        if not usage.reserve(c,{'ai_tokens':capacity},attempt['id']):return None
        c.commit() # Durable before the provider can receive the request.
    scope.attempts.append(attempt)
    return attempt

def complete_attempt(provider,attempt,reported,*,rejected=False):
    if attempt is None:return
    connection=getattr(provider,'usage_connection',None)
    with nullcontext(connection) if connection is not None else db_session() as c:
        if rejected:
            usage.settle(c,attempt['id'],release=True)
            attempt['outcome']='REJECTED'
        elif all(reported.get(key) is not None for key in ('input_tokens','output_tokens','thinking_tokens')):
            actual=reported['input_tokens']+reported['output_tokens']+reported['thinking_tokens']
            if actual>attempt['capacity']:
                # Record a provider-reported overrun truthfully, even if it
                # exceeds remaining capacity. This is usage, never a monetary
                # charge. Future reservations fail against the actual total.
                from app.billing.contracts import verified_workspace
                from app.developer.keys import lock
                org=verified_workspace(c);lock(c,org)
                usage_table,reservations_table=access_periods.ledgers(c,org)
                row=c.execute(f"SELECT * FROM {reservations_table} WHERE organization_id=? AND operation_id=? AND dimension='ai_tokens'",(org,attempt['id'])).fetchone()
                if row and row['state']=='RESERVED' and row['amount']<actual:
                    c.execute(f"UPDATE {reservations_table} SET amount=? WHERE organization_id=? AND operation_id=? AND dimension='ai_tokens'",(actual,org,attempt['id']))
                    c.execute(f"UPDATE {usage_table} SET reserved=reserved+? WHERE organization_id=? AND contract_id=? AND period_start=? AND dimension='ai_tokens'",(actual-row['amount'],org,row['contract_id'],row['period_start']))
            usage.settle(c,attempt['id'],actual={'ai_tokens':actual})
            attempt['outcome']='REPORTED'
        c.commit()
