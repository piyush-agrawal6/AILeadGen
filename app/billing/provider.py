"""Bounded Razorpay API calls. No blind POST retries; no credential/error echo."""
import hashlib,hmac,re
import httpx
from fastapi import HTTPException
from app.config.settings import get_settings

class ProviderUnavailable(RuntimeError):pass
class ProviderRejected(RuntimeError):pass

def configured():
    s=get_settings()
    return bool(s.razorpay_key_id.startswith('rzp_test_') and s.razorpay_key_secret.get_secret_value() and s.razorpay_mode=='test' and s.billing_test_mode)

def guard():
    s=get_settings()
    if not s.billing_enabled or s.billing_provider!='razorpay' or not configured():raise HTTPException(503,'Razorpay Test Mode is not configured. No payment has been initiated.')
    return s

def identifier(value,prefix):
    if not isinstance(value,str) or not re.fullmatch(prefix+r'_[A-Za-z0-9]{1,80}',value):raise ProviderRejected('Invalid provider identifier.')
    return value

def request(method,path,payload=None,params=None):
    s=guard()
    # All paths are generated internally from validated provider identifiers.
    try:
        with httpx.Client(base_url='https://api.razorpay.com/v1/',auth=(s.razorpay_key_id,s.razorpay_key_secret.get_secret_value()),timeout=httpx.Timeout(12,connect=4),follow_redirects=False) as client:
            with client.stream(method,path,json=payload,params=params) as response:
                body=bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body)>500000:raise ProviderUnavailable('Provider response exceeded the safe limit.')
                if response.status_code in (400,401,403,404,422):raise ProviderRejected('Provider rejected the request; check authorized test configuration.')
                if response.status_code>=300:raise ProviderUnavailable('Provider is temporarily unavailable; reconcile before retrying a creation.')
                import json
                result=json.loads(body)
                if not isinstance(result,dict):raise ValueError()
                return result
    except (httpx.HTTPError,ValueError) as error:raise ProviderUnavailable('Provider response could not be verified.') from None

def verify_signature(message,signature,secret):
    if not isinstance(signature,str) or not re.fullmatch('[a-fA-F0-9]{64}',signature):return False
    return hmac.compare_digest(hmac.new(secret.encode(),message,hashlib.sha256).hexdigest(),signature.lower())

def verify_plan(p,remote):
    item=remote.get('item') or {}
    if remote.get('id')!=p.provider_plan_id or remote.get('period')!=p.period or remote.get('interval')!=p.interval or item.get('amount')!=p.amount or item.get('currency')!=p.currency or item.get('active') is False:
        raise ProviderRejected('Provider plan does not match the server-approved test catalog.')
