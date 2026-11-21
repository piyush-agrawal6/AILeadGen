"""Provider-authoritative reconciliation, safe for duplicate/out-of-order events."""
import json,time,uuid
from datetime import datetime,timezone
from fastapi import HTTPException
from app.billing import creem,commercial,subscription_access as access
from app.database.connection import db_session
from app.database.prospects import now
from app.developer.keys import lock
from app.api.organization import membership_role
from app.notifications.transactional import cipher

def ref(value):return value.get('id') if isinstance(value,dict) else value
def epoch(value):
 try:
  if not isinstance(value,str):raise ValueError()
  d=datetime.fromisoformat(value.replace('Z','+00:00'))
  if d.tzinfo is None:raise ValueError()
  return int(d.timestamp())
 except (ValueError,TypeError):raise creem.Rejected('Provider billing date is invalid.') from None

def reconcile_subscription(provider_id,mode,*,checkout_hint=None):
 sub=creem.object_mode(creem.get_subscription(provider_id,mode=mode),mode)
 if sub.get('id')!=provider_id:raise creem.Rejected('Provider subscription identity differs.')
 customer_id=creem.identifier(ref(sub.get('customer')),'cust_');product_id=creem.identifier(ref(sub.get('product')),'prod_')
 customer=creem.object_mode(creem.get_customer(customer_id,mode=mode),mode)
 with db_session() as c:
  mapping=c.execute("SELECT organization_id FROM subscription_customers WHERE provider='creem' AND environment=? AND customer_id=?",(mode,customer_id)).fetchone()
  if not mapping:raise creem.Rejected('Unattributed provider customer; no access is granted.')
  org=mapping['organization_id']
  prior=c.execute("SELECT * FROM subscription_contracts WHERE provider='creem' AND environment=? AND provider_id=?",(mode,provider_id)).fetchone()
  if prior:checkout=c.execute('SELECT * FROM subscription_checkouts WHERE organization_id=? AND id=?',(org,prior['checkout_id'])).fetchone()
  elif checkout_hint:checkout=c.execute('SELECT * FROM subscription_checkouts WHERE organization_id=? AND provider_checkout_id=?',(org,checkout_hint)).fetchone()
  else:
   matches=c.execute("SELECT * FROM subscription_checkouts WHERE organization_id=? AND provider='creem' AND environment=? AND customer_id=? AND product_id=? AND status IN ('CREATING','PENDING','COMPLETED','REVIEW') ORDER BY created_at DESC LIMIT 2",(org,mode,customer_id,product_id)).fetchall()
   checkout=matches[0] if len(matches)==1 else None
  change=None
  from app.billing.plan_changes import schema_ready
  if prior and checkout and schema_ready(c):
   latest=c.execute('SELECT * FROM subscription_plan_changes WHERE organization_id=? AND environment=? AND contract_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(org,mode,prior['id'])).fetchone()
   if latest and latest['product_id']==product_id:change=latest
   elif latest and latest['status'] in ('CONFIRMED','APPLIED'):raise creem.Rejected('Provider product differs from the last authorized change.')
  if not checkout or checkout['environment']!=mode or checkout['customer_id']!=customer_id or (checkout['product_id']!=product_id and not change) or not checkout['provider_checkout_id']:raise creem.Rejected('No matching server-created checkout exists.')
  checkout=dict(checkout);plan=json.loads(prior['plan_json']) if prior else {**commercial.plan(checkout['plan_code']),'version':commercial.catalog()['version']}
  billing=c.execute('SELECT * FROM subscription_billing_profiles WHERE organization_id=?',(org,)).fetchone()
  from app.config.locations import country
  try:verified_country=country(customer.get('country')).alpha_2
  except Exception:raise creem.Rejected('Provider billing country has not been confirmed.') from None
  if verified_country!=customer.get('country'):raise creem.Rejected('Provider billing country is invalid.')
  if customer.get('id')!=customer_id or customer.get('email','').lower()!=checkout['created_by'] or customer.get('external_id')!=org:raise creem.Rejected('Provider customer ownership differs from the verified workspace.')
  if membership_role(c,checkout['created_by'],org)!='OWNER':raise creem.Rejected('Purchasing workspace owner requires review.')
 remote_checkout=creem.object_mode(creem.get_checkout(checkout['provider_checkout_id'],mode=mode),mode)
 if remote_checkout.get('status')!='completed' or remote_checkout.get('request_id')!=checkout['id'] or ref(remote_checkout.get('subscription'))!=provider_id or ref(remote_checkout.get('customer'))!=customer_id or ref(remote_checkout.get('product'))!=checkout['product_id']:raise creem.Rejected('Checkout completion and subscription mapping are not confirmed.')
 target_plan={**commercial.plan(change['plan_code']),'version':commercial.catalog()['version']} if change else plan
 checked=creem.validate_product(creem.get_product(product_id,mode=mode),target_plan,'paid' if change else checkout['variant'],mode)
 if checked['id']!=product_id:raise creem.Rejected('Provider product identity differs.')
 if sub.get('collection_method')!='charge_automatically':raise creem.Rejected('Provider recurring authorization is not confirmed.')
 state=sub.get('status')
 if state not in ('active','trialing','scheduled_cancel','canceled','expired','paused','past_due','unpaid'):raise creem.Rejected('Unsupported provider subscription state.')
 start=epoch(sub.get('current_period_start_date'));end=epoch(sub.get('current_period_end_date'));updated=epoch(sub.get('updated_at'))
 if end<=start:raise creem.Rejected('Provider billing period is invalid.')
 if change and start>=change['effective_at']:plan=target_plan
 trial=checkout['variant']=='trial' and state in ('trialing','scheduled_cancel','canceled') and end-start==access.TRIAL_SECONDS
 if state=='trialing' and not trial:raise creem.Rejected('Provider trial is not the approved 72-hour card trial.')
 transaction=None
 if not trial and state in ('active','scheduled_cancel','canceled'):
  tid=creem.identifier(sub.get('last_transaction_id'),'tran_');transaction=creem.object_mode(creem.get_transaction(tid,mode=mode),mode)
  amount=transaction.get('amount_paid');status=transaction.get('status')
  if ref(transaction.get('subscription'))!=provider_id or ref(transaction.get('customer'))!=customer_id or transaction.get('currency')!='USD' or type(amount) is not int or amount!=plan['monthly_minor'] or status not in ('paid','refunded','partialRefund','chargedBack'):raise creem.Rejected('Independent payment verification did not match the approved plan.')
  # Transaction periods are epoch seconds in the official API. No local
  # 30-day approximation replaces a provider's actual calendar-month period.
  if transaction.get('period_start')!=start or transaction.get('period_end')!=end:raise creem.Rejected('Payment does not cover the provider billing period.')
  if status in ('refunded','chargedBack'):state='refunded' if status=='refunded' else 'disputed'
 with db_session() as c:
  lock(c,org)
  prior=c.execute("SELECT * FROM subscription_contracts WHERE provider='creem' AND environment=? AND provider_id=?",(mode,provider_id)).fetchone()
  if prior and prior['provider_updated_at'] is not None and updated<prior['provider_updated_at']:return dict(prior)
  slot=c.execute('SELECT contract_id FROM subscription_workspace_slots WHERE organization_id=? AND environment=?',(org,mode)).fetchone()
  key=prior['id'] if prior else str(uuid.uuid4())
  if slot and slot['contract_id']!=key:
   if prior:return dict(prior)  # A delayed event for a retired contract cannot reclaim the slot.
   other=c.execute('SELECT p.status,p.period_end,ch.created_at checkout_created FROM subscription_contracts p JOIN subscription_checkouts ch ON ch.organization_id=p.organization_id AND ch.id=p.checkout_id WHERE p.organization_id=? AND p.id=?',(org,slot['contract_id'])).fetchone()
   if not other or other['status']!='canceled' or not other['period_end'] or other['period_end']>int(time.time()) or checkout['created_at']<other['checkout_created']:raise creem.Rejected('A different subscription owns this workspace period.')
  stamp=now()
  c.execute("INSERT INTO subscription_billing_profiles(organization_id,country,status,verification_source,verification_reference,verified_at,updated_at) VALUES(?,?,'VERIFIED','CREEM_API',?,?,?) ON CONFLICT(organization_id) DO UPDATE SET country=excluded.country,status=excluded.status,verification_source=excluded.verification_source,verification_reference=excluded.verification_reference,verified_at=excluded.verified_at,updated_at=excluded.updated_at",(org,verified_country,customer_id,stamp,stamp))
  cancel=state in ('scheduled_cancel','canceled');evidence={'subscription_id':provider_id,'checkout_id':remote_checkout['id'],'customer_id':customer_id,'product_id':product_id,'provider_status':state,'collection_method':sub['collection_method'],'verified_country':verified_country,'provider_updated_at':updated,'card_verification_basis':'Creem hosted recurring checkout with provider-confirmed trialing state' if trial else 'Independent paid transaction'}
  if not prior:
   c.execute('INSERT INTO subscription_contracts(id,organization_id,created_by,provider,environment,provider_id,customer_id,checkout_id,plan_code,plan_json,status,recurring_authorized,period_start,period_end,trial_start,trial_end,next_charge_at,cancel_at,cancel_confirmed_at,provider_updated_at,verified_at,evidence_json,created_at,updated_at) VALUES(?,?,?,\'creem\',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,org,checkout['created_by'],mode,provider_id,customer_id,checkout['id'],checkout['plan_code'],json.dumps(plan,sort_keys=True),state,1,start,end,start if trial else None,end if trial else None,epoch(sub['next_transaction_date']) if sub.get('next_transaction_date') and not cancel else None,end if cancel else None,stamp if cancel else None,updated,stamp,json.dumps(evidence,sort_keys=True),stamp,stamp))
  else:
   c.execute('UPDATE subscription_contracts SET status=?,recurring_authorized=1,period_start=?,period_end=?,next_charge_at=?,cancel_at=?,cancel_confirmed_at=?,provider_updated_at=?,verified_at=?,evidence_json=?,updated_at=? WHERE id=? AND organization_id=?',(state,start,end,epoch(sub['next_transaction_date']) if sub.get('next_transaction_date') and not cancel else None,end if cancel else None,stamp if cancel else prior['cancel_confirmed_at'],updated,stamp,json.dumps(evidence,sort_keys=True),stamp,key,org))
  if trial:
   from app.accounts.policy import company_domain
   domain=company_domain(checkout['created_by'])
   used=c.execute('SELECT * FROM subscription_trials WHERE user_id=? OR company_domain=?',(checkout['created_by'],domain)).fetchall()
   if used and (len(used)!=1 or used[0]['contract_id']!=key or used[0]['starts_at']!=start or used[0]['ends_at']!=end):raise creem.Rejected('Trial identity has already been used.')
   if c.execute('SELECT 1 FROM launch_trial_claims WHERE user_id=? OR company_domain=?',(checkout['created_by'],domain)).fetchone():raise creem.Rejected('A previous trial already consumed eligibility.')
   if not used:c.execute('INSERT INTO subscription_trials(id,user_id,company_domain,organization_id,contract_id,policy_version,starts_at,ends_at) VALUES(?,?,?,?,?,?,?,?)',(str(uuid.uuid4()),checkout['created_by'],domain,org,key,access.POLICY,start,end))
  if transaction:
   if change and transaction['status']=='paid' and start>=change['effective_at']:
    c.execute('UPDATE subscription_contracts SET plan_code=?,plan_json=? WHERE id=? AND organization_id=?',(change['plan_code'],json.dumps(plan,sort_keys=True),key,org));c.execute("UPDATE subscription_plan_changes SET status='APPLIED' WHERE id=?",(change['id'],))
   elif change:c.execute("UPDATE subscription_plan_changes SET status='CONFIRMED' WHERE id=? AND status IN ('REQUESTED','REVIEW')",(change['id'],))
   previous=c.execute("SELECT * FROM subscription_payments WHERE provider='creem' AND environment=? AND payment_id=?",(mode,transaction['id'])).fetchone()
   if previous and any(previous[k]!=v for k,v in {'organization_id':org,'contract_id':key,'amount_minor':transaction['amount_paid'],'currency':'USD','period_start':start,'period_end':end}.items()):raise creem.Rejected('Payment identity conflicts with its original attribution.')
   c.execute("INSERT INTO subscription_payments(provider,environment,payment_id,organization_id,contract_id,amount_minor,currency,status,period_start,period_end,evidence_json,recorded_at) VALUES('creem',?,?,?,?,?,'USD',?,?,?,?,?) ON CONFLICT(provider,environment,payment_id) DO UPDATE SET status=excluded.status,evidence_json=excluded.evidence_json",(mode,transaction['id'],org,key,transaction['amount_paid'],transaction['status'],start,end,json.dumps(transaction,sort_keys=True),stamp))
  c.execute('INSERT INTO subscription_workspace_slots(organization_id,environment,contract_id) VALUES(?,?,?) ON CONFLICT(organization_id,environment) DO UPDATE SET contract_id=excluded.contract_id',(org,mode,key))
  c.execute("UPDATE subscription_checkouts SET status='COMPLETED',checkout_url=NULL,updated_at=? WHERE id=? AND organization_id=?",(stamp,checkout['id'],org))
  from app.notifications import transactional as mail
  from app.config.settings import get_settings
  if get_settings().transactional_mail_enabled and mail.configured():
   messages={'trialing':'Your 72-hour card trial is provider-confirmed. Unless canceled, '+plan['name']+' renews at USD '+f"{plan['monthly_minor']/100:.2f}"+' per month beginning '+iso_date(end)+'.',
    'active':'Your '+plan['name']+' subscription payment is verified for '+iso_date(start)+' through '+iso_date(end)+'. Monthly renewal amount: USD '+f"{plan['monthly_minor']/100:.2f}"+'.',
    'scheduled_cancel':'Automatic renewal is canceled with the provider. Your confirmed access continues until '+iso_date(end)+'. No later renewal charge is authorized by this subscription.',
    'canceled':'The provider confirms cancellation. Review your effective access end in Billing.',
    'past_due':'Your subscription payment is past due. Product access is restricted. Review your payment method and recovery options in the secure billing portal.',
    'unpaid':'The provider reports an unpaid subscription. Product access is restricted; review billing for recovery options.',
    'refunded':'The provider confirms a refund for this payment. Its associated subscription access is restricted.',
    'disputed':'A provider payment dispute requires review. Associated product access is restricted.'}
   if state in messages and (not prior or prior['status']!=state or prior['period_start']!=start):
    mail.queue(c,checkout['created_by'],'SUBSCRIPTION_STATUS',key,{'summary':messages[state]},dedupe_key='subscription:'+key+':'+state+':'+str(start),expires_at=int(time.time())+86400,organization_id=org)
  return dict(c.execute('SELECT * FROM subscription_contracts WHERE id=? AND organization_id=?',(key,org)).fetchone())

def iso_date(stamp):return datetime.fromtimestamp(stamp,timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

def process_event(event_id,mode):
 token=str(uuid.uuid4());stamp=int(time.time())
 with db_session() as c:
  changed=c.execute("UPDATE subscription_provider_events SET status='PROCESSING',attempts=attempts+1,lease_token=?,lease_until=? WHERE provider='creem' AND environment=? AND event_id=? AND status IN ('PENDING','REVIEW','PROCESSING') AND attempts<5 AND (lease_until IS NULL OR lease_until<?)",(token,stamp+120,mode,event_id,stamp)).rowcount
  if not changed:return
  row=dict(c.execute("SELECT * FROM subscription_provider_events WHERE provider='creem' AND environment=? AND event_id=?",(mode,event_id)).fetchone())
 try:
  data=json.loads(cipher().decrypt(row['payload_encrypted'].encode()));obj=data['object'];kind=row['event_type'];hint=None
  if kind=='checkout.completed':
   hint=obj.get('id');provider_id=ref(obj.get('subscription'))
  elif kind.startswith('subscription.'):provider_id=obj.get('id')
  elif kind in ('refund.created','dispute.created'):
   provider_id=ref(obj.get('subscription'))
   if not provider_id and ref(obj.get('transaction')):
    transaction=creem.get_transaction(ref(obj['transaction']),mode=mode);provider_id=ref(transaction.get('subscription'))
  else:provider_id=None
  if not provider_id:raise creem.Rejected('Event has no attributable subscription.')
  result=reconcile_subscription(provider_id,mode,checkout_hint=hint)
  if kind in ('refund.created','dispute.created'):
   with db_session() as c:
    lock(c,result['organization_id'])
    c.execute('INSERT INTO subscription_adjustments(provider,environment,adjustment_id,organization_id,contract_id,payment_id,kind,status,amount_minor,currency,evidence_json,recorded_at) VALUES(\'creem\',?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(provider,environment,adjustment_id) DO NOTHING',(mode,obj['id'],result['organization_id'],result['id'],ref(obj.get('transaction')) or '',kind.split('.')[0],obj.get('status','REVIEW'),obj.get('refund_amount'),obj.get('refund_currency'),json.dumps({'event_id':event_id,'provider_object':obj},sort_keys=True),now()))
    if kind=='dispute.created':c.execute("UPDATE subscription_contracts SET status='disputed',updated_at=? WHERE id=? AND organization_id=?",(now(),result['id'],result['organization_id']))
  state,error='PROCESSED',None
 except (creem.Unavailable,creem.Rejected,HTTPException,ValueError,KeyError):state,error='REVIEW','PROVIDER_RECONCILIATION_REQUIRED'
 with db_session() as c:
  c.execute("UPDATE subscription_provider_events SET status=?,error_code=?,processed_at=?,lease_token=NULL,lease_until=NULL WHERE provider='creem' AND environment=? AND event_id=? AND lease_token=?",(state,error,now(),mode,event_id,token))
