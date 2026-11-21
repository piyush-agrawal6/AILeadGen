"""One-time PayU orders; immutable quotes and independently verified access.

No recurring mandate. No exchange-rate conversion. No tax ID is required.
Official contract: docs.payu.in/v2/reference/collect-payment-api-payu-hosted-v2-_payment
Production activation still requires merchant USD evidence, legal approval and
separate explicit permission for a controlled real-money transaction.
"""
import hashlib,json,time,uuid
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
from fastapi import HTTPException
from app.api.organization import membership_role
from app.billing import access_periods,commercial,payu,payu_v2
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.developer.keys import lock
from app.platform.context import current
from app.notifications.transactional import cipher

POLICY='2026-11-15.fixed-term.1'
class BillingAddress(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    first_name:str=Field(min_length=1,max_length=60)
    last_name:str=Field(min_length=1,max_length=60)
    address1:str=Field(min_length=3,max_length=200)
    city:str=Field(min_length=1,max_length=100)
    state:str=Field(min_length=1,max_length=100)
    country:str=Field(pattern=r'^[A-Z]{2}$')
    postal_code:str=Field(min_length=2,max_length=16)
    phone:str=Field(pattern=r'^\+?[0-9]{7,15}$')
    @field_validator('first_name','last_name','address1','city','state','postal_code')
    @classmethod
    def bounded_text(cls,value):
        if any(ord(ch)<32 or ch=='|' for ch in value):raise ValueError('Enter billing details without control characters.')
        return value
class Purchase(BaseModel):
    model_config=ConfigDict(extra='forbid')
    plan_code:Literal['starter','growth','scale']
    interval:Literal['monthly','yearly']='monthly'
    billing:BillingAddress
    request_id:uuid.UUID
    terms_version:str=Field(min_length=1,max_length=100)
    accepted_terms:Literal[True]
class RefundRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:uuid.UUID


def manager(c,org=None):
    ctx=current();org=org or ctx.organization_id
    if org!=ctx.organization_id or membership_role(c,ctx.actor,org)!='OWNER':raise HTTPException(403,'Only the active workspace owner can manage payments.')
    return ctx

def test_allowed(org):
    s=get_settings()
    return s.payu_mode=='live' or org in {v.strip() for v in s.billing_test_workspaces.split(',') if v.strip()}

def capabilities():
    s=get_settings()
    try:proof=json.loads(s.payu_merchant_capabilities_json)
    except ValueError:proof={}
    verified=proof.get(s.payu_mode,{}) if isinstance(proof,dict) else {}
    return bool(isinstance(verified,dict) and verified.get('provider')=='payu' and verified.get('hosted_v2_verified') is True and 'USD' in verified.get('charge_currencies',[]) and verified.get('verification_reference') and verified.get('merchant_key_sha256')==hashlib.sha256(s.payu_merchant_key.encode()).hexdigest())

def blockers():
    s=get_settings();result=[]
    if not s.fixed_term_billing_enabled or not s.heysow_access_periods_enabled:result.append('Fixed-term payment access is not enabled.')
    if not capabilities():result.append('PayU account-specific USD hosted-checkout capability is not verified.')
    if not s.payu_currency_approved or s.payu_charge_currency!='USD':result.append('USD charging is not configured for this deployment.')
    if not s.billing_terms_version:result.append('The one-time purchase and digital fulfillment terms await publication approval.')
    if not s.payu_one_time_checkout_enabled:result.append('Public payment initiation is closed.')
    from app.notifications import transactional as mail
    if not s.transactional_mail_enabled or not mail.configured():result.append('Payment email delivery is not yet available.')
    return result

def price(plan_code,interval):
    plan=commercial.plan(plan_code)
    if plan_code=='enterprise':raise HTTPException(409,'Contact PlaneByte for a reviewed custom agreement.')
    if interval=='monthly':return plan['monthly_minor']
    if interval!='yearly':raise HTTPException(422,'Choose a supported billing interval.')
    try:approved=json.loads(get_settings().payu_yearly_prices_json)
    except ValueError:approved={}
    # Annual pricing and quota cadence must both be explicit before activation.
    amount=approved.get('prices',{}).get(plan_code)
    if approved.get('approved') is not True or approved.get('currency')!='USD' or not approved.get('version') or approved.get('usage_cadence')!='annual' or type(amount) is not int or amount<=0:
        raise HTTPException(409,'Yearly pricing and allowance cadence await approval. No payment has been initiated.')
    return amount

def quote(plan_code,interval):
    subtotal=price(plan_code,interval)
    # Owner-confirmed unregistered status: never add GST or invent a GSTIN.
    # Other tax rules cannot silently alter the accepted quote. Any later tax
    # policy requires a versioned owner-reviewed configuration and fresh consent.
    return {'plan_code':plan_code,'interval':interval,'currency':'USD','subtotal_minor':subtotal,'tax_minor':0,'total_minor':subtotal,'tax':{'version':'2026-11-15.owner-no-gst','gst_registered':False,'gst_collected':False,'label':'No GST charged'},'policy_version':POLICY,'automatic_renewal':False,'trial_replaced_on_payment':True,'duration':'30 days' if interval=='monthly' else 'One calendar year','terms_version':get_settings().billing_terms_version}

def public(row):
    result={key:row[key] for key in ('id','provider','mode','plan_code','interval','terms_version','currency','subtotal_minor','tax_minor','total_minor','status','period_start','period_end','verified_at','created_at')}
    result['automatic_renewal']=False
    result['tax']=json.loads(row['tax_json'])
    return result

def owned(c,key):
    ctx=manager(c)
    row=c.execute('SELECT * FROM payu_access_orders WHERE id=? AND organization_id=?',(key,ctx.organization_id)).fetchone()
    if not row:raise HTTPException(404,'Payment order not found in this workspace.')
    return dict(row)

def history(c):
    ctx=manager(c)
    if not (get_settings().fixed_term_billing_enabled or access_periods.enabled()):return {'items':[],'checkout_enabled':False,'blockers':blockers()}
    return {'mode':get_settings().payu_mode,'items':[public(r) for r in c.execute('SELECT * FROM payu_access_orders WHERE organization_id=? ORDER BY created_at DESC,id DESC LIMIT 50',(ctx.organization_id,)).fetchall()],'refunds':[dict(r) for r in c.execute('SELECT order_id,amount_minor,currency,status,updated_at FROM payu_refund_observations WHERE organization_id=? ORDER BY updated_at DESC LIMIT 100',(ctx.organization_id,)).fetchall()],'refund_requests':[dict(r) for r in c.execute('SELECT id,order_id,status,created_at FROM payu_access_refunds WHERE organization_id=? ORDER BY created_at DESC LIMIT 50',(ctx.organization_id,)).fetchall()],'checkout_enabled':not blockers() and test_allowed(ctx.organization_id),'blockers':blockers(),'yearly_prices_approved':False,'renewal':'Manual renewal only; no automatic charges.','upgrade_policy':'Plan changes take effect after existing paid access expires. No early upgrades, proration or unused-time credits.'}

def _guard(org):
    if blockers():raise HTTPException(503,'One-time checkout is not yet available. No payment has been initiated.')
    if not test_allowed(org):raise HTTPException(403,'PayU Test Mode is restricted to approved workspaces.')
    payu.credentials()

def create(body):
    from app.billing import accounts
    s=get_settings()
    with db_session() as c:
        ctx=manager(c)
        accounts.guard_purchase(c,ctx.organization_id,ctx.actor)
        from app.billing.subscription_access import required
        if required(c,ctx.organization_id):
            raise HTTPException(409,'Use Step 5 with verified provider routing. New India purchases require approved INR pricing and PayU merchant acceptance; the historical USD purchase path cannot bypass those checks.')
        _guard(ctx.organization_id)
        if body.terms_version!=s.billing_terms_version:raise HTTPException(409,'Review the current purchase terms before continuing.')
        selected=quote(body.plan_code,body.interval);digest=hashlib.sha256(json.dumps(body.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()
        lock(c,ctx.organization_id)
        previous=c.execute('SELECT * FROM payu_access_orders WHERE organization_id=? AND request_id=?',(ctx.organization_id,str(body.request_id))).fetchone()
        if previous:
            if previous['request_fingerprint']!=digest:raise HTTPException(409,'Use a new payment request after changing the purchase details.')
            return {'order':public(previous),'checkout_url':previous['checkout_url'] if previous['status']=='PENDING' and previous['expires_at']>int(time.time()) else None}
        if c.execute("SELECT 1 FROM payu_access_orders WHERE organization_id=? AND status IN ('CREATING','PENDING','REVIEW')",(ctx.organization_id,)).fetchone():raise HTTPException(409,'Reconcile the existing pending purchase before creating another order.')
        from app.billing.contracts import active
        existing=active(c,ctx.organization_id)
        if existing and 'source_kind' not in existing:raise HTTPException(409,'An existing recurring contract requires a reviewed transition before a fixed-term purchase.')
        access_periods.next_period(c,ctx.organization_id,body.plan_code,body.interval)
        key=str(uuid.uuid4());txnid='pb'+uuid.uuid4().hex[:23];stamp=now();plan=commercial.plan(body.plan_code)
        snapshot={**plan,'version':commercial.catalog()['version'],'interval':body.interval,'automatic_renewal':False}
        expected={'txnid':txnid,'amount':f"{Decimal(selected['total_minor'])/100:.2f}",'currency':'USD','email':ctx.actor,'firstname':body.billing.first_name,'productinfo':'PlaneByte Intent Radar '+body.plan_code+' '+body.interval,'udf1':ctx.organization_id,'udf2':key,'udf3':body.plan_code,'udf4':body.interval,'udf5':POLICY}
        encrypted=cipher().encrypt(json.dumps(body.billing.model_dump()).encode()).decode()
        c.execute("INSERT INTO payu_access_orders(id,organization_id,created_by,mode,txn_id,request_id,request_fingerprint,plan_code,interval,plan_json,catalog_version,policy_version,terms_version,terms_accepted_at,currency,subtotal_minor,tax_minor,total_minor,tax_json,expected_json,billing_encrypted,status,creation_started_at,expires_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'CREATING',?,?,?,?)",(key,ctx.organization_id,ctx.actor,s.payu_mode,txnid,str(body.request_id),digest,body.plan_code,body.interval,json.dumps(snapshot,sort_keys=True),snapshot['version'],POLICY,body.terms_version,stamp,'USD',selected['subtotal_minor'],0,selected['total_minor'],json.dumps(selected['tax']),json.dumps(expected),encrypted,stamp,int(time.time())+1800,stamp,stamp))
    # Durable CREATING state precedes provider I/O. An uncertain POST is never
    # repeated, even for an identical request ID; verification must reconcile it.
    payload={'accountId':s.payu_merchant_key,'txnId':txnid,'currency':'USD','order':{'productInfo':expected['productinfo'],'paymentChargeSpecification':{'price':selected['total_minor']/100},'userDefinedFields':{k:expected[k] for k in payu.UDFS}},'billingDetails':{'firstName':body.billing.first_name,'lastName':body.billing.last_name,'email':ctx.actor,'phone':body.billing.phone,'address1':body.billing.address1,'city':body.billing.city,'state':body.billing.state,'country':body.billing.country,'zipCode':body.billing.postal_code},'callBackActions':{k:'https://app.planebyte.com/api/payments/payu-return' for k in ('successAction','failureAction','cancelAction')},'additionalInfo':{'txnFlow':'nonseamless'}}
    try:checkout=payu_v2.checkout_url(payu_v2.request('create',payload))
    except (payu.PayURejected,payu.PayUUnavailable):
        with db_session() as c:c.execute("UPDATE payu_access_orders SET status='REVIEW',updated_at=? WHERE id=? AND mode=? AND status='CREATING'",(now(),key,s.payu_mode))
        raise HTTPException(502,'PayU checkout could not be confirmed. Reconcile this order before trying another purchase; no access is assumed.') from None
    with db_session() as c:
        c.execute("UPDATE payu_access_orders SET status='PENDING',checkout_url=?,updated_at=? WHERE id=? AND mode=? AND status='CREATING'",(checkout,now(),key,s.payu_mode))
        return {'order':public(c.execute('SELECT * FROM payu_access_orders WHERE id=?',(key,)).fetchone()),'checkout_url':checkout}


def _fulfill(c,key,verified):
    row=c.execute('SELECT * FROM payu_access_orders WHERE id=?',(key,)).fetchone()
    if not row:raise HTTPException(404,'Payment order not found.')
    org=row['organization_id'];lock(c,org)
    row=c.execute('SELECT * FROM payu_access_orders WHERE id=? AND organization_id=?',(key,org)).fetchone()
    if row['mode']!=get_settings().payu_mode or not test_allowed(org):raise HTTPException(409,'Payment environment differs; no access was granted.')
    if row['status']=='PAID':
        if row['provider_payment_id']!=verified['provider_payment_id']:raise HTTPException(409,'Payment reference conflicts with the recorded purchase.')
        return public(row)
    if row['status'] not in ('CREATING','PENDING','REVIEW','FAILED','CANCELLED','EXPIRED'):raise HTTPException(409,'This purchase requires payment review.')
    if membership_role(c,row['created_by'],org)!='OWNER':raise HTTPException(409,'The purchasing account requires administrator review before access can be granted.')
    if not access_periods.enabled():raise HTTPException(503,'Payment access enforcement is unavailable; no access was granted.')
    if c.execute('SELECT 1 FROM payu_access_orders WHERE mode=? AND provider_payment_id=? AND id<>?',(row['mode'],verified['provider_payment_id'],key)).fetchone():raise HTTPException(409,'This provider payment is already attributed to another purchase.')
    start,end=access_periods.next_period(c,org,row['plan_code'],row['interval']);stamp=now()
    c.execute('INSERT INTO customer_workspace_access(organization_id,registered_by,created_at) VALUES(?,?,?) ON CONFLICT(organization_id) DO NOTHING',(org,row['created_by'],stamp))
    c.execute("UPDATE access_periods SET status='REPLACED',updated_at=? WHERE organization_id=? AND source_kind='TRIAL' AND status='ACTIVE'",(stamp,org))
    c.execute("INSERT INTO access_periods(id,organization_id,source_kind,source_id,plan_code,plan_json,status,paid_start,paid_end,verified_at,mode,created_at,updated_at) VALUES(?,?,'PAYMENT',?,?,?,'ACTIVE',?,?,?,?,?,?)",(str(uuid.uuid4()),org,key,row['plan_code'],row['plan_json'],start,end,stamp,row['mode'],stamp,stamp))
    c.execute("UPDATE payu_access_orders SET status='PAID',provider_payment_id=?,verified_json=?,period_start=?,period_end=?,verified_at=?,checkout_url=NULL,updated_at=? WHERE id=? AND organization_id=?",(verified['provider_payment_id'],json.dumps(verified,sort_keys=True),start,end,stamp,stamp,key,org))
    c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),row['created_by'],'FIXED_TERM_PAYMENT_VERIFIED','payment:'+key,'SUCCESS',org,stamp))
    from app.notifications import transactional as mail
    if get_settings().transactional_mail_enabled and mail.configured():
        mail.queue(c,row['created_by'],'PAYMENT_CONFIRMED',key,{'summary':'Your one-time '+row['plan_code']+' purchase of USD '+f"{Decimal(row['total_minor'])/100:.2f}"+' is verified. No GST was collected. Access starts and expires on the dates shown in your workspace billing history.'},dedupe_key='payment-confirmed:'+key,expires_at=int(time.time())+86400,organization_id=org)
    return public(c.execute('SELECT * FROM payu_access_orders WHERE id=?',(key,)).fetchone())


def reconcile(key):
    with db_session() as c:
        row=owned(c,key)
        if row['mode']!=get_settings().payu_mode or not test_allowed(row['organization_id']):raise HTTPException(403,'Payment environment differs.')
        from app.accounts.security import limited
        lock(c,row['organization_id'])
        if limited(c,'payment-verify',row['organization_id'],6,60):raise HTTPException(429,'Please wait before checking payment status again.')
    return reconcile_refunds(row) if row['status'] in ('PAID','REFUNDED') else verify_order(row)


def reconcile_refunds(row):
    """Observe independently issued refunds; this cannot move money.

    A missing currency or partial refund requires review. Only a full matching
    refund revokes that order's access; other purchases and saved data survive.
    """
    try:observations=payu.refund_actions(row['provider_payment_id'])
    except (payu.PayURejected,payu.PayUUnavailable):raise HTTPException(502,'Refund status could not be independently established. Existing records are retained; no refund success is assumed.') from None
    with db_session() as c:
        lock(c,row['organization_id']);saved=owned(c,row['id'])
        if saved['mode']!=get_settings().payu_mode or not test_allowed(saved['organization_id']) or saved['status'] not in ('PAID','REFUNDED') or saved['provider_payment_id']!=row['provider_payment_id']:raise HTTPException(409,'Payment attribution changed; refund review is required.')
        stamp=now()
        for item in observations:
            existing=c.execute('SELECT * FROM payu_refund_observations WHERE mode=? AND provider_refund_id=?',(saved['mode'],item['provider_refund_id'])).fetchone()
            if existing and (existing['order_id']!=saved['id'] or existing['provider_payment_id']!=saved['provider_payment_id'] or existing['amount_minor']!=item['amount_minor'] or existing['currency'] is not None and existing['currency']!=item['currency']):raise HTTPException(409,'Refund reference conflicts with the recorded payment.')
            state=item['status'] if item['currency']==saved['currency'] else 'REVIEW'
            if existing and existing['status']=='SUCCEEDED':continue
            c.execute('INSERT INTO payu_refund_observations(mode,provider_refund_id,order_id,organization_id,provider_payment_id,amount_minor,currency,status,verified_json,first_seen_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(mode,provider_refund_id) DO UPDATE SET currency=excluded.currency,status=excluded.status,verified_json=excluded.verified_json,updated_at=excluded.updated_at',(saved['mode'],item['provider_refund_id'],saved['id'],saved['organization_id'],saved['provider_payment_id'],item['amount_minor'],item['currency'],state,json.dumps(item,sort_keys=True),stamp,stamp))
        total=c.execute("SELECT COALESCE(SUM(amount_minor),0) FROM payu_refund_observations WHERE order_id=? AND organization_id=? AND mode=? AND status='SUCCEEDED' AND currency=?",(saved['id'],saved['organization_id'],saved['mode'],saved['currency'])).fetchone()[0]
        full=total==saved['total_minor']
        if full and saved['status']=='PAID':
            c.execute("UPDATE payu_access_orders SET status='REFUNDED',updated_at=? WHERE id=? AND organization_id=? AND status='PAID'",(stamp,saved['id'],saved['organization_id']))
            c.execute("UPDATE access_periods SET status='REVOKED',updated_at=? WHERE organization_id=? AND source_kind='PAYMENT' AND source_id=?",(stamp,saved['organization_id'],saved['id']))
            c.execute("UPDATE payu_access_refunds SET status='SUCCEEDED',updated_at=? WHERE organization_id=? AND order_id=? AND status IN ('REQUESTED','REVIEW','PENDING')",(stamp,saved['organization_id'],saved['id']))
            c.execute('INSERT INTO audit_log(id,actor,action,entity,result,organization_id,created_at) VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),current().actor,'FIXED_TERM_REFUND_VERIFIED','payment:'+saved['id'],'SUCCESS',saved['organization_id'],stamp))
        review=bool(total and not full) or bool(c.execute("SELECT 1 FROM payu_refund_observations WHERE order_id=? AND organization_id=? AND status='REVIEW'",(saved['id'],saved['organization_id'])).fetchone())
        return {'order':public(c.execute('SELECT * FROM payu_access_orders WHERE id=?',(saved['id'],)).fetchone()),'payment_verified':True,'full_refund_verified':full,'refund_review_required':review,'refund_initiated':False}


def verify_order(row):
    if row['status']=='PAID':return {'order':public(row),'payment_verified':True}
    if row['mode']!=get_settings().payu_mode:raise HTTPException(409,'Payment environment differs.')
    try:
        item=payu_v2.verify(row['txn_id'])
        if item.get('status') in ('pending','in_progress'):
            return {'order':public(row),'payment_pending':True}
        if item.get('status') in ('failure','failed'):
            # An independently verified failure can close an order; posted
            # callback status alone never changes payment/access state.
            with db_session() as c:c.execute("UPDATE payu_access_orders SET status='FAILED',checkout_url=NULL,updated_at=? WHERE id=? AND mode=? AND status IN ('CREATING','PENDING','REVIEW')",(now(),row['id'],row['mode']))
            return {'order_id':row['id'],'status':'FAILED','access_activated':False}
        verified=payu_v2.validate(item,json.loads(row['expected_json']))
    except (payu.PayURejected,payu.PayUUnavailable):raise HTTPException(502,'PayU payment verification did not establish a captured payment with matching amount, currency and purchase details. No access was granted.') from None
    with db_session() as c:return {'order':_fulfill(c,row['id'],verified),'payment_verified':True}


def callback(fields):
    txnid=fields.get('txnid','');payu.identifier(txnid)
    with db_session() as c:
        row=c.execute('SELECT * FROM payu_access_orders WHERE mode=? AND txn_id=?',(get_settings().payu_mode,txnid)).fetchone()
        if not row:raise HTTPException(404,'Payment order not found.')
        row=dict(row)
        try:payu.validate_callback(fields,json.loads(row['expected_json']))
        except payu.PayURejected:raise HTTPException(400,'Invalid payment callback.') from None
        digest=hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        from app.accounts.security import limited
        lock(c,row['organization_id'])
        previous=c.execute('SELECT 1 FROM payu_access_callback_events WHERE order_id=? AND body_sha256=?',(row['id'],digest)).fetchone()
        if previous and row['status']=='PAID':return {'order':public(row),'payment_verified':True,'duplicate':True}
        blocked=limited(c,'payment-callback',row['id'],6,60)
        c.execute('INSERT INTO payu_access_callback_events(id,order_id,body_sha256,event_type,created_at) VALUES(?,?,?,?,?) ON CONFLICT(order_id,body_sha256) DO NOTHING',(str(uuid.uuid4()),row['id'],digest,'PAYMENT_RETURN',now()))
    if blocked:raise HTTPException(429,'Payment status will be reconciled after the current verification window.')
    return verify_order(row)


def refund_request(c,key,body):
    row=owned(c,key);lock(c,row['organization_id'])
    if row['status']!='PAID' or not row['provider_payment_id']:raise HTTPException(409,'Only a verified payment can be reviewed for refund.')
    previous=c.execute('SELECT * FROM payu_access_refunds WHERE organization_id=? AND request_id=?',(row['organization_id'],str(body.request_id))).fetchone()
    if previous:
        if previous['order_id']!=key:raise HTTPException(409,'Refund request belongs to a different purchase.')
        return {'id':previous['id'],'status':previous['status'],'money_refunded':False}
    pending=c.execute("SELECT id,status FROM payu_access_refunds WHERE organization_id=? AND order_id=? AND status IN ('REQUESTED','REVIEW','PENDING') ORDER BY created_at LIMIT 1",(row['organization_id'],key)).fetchone()
    if pending:return {'id':pending['id'],'status':pending['status'],'money_refunded':False}
    key_refund=str(uuid.uuid4());stamp=now()
    c.execute("INSERT INTO payu_access_refunds(id,organization_id,order_id,requested_by,request_id,amount_minor,currency,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'REQUESTED',?,?)",(key_refund,row['organization_id'],key,current().actor,str(body.request_id),row['total_minor'],row['currency'],stamp,stamp))
    return {'id':key_refund,'status':'REQUESTED','money_refunded':False,'message':'Your refund request is recorded for review under the applicable purchase policy. No refund is assumed until PayU independently confirms it.'}


def expiry_notices(c,limit=10):
    """Retained access data expires by timestamp; notifications cannot extend it."""
    from app.notifications import transactional as mail
    if not access_periods.enabled() or not get_settings().transactional_mail_enabled or not mail.configured():return 0
    limit=max(1,min(10,limit));stamp=int(time.time());created=now()
    c.execute("UPDATE access_periods SET status='EXPIRED',updated_at=? WHERE id IN (SELECT id FROM access_periods WHERE status='ACTIVE' AND paid_end<=? ORDER BY paid_end,id LIMIT 20)",(created,stamp))
    rows=c.execute("""SELECT p.*,o.created_by FROM access_periods p JOIN payu_access_orders o ON o.id=p.source_id AND o.organization_id=p.organization_id
        JOIN organization_memberships m ON m.organization_id=p.organization_id AND m.user_id=o.created_by AND m.status='ACTIVE' AND m.role='OWNER'
        WHERE p.source_kind='PAYMENT' AND p.status IN ('ACTIVE','EXPIRED') AND o.status='PAID'
        AND p.mode=? AND p.paid_end>? AND p.paid_end<=?
        AND NOT EXISTS(SELECT 1 FROM access_periods next WHERE next.organization_id=p.organization_id AND next.source_kind='PAYMENT' AND next.status='ACTIVE' AND next.paid_start<=p.paid_end AND next.paid_end>p.paid_end)
        ORDER BY p.paid_end,p.id LIMIT ?""",(get_settings().payu_mode,stamp-3*86400,stamp+3*86400,limit)).fetchall()
    count=0
    for row in rows:
        if not test_allowed(row['organization_id']):continue
        purpose='ACCESS_EXPIRED' if row['paid_end']<=stamp else 'RENEWAL_REMINDER'
        if c.execute('SELECT 1 FROM transactional_notifications WHERE dedupe_key=?',(purpose+':'+row['id'],)).fetchone():continue
        summary='Your PlaneByte paid access '+('has expired.' if purpose=='ACCESS_EXPIRED' else 'expires within three days.')+' No automatic payment will be taken.'
        mail.queue(c,row['created_by'],purpose,row['id'],{'summary':summary},dedupe_key=purpose+':'+row['id'],expires_at=stamp+86400,organization_id=row['organization_id']);count+=1
    return count
