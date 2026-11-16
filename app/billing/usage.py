"""Atomic cycle quotas: no resets, client periods, unlimited grants or free retries."""
import json
from fastapi import HTTPException
from app.billing import service,catalog
from app.platform.context import organization
from app.developer.keys import lock
from app.database.prospects import now

def reserve(c,amounts,request_id):
    org=organization()
    if not isinstance(request_id,str) or not request_id.strip() or len(request_id)>200:raise ValueError('A bounded, stable operation reservation is required.')
    from app.billing.commercial_usage import reserve as commercial_reserve
    if commercial_reserve(c,amounts,request_id):return True
    if not service.test_allowed(org):return False
    if not request_id or len(str(request_id))>200 or not amounts or set(amounts)-set(catalog.DIMENSIONS) or any(type(n) is not int or n<=0 for n in amounts.values()):raise ValueError('A bounded, stable operation reservation is required.')
    lock(c,org);row=service.active(c,org)
    # Existing manual/beta access has independent operator budgets; billing does
    # not remove it or manufacture a plan when no settled subscription exists.
    if not row:return False
    limits=json.loads(row['plan_json'])['limits'];pending=[]
    for dimension,amount in sorted(amounts.items()):
        old=c.execute('SELECT amount FROM billing_reservations WHERE organization_id=? AND dimension=? AND request_id=?',(org,dimension,str(request_id))).fetchone()
        if old:
            if old[0]!=amount:raise HTTPException(409,'Usage request ID was reused with a different amount.')
            continue
        counter=c.execute('SELECT used FROM billing_usage WHERE organization_id=? AND subscription_id=? AND period_start=? AND dimension=?',(org,row['id'],row['paid_start'],dimension)).fetchone()
        if (counter[0] if counter else 0)+amount>limits[dimension]:raise HTTPException(429,'The current test subscription allowance for '+dimension.replace('_',' ')+' is exhausted.')
        pending.append((dimension,amount))
    for dimension,amount in pending:
        c.execute('INSERT INTO billing_usage(organization_id,subscription_id,period_start,period_end,dimension,used) VALUES(?,?,?,?,?,?) ON CONFLICT(organization_id,subscription_id,period_start,dimension) DO UPDATE SET used=billing_usage.used+excluded.used',(org,row['id'],row['paid_start'],row['paid_end'],dimension,amount))
        c.execute('INSERT INTO billing_reservations(organization_id,dimension,request_id,subscription_id,period_start,amount,created_at) VALUES(?,?,?,?,?,?,?)',(org,dimension,str(request_id),row['id'],row['paid_start'],amount,now()))
    return True

def capacity(c,dimension,current_count):
    if dimension not in ('monitors','team_members'):raise ValueError('Unsupported capacity dimension.')
    capacity_for_workspace(c,organization(),dimension,current_count)

def capacity_for_workspace(c,org,dimension,current_count):
    # Internal target comes from a verified invitation, never a request's org ID.
    if dimension not in ('monitors','team_members'):raise ValueError('Unsupported capacity dimension.')
    from app.billing.commercial_usage import capacity as commercial_capacity
    from app.billing import access_periods
    native=access_periods.require_current(c,org)
    # The approved trial includes one stored manual monitor; paid plans retain
    # their existing active-monitor accounting.
    if dimension!='monitors' or native and native['source_kind']=='TRIAL':
        if commercial_capacity(c,org,dimension,current_count):return
    lock(c,org);row=service.active(c,org)
    if row and current_count>=json.loads(row['plan_json'])['limits'][dimension]:raise HTTPException(429,'The current test plan '+dimension.replace('_',' ')+' capacity is exhausted.')
