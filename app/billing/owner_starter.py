"""Temporary owner-only development entitlement. No provider or public writer.

The archived slot is only a foreign-key anchor for a distinct usage period.
No trial/contract/payment row is created or altered. The server-configured UUID
and an independent, unrevoked operator audit record must both be present.
"""
import json,time,uuid
from app.config.settings import get_settings
from app.billing import commercial

OWNER='contact@planebyte.com'
ISSUED='OWNER_STARTER_DEVELOPMENT_GRANTED'
REVOKED='OWNER_STARTER_DEVELOPMENT_REVOKED'
MAX_SECONDS=7*86400

def configured_id():
    value=get_settings().owner_starter_grant_id
    try:return str(uuid.UUID(value)) if value else None
    except ValueError:return None

def anchor(c,org):
    return c.execute('''SELECT p.id,p.period_end FROM subscription_workspace_slots w
        JOIN subscription_contracts p ON p.id=w.contract_id AND p.organization_id=w.organization_id AND p.environment=w.environment
        JOIN organizations o ON o.id=w.organization_id AND o.status='ACTIVE'
        JOIN organization_memberships m ON m.organization_id=o.id AND m.user_id=? AND m.role='OWNER' AND m.status='ACTIVE'
        JOIN customer_accounts a ON a.user_id=m.user_id AND a.email=? AND a.status='ACTIVE' AND a.verified_at IS NOT NULL
        WHERE w.organization_id=? AND w.environment=? AND p.status='canceled' AND p.verified_at IS NOT NULL AND p.period_end<=?''',
        (OWNER,OWNER,org,get_settings().creem_environment,int(time.time()))).fetchone()

def active(c,org):
    key=configured_id()
    if not key:return None
    receipt=c.execute('''SELECT details_json FROM audit_log WHERE id=? AND organization_id=? AND action=? AND result='SUCCESS'
        AND NOT EXISTS (SELECT 1 FROM audit_log WHERE id=? AND organization_id=? AND action=?)''',(key,org,ISSUED,key+':revoked',org,REVOKED)).fetchone()
    if not receipt:return None
    grant=json.loads(receipt[0]);start=grant['start'];end=grant['end'];stamp=int(time.time())
    if grant['owner']!=OWNER or grant['plan']!='starter' or not start<=stamp<end or not 0<end-start<=MAX_SECONDS:return None
    slot=anchor(c,org)
    if not slot or slot['id']!=grant['anchor'] or slot['period_end']>start:return None
    plan=grant['snapshot'];label='Complimentary Starter · development'
    return {'id':slot['id'],'grant_id':key,'organization_id':org,'plan_code':'starter','plan_json':json.dumps(plan),'paid_start':start,'paid_end':end,'usage_period_start':start,'usage_period_end':end,'catalog_version':grant['catalog'],'status':'COMPLIMENTARY','provider_status':'complimentary','source_kind':'COMPLIMENTARY','mode':'development','is_trial':False,'entitlement_label':label}

def record(c,org,key,*,end,reason,administrator,revoke=False):
    """Operator CLI only; caller has verified database ownership. Never renew implicitly."""
    from app.database.prospects import now
    from app.developer.keys import lock
    from fastapi import HTTPException
    key=str(uuid.UUID(key));lock(c,org);stamp=int(time.time());slot=anchor(c,org)
    if revoke:
        if not c.execute('SELECT 1 FROM audit_log WHERE id=? AND organization_id=? AND action=?',(key,org,ISSUED)).fetchone():raise ValueError('Grant not found')
        info={'grant':key,'reason':reason};action=REVOKED;identifier=key+':revoked'
    else:
        selected=c.execute('SELECT active_organization_id FROM user_profiles WHERE user_id=?',(OWNER,)).fetchone()
        if not slot or not selected or selected[0]!=org:raise HTTPException(403,'The verified owner, selected workspace and ended subscription must agree.')
        if not stamp<end<=stamp+MAX_SECONDS or not reason.strip():raise ValueError('A reason and expiry within seven days are required')
        info={'owner':OWNER,'plan':'starter','start':stamp,'end':end,'anchor':slot['id'],'snapshot':commercial.plan('starter'),'catalog':commercial.catalog()['version'],'reason':reason};action=ISSUED;identifier=key
    c.execute("INSERT INTO audit_log(id,organization_id,actor,action,entity,result,details_json,created_at) VALUES(?,?,?,?,?,'SUCCESS',?,?)",(identifier,org,administrator,action,'development-grant:'+key,json.dumps(info),now()))
