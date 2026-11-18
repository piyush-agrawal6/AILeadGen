"""Atomic monthly capacity accounting, scoped to a verified paid contract.

Reservations count once, including worker retries. Released pre-provider work
can be retried under its original operation; unknown outcomes remain reserved.
Monitoring increments one search plus its classification, never two searches.
"""
import json
from fastapi import HTTPException
from app.billing import contracts,access_periods
from app.database.prospects import now
from app.developer.keys import lock

def reserve(c,amounts,operation_id):
    from app.config.settings import get_settings
    if not (get_settings().payu_billing_enabled or access_periods.enabled()):return False
    org=contracts.verified_workspace(c)
    if not isinstance(operation_id,str) or not 1<=len(operation_id)<=200 or not amounts or any(type(v) is not int or v<=0 for v in amounts.values()):
        raise ValueError('A stable bounded operation reservation is required.')
    if set(amounts)-set((*contracts.METERED,'opportunities')):raise ValueError('Unknown usage dimension.')
    lock(c,org)
    from app.billing.subscription_access import setup_contract
    row=setup_contract(c,org,amounts,operation_id)
    if row is None:
        access_periods.require_current(c,org);row=contracts.active(c,org)
    if not row:return False
    # No approved monthly opportunity quota: preserve ordinary saved-record work.
    values={k:v for k,v in amounts.items() if k in contracts.METERED}
    usage_table,reservations_table=access_periods.ledgers(c,org)
    usage_start=row.get('usage_period_start',row['paid_start'])
    usage_end=row.get('usage_period_end',row['paid_end'])
    limits=contracts.snapshot(row)['limits'];pending=[]
    for dim,n in sorted(values.items()):
        previous=c.execute(f'SELECT * FROM {reservations_table} WHERE organization_id=? AND operation_id=? AND dimension=?',(org,operation_id,dim)).fetchone()
        if previous:
            if previous['amount']!=n:raise HTTPException(409,'Usage operation was reused with different capacity.')
            if previous['state']!='RELEASED':continue
            if previous['contract_id']!=row['id'] or previous['period_start']!=usage_start:
                raise HTTPException(409,'Released work belongs to a previous subscription period.')
        counter=c.execute(f'SELECT reserved,used FROM {usage_table} WHERE organization_id=? AND contract_id=? AND period_start=? AND dimension=?',(org,row['id'],usage_start,dim)).fetchone()
        if (counter['reserved']+counter['used'] if counter else 0)+n>limits[dim]:
            raise HTTPException(429,'Monthly '+dim.replace('_',' ')+' allowance exhausted. Saved records remain available; review usage or upgrade.')
        pending.append((dim,n,bool(previous)))
    stamp=now()
    for dim,n,previous in pending:
        c.execute(f'INSERT INTO {usage_table}(organization_id,contract_id,period_start,period_end,dimension,reserved) VALUES(?,?,?,?,?,?) ON CONFLICT(organization_id,contract_id,period_start,dimension) DO UPDATE SET reserved={usage_table}.reserved+excluded.reserved',(org,row['id'],usage_start,usage_end,dim,n))
        if previous:c.execute(f"UPDATE {reservations_table} SET state='RESERVED',actual_amount=NULL,updated_at=? WHERE organization_id=? AND operation_id=? AND dimension=?",(stamp,org,operation_id,dim))
        else:c.execute(f"INSERT INTO {reservations_table}(organization_id,contract_id,period_start,operation_id,dimension,amount,state,created_at,updated_at) VALUES(?,?,?,?,?,?,'RESERVED',?,?)",(org,row['id'],usage_start,operation_id,dim,n,stamp,stamp))
    if pending and row.get('internal_testing'):
        from app.billing.subscription_access import record_internal_testing_audit
        record_internal_testing_audit(c,org,row['internal_testing'],contract_id=row['id'],operation_id=operation_id,dimensions=[dim for dim,_,_ in pending])
    return True

def settle(c,operation_id,*,actual=None,release=False,dimensions=None):
    """Internal completion only. Release only when no provider work was attempted."""
    org=contracts.verified_workspace(c);lock(c,org)
    usage_table,reservations_table=access_periods.ledgers(c,org)
    rows=c.execute(f'SELECT * FROM {reservations_table} WHERE organization_id=? AND operation_id=? ORDER BY dimension',(org,operation_id)).fetchall()
    if dimensions is not None:
        if not dimensions or set(dimensions)-set(contracts.METERED):raise ValueError('Known settlement dimensions required.')
        rows=[r for r in rows if r['dimension'] in dimensions]
    if not rows:return False
    if actual is not None and (not isinstance(actual,dict) or set(actual)!={r['dimension'] for r in rows}):raise ValueError('Complete actual usage attribution required.')
    # Validate every dimension before any write (callers may catch exceptions).
    for r in rows:
        n=0 if release else (actual[r['dimension']] if actual is not None else r['amount'])
        if type(n) is not int or not 0<=n<=r['amount']:raise ValueError('Actual usage exceeds reserved capacity.')
        state='RELEASED' if release else 'COMMITTED'
        if r['state']!='RESERVED' and (r['state']!=state or r['actual_amount']!=n):raise HTTPException(409,'Usage completion conflicts with its recorded outcome.')
    for r in rows:
        if r['state']!='RESERVED':continue
        n=0 if release else (actual[r['dimension']] if actual is not None else r['amount'])
        c.execute(f'UPDATE {usage_table} SET reserved=reserved-?,used=used+? WHERE organization_id=? AND contract_id=? AND period_start=? AND dimension=?',(r['amount'],n,org,r['contract_id'],r['period_start'],r['dimension']))
        c.execute(f'UPDATE {reservations_table} SET state=?,actual_amount=?,updated_at=? WHERE organization_id=? AND operation_id=? AND dimension=?',('RELEASED' if release else 'COMMITTED',n,now(),org,operation_id,r['dimension']))
    return True

def capacity(c,org,dimension,count):
    if dimension not in contracts.CAPACITY:raise ValueError('Unknown capacity dimension.')
    lock(c,org);access_periods.require_current(c,org);row=contracts.active(c,org)
    if row and count>=contracts.snapshot(row)['limits'][dimension]:raise HTTPException(429,'Monthly plan '+dimension.replace('_',' ')+' capacity exhausted.')
    if row and row.get('internal_testing') and row.get('base_limits') and count>=row['base_limits'].get(dimension,0):
        from app.billing.subscription_access import record_internal_testing_audit
        record_internal_testing_audit(c,org,row['internal_testing'],contract_id=row['id'],operation_id=f'capacity:{dimension}:{count}',dimensions=[dimension])
    return bool(row)

def interval(c,hours):
    org=contracts.verified_workspace(c);access_periods.require_paid_feature(c,org,'monitor_executions');row=contracts.active(c,org)
    if row and hours<contracts.snapshot(row)['limits']['monitor_interval_hours']:
        raise HTTPException(429,'The current plan supports daily monitoring. Existing saved records remain available.')
