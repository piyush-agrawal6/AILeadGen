"""Verified commercial access; catalog edits never replace contract snapshots.

No public writer exists. PayU lifecycle reconciliation must supply independent
settlement and mandate evidence before a contract can become ACTIVE.
"""
import json,time
from fastapi import HTTPException
from app.config.settings import get_settings
from app.api.organization import membership_role
from app.platform.context import current

METERED=('searches','ai_calls','ai_tokens','monitor_executions','reports','api_requests')
CAPACITY=('monitors','team_members')

def snapshot(row):
    value=json.loads(row['plan_json'])
    limits=value.get('limits')
    if not isinstance(limits,dict) or any(type(limits.get(k)) is not int or limits[k]<0 for k in (*METERED,*CAPACITY,'monitor_interval_hours')):
        raise HTTPException(503,'The verified subscription snapshot requires review.')
    if limits['monitor_interval_hours']<24:raise HTTPException(503,'Subscription monitoring policy requires review.')
    return value

def active(c,org):
    from app.billing.subscription_access import active as recurring
    value=recurring(c,org)
    if value:return value
    from app.billing import access_periods
    if access_periods.managed(c,org):return access_periods.active(c,org)
    if not get_settings().payu_billing_enabled:return None
    if get_settings().payu_mode=='test' and org not in {x.strip() for x in get_settings().billing_test_workspaces.split(',') if x.strip()}:return None
    stamp=int(time.time())
    row=c.execute("""SELECT p.* FROM commercial_contracts p JOIN commercial_workspace_slots s
       ON s.contract_id=p.id AND s.organization_id=p.organization_id AND s.mode=p.mode
       WHERE p.organization_id=? AND p.provider='payu' AND p.mode=? AND p.status='ACTIVE'
       AND p.mandate_verified=1 AND p.verified_at IS NOT NULL AND p.paid_start<=? AND p.paid_end>?""",
       (org,get_settings().payu_mode,stamp,stamp)).fetchone()
    if row:snapshot(row)
    return dict(row) if row else None

def verified_workspace(c):
    ctx=current()
    if not membership_role(c,ctx.actor,ctx.organization_id):raise HTTPException(403,'Active workspace membership required.')
    return ctx.organization_id

def eligibility_sql(org):
    if org not in ('m.organization_id','j.organization_id'):raise ValueError('Internal scheduler alias required.')
    if not get_settings().payu_billing_enabled:return '0=1',[]
    if get_settings().payu_mode=='test':
        approved=[x.strip() for x in get_settings().billing_test_workspaces.split(',') if x.strip()][:100]
        if not approved:return '0=1',[]
        restriction=' AND p.organization_id IN ('+','.join('?' for _ in approved)+')'
    else:approved=[];restriction=''
    stamp=int(time.time())
    return ("EXISTS(SELECT 1 FROM commercial_contracts p JOIN commercial_workspace_slots s ON s.contract_id=p.id AND s.organization_id=p.organization_id AND s.mode=p.mode WHERE p.organization_id="+org+" AND p.provider='payu' AND p.mode=? AND p.status='ACTIVE' AND p.mandate_verified=1 AND p.verified_at IS NOT NULL AND p.paid_start<=? AND p.paid_end>?"+restriction+")",[get_settings().payu_mode,stamp,stamp,*approved])
