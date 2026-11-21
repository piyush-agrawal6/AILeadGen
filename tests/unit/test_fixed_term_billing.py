"""Synthetic PayU transport only; no live charges or merchant acceptance claim."""
import hashlib,json,time,uuid
import pytest
from pydantic import SecretStr
from fastapi import HTTPException
from test_customer_accounts import customer,accounts,verified
from app.billing import fixed_term as billing,payu_v2,payu,access_periods
from app.platform.context import workspace_scope
refund_protocol=payu.refund_actions

@pytest.fixture
def purchase(customer,monkeypatch):
    c,s=customer;registration,_=verified(c);org=registration['organization_id'];actor='person@example.com'
    for name,value in {'fixed_term_billing_enabled':True,'payu_one_time_checkout_enabled':True,'payu_mode':'test','payu_merchant_key':'fixture-key','payu_merchant_salt':SecretStr('fixture-only-salt'),'payu_charge_currency':'USD','payu_currency_approved':True,'billing_test_workspaces':org,'billing_terms_version':'fixture-one-time-terms'}.items():monkeypatch.setattr(s,name,value)
    s.payu_merchant_capabilities_json=json.dumps({'test':{'provider':'payu','hosted_v2_verified':True,'charge_currencies':['USD'],'verification_reference':'SYNTHETIC CONTRACT ONLY','merchant_key_sha256':hashlib.sha256(s.payu_merchant_key.encode()).hexdigest()}})
    monkeypatch.setattr(payu,'refund_actions',lambda _:[])
    monkeypatch.setattr(payu_v2,'request',lambda *_:{'result':{'checkoutUrl':'https://test.payu.in/_payment_options?reference=fixture'}})
    return c,s,org,actor

def body(**updates):return billing.Purchase(plan_code='starter',billing={'first_name':'Test','last_name':'Owner','address1':'1 Fixture Street','city':'Test City','state':'Test State','country':'US','postal_code':'12345','phone':'+12025550100'},request_id=uuid.uuid4(),terms_version='fixture-one-time-terms',accepted_terms=True,**updates)

def captured(c,key,**updates):
    expected=json.loads(c.execute('SELECT expected_json FROM payu_access_orders WHERE id=?',(key,)).fetchone()[0])
    return {'txnId':expected['txnid'],'originalAmount':expected['amount'],'amount':expected['amount'],'netDebitAmount':expected['amount'],'originalCurrency':expected['currency'],'additionalCharges':'0','discount':'0','productInfo':expected['productinfo'],'status':'success','unmappedStatus':'captured','mihpayId':str(uuid.uuid4().int)[:20],**{k:expected[k] for k in payu.UDFS},**updates}

def test_monthly_order_no_gstin_no_gst_and_idempotent_create(purchase,monkeypatch):
    c,s,org,actor=purchase;calls=[]
    def create(action,payload):calls.append(payload);return {'result':{'checkoutUrl':'https://test.payu.in/_payment_options?reference=fixture'}}
    monkeypatch.setattr(payu_v2,'request',create)
    with workspace_scope(c,actor,org):
        request=body();first=billing.create(request);second=billing.create(request)
        assert first==second and len(calls)==1
        assert first['order']['currency']=='USD' and first['order']['total_minor']==5900 and first['order']['tax_minor']==0
        assert first['order']['tax']['gst_collected'] is False
        assert calls[0]['additionalInfo']=={'txnFlow':'nonseamless'}
        assert calls[0]['txnId'] and calls[0]['currency']=='USD' and calls[0]['order']['paymentChargeSpecification']['price']==59
        assert not any('gst' in key.lower() for key in calls[0]['billingDetails'])
        assert c.execute("SELECT COUNT(*) FROM access_periods WHERE source_kind='PAYMENT'").fetchone()[0]==0

def test_checkout_gate_requires_merchant_specific_usd_and_yearly_prices(purchase):
    c,s,org,actor=purchase;s.payu_merchant_capabilities_json='{}'
    with workspace_scope(c,actor,org):
        with pytest.raises(HTTPException) as denied:billing.create(body())
        assert denied.value.status_code==503
        with pytest.raises(HTTPException):billing.quote('starter','yearly')
    assert c.execute('SELECT COUNT(*) FROM payu_access_orders').fetchone()[0]==0
    assert billing.quote('growth','monthly')['total_minor']==14900

def test_successful_server_verification_fulfills_once_and_renews_after_expiry(purchase,monkeypatch):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):
        first=billing.create(body());key=first['order']['id'];item=captured(c,key)
        monkeypatch.setattr(payu_v2,'verify',lambda txn:item)
        result=billing.reconcile(key);again=billing.reconcile(key)
        assert result['payment_verified'] and again['payment_verified']
        period=result['order'];assert period['period_end']-period['period_start']==30*86400
        assert c.execute("SELECT COUNT(*) FROM access_periods WHERE source_kind='PAYMENT'").fetchone()[0]==1
        assert c.execute("SELECT status FROM access_periods WHERE source_kind='TRIAL'").fetchone()[0]=='REPLACED'
        assert access_periods.active(c,org)['source_id']==key
        next_order=billing.create(body());key2=next_order['order']['id'];item2=captured(c,key2)
        monkeypatch.setattr(payu_v2,'verify',lambda txn:item2)
        renewed=billing.reconcile(key2)['order']
        assert renewed['period_start']==period['period_end'] and renewed['period_end']-renewed['period_start']==30*86400
        assert access_periods.active(c,org)['source_id']==key
        assert c.execute('SELECT COUNT(*) FROM billing_payments').fetchone()[0]==0

@pytest.mark.parametrize('update',[{'originalCurrency':'INR'},{'amount':'0.01'},{'udf1':'another-workspace'},{'status':'pending'},{'unmappedStatus':'authorized'},{'additionalCharges':'1'}])
def test_unverified_or_mismatched_payment_never_grants_access(purchase,monkeypatch,update):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):
        key=billing.create(body())['order']['id'];item=captured(c,key,**update)
        monkeypatch.setattr(payu_v2,'verify',lambda txn:item)
        try:billing.reconcile(key)
        except HTTPException as error:assert error.status_code==502
        assert c.execute("SELECT COUNT(*) FROM access_periods WHERE source_kind='PAYMENT'").fetchone()[0]==0
        assert c.execute('SELECT status FROM payu_access_orders WHERE id=?',(key,)).fetchone()[0]=='PENDING'

def test_callback_hash_duplicate_and_tampering(purchase,monkeypatch):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):key=billing.create(body())['order']['id']
    expected=json.loads(c.execute('SELECT expected_json FROM payu_access_orders WHERE id=?',(key,)).fetchone()[0]);fields={**expected,'key':s.payu_merchant_key,'status':'success'};fields['hash']=payu.response_hash(fields)
    verified=captured(c,key);calls=[]
    monkeypatch.setattr(payu_v2,'verify',lambda txn:(calls.append(txn) or verified))
    assert billing.callback(fields)['payment_verified']
    assert billing.callback(fields)['duplicate'] and len(calls)==1
    with pytest.raises(HTTPException):billing.callback({**fields,'amount':'1.00'})
    assert c.execute('SELECT COUNT(*) FROM payu_access_callback_events').fetchone()[0]==1

def test_unknown_create_post_is_not_retried_and_refund_is_review_only(purchase,monkeypatch):
    c,s,org,actor=purchase;calls=[]
    def uncertain(*args):calls.append(1);raise payu.PayUUnavailable('Fixture uncertain response')
    monkeypatch.setattr(payu_v2,'request',uncertain)
    with workspace_scope(c,actor,org):
        request=body()
        with pytest.raises(HTTPException):billing.create(request)
        result=billing.create(request)
        assert result['order']['status']=='REVIEW' and not result['checkout_url'] and len(calls)==1
        key=result['order']['id'];item=captured(c,key);monkeypatch.setattr(payu_v2,'verify',lambda _:item)
        billing.reconcile(key)
        refund=billing.RefundRequest(request_id=uuid.uuid4())
        one=billing.refund_request(c,key,refund);two=billing.refund_request(c,key,refund)
        assert one['id']==two['id'] and not one['money_refunded'] and one['status']=='REQUESTED'
        assert c.execute('SELECT COUNT(*) FROM payu_access_refunds').fetchone()[0]==1

def test_foreign_workspace_missing_context_and_mode_change_are_denied(purchase):
    c,s,org,actor=purchase
    with pytest.raises(HTTPException):billing.history(c)
    with workspace_scope(c,actor,org):key=billing.create(body())['order']['id']
    s.payu_mode='live'
    with workspace_scope(c,actor,org):
        with pytest.raises(HTTPException):billing.reconcile(key)
    assert c.execute("SELECT COUNT(*) FROM access_periods WHERE source_kind='PAYMENT'").fetchone()[0]==0

def test_payment_confirmation_and_expiry_outbox_are_deduplicated(purchase,monkeypatch):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):
        key=billing.create(body())['order']['id'];item=captured(c,key);monkeypatch.setattr(payu_v2,'verify',lambda _:item)
        billing.reconcile(key);billing.reconcile(key)
        assert c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE purpose='PAYMENT_CONFIRMED'").fetchone()[0]==1
        stamp=int(time.time())
        c.execute("UPDATE access_periods SET paid_end=?,paid_start=? WHERE source_kind='PAYMENT'",(stamp+1000,stamp-30*86400+1000))
        assert billing.expiry_notices(c)==1 and billing.expiry_notices(c)==0
        assert c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE purpose='RENEWAL_REMINDER'").fetchone()[0]==1
        c.execute("UPDATE access_periods SET paid_end=?,paid_start=? WHERE source_kind='PAYMENT'",(stamp-1,stamp-30*86400-1))
        assert billing.expiry_notices(c)==1 and billing.expiry_notices(c)==0
        assert c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE purpose='ACCESS_EXPIRED'").fetchone()[0]==1
        assert c.execute("SELECT status FROM access_periods WHERE source_kind='PAYMENT'").fetchone()[0]=='EXPIRED'

def test_invitation_email_quota_and_verified_recipient_explicit_acceptance(purchase,monkeypatch):
    # This test inspects the pending, encrypted outbox before delivery. The
    # admission fixture otherwise runs in development and consumes the row.
    monkeypatch.setattr('app.notifications.dispatch.enqueue_notification',lambda _:None)
    from app.platform import invitations
    from app.accounts import service as accounts,models as account_models
    from test_customer_accounts import signup,otp
    c,s,org,actor=purchase;s.heysow_invited_registration_enabled=True
    with workspace_scope(c,actor,org):
        key=billing.create(body().model_copy(update={'plan_code':'growth'}))['order']['id'];item=captured(c,key);monkeypatch.setattr(payu_v2,'verify',lambda _:item);billing.reconcile(key)
        invite=invitations.create(c,invitations.InviteCreate(email='teammate@example.com'));c.commit()
        assert invite['delivery']=='EMAIL_QUEUED'
        queued=c.execute("SELECT * FROM transactional_notifications WHERE purpose='TEAM_INVITATION'").fetchone()
        from app.notifications import transactional as mail
        payload=json.loads(mail.cipher().decrypt(queued['payload_encrypted'].encode()))
        assert '/accept-invitation#'+invite['token'] in payload['text']
        assert mail.authorized(c,queued)
    s.heysow_public_registration_enabled=False
    registered=accounts.begin_signup(signup(email='teammate@example.com',invitation_token=SecretStr(invite['token'])),'invited-client')
    result=accounts.verify_email(account_models.Verify(challenge_id=registered['challenge_id'],capability=registered['capability'],code=otp(c,registered['challenge_id'])),'invited-client')
    assert result['verified'] and 'organization_id' not in result
    assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',('teammate@example.com',)).fetchone()[0]==0
    assert c.execute('SELECT COUNT(*) FROM launch_trial_claims').fetchone()[0]==1
    accepted=invitations.respond(c,'teammate@example.com',invitations.InviteRespond(token=invite['token'],action='ACCEPT'));c.commit()
    assert accepted['organization_id']==org
    assert not mail.authorized(c,queued)

def test_trial_does_not_queue_invites_above_one_member(customer):
    from app.platform import invitations
    c,s=customer;registration,_=verified(c);org=registration['organization_id']
    with workspace_scope(c,'person@example.com',org):
        with pytest.raises(HTTPException) as denied:invitations.create(c,invitations.InviteCreate(email='teammate@example.com'))
        assert denied.value.status_code==429
    assert c.execute('SELECT COUNT(*) FROM workspace_invitations').fetchone()[0]==0
    assert c.execute("SELECT COUNT(*) FROM transactional_notifications WHERE purpose='TEAM_INVITATION'").fetchone()[0]==0

def test_future_plan_change_and_late_capture_never_overlap_current_access(purchase,monkeypatch):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):
        first=billing.create(body())['order'];item=captured(c,first['id']);monkeypatch.setattr(payu_v2,'verify',lambda _:item)
        current=billing.reconcile(first['id'])['order']
        second=billing.create(body().model_copy(update={'plan_code':'growth'}))['order'];later=captured(c,second['id'])
        c.execute("UPDATE payu_access_orders SET status='FAILED' WHERE id=?",(second['id'],));c.commit()
        monkeypatch.setattr(payu_v2,'verify',lambda _:later)
        queued=billing.reconcile(second['id'])['order']
        assert queued['period_start']==current['period_end']
        assert access_periods.active(c,org)['plan_code']=='starter'
        saved=c.execute('SELECT terms_version,terms_accepted_at FROM payu_access_orders WHERE id=?',(second['id'],)).fetchone()
        assert saved['terms_version']=='fixture-one-time-terms' and saved['terms_accepted_at']

@pytest.mark.parametrize('amount,currency,state,revoked',[(5900,'USD','SUCCEEDED',True),(5900,None,'SUCCEEDED',False),(5900,'INR','SUCCEEDED',False),(100,'USD','SUCCEEDED',False),(5900,'USD','PENDING',False),(5900,'USD','FAILED',False)])
def test_refunds_require_matching_independent_full_currency_evidence(purchase,monkeypatch,amount,currency,state,revoked):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):
        key=billing.create(body())['order']['id'];item=captured(c,key);monkeypatch.setattr(payu_v2,'verify',lambda _:item);billing.reconcile(key)
        observations=[{'provider_refund_id':'12345','provider_payment_id':item['mihpayId'],'amount_minor':amount,'currency':currency,'status':state}]
        monkeypatch.setattr(payu,'refund_actions',lambda _:observations)
        result=billing.reconcile(key)
        assert result['refund_initiated'] is False and result['full_refund_verified'] is revoked
        assert result['order']['status']==('REFUNDED' if revoked else 'PAID')
        assert bool(access_periods.active(c,org)) is not revoked
        assert c.execute('SELECT COUNT(*) FROM access_periods').fetchone()[0]==2
        billing.reconcile(key)
        assert c.execute('SELECT COUNT(*) FROM payu_refund_observations').fetchone()[0]==1
        if revoked:
            # A late stale pending response cannot resurrect paid access or
            # erase verified accounting evidence.
            observations[0]['status']='PENDING';billing.reconcile(key)
            assert c.execute('SELECT status FROM payu_refund_observations').fetchone()[0]=='SUCCEEDED'
            assert access_periods.active(c,org) is None


def test_refund_request_deduplicates_different_browser_request_ids(purchase,monkeypatch):
    c,s,org,actor=purchase
    with workspace_scope(c,actor,org):
        key=billing.create(body())['order']['id'];item=captured(c,key);monkeypatch.setattr(payu_v2,'verify',lambda _:item);billing.reconcile(key)
        first=billing.refund_request(c,key,billing.RefundRequest(request_id=uuid.uuid4()))
        second=billing.refund_request(c,key,billing.RefundRequest(request_id=uuid.uuid4()))
        assert first['id']==second['id'] and c.execute('SELECT COUNT(*) FROM payu_access_refunds').fetchone()[0]==1
        assert billing.history(c)['refund_requests'][0]['status']=='REQUESTED'


def test_payu_refund_lookup_is_read_only_and_does_not_infer_currency(purchase,monkeypatch):
    import httpx
    from urllib.parse import parse_qs
    c,s,org,actor=purchase;requests=[];client=httpx.Client
    def transport(request):
        fields=parse_qs(request.content.decode());requests.append(fields)
        assert fields['command']==['check_action_status'] and fields['var1']==['123456'] and fields['var2']==['payuid']
        assert fields['hash']==[payu.sha('|'.join((s.payu_merchant_key,'check_action_status','123456',s.payu_merchant_salt.get_secret_value())))]
        return httpx.Response(200,json={'status':1,'transaction_details':{'123456':{'9988':{'mihpayid':'123456','request_id':'9988','amt':'59.00','action':'refund','status':'success'},'9989':{'mihpayid':'123456','request_id':'9989','amt':'59.00','action':'capture','status':'SUCCESS'}}}})
    monkeypatch.setattr(payu.httpx,'Client',lambda **kwargs:client(transport=httpx.MockTransport(transport),**kwargs))
    result=refund_protocol('123456')
    assert len(requests)==1 and result==[{'provider_refund_id':'9988','provider_payment_id':'123456','amount_minor':5900,'currency':None,'status':'SUCCEEDED'}]
