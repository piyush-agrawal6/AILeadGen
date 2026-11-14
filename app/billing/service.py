"""Owner-managed sandbox subscriptions with independently reconciled settlement.

Provider calls happen outside database locks. Unknown POST outcomes are durable;
retries must reconcile rather than creating a second recurring mandate.
"""
import hashlib,json,time,uuid
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import current
from app.api.organization import require_role,membership_role
from app.developer.keys import lock
from app.billing import catalog,provider

TERMINAL={'cancelled','completed','expired','REJECTED'}
STATES={'created','authenticated','active','pending','halted','cancelled','completed','expired','paused'}
class Create(BaseModel):
    model_config=ConfigDict(extra='forbid')
    plan_code:Literal['starter','growth','scale']
    request_id:uuid.UUID
    confirm_test_mode:Literal[True]
class Verification(BaseModel):
    model_config=ConfigDict(extra='forbid')
    payment_id:str=Field(pattern=r'^pay_[A-Za-z0-9]{1,80}$')
    signature:str=Field(pattern=r'^[a-fA-F0-9]{64}$')
class Cancel(BaseModel):
    model_config=ConfigDict(extra='forbid')
    at_cycle_end:bool=True
    confirm:Literal[True]

def enabled():
    if not get_settings().billing_enabled:raise HTTPException(404,'Workspace billing is not enabled.')

def test_allowed(org):
    s=get_settings()
    return s.billing_enabled and s.billing_test_mode and s.razorpay_mode=='test' and org in {x.strip() for x in s.billing_test_workspaces.split(',') if x.strip()}

def access(c,manager=False):
    enabled();ctx=current()
    require_role(c,ctx.actor,ctx.organization_id,('OWNER',) if manager else ('OWNER','ADMIN'))
    return ctx

def rate(c,action,maximum=6):
    ctx=access(c,True);lock(c,ctx.organization_id);window=int(time.time())//60
    row=c.execute('SELECT requests FROM billing_action_windows WHERE organization_id=? AND action=? AND window_start=?',(ctx.organization_id,action,window)).fetchone()
    if row and row[0]>=maximum:raise HTTPException(429,'Please wait a minute before another billing action.')
    c.execute('INSERT INTO billing_action_windows(organization_id,action,window_start,requests) VALUES(?,?,?,1) ON CONFLICT(organization_id,action,window_start) DO UPDATE SET requests=billing_action_windows.requests+1',(ctx.organization_id,action,window))
    c.execute('DELETE FROM billing_action_windows WHERE organization_id=? AND window_start<?',(ctx.organization_id,window-10))

def audit(c,action,key):
    ctx=current()
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),ctx.actor,'BILLING_'+action,'subscription:'+key,'SUCCESS',ctx.organization_id,now()))

def owned(c,key,manager=False):
    ctx=access(c,manager)
    row=c.execute('SELECT * FROM billing_subscriptions WHERE id=? AND organization_id=?',(str(key),ctx.organization_id)).fetchone()
    if not row:raise HTTPException(404,'Subscription not found in this workspace.')
    return dict(row)

def public(row):
    result={k:row.get(k) for k in ('id','plan_code','mode','status','current_start','current_end','paid_start','paid_end','cancel_at_cycle_end','last_reconciled_at','created_at','updated_at')}
    result['plan']=json.loads(row['plan_json'])
    result['test_only']=True;result['commercial_entitlement']=False
    result['settled_current_period']=settled(row)
    return result

def settled(row):
    stamp=int(time.time())
    return bool(row['mode']=='test' and test_allowed(row['organization_id']) and row['status']=='active' and row.get('paid_start') is not None and row.get('paid_end') is not None and row['paid_start']<=stamp<row['paid_end'] and row['paid_start']==row['current_start'] and row['paid_end']==row['current_end'])

def active(c,org):
    if not test_allowed(org):return None
    row=c.execute("SELECT s.* FROM billing_subscriptions s JOIN billing_workspace_slots w ON w.subscription_id=s.id AND w.organization_id=s.organization_id AND w.mode=s.mode WHERE s.organization_id=? AND s.mode='test'",(org,)).fetchone()
    if row and settled(dict(row)):return dict(row)
    return None

def granted(c,org):
    row=active(c,org)
    return {'INTENT_RADAR'} if row else set()

def eligibility_sql(org):
    # SQL identifiers are fixed by scheduler code, never caller input.
    if org not in ('m.organization_id','j.organization_id'):raise ValueError('Internal scheduler alias required.')
    s=get_settings();approved=[value.strip() for value in s.billing_test_workspaces.split(',') if value.strip()][:100]
    if not s.billing_enabled or not s.billing_test_mode or not approved:return '0=1',[]
    stamp=int(time.time());marks=','.join('?' for _ in approved)
    sql="EXISTS(SELECT 1 FROM billing_subscriptions b JOIN billing_workspace_slots slot ON slot.organization_id=b.organization_id AND slot.subscription_id=b.id AND slot.mode=b.mode WHERE b.organization_id="+org+" AND b.organization_id IN ("+marks+") AND b.mode='test' AND b.status='active' AND b.paid_start=b.current_start AND b.paid_end=b.current_end AND b.paid_start<=? AND b.paid_end>?)"
    return sql,[*approved,stamp,stamp]

def fence_grant(c,org):
    lock(c,org)
    return bool(active(c,org))

def info(c):
    ctx=access(c);s=get_settings();rows=c.execute('SELECT * FROM billing_subscriptions WHERE organization_id=? ORDER BY created_at DESC,id DESC LIMIT 20',(ctx.organization_id,)).fetchall()
    payments=c.execute('SELECT provider_id,subscription_id,mode,amount,currency,status,period_start,period_end,recorded_at FROM billing_payments WHERE organization_id=? ORDER BY recorded_at DESC,provider_id DESC LIMIT 50',(ctx.organization_id,)).fetchall()
    selected=active(c,ctx.organization_id);usage=[]
    if selected:
        limits=json.loads(selected['plan_json'])['limits']
        counters={r['dimension']:r['used'] for r in c.execute('SELECT dimension,used FROM billing_usage WHERE organization_id=? AND subscription_id=? AND period_start=?',(ctx.organization_id,selected['id'],selected['paid_start'])).fetchall()}
        usage=[{'dimension':d,'used':counters.get(d,0),'limit':limits[d],'remaining':max(0,limits[d]-counters.get(d,0))} for d in catalog.DIMENSIONS]
    return {'mode':'test','provider':'razorpay','provider_configured':provider.configured(),'webhook_configured':bool(s.razorpay_webhook_secret.get_secret_value()),'controlled_workspace':test_allowed(ctx.organization_id),'can_manage':membership_role(c,ctx.actor,ctx.organization_id)=='OWNER','checkout_available':s.app_env!='production' and membership_role(c,ctx.actor,ctx.organization_id)=='OWNER' and test_allowed(ctx.organization_id) and provider.configured(),'public_checkout_enabled':False,'commercial_pricing_approved':False,'provider_health':'Credentials present; live Test Mode acceptance not certified' if provider.configured() else 'Not configured','plans':[p.model_dump() for p in catalog.plans(c).values()],'subscriptions':[public(dict(row)) for row in rows],'payments':[dict(row) for row in payments],'usage':usage,'manual_access_preserved':True,'plan_changes':'Cancel the existing subscription before selecting another sandbox plan. In-place proration is not enabled.'}

def checkout(c,key):
    row=owned(c,key,True)
    if get_settings().app_env=='production':raise HTTPException(410,'New Razorpay checkout is retired. Historical billing remains available.')
    if not test_allowed(row['organization_id']):raise HTTPException(403,'Test checkout is restricted to approved workspaces.')
    s=provider.guard()
    if row['status'] not in ('created','authenticated') or not row['provider_id']:raise HTTPException(409,'Reconcile this subscription before opening checkout.')
    p=catalog.Plan.model_validate(json.loads(row['plan_json']))
    return {'key':s.razorpay_key_id,'subscription_id':row['provider_id'],'name':'PlaneByte — internal Test Mode','description':p.name,'mode':'test','local_subscription_id':row['id']}

def create(c,body):
    ctx=access(c,True)
    if get_settings().app_env=='production':raise HTTPException(410,'New Razorpay subscriptions are retired. No payment has been initiated.')
    if not test_allowed(ctx.organization_id):raise HTTPException(403,'Test checkout is restricted to approved workspaces.')
    provider.guard();p=catalog.plan(body.plan_code,c)
    if not p.provider_plan_id or not p.amount:raise HTTPException(409,'This test plan has no verified provider mapping. No payment has been initiated.')
    lock(c,ctx.organization_id)
    old=c.execute('SELECT * FROM billing_subscriptions WHERE organization_id=? AND mode=? AND request_id=?',(ctx.organization_id,'test',str(body.request_id))).fetchone()
    if old:
        if old['plan_code']!=p.code:raise HTTPException(409,'Request ID belongs to a different plan.')
        return public(dict(old))
    slot=c.execute('SELECT s.status FROM billing_workspace_slots w JOIN billing_subscriptions s ON s.id=w.subscription_id AND s.organization_id=w.organization_id WHERE w.organization_id=? AND w.mode=?',(ctx.organization_id,'test')).fetchone()
    if slot and slot['status'] not in TERMINAL:raise HTTPException(409,'An existing subscription or unresolved creation must be reconciled or cancelled first.')
    rate(c,'create',3)
    key=str(uuid.uuid4());stamp=now()
    c.execute('INSERT INTO billing_subscriptions(id,organization_id,created_by,mode,request_id,plan_code,plan_json,status,next_reconcile_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(key,ctx.organization_id,ctx.actor,'test',str(body.request_id),p.code,p.model_dump_json(),'CREATING',stamp,stamp,stamp))
    c.execute('INSERT INTO billing_workspace_slots(organization_id,mode,subscription_id) VALUES(?,?,?) ON CONFLICT(organization_id,mode) DO UPDATE SET subscription_id=excluded.subscription_id',(ctx.organization_id,'test',key))
    audit(c,'CREATION_RESERVED',key);c.commit()
    try:
        provider.verify_plan(p,provider.request('GET','plans/'+provider.identifier(p.provider_plan_id,'plan')))
    except (provider.ProviderRejected,provider.ProviderUnavailable):
        c.execute("UPDATE billing_subscriptions SET status='REJECTED',updated_at=? WHERE id=? AND organization_id=?",(now(),key,ctx.organization_id));c.commit()
        raise HTTPException(502,'The configured test plan could not be verified. No subscription creation was attempted.') from None
    try:
        result=provider.request('POST','subscriptions',{'plan_id':p.provider_plan_id,'quantity':1,'total_count':p.total_count,'customer_notify':False,'notes':{'workspace_id':ctx.organization_id,'local_subscription_id':key,'mode':'test'}})
        identifier=provider.identifier(result.get('id'),'sub')
        if result.get('plan_id')!=p.provider_plan_id or result.get('status') not in ('created','authenticated'):raise provider.ProviderUnavailable('Unexpected creation response.')
        c.execute('UPDATE billing_subscriptions SET provider_id=?,status=?,updated_at=? WHERE id=? AND organization_id=?',(identifier,result['status'],now(),key,ctx.organization_id));audit(c,'CREATED',key);c.commit()
    except (provider.ProviderUnavailable,provider.ProviderRejected):
        c.execute("UPDATE billing_subscriptions SET status='OUTCOME_UNKNOWN',updated_at=? WHERE id=? AND organization_id=?",(now(),key,ctx.organization_id));c.commit()
        raise HTTPException(502,'Creation outcome requires reconciliation. Reuse this request; do not create another mandate.') from None
    return public(owned(c,key))

def _reconcile(c,key,*,worker=False):
    # Worker keys originate only from durable local records, never webhook notes.
    row=dict(c.execute('SELECT * FROM billing_subscriptions WHERE id=?',(key,)).fetchone()) if worker else owned(c,key,True)
    if not test_allowed(row['organization_id']) or row['mode']!='test':raise HTTPException(403,'This subscription is outside the authorized test environment.')
    provider.guard()
    if not row['provider_id']:raise HTTPException(409,'Creation outcome is unresolved. An operator must match provider notes to this exact local subscription before retrying.')
    p=catalog.Plan.model_validate(json.loads(row['plan_json']))
    known={r[0] for r in c.execute("SELECT provider_id FROM billing_payments WHERE organization_id=? AND subscription_id=? AND mode='test' ORDER BY recorded_at DESC LIMIT 10",(row['organization_id'],key)).fetchall()}
    # Provider latency must not retain an idle database transaction. The later
    # workspace lock and revision check still fence concurrent state changes.
    c.commit()
    sub=provider.request('GET','subscriptions/'+provider.identifier(row['provider_id'],'sub'))
    provider.verify_plan(p,provider.request('GET','plans/'+provider.identifier(p.provider_plan_id,'plan')))
    if sub.get('id')!=row['provider_id'] or sub.get('plan_id')!=p.provider_plan_id or sub.get('quantity')!=1 or sub.get('status') not in STATES:raise provider.ProviderRejected('Subscription state does not match the local record.')
    notes=sub.get('notes') or {}
    if notes.get('workspace_id')!=row['organization_id'] or notes.get('local_subscription_id')!=row['id'] or notes.get('mode')!='test':raise provider.ProviderRejected('Provider subscription attribution does not match.')
    customer=sub.get('customer_id')
    if customer:provider.identifier(customer,'cust')
    if row['customer_id'] and row['customer_id']!=customer:raise provider.ProviderRejected('Subscription customer changed unexpectedly.')
    start,end=sub.get('current_start'),sub.get('current_end')
    period=type(start) is int and type(end) is int and 0<start<end
    paid_count=sub.get('paid_count',0)
    if type(paid_count) is not int or paid_count<0:raise provider.ProviderRejected('Invalid subscription payment count.')
    payment=None;verified=[]
    # Catch up captured history even if a later charge has already moved the
    # mandate to pending/cancelled. Only the exact active current period can grant
    # access. A nominal authorization payment is never a settled billing period.
    if paid_count>0:
        invoices=provider.request('GET','invoices',params={'subscription_id':sub['id'],'count':10,'skip':0})
        if not isinstance(invoices.get('items'),list) or len(invoices['items'])>10:raise provider.ProviderRejected('Invalid bounded invoice response.')
        candidates=[]
        for invoice in invoices['items']:
            if not isinstance(invoice,dict):raise provider.ProviderRejected('Invalid invoice record.')
            if invoice.get('subscription_id')!=sub['id'] or invoice.get('status')!='paid':continue
            first,last=invoice.get('billing_start'),invoice.get('billing_end')
            if type(first) is not int or type(last) is not int or not 0<first<last:raise provider.ProviderRejected('Invalid invoice billing period.')
            current_period=sub['status']=='active' and period and first==start and last==end
            if current_period or invoice.get('payment_id') not in known:candidates.append((current_period,invoice))
        # Prioritize current settlement and verify at most three payments per
        # pass. Further missed history catches up on later bounded worker reads.
        candidates.sort(key=lambda item:(item[0],item[1]['billing_start']),reverse=True)
        for current_period,invoice in candidates[:3]:
            if invoice.get('customer_id')!=customer or invoice.get('amount')!=p.amount or invoice.get('amount_paid')!=p.amount or invoice.get('amount_due')!=0 or invoice.get('currency')!=p.currency:raise provider.ProviderRejected('Invoice is inconsistent with the approved test plan.')
            pay=provider.request('GET','payments/'+provider.identifier(invoice.get('payment_id'),'pay'))
            if pay.get('id')!=invoice['payment_id'] or pay.get('status')!='captured' or pay.get('captured') is not True or pay.get('amount')!=p.amount or pay.get('currency')!=p.currency or pay.get('order_id')!=invoice.get('order_id') or pay.get('invoice_id')!=invoice.get('id') or pay.get('amount_refunded',0)!=0:raise provider.ProviderRejected('Payment settlement could not be independently verified.')
            provider.identifier(invoice.get('id'),'inv');verified.append((invoice,pay))
            if current_period:payment=(invoice,pay)
    lock(c,row['organization_id'])
    latest=c.execute('SELECT * FROM billing_subscriptions WHERE id=? AND organization_id=?',(key,row['organization_id'])).fetchone()
    # Concurrent cancellation/reconciliation may have won while network I/O ran.
    if latest['updated_at']!=row['updated_at']:raise HTTPException(409,'Subscription changed during reconciliation; retry the read safely.')
    if customer:
        c.execute('INSERT INTO billing_customers(organization_id,mode,provider_id,created_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,mode,provider_id) DO NOTHING',(row['organization_id'],'test',customer,now()))
    paid_start,paid_end=(start,end) if payment else (None,None)
    for invoice,pay in verified:
        prior=c.execute('SELECT organization_id,subscription_id FROM billing_payments WHERE mode=? AND provider_id=?',('test',pay['id'])).fetchone()
        if prior and (prior['organization_id']!=row['organization_id'] or prior['subscription_id']!=key):raise provider.ProviderRejected('Payment is already attributed elsewhere.')
        c.execute('INSERT INTO billing_payments(mode,provider_id,organization_id,subscription_id,invoice_id,amount,currency,status,period_start,period_end,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(mode,provider_id) DO UPDATE SET status=excluded.status',('test',pay['id'],row['organization_id'],key,invoice['id'],pay['amount'],pay['currency'],'captured',invoice['billing_start'],invoice['billing_end'],now()))
    stamp=now();due=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat()
    c.execute('UPDATE billing_subscriptions SET customer_id=?,status=?,current_start=?,current_end=?,paid_start=?,paid_end=?,last_reconciled_at=?,next_reconcile_at=?,failures=0,updated_at=? WHERE id=? AND organization_id=?',(customer,sub['status'],start if period else None,end if period else None,paid_start,paid_end,stamp,due,stamp,key,row['organization_id']))
    c.commit()
    return public(dict(c.execute('SELECT * FROM billing_subscriptions WHERE id=? AND organization_id=?',(key,row['organization_id'])).fetchone()))

def reconcile(c,key,*,worker=False):
    try:return _reconcile(c,key,worker=worker)
    except provider.ProviderRejected:
        # Known inconsistent/refunded settlement cannot retain a previous grant.
        # A client-owned UUID is checked before ever touching this local record.
        c.rollback()
        row=c.execute('SELECT organization_id FROM billing_subscriptions WHERE id=?',(key,)).fetchone()
        if row and (worker or current().organization_id==row['organization_id']):
            lock(c,row['organization_id'])
            c.execute("UPDATE billing_subscriptions SET status='REVIEW_REQUIRED',paid_start=NULL,paid_end=NULL,failures=failures+1,updated_at=? WHERE id=? AND organization_id=?",(now(),key,row['organization_id']));c.commit()
        raise

def recover(c,key):
    row=owned(c,key,True);provider.guard()
    if not test_allowed(row['organization_id']):raise HTTPException(403,'Test billing is restricted.')
    if row['provider_id']:return reconcile(c,key)
    if row['status'] not in ('CREATING','OUTCOME_UNKNOWN'):raise HTTPException(409,'This record does not need creation recovery.')
    rate(c,'recover',2);c.commit();matches=[]
    for offset in range(0,500,100):
        result=provider.request('GET','subscriptions',params={'count':100,'skip':offset})
        items=result.get('items')
        if not isinstance(items,list) or len(items)>100:raise provider.ProviderRejected('Invalid subscription history response.')
        matches += [item for item in items if (item.get('notes') or {}).get('local_subscription_id')==row['id'] and (item.get('notes') or {}).get('workspace_id')==row['organization_id'] and (item.get('notes') or {}).get('mode')=='test']
        if len(items)<100:break
    else:raise HTTPException(409,'Provider history exceeds the safe recovery window; an operator must inspect it.')
    if len(matches)!=1:raise HTTPException(409,'Exactly one matching provider subscription is required. No new mandate was created.')
    remote=matches[0];p=catalog.Plan.model_validate(json.loads(row['plan_json']))
    if remote.get('plan_id')!=p.provider_plan_id or remote.get('quantity')!=1:raise provider.ProviderRejected('Recovered subscription plan does not match.')
    identifier=provider.identifier(remote.get('id'),'sub');lock(c,row['organization_id'])
    if not c.execute("UPDATE billing_subscriptions SET provider_id=?,updated_at=? WHERE id=? AND organization_id=? AND provider_id IS NULL AND status IN ('CREATING','OUTCOME_UNKNOWN')",(identifier,now(),key,row['organization_id'])).rowcount:raise HTTPException(409,'Recovery state changed; reload before continuing.')
    audit(c,'CREATION_RECOVERED',key);c.commit();return reconcile(c,key)

def verify(c,key,body):
    row=owned(c,key,True);rate(c,'verify');c.commit();provider.guard()
    if not row['provider_id'] or not provider.verify_signature((body.payment_id+'|'+row['provider_id']).encode(),body.signature,get_settings().razorpay_key_secret.get_secret_value()):raise HTTPException(400,'Checkout signature verification failed. No access was granted.')
    # The payment ID in the callback has no entitlement authority. Settlement is
    # reloaded through the stored subscription's own invoices and payments.
    return reconcile(c,key)

def sync(c,key):
    owned(c,key,True);rate(c,'reconcile');c.commit()
    return reconcile(c,key)

def cancel(c,key,body):
    row=owned(c,key,True)
    if not test_allowed(row['organization_id']):raise HTTPException(403,'Test billing is restricted.')
    provider.guard()
    if row['status'] in TERMINAL:return public(row)
    if not row['provider_id']:raise HTTPException(409,'Resolve the creation outcome before cancelling.')
    rate(c,'cancel',3)
    c.execute('UPDATE billing_subscriptions SET cancel_at_cycle_end=?,updated_at=? WHERE id=? AND organization_id=?',(int(body.at_cycle_end),now(),key,row['organization_id']));audit(c,'CANCELLATION_REQUESTED',key);c.commit()
    provider.request('POST','subscriptions/'+provider.identifier(row['provider_id'],'sub')+'/cancel',{'cancel_at_cycle_end':body.at_cycle_end})
    return reconcile(c,key)
