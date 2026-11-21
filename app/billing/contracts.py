"""Verified commercial access; catalog edits never replace contract snapshots.

Commercial access requires verified Creem settlement, an authorized grant or
a server-validated trial. Historical payment receipts are not entitlements.
"""
import json
from fastapi import HTTPException
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
    from app.billing.owner_starter import active as development
    from app.billing.accounts import anchor
    value=development(c,anchor(c,org))
    if value:return value
    from app.billing import access_periods
    if access_periods.managed(c,org):return access_periods.active(c,org)
    return None

def verified_workspace(c):
    ctx=current()
    if not membership_role(c,ctx.actor,ctx.organization_id):raise HTTPException(403,'Active workspace membership required.')
    return ctx.organization_id
