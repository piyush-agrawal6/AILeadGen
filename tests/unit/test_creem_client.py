import json
import httpx,pytest
from pydantic import SecretStr
from app.billing import creem,commercial
from app.config.settings import get_settings

def test_creem_client_uses_separate_test_key_fixed_origin_and_does_not_retry(monkeypatch):
 s=get_settings();monkeypatch.setattr(s,'creem_api_key',SecretStr('synthetic-live'))
 monkeypatch.setattr(s,'creem_test_api_key',SecretStr('synthetic-test'))
 calls=[]
 def handler(request):
  calls.append(request)
  assert str(request.url)=='https://test-api.creem.io/v1/checkouts'
  assert request.headers['x-api-key']=='synthetic-test'
  return httpx.Response(503,json={'ignored':'not logged'})
 with pytest.raises(creem.Unavailable):creem.request('POST','/checkouts',body={'product_id':'prod_fixture'},mode='test',transport=httpx.MockTransport(handler))
 assert len(calls)==1
 monkeypatch.setattr(s,'creem_test_api_key',SecretStr(''))
 with pytest.raises(creem.Unavailable):creem.request('GET','/products/search',mode='test',transport=httpx.MockTransport(handler))
 assert len(calls)==1

@pytest.mark.parametrize('url',['http://creem.io/pay','https://creem.io.evil.test/pay','https://user:secret@creem.io/pay','https://creem.io:444/pay','javascript:alert(1)'])
def test_hosted_links_cannot_redirect_to_untrusted_destinations(url):
 with pytest.raises(creem.Rejected):creem.hosted_url(url)

def test_product_validation_requires_exact_price_environment_and_trial():
 plan=commercial.plan('starter')
 value={'id':'prod_fixture','mode':'test','price':5900,'currency':'USD','billing_type':'recurring','billing_period':'every-month','trial_period_days':3,'trial_price':0,'tax_mode':'inclusive'}
 assert creem.validate_product(value,plan,'trial','test')==value
 for update in ({'price':590},{'trial_period_days':7},{'trial_price':100},{'mode':'prod'},{'currency':'INR'},{'billing_type':'onetime'},{'tax_mode':'exclusive'}):
  with pytest.raises(creem.Rejected):creem.validate_product({**value,**update},plan,'trial','test')
