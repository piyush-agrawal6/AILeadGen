"""Bounded PayU Hosted Checkout cryptography and independent verification.

References: PayU Hosted consent, Verify Payment API, Collect Additional Charges.
No card data, POST retries, dynamic hosts, inferred currencies or mandate grants.
Zion/account enablement must be verified before a recurring flow is activated.
"""
import hashlib,hmac,json,re,time
from decimal import Decimal,InvalidOperation
import httpx
from fastapi import HTTPException
from app.config.settings import get_settings

class PayUUnavailable(RuntimeError):pass
class PayURejected(RuntimeError):pass

ENDPOINTS={
    'test':('https://test.payu.in/_payment','https://test.payu.in/merchant/postservice.php?form=2'),
    'live':('https://secure.payu.in/_payment','https://info.payu.in/merchant/postservice.php?form=2'),
}
UDFS=tuple('udf'+str(i) for i in range(1,6))

def configuration_status():
    s=get_settings();configured=bool(s.payu_merchant_key and s.payu_merchant_salt.get_secret_value())
    return {'provider':'payu','mode':s.payu_mode,'credentials_configured':configured,'checkout_enabled':False,
      'recurring_verified':False,'charge_currency':None,
      'blockers':([] if configured else ['PayU merchant key and salt are not configured.'])+['Account-specific Zion activation and API authentication contract are unverified.']}

def credentials():
    s=get_settings();key=s.payu_merchant_key;salt=s.payu_merchant_salt.get_secret_value()
    if not key or not salt:raise HTTPException(503,'PayU credentials are not configured. No payment was initiated.')
    if any(char in key+salt for char in ('|','\n','\r')):raise HTTPException(503,'PayU credential format is invalid.')
    return key,salt

def text(value):
    if not isinstance(value,str) or len(value)>2048 or any(c in value for c in ('|','\r','\n','\x00')):raise PayURejected('Invalid payment field.')
    return value

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,25}',value):raise PayURejected('Invalid merchant transaction reference.')
    return value

def amount(value):
    try:
        if not isinstance(value,str) or not re.fullmatch(r'\d{1,10}(?:\.\d{1,2})?',value):raise ValueError()
        number=Decimal(value)
        if not number.is_finite() or number<0:raise ValueError()
        return number
    except (InvalidOperation,ValueError):raise PayURejected('Invalid payment amount.') from None

def sha(value):return hashlib.sha512(value.encode('utf-8')).hexdigest()

def additional_charge(fields):
    values=[fields[name] for name in ('additionalCharges','additional_charges') if fields.get(name) not in ('',None)]
    if len(values)==2 and amount(values[0])!=amount(values[1]):raise PayURejected('Ambiguous additional charge fields.')
    return values[0] if values else ''

def request_hash(fields,*,consent=False):
    key,salt=credentials()
    if fields.get('key')!=key:raise PayURejected('Merchant key does not match the configured environment.')
    identifier(fields.get('txnid'));amount(fields.get('amount'))
    values=[key,*[text(fields.get(name,'')) for name in ('txnid','amount','productinfo','firstname','email',*UDFS)],*['']*5]
    if consent:
        # The exact serialized SI object is signed; never reserialize afterward.
        details=text(fields.get('si_details',''))
        if not details:raise PayURejected('Recurring consent details are required.')
        values.append(details)
    return sha('|'.join([*values,salt]))

def response_hash(fields):
    key,salt=credentials()
    if fields.get('key')!=key:raise PayURejected('Callback merchant does not match.')
    identifier(fields.get('txnid'));amount(fields.get('amount'))
    # Only the supported non-split Hosted Checkout flow is accepted. Do not
    # loosen comparison by trying arbitrary pipe counts or posted merchant keys.
    if fields.get('splitInfo') or fields.get('splitinfo'):raise PayURejected('Split-payment callbacks are unsupported.')
    values=[salt,text(fields.get('status','')),*['']*5,*[text(fields.get(name,'')) for name in reversed(UDFS)],*[text(fields.get(name,'')) for name in ('email','firstname','productinfo','amount','txnid')],key]
    extra=additional_charge(fields)
    if extra:
        amount(extra);values.insert(0,extra)
    return sha('|'.join(values))

def validate_callback(fields,expected):
    signature=fields.get('hash','')
    if not isinstance(signature,str) or not re.fullmatch(r'[a-fA-F0-9]{128}',signature) or not hmac.compare_digest(response_hash(fields),signature.lower()):
        raise PayURejected('Callback hash verification failed.')
    for name in ('txnid','email','firstname','productinfo',*UDFS):
        if fields.get(name,'')!=expected.get(name,''):raise PayURejected('Callback does not match the original transaction.')
    if amount(fields['amount'])!=amount(expected['amount']):raise PayURejected('Callback amount differs from the authorized transaction.')
    # Amounts outside the disclosed consent cannot silently become paid access.
    if amount(additional_charge(fields) or '0')!=0:raise PayURejected('Undisclosed additional payment charge.')
    return True

def verify_payment(txnid):
    key,salt=credentials();identifier(txnid)
    data={'key':key,'command':'verify_payment','var1':txnid,'hash':sha('|'.join((key,'verify_payment',txnid,salt)))}
    try:
        with httpx.Client(timeout=httpx.Timeout(12,connect=4),follow_redirects=False) as client:
            with client.stream('POST',ENDPOINTS[get_settings().payu_mode][1],data=data) as response:
                if response.status_code>=500 or response.status_code==429:raise PayUUnavailable('PayU verification temporarily unavailable.')
                if response.status_code!=200:raise PayURejected('PayU verification rejected the request.')
                raw=bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw)>262144:raise PayURejected('PayU verification response exceeded its bound.')
        result=json.loads(raw)
        if not isinstance(result,dict):raise PayURejected('Invalid PayU verification response.')
        details=result.get('transaction_details')
        if result.get('status') not in (1,'1') or not isinstance(details,dict) or txnid not in details:
            # No provider message or raw body is surfaced; these may contain PII.
            raise PayURejected('PayU did not return a verified transaction.')
        item=details[txnid]
        if not isinstance(item,dict) or item.get('txnid')!=txnid:raise PayURejected('Provider transaction reference does not match.')
        return item
    except (httpx.HTTPError,TimeoutError):raise PayUUnavailable('PayU verification temporarily unavailable.') from None
    except (ValueError,UnicodeError):raise PayURejected('Invalid PayU verification response.') from None

def validate_payment(item,expected):
    if item.get('txnid')!=expected['txnid']:raise PayURejected('Payment reference differs.')
    if amount(str(item.get('amt','')))!=amount(expected['amount']):raise PayURejected('Verified amount differs.')
    for name in ('productinfo','firstname',*UDFS):
        if (item.get(name) or '')!=expected.get(name,''):raise PayURejected('Verified transaction attribution differs.')
    if item.get('email') is not None and item['email']!=expected['email']:raise PayURejected('Verified payer differs.')
    if amount(str(item.get('additional_charges','0') or '0'))!=0:raise PayURejected('Additional charge requires review.')
    if item.get('currency')!=expected['currency']:raise PayURejected('Verified currency is absent or differs; do not infer it from the list price.')
    if item.get('status')!='success' or item.get('unmappedstatus')!='captured':raise PayURejected('Payment is not captured.')
    if not re.fullmatch(r'[0-9]{1,40}',str(item.get('mihpayid',''))):raise PayURejected('Provider payment reference is invalid.')
    # This validates a payment only. It does NOT prove a recurring mandate,
    # renewal period, refund status, charge-currency capability, or entitlement.
    return {'provider':'payu','mode':get_settings().payu_mode,'transaction_id':expected['txnid'],'provider_payment_id':str(item['mihpayid']),'payment_verified':True,'recurring_verified':False}

def refund_actions(payment_id):
    """Read-only reconciliation; never calls a refund/cancellation command.

    docs.payu.in/reference/check_action_status_api_with_payu_id
    No response body, bank reference or raw provider error leaves this module.
    """
    if not isinstance(payment_id,str) or not re.fullmatch(r'[0-9]{1,40}',payment_id):raise PayURejected('Invalid provider payment reference.')
    key,salt=credentials();command='check_action_status'
    data={'key':key,'command':command,'var1':payment_id,'var2':'payuid','hash':sha('|'.join((key,command,payment_id,salt)))}
    deadline=time.monotonic()+20
    try:
        with httpx.Client(timeout=httpx.Timeout(12,connect=4),follow_redirects=False) as client:
            with client.stream('POST',ENDPOINTS[get_settings().payu_mode][1],data=data) as response:
                if response.status_code>=500 or response.status_code==429:raise PayUUnavailable('PayU refund reconciliation is temporarily unavailable.')
                if response.status_code!=200:raise PayURejected('PayU refund reconciliation was rejected.')
                raw=bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic()>deadline:raise PayUUnavailable('PayU refund reconciliation exceeded its deadline.')
                    raw.extend(chunk)
                    if len(raw)>262144:raise PayURejected('Refund reconciliation response exceeds its bound.')
        result=json.loads(raw,parse_float=str)
        details=result.get('transaction_details',{}).get(payment_id) if isinstance(result,dict) and isinstance(result.get('transaction_details'),dict) else None
        if result.get('status') not in (1,'1') or not isinstance(details,dict) or len(details)>100:raise PayURejected('A bounded payment action history was not established.')
        refunds=[]
        for reference,item in details.items():
            if not isinstance(item,dict):raise PayURejected('Invalid payment action.')
            if item.get('action')!='refund':continue
            if str(item.get('mihpayid','')).strip()!=payment_id or not re.fullmatch(r'[0-9]{1,40}',str(reference)) or str(item.get('request_id'))!=str(reference):raise PayURejected('Refund attribution differs.')
            value=amount(str(item.get('amt','')))*100
            if value<=0 or value!=value.to_integral_value():raise PayURejected('Refund amount is invalid.')
            state=str(item.get('status','')).upper()
            # Currency is not documented on every account's response. Retain an
            # unknown currency as REVIEW; never equate INR action amounts to USD.
            currency=item.get('originalCurrency') or item.get('currency')
            if currency is not None and (not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency)):raise PayURejected('Invalid refund currency.')
            normalized='SUCCEEDED' if state=='SUCCESS' else 'FAILED' if state=='FAILURE' else 'PENDING' if state in ('QUEUED','IN PROGRESS','REQUESTED','OD_HIT') else 'REVIEW'
            refunds.append({'provider_refund_id':str(reference),'provider_payment_id':payment_id,'amount_minor':int(value),'currency':currency,'status':normalized})
        return refunds
    except (httpx.HTTPError,TimeoutError):raise PayUUnavailable('PayU refund reconciliation is temporarily unavailable.') from None
    except (ValueError,UnicodeError,AttributeError):raise PayURejected('Invalid refund reconciliation response.') from None
