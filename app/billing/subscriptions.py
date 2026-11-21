"""Workspace-owned subscription orchestration; provider redirects grant nothing."""
import hashlib,json,time,uuid
from datetime import datetime,timezone
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.billing import commercial,creem,subscription_access as access
from app.config.settings import get_settings
from app.platform.context import current
from app.api.organization import membership_role
from app.database.connection import db_session
from app.database.prospects import now
from app.developer.keys import lock

class Checkout(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
 plan_code:Literal['starter','growth','scale']
 variant:Literal['paid','trial']
 request_id:uuid.UUID
 expected_workspace:uuid.UUID|None=None
 terms_version:str=Field(min_length=1,max_length=100)
 accepted_terms:Literal[True]
 accepted_recurring:Literal[True]
 customer_name:str|None=Field(default=None,min_length=2,max_length=120)

def _real_customer_name(c,actor):
 local=actor.split('@')[0].casefold()
 try:
  row=c.execute('SELECT display_name FROM user_profiles WHERE user_id=?',(actor,)).fetchone()
  name=(row['display_name'] or '').strip() if row else ''
  if not name:
   user=c.execute('SELECT display_name FROM users WHERE id=?',(actor,)).fetchone()
   name=(user[0] or '').strip() if user else ''
 except Exception:
  return None
 if len(name)<2 or name.casefold()==local or any(ord(ch)<32 for ch in name):return None
 return name

class Action(BaseModel):
 model_config=ConfigDict(extra='forbid')
 request_id:uuid.UUID

def owner(c):
 ctx=current()
 if membership_role(c,ctx.actor,ctx.organization_id)!='OWNER':raise HTTPException(403,'Only the active workspace owner can manage subscriptions.')
 return ctx

def trial_available(c,actor):
 from app.accounts.policy import company_domain
 try:domain=company_domain(actor)
 except ValueError:return False  # A non-qualifying domain restricts the trial, not paid recovery.
 if c.execute('SELECT 1 FROM launch_trial_claims WHERE user_id=? OR company_domain=?',(actor,domain)).fetchone() or c.execute('SELECT 1 FROM subscription_trials WHERE user_id=? OR company_domain=?',(actor,domain)).fetchone():return False
 return not c.execute("SELECT 1 FROM subscription_checkouts WHERE environment=? AND variant='trial' AND status='COMPLETED' AND (created_by=? OR LOWER(created_by) LIKE ? OR LOWER(created_by) LIKE ?) LIMIT 1",(get_settings().creem_environment,actor,'%@'+domain,'%@%.'+domain)).fetchone()

def profile(c,org):
 row=c.execute('SELECT * FROM subscription_billing_profiles WHERE organization_id=?',(org,)).fetchone()
 return dict(row) if row else None

def route(c,org):
 # Creem hosted checkout determines supported countries and methods.
 return 'creem',None

def blockers(c,org,variant):
 s=get_settings();provider,reason=route(c,org);result=[reason] if reason else []
 if provider in ('creem',None):
  try:creem.key_for(s.creem_environment)
  except creem.Unavailable:result.append('Creem '+s.creem_environment+' connectivity is not configured.')
  if not s.subscription_terms_version:result.append('The updated card-trial and automatic-renewal terms await final owner approval.')
  if s.creem_environment=='production':
   proof=c.execute("SELECT * FROM subscription_provider_readiness WHERE provider='creem' AND environment='production'").fetchone()
   if not proof or not proof['checkout_verified'] or not proof['merchant_verified'] or not proof['recurring_verified'] or not proof['verification_reference'] or not proof['verified_at'] or variant=='trial' and not proof['trial_verified']:
    result.append('Live Creem checkout is awaiting genuine sandbox acceptance and merchant verification.')
   if not s.subscription_checkout_enabled:result.append('Live checkout is not activated. No card or payment will be requested.')
  elif org not in {v.strip() for v in s.billing_test_workspaces.split(',') if v.strip()}:result.append('Sandbox checkout is restricted to explicitly approved test workspaces.')
 if variant=='trial' and not trial_available(c,current().actor):result.append('A trial has already been used by this verified account or company domain. Choose a paid plan.')
 return list(dict.fromkeys(result))

def public_contract(row):
 if not row:return None
 data={k:row[k] for k in ('id','provider','environment','plan_code','status','period_start','period_end','trial_start','trial_end','next_charge_at','cancel_at','cancel_confirmed_at','recurring_authorized','verified_at')}
 data['is_trial']=access.is_trial_contract(row)
 data['entitlement_label']=access.entitlement_label(row)
 return data

def lifecycle(c,org,actor):
 """The slot identifies the contract. History is never selected by plan name."""
 env=get_settings().creem_environment
 row=c.execute('SELECT p.* FROM subscription_workspace_slots w JOIN subscription_contracts p ON p.id=w.contract_id AND p.organization_id=w.organization_id AND p.environment=w.environment WHERE w.organization_id=? AND w.environment=?',(org,env)).fetchone()
 pending=c.execute("SELECT id,created_by,status,plan_code,variant,checkout_url FROM subscription_checkouts WHERE organization_id=? AND environment=? AND status IN ('CREATING','PENDING','REVIEW') ORDER BY created_at DESC,id LIMIT 1",(org,env)).fetchone()
 grant=access.product_grant(c,org);eligible=trial_available(c,actor);raw=row['status'] if row else None
 if grant:
  phase='cancellation_scheduled' if raw in ('canceled','scheduled_cancel') else 'trial_active' if grant.get('is_trial') else 'paid_active'
 elif pending:phase='checkout_pending'
 elif raw=='canceled':phase='trial_ended' if access.is_trial_contract(row) else 'canceled'
 elif raw in ('past_due','expired','unpaid','paused','refunded','disputed'):phase=raw
 elif row:phase='verification_required'
 else:phase='trial_eligible' if eligible else 'no_subscription'
 # Creem can retry an expired subscription; verify terminal cancellation before replacing it.
 buy=not grant and not pending and (not row or raw=='canceled' and row['verified_at'] and row['period_end'] and row['period_end']<=int(time.time()))
 change=None
 from app.billing.plan_changes import pending as pending_change
 version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
 supports_change=version>=(1012 if version>=1000 else 54)
 if row and supports_change:change=pending_change(c,row['id'],env)
 return {'phase':phase,'can_purchase':bool(buy),'can_change':bool(supports_change and grant and raw=='active' and not grant.get('is_trial') and not change),'pending_change':{k:change[k] for k in ('plan_code','status','effective_at')} if change else None,'effective_plan':grant.get('plan_code') if grant else None,'effective_label':grant.get('entitlement_label') if grant else None,'trial_eligible':eligible,'pending_checkout':({'status':pending['status'],'plan_code':pending['plan_code'],'variant':pending['variant'],'resume_url':pending['checkout_url'] if pending['status']=='PENDING' and pending['created_by']==actor and membership_role(c,actor,org)=='OWNER' else None} if pending else None)}

def summary(c):
 ctx=current()
 if not membership_role(c,ctx.actor,ctx.organization_id):raise HTTPException(403,'Active workspace membership required.')
 if not access.enabled():return {'enabled':False,'required':False,'active':False,'plans':commercial.catalog()['plans'],'blockers':['Subscription onboarding is not enabled.']}
 org=ctx.organization_id;s=get_settings();active=access.product_grant(c,org)
 row=c.execute('SELECT p.* FROM subscription_contracts p JOIN subscription_workspace_slots w ON w.contract_id=p.id AND w.organization_id=p.organization_id AND w.environment=p.environment WHERE p.organization_id=? AND p.environment=?',(org,s.creem_environment)).fetchone()
 provider,reason=route(c,org);billing=profile(c,org)
 history=[dict(r) for r in c.execute('SELECT provider,environment,payment_id,amount_minor,currency,status,period_start,period_end,receipt_url,recorded_at FROM subscription_payments WHERE organization_id=? AND environment=? ORDER BY recorded_at DESC,payment_id DESC LIMIT 50',(org,s.creem_environment)).fetchall()]
 return {'enabled':True,'required':access.required(c,org),'active':bool(active),'provider':provider,'country':billing['country'] if billing else None,'country_verified':bool(billing and billing['status']=='VERIFIED' and billing['verified_at']),
  'workspace_id':org,'account_email':ctx.actor,'customer_name':_real_customer_name(c,ctx.actor),
  'terms_version':s.subscription_terms_version,'policy_version':access.POLICY,'trial_seconds':access.TRIAL_SECONDS,'trial_limits':access.TRIAL_LIMITS,
  'trial_eligible':trial_available(c,ctx.actor),'plans':commercial.catalog()['plans'],'can_manage':membership_role(c,ctx.actor,org)=='OWNER',
  'contract':public_contract(row),'history':history,'lifecycle':lifecycle(c,org,ctx.actor),
  'checkouts':[dict(r) for r in c.execute('SELECT id,provider,environment,plan_code,variant,status,created_at FROM subscription_checkouts WHERE organization_id=? AND environment=? ORDER BY created_at DESC,id DESC LIMIT 10',(org,s.creem_environment)).fetchall()],
  'paid_blockers':blockers(c,org,'paid'),'trial_blockers':blockers(c,org,'trial'),
  'renewal_disclosure':'The selected monthly plan renews automatically until canceled. The secure hosted checkout shows the final amount, currency and renewal date before authorization. Cancel in Settings → Billing & Subscription or the provider billing portal.',
  'tax_disclosure':'Creem is the merchant of record for all supported countries, including India where available. USD list prices are tax-inclusive; Creem discloses the final amount, supported currency, payment methods and tax breakdown. PlaneByte adds no unverified GST or homemade conversion.'}

def start(body):
 s=get_settings()
 with db_session() as c:
  ctx=owner(c);org=ctx.organization_id
  if body.expected_workspace and str(body.expected_workspace)!=org:raise HTTPException(409,'Workspace changed. Review the plan in the selected workspace.')
  if not access.enabled():raise HTTPException(503,'Subscription onboarding is unavailable.')
  errors=blockers(c,org,body.variant)
  if errors:raise HTTPException(409,{'code':'CHECKOUT_NOT_READY','message':errors[0],'blockers':errors})
  if body.terms_version!=s.subscription_terms_version:raise HTTPException(409,'Review the current automatic-renewal terms.')
  selected=commercial.plan(body.plan_code);provider,_=route(c,org)
  if provider!='creem':raise HTTPException(409,'This provider payment path is not ready.')
  mode=s.creem_environment;lock(c,org)
  if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(hashtext(?))',('subscription-actor:'+ctx.actor,))
  if c.execute("SELECT 1 FROM subscription_checkouts WHERE created_by=? AND organization_id<>? AND environment=? AND status IN ('CREATING','PENDING','REVIEW') LIMIT 1",(ctx.actor,org,mode)).fetchone():raise HTTPException(409,'An existing billing request for this owner needs verification before starting another checkout.')
  if body.variant=='trial':
   from app.accounts.policy import company_domain
   domain=company_domain(ctx.actor)
   if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(hashtext(?))',('trial:'+domain,))
   if not trial_available(c,ctx.actor):raise HTTPException(409,'Trial already used. Choose a paid plan.')
   if c.execute("SELECT 1 FROM subscription_checkouts WHERE environment=? AND organization_id<>? AND variant='trial' AND (LOWER(created_by) LIKE ? OR LOWER(created_by) LIKE ?) AND status IN ('CREATING','PENDING','REVIEW') LIMIT 1",(mode,org,'%@'+domain,'%@%.'+domain)).fetchone():raise HTTPException(409,'A trial request for this company is already pending.')
  digest=hashlib.sha256(json.dumps({**body.model_dump(mode='json'),'mode':mode},sort_keys=True).encode()).hexdigest()
  previous=c.execute('SELECT * FROM subscription_checkouts WHERE organization_id=? AND request_id=?',(org,str(body.request_id))).fetchone()
  if previous:
   if previous['request_hash']!=digest:raise HTTPException(409,'Checkout request was reused with different terms.')
   return {'checkout_id':previous['id'],'status':previous['status'],'checkout_url':previous['checkout_url'] if previous['status']=='PENDING' else None}
  if c.execute("SELECT 1 FROM subscription_checkouts WHERE organization_id=? AND environment=? AND status IN ('CREATING','PENDING','REVIEW')",(org,mode)).fetchone():raise HTTPException(409,'Review the existing checkout before starting another subscription.')
  slot=c.execute('SELECT p.* FROM subscription_contracts p JOIN subscription_workspace_slots w ON w.contract_id=p.id AND w.organization_id=p.organization_id AND w.environment=p.environment WHERE p.organization_id=? AND p.environment=?',(org,mode)).fetchone()
  if slot:
   if slot['status']!='canceled' or not slot['verified_at'] or not slot['period_end'] or slot['period_end']>int(time.time()):raise HTTPException(409,'Refresh or manage the existing subscription before another purchase. Creem may still renew or retry payment.')
   try:remote=creem.object_mode(creem.get_subscription(slot['provider_id'],mode=mode),mode)
   except (creem.Rejected,creem.Unavailable):raise HTTPException(503,'Unable to verify the previous subscription. Retry billing status.') from None
   ref=lambda x:x.get('id') if isinstance(x,dict) else x
   if remote.get('id')!=slot['provider_id'] or ref(remote.get('customer'))!=slot['customer_id'] or remote.get('status')!='canceled':raise HTTPException(409,'Provider status changed. Refresh billing before purchasing.')
  from app.billing.access_periods import active as legacy
  old=legacy(c,org)
  if old and old['source_kind']=='PAYMENT':raise HTTPException(409,'Existing paid access requires a reviewed provider transition; no overlapping subscription is created.')
  product=c.execute("SELECT * FROM subscription_products WHERE provider='creem' AND environment=? AND plan_code=? AND variant=?",(mode,body.plan_code,body.variant)).fetchone()
  if not product or product['catalog_hash']!=commercial.catalog()['catalog_sha256']:raise HTTPException(503,'Provider product mapping is awaiting verification.')
  key=str(uuid.uuid4());stamp=now();customer=c.execute("SELECT customer_id FROM subscription_customers WHERE provider='creem' AND environment=? AND organization_id=?",(mode,org)).fetchone()
  disclosure={'plan':body.plan_code,'amount_minor':selected['monthly_minor'],'currency':'USD','billing_interval':'every-month','trial_seconds':access.TRIAL_SECONDS if body.variant=='trial' else 0,'automatic_renewal':True,'accepted_recurring':True,'hosted_final_disclosure_required':True,'policy_version':access.POLICY}
  resolved_name=(body.customer_name or '').strip()
  if resolved_name and (any(ord(ch)<32 for ch in resolved_name) or resolved_name.casefold()==ctx.actor.split('@')[0].casefold()):
   resolved_name=''
  if not resolved_name:resolved_name=_real_customer_name(c,ctx.actor) or ''
  if resolved_name and body.customer_name and not _real_customer_name(c,ctx.actor):
   try:
    c.execute("INSERT INTO user_profiles(user_id,display_name,job_title,phone,timezone,locale,created_at,updated_at) VALUES(?,?,'','','UTC','en',?,?) ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name,updated_at=excluded.updated_at",(ctx.actor,resolved_name,stamp,stamp))
    c.execute('UPDATE users SET display_name=?,updated_at=? WHERE id=?',(resolved_name,stamp,ctx.actor))
   except Exception:
    pass
  c.execute("INSERT INTO subscription_checkouts(id,organization_id,created_by,provider,environment,plan_code,variant,request_id,request_hash,customer_id,product_id,status,country,currency,amount_minor,trial_days,terms_version,accepted_at,disclosure_json,created_at,updated_at) VALUES(?,?,?,'creem',?,?,?,?,?,?,?,'CREATING',?,'USD',?,?,?,?,?,?,?)",(key,org,ctx.actor,mode,body.plan_code,body.variant,str(body.request_id),digest,customer['customer_id'] if customer else None,product['product_id'],'UNCONFIRMED',selected['monthly_minor'],3 if body.variant=='trial' else 0,body.terms_version,stamp,json.dumps(disclosure,sort_keys=True),stamp,stamp))
 # CREATING is committed before any remote POST; uncertain creates never retry.
 uncertain=False
 try:
  creem.validate_product(creem.get_product(product['product_id'],mode=mode),selected,body.variant,mode)
  if not customer:
   customer_body={'email':ctx.actor,'external_id':org,'metadata':{'planebyte_workspace':org}}
   if resolved_name:customer_body['name']=resolved_name
   uncertain=True
   created=creem.object_mode(creem.request('POST','/customers',mode=mode,body=customer_body),mode)
   customer_id=creem.identifier(created.get('id'),'cust_')
   if created.get('external_id')!=org or created.get('email','').lower()!=ctx.actor:raise creem.Rejected('Provider customer mapping does not match.')
   with db_session() as c:
    lock(c,org)
    existing=c.execute("SELECT organization_id FROM subscription_customers WHERE provider='creem' AND environment=? AND customer_id=?",(mode,customer_id)).fetchone()
    if existing and existing['organization_id']!=org:raise creem.Rejected('Provider customer is already assigned to another workspace; billing review is required.')
    c.execute("INSERT INTO subscription_customers(provider,environment,organization_id,customer_id,created_at) VALUES('creem',?,?,?,?)",(mode,org,customer_id,now()))
    c.execute('UPDATE subscription_checkouts SET customer_id=? WHERE id=? AND organization_id=?',(customer_id,key,org))
   uncertain=False
  else:
   customer_id=customer['customer_id']
   identity=creem.object_mode(creem.get_customer(customer_id,mode=mode),mode)
   if identity.get('id')!=customer_id or identity.get('external_id')!=org or identity.get('email','').lower()!=ctx.actor:raise creem.Rejected('Existing customer attribution requires billing review.')
   if body.customer_name and resolved_name:
    try:creem.request('PATCH','/customers/'+creem.identifier(customer_id,'cust_'),mode=mode,body={'name':resolved_name})
    except (creem.Unavailable,creem.Rejected):pass
  with db_session() as c:
   onb=c.execute('SELECT status FROM organization_onboarding WHERE organization_id=?',(org,)).fetchone()
   onboarded=bool(onb and onb['status']=='COMPLETED')
  creem.verify_replacement_customer(customer_id,mode,slot['provider_id'] if slot else None)
  success_url='https://app.planebyte.com/settings?category=billing&tab=overview&payment=returned' if onboarded else 'https://app.planebyte.com/onboarding?payment=returned'
  uncertain=True
  checkout=creem.object_mode(creem.request('POST','/checkouts',mode=mode,body={'product_id':product['product_id'],'request_id':key,'units':1,'customer':{'id':customer_id},'success_url':success_url,'metadata':{'planebyte_checkout':key,'planebyte_workspace':org,'planebyte_policy':access.POLICY}}),mode)
  checkout_id=creem.identifier(checkout.get('id'),'ch_');url=creem.hosted_url(checkout.get('checkout_url'))
  # Persist a known provider ID before further reads. Ambiguous creates can be
  # reconciled without repeating the non-idempotent POST.
  with db_session() as c:
   c.execute("UPDATE subscription_checkouts SET provider_checkout_id=?,checkout_url=?,updated_at=? WHERE id=? AND organization_id=? AND status='CREATING'",(checkout_id,url,now(),key,org))
  verified=creem.object_mode(creem.get_checkout(checkout_id,mode=mode),mode)
  expected={'planebyte_checkout':key,'planebyte_workspace':org,'planebyte_policy':access.POLICY}
  from app.billing.subscription_sync import ref
  if verified.get('id')!=checkout_id or verified.get('request_id')!=key or ref(verified.get('product'))!=product['product_id'] or any((verified.get('metadata') or {}).get(k)!=v for k,v in expected.items()):raise creem.Rejected('Provider checkout mapping does not match.')
  if checkout.get('request_id') not in (None,key):raise creem.Rejected('Provider checkout mapping does not match.')
 except (creem.Unavailable,creem.Rejected) as error:
  import logging
  logging.getLogger(__name__).warning('Subscription checkout unconfirmed (%s)',type(error).__name__)
  with db_session() as c:c.execute("UPDATE subscription_checkouts SET status=?,updated_at=? WHERE id=? AND organization_id=? AND status='CREATING'",('REVIEW' if uncertain else 'CANCELLED',now(),key,org))
  if not uncertain:raise HTTPException(502,'Creem could not verify billing details. No checkout was created. Review the plan and try again.') from None
  raise HTTPException(502,'Checkout could not be confirmed. The saved request requires reconciliation; no access was granted.') from None
 with db_session() as c:
  c.execute("UPDATE subscription_checkouts SET provider_checkout_id=?,checkout_url=?,status='PENDING',updated_at=? WHERE id=? AND organization_id=? AND status='CREATING'",(checkout_id,url,now(),key,org))
 return {'checkout_id':key,'status':'PENDING','checkout_url':url}

def portal():
 with db_session() as c:
  ctx=owner(c);row=c.execute("SELECT customer_id FROM subscription_customers WHERE provider='creem' AND environment=? AND organization_id=?",(get_settings().creem_environment,ctx.organization_id)).fetchone()
  if not row:raise HTTPException(409,'A verified provider customer is required before the billing portal is available.')
  if c.execute("SELECT 1 FROM subscription_contracts WHERE provider='creem' AND environment=? AND customer_id=? AND organization_id<>? LIMIT 1",(get_settings().creem_environment,row['customer_id'],ctx.organization_id)).fetchone():raise HTTPException(409,'This historical provider customer has records in multiple workspaces. Use workspace billing history or contact support for portal access.')
 try:response=creem.request('POST','/customers/billing',body={'customer_id':row['customer_id']});url=creem.hosted_url(response.get('customer_portal_link'))
 except (creem.Unavailable,creem.Rejected):raise HTTPException(502,'The provider billing portal is unavailable. Cancellation remains available here.') from None
 return {'url':url}

def cancel(body):
 with db_session() as c:
  ctx=owner(c);org=ctx.organization_id;lock(c,org)
  row=c.execute('SELECT p.* FROM subscription_contracts p JOIN subscription_workspace_slots w ON w.contract_id=p.id AND w.organization_id=p.organization_id WHERE p.organization_id=? AND p.environment=?',(org,get_settings().creem_environment)).fetchone()
  if not row:raise HTTPException(404,'No subscription exists for this workspace.')
  previous=c.execute('SELECT * FROM subscription_cancellations WHERE organization_id=? AND request_id=?',(org,str(body.request_id))).fetchone()
  if previous:return {'status':previous['status'],'effective_at':previous['effective_at']}
  pending=c.execute("SELECT status,effective_at FROM subscription_cancellations WHERE organization_id=? AND contract_id=? AND status IN ('REQUESTED','REVIEW') ORDER BY created_at DESC LIMIT 1",(org,row['id'])).fetchone()
  if pending:return {'status':pending['status'],'effective_at':pending['effective_at']}
  key=str(uuid.uuid4());stamp=now()
  c.execute("INSERT INTO subscription_cancellations(id,organization_id,contract_id,request_id,status,created_at,updated_at) VALUES(?,?,?,?,'REQUESTED',?,?)",(key,org,row['id'],str(body.request_id),stamp,stamp))
 try:
  creem.request('POST','/subscriptions/'+creem.identifier(row['provider_id'],'sub_')+'/cancel',body={'mode':'scheduled','onExecute':'cancel'})
  from app.billing.subscription_sync import reconcile_subscription
  result=reconcile_subscription(row['provider_id'],row['environment'])
  if result['status'] not in ('scheduled_cancel','canceled'):raise creem.Unavailable('Provider cancellation is not yet confirmed.')
 except (creem.Unavailable,creem.Rejected):
  with db_session() as c:c.execute("UPDATE subscription_cancellations SET status='REVIEW',updated_at=? WHERE id=? AND organization_id=?",(now(),key,org))
  raise HTTPException(502,'Cancellation has not been confirmed by the provider. Refresh subscription status before retrying; no cancellation success is assumed.') from None
 with db_session() as c:
  c.execute("UPDATE subscription_cancellations SET status='CONFIRMED',effective_at=?,updated_at=? WHERE id=? AND organization_id=?",(result['period_end'],now(),key,org))
  try:
   from app.notifications import center
   center.emit(c,org,category='billing',event_type='SUBSCRIPTION_CANCELED',title='Subscription auto-renewal canceled',description=f"Access remains active until {result['period_end'] or 'the end of the current period'}.",priority='high',resource_url='/settings?category=billing&tab=overview',dedupe_key=f"sub-cancel:{key}",recipient_email=ctx.actor)
  except Exception:
   pass
 return {'status':'CONFIRMED','effective_at':result['period_end']}


def refresh_checkout(c,org):
 """Resolve a known hosted checkout without replaying its creation POST."""
 mode=get_settings().creem_environment
 row=c.execute("SELECT * FROM subscription_checkouts WHERE organization_id=? AND environment=? AND status IN ('PENDING','CREATING','REVIEW') ORDER BY created_at DESC LIMIT 1",(org,mode)).fetchone()
 if not row:return
 row=dict(row)
 if not row['provider_checkout_id']:return  # uncertain create: operator/provider review
 c.commit()
 value=creem.object_mode(creem.get_checkout(row['provider_checkout_id'],mode=mode),mode)
 from app.billing.subscription_sync import ref,reconcile_subscription
 metadata=value.get('metadata') or {}
 if value.get('id')!=row['provider_checkout_id'] or value.get('request_id')!=row['id'] or ref(value.get('product'))!=row['product_id'] or metadata.get('planebyte_checkout')!=row['id'] or metadata.get('planebyte_workspace')!=org:raise creem.Rejected('Provider checkout ownership does not match.')
 state=value.get('status')
 if state=='completed':
  reconcile_subscription(creem.identifier(ref(value.get('subscription')),'sub_'),mode,checkout_hint=row['provider_checkout_id'])
 elif state=='expired':
  c.execute("UPDATE subscription_checkouts SET status='EXPIRED',updated_at=? WHERE id=? AND organization_id=? AND status IN ('PENDING','CREATING','REVIEW')",(now(),row['id'],org));c.commit()
 elif state=='pending' and row['checkout_url'] and metadata.get('planebyte_policy')==access.POLICY:
  url=creem.hosted_url(row['checkout_url']);c.execute("UPDATE subscription_checkouts SET status='PENDING',checkout_url=?,updated_at=? WHERE id=? AND organization_id=? AND status IN ('CREATING','REVIEW')",(url,now(),row['id'],org));c.commit()
 # pending/processing remain saved, without entitlement or duplicate checkout.
