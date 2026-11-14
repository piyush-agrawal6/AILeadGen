"""Payment security primitives; fixtures never represent provider acceptance."""
import hashlib,json
from unittest.mock import Mock
from pydantic import SecretStr
import httpx,pytest
from app.config.settings import get_settings
from app.billing import payu,commercial

@pytest.fixture
def fields(monkeypatch):
    s=get_settings()
    monkeypatch.setattr(s,'payu_mode','test');monkeypatch.setattr(s,'payu_merchant_key','fixturekey');monkeypatch.setattr(s,'payu_merchant_salt',SecretStr('fixturesalt'))
    return {'key':'fixturekey','txnid':'pbfixture123','amount':'59.00','productinfo':'Intent Radar Starter','firstname':'Owner','email':'owner@example.test','udf1':'org-fixture','udf2':'attempt-fixture','udf3':'test','udf4':'2026-11-14.1','udf5':'starter','currency':'USD'}

def callback(fields,**changes):
    result={**fields,'status':'success','mihpayid':'123456',**changes};result['hash']=payu.response_hash(result);return result

def test_catalog_approved_prices_not_arbitrary_test_amounts_or_binding_limits():
    catalog=commercial.catalog()
    assert [(p['code'],p['monthly_minor']) for p in catalog['plans']]==[('starter',5900),('growth',14900),('scale',37900),('enterprise',None)]
    assert catalog['prices_approved'] and not catalog['allowances_approved'] and not catalog['checkout_enabled']
    assert not catalog['annual_billing'] and not catalog['free_trial']
    assert all(p['limits'] is None for p in catalog['plans'])
    assert catalog['excluded_products']==['lead-engine']

def test_hosted_request_and_consent_hash_exact_pipe_order(fields):
    reference='fixturekey|pbfixture123|59.00|Intent Radar Starter|Owner|owner@example.test|org-fixture|attempt-fixture|test|2026-11-14.1|starter||||||fixturesalt'
    assert payu.request_hash(fields)==hashlib.sha512(reference.encode()).hexdigest()
    details='{"billingAmount":"59.00","billingCurrency":"USD","billingCycle":"MONTHLY","billingInterval":1}'
    fields['si_details']=details
    assert payu.request_hash(fields,consent=True)==hashlib.sha512(reference.replace('|fixturesalt','|'+details+'|fixturesalt').encode()).hexdigest()
    assert payu.request_hash(fields,consent=True)!=payu.request_hash(fields)

def test_callback_reverse_hash_exact_and_merchant_mode_attribution(fields):
    response=callback(fields)
    reference='fixturesalt|success||||||starter|2026-11-14.1|test|attempt-fixture|org-fixture|owner@example.test|Owner|Intent Radar Starter|59.00|pbfixture123|fixturekey'
    assert response['hash']==hashlib.sha512(reference.encode()).hexdigest()
    assert payu.validate_callback(response,fields)
    for name,value in [('amount','149.00'),('udf1','foreign-org'),('udf3','live'),('txnid','other'),('email','someone@example.test'),('hash','0'*128),('key','other')]:
        with pytest.raises(payu.PayURejected):payu.validate_callback({**response,name:value},fields)

def test_valid_hash_does_not_authorize_another_price_workspace_or_extra_fee(fields):
    for changes in ({'amount':'149.00'},{'udf1':'foreign-org'},{'additionalCharges':'1.00'},{'udf3':'live'},{'splitInfo':'unsupported'}):
        with pytest.raises(payu.PayURejected):payu.validate_callback(callback(fields,**changes),fields)
    with pytest.raises(payu.PayURejected):callback(fields,additionalCharges='0.00',additional_charges='1.00')

@pytest.mark.parametrize('value',['NaN','Infinity','-1','1e4','1.234','59|0','59\n',''])
def test_amount_parser_rejects_invalid_unbounded_or_ambiguous_values(value):
    with pytest.raises(payu.PayURejected):payu.amount(value)

def test_independent_captured_payment_does_not_claim_a_recurring_mandate(fields):
    item={**fields,'amt':'59.00','mihpayid':'12345','status':'success','unmappedstatus':'captured','additional_charges':'0'}
    assert payu.validate_payment(item,fields)['recurring_verified'] is False
    for changes in ({'status':'pending'},{'unmappedstatus':'auth'},{'amt':'1.00'},{'udf1':'foreign-org'},{'currency':'INR'},{'additional_charges':'1.00'},{'txnid':'other'},{'mihpayid':'invalid'}):
        with pytest.raises(payu.PayURejected):payu.validate_payment({**item,**changes},fields)
    without_currency={k:v for k,v in item.items() if k!='currency'}
    with pytest.raises(payu.PayURejected):payu.validate_payment(without_currency,fields)

def test_provider_verification_is_bounded_no_redirect_no_post_retry(fields,monkeypatch):
    calls=[]
    def handler(request):
        calls.append(request)
        assert request.url.host=='test.payu.in' and request.method=='POST'
        assert '59.00' not in request.content.decode() # verification is non-chargeable
        return httpx.Response(200,json={'status':1,'transaction_details':{fields['txnid']:{'txnid':fields['txnid'],'amt':'59.00'}}})
    real=httpx.Client
    def client(**kwargs):
        assert kwargs['follow_redirects'] is False
        return real(**kwargs,transport=httpx.MockTransport(handler))
    monkeypatch.setattr(payu.httpx,'Client',client)
    assert payu.verify_payment(fields['txnid'])['amt']=='59.00' and len(calls)==1

def test_missing_credentials_fail_closed_without_network(monkeypatch):
    monkeypatch.setattr(get_settings(),'payu_merchant_key','')
    network=Mock();monkeypatch.setattr(payu.httpx,'Client',network)
    assert not payu.configuration_status()['credentials_configured']
    from fastapi import HTTPException
    with pytest.raises(HTTPException):payu.verify_payment('valid')
    network.assert_not_called()
