"""PayU's dated JSON protocol. All URLs are fixed; no provider POST retries.

Official v2 Hosted Checkout / v3 verify_payment documentation (2026-11-14).
A captured payment is not evidence of an active recurring mandate.
"""
from datetime import datetime, timezone
from email.utils import format_datetime
import json, re, time
from urllib.parse import urlsplit
import httpx
from app.billing.payu import credentials, sha, identifier, amount, PayURejected, PayUUnavailable
from app.config.settings import get_settings

URLS = {
    'test': {'verify': 'https://test.payu.in/v3/transaction', 'create': 'https://apitest.payu.in/v2/payments'},
    'live': {'verify': 'https://info.payu.in/v3/transaction', 'create': 'https://api.payu.in/v2/payments'},
}

def encode(payload, date=None):
    key, salt = credentials()
    # Quotes/backslashes must never enter the Authorization header grammar.
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,50}', key):
        raise PayURejected('Unsupported merchant identifier format.')
    body = json.dumps(payload, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
    if len(body.encode()) > 16000: raise PayURejected('Payment request exceeds its bound.')
    date = date or format_datetime(datetime.now(timezone.utc), usegmt=True)
    if not re.fullmatch(r'[A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} GMT', date):
        raise PayURejected('Invalid payment request date.')
    signature = sha(body+'|'+date+'|'+salt)
    return body.encode(), {'Content-Type':'application/json','date':date,
        'authorization':f'hmac username="{key}", algorithm="sha512", headers="date", signature="{signature}"'}

def request(action, payload):
    if action not in ('verify','create'): raise ValueError('Unsupported PayU action.')
    body, headers = encode(payload)
    if action == 'verify': headers['Info-Command'] = 'verify_payment'
    deadline=time.monotonic()+20
    try:
        with httpx.Client(timeout=httpx.Timeout(12, connect=4), follow_redirects=False) as client:
            with client.stream('POST', URLS[get_settings().payu_mode][action], content=body, headers=headers) as response:
                if response.status_code >= 500 or response.status_code == 429:
                    raise PayUUnavailable('PayU temporarily unavailable; reconcile before retrying creation.')
                if response.status_code != 200: raise PayURejected('PayU rejected the request.')
                raw=bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic()>deadline:raise PayUUnavailable('PayU exceeded its bounded response deadline.')
                    raw.extend(chunk)
                    if len(raw)>262144: raise PayURejected('PayU response exceeds its bound.')
        result=json.loads(raw, parse_float=str)
        if not isinstance(result, dict): raise PayURejected('Invalid PayU response.')
        return result
    except (httpx.HTTPError, TimeoutError):
        raise PayUUnavailable('PayU response unavailable; do not repeat an uncertain creation.') from None
    except (ValueError, UnicodeError): raise PayURejected('Invalid PayU response.') from None

def verify(txnid):
    identifier(txnid)
    result=request('verify', {'txnId':[txnid]})
    rows=result.get('result')
    if result.get('status') not in (1,'1') or not isinstance(rows, list) or len(rows)!=1:
        raise PayURejected('PayU did not return one verified transaction.')
    if not isinstance(rows[0],dict) or rows[0].get('txnId')!=txnid:
        raise PayURejected('Provider transaction reference differs.')
    return rows[0]

def validate(item, expected):
    """Retain only verified, minimal payment metadata; never card/contact fields."""
    if item.get('txnId')!=expected['txnid']: raise PayURejected('Payment reference differs.')
    for name in ('originalAmount','amount','netDebitAmount'):
        if amount(str(item.get(name,'')))!=amount(expected['amount']):
            raise PayURejected('Verified payment amount differs.')
    if item.get('originalCurrency')!=expected['currency']:
        raise PayURejected('Original transaction currency is absent or differs.')
    for name in ('additionalCharges','discount'):
        if amount(str(item.get(name,'')))!=0: raise PayURejected('Undisclosed charge or discount.')
    for name in ('udf1','udf2','udf3','udf4','udf5'):
        if item.get(name)!=expected[name]: raise PayURejected('Verified workspace or contract attribution differs.')
    if item.get('productInfo')!=expected['productinfo']: raise PayURejected('Verified product differs.')
    if item.get('status')!='success' or item.get('unmappedStatus')!='captured':
        raise PayURejected('Payment is not captured.')
    payment_id=str(item.get('mihpayId',''))
    if not re.fullmatch(r'[0-9]{1,40}',payment_id): raise PayURejected('Invalid provider payment reference.')
    return {'provider':'payu','mode':get_settings().payu_mode,'transaction_id':expected['txnid'],
        'provider_payment_id':payment_id,'amount':expected['amount'],'currency':expected['currency'],
        'payment_verified':True,'recurring_verified':False}

def checkout_url(result):
    value=result.get('result',{}).get('checkoutUrl') if isinstance(result.get('result'),dict) else None
    if not isinstance(value,str) or len(value)>4096: raise PayURejected('PayU checkout URL is absent.')
    try: parsed=urlsplit(value)
    except ValueError: raise PayURejected('Invalid PayU checkout URL.') from None
    hosts={'live':{'secure.payu.in','pp78secure.payu.in'},'test':{'test.payu.in'}}
    if parsed.scheme!='https' or parsed.hostname not in hosts[get_settings().payu_mode] or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.fragment:
        raise PayURejected('Checkout must use an authorized PayU HTTPS host.')
    return value
