"""Small server-only adapter for Creem's official REST API.

POSTs are never automatically retried. A redirect, provider error or ambiguous
response never establishes a payment, mandate or entitlement.
"""
import hashlib,json,re
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from app.config.settings import get_settings

BASE={'production':'https://api.creem.io/v1','test':'https://test-api.creem.io/v1'}
class Unavailable(RuntimeError):pass
class Rejected(RuntimeError):pass

def environment():return get_settings().creem_environment
def key_for(mode):
 s=get_settings();key=(s.creem_api_key if mode=='production' else s.creem_test_api_key).get_secret_value()
 if not key:raise Unavailable('Creem '+mode+' credentials are not configured.')
 return key

def identifier(value,prefix):
 if not isinstance(value,str) or not re.fullmatch(re.escape(prefix)+r'[A-Za-z0-9_-]{1,180}',value):raise Rejected('Invalid provider reference.')
 return value

def request(method,path,*,mode=None,body=None,params=None,idempotency_key=None,transport=None):
 mode=mode or environment()
 if mode not in BASE or not path.startswith('/') or '..' in path or '?' in path or '#' in path:raise ValueError('Internal Creem endpoint required')
 s=get_settings()
 if s.app_env=='test' and transport is None:raise Unavailable('Live provider requests are disabled in isolated tests.')
 headers={'x-api-key':key_for(mode),'accept':'application/json'}
 if idempotency_key:headers['Idempotency-Key']=idempotency_key
 try:
  with httpx.Client(timeout=httpx.Timeout(12,connect=5),follow_redirects=False,transport=transport) as client:
   with client.stream(method,BASE[mode]+path,headers=headers,json=body,params=params) as r:
    if r.status_code not in (200,201):
     if r.status_code>=500 or r.status_code==429:raise Unavailable('Creem is temporarily unavailable.')
     raise Rejected('Creem rejected the server request (HTTP '+str(r.status_code)+').')
    raw=bytearray()
    for chunk in r.iter_bytes():
     raw.extend(chunk)
     if len(raw)>524288:raise Unavailable('Creem response exceeded its size limit.')
    result=json.loads(raw)
    if not isinstance(result,(dict,list)):raise ValueError()
    return result
 except (httpx.HTTPError,ValueError,UnicodeError):raise Unavailable('Creem response could not be confirmed.') from None

def get_product(key,**kw):return request('GET','/products/'+identifier(key,'prod_'),**kw)
def get_checkout(key,**kw):return request('GET','/checkouts',params={'checkout_id':identifier(key,'ch_')},**kw)
def get_subscription(key,**kw):return request('GET','/subscriptions',params={'subscription_id':identifier(key,'sub_')},**kw)
def get_customer(key,**kw):return request('GET','/customers',params={'customer_id':identifier(key,'cust_')},**kw)
def get_transaction(key,**kw):return request('GET','/transactions',params={'transaction_id':identifier(key,'tran_')},**kw)

def hosted_url(value):
 if not isinstance(value,str) or len(value)>2048:raise Rejected('Invalid Creem hosted URL.')
 u=urlsplit(value)
 if u.scheme!='https' or u.username or u.password or u.port not in (None,443) or not u.hostname or not (u.hostname=='creem.io' or u.hostname.endswith('.creem.io')):raise Rejected('Invalid Creem hosted URL.')
 return value

def object_mode(value,mode):
 if not isinstance(value,dict) or value.get('mode')!=('prod' if mode=='production' else 'test'):raise Rejected('Creem object environment does not match.')
 return value

def validate_product(value,plan,variant,mode):
 object_mode(value,mode);identifier(value.get('id'),'prod_')
 expected_days=3 if variant=='trial' else 0
 if value.get('price')!=plan['monthly_minor'] or value.get('currency')!='USD' or value.get('billing_type')!='recurring' or value.get('billing_period')!='every-month' or (value.get('trial_period_days') or 0)!=expected_days or (value.get('trial_price') or 0)!=0 or value.get('tax_mode')!='inclusive':raise Rejected('Creem product differs from approved pricing or trial terms.')
 return value
