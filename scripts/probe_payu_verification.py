"""One non-chargeable Live/Test verify request. Never creates a transaction.

Only safe transport/authentication categories are printed. A nonexistent payment
cannot prove currency, mandate, settlement or subscription readiness.
"""
import json,uuid
from pathlib import Path
import httpx
from dotenv import dotenv_values
from pydantic import SecretStr
from app.config.settings import get_settings
from app.billing import payu_v2

ROOT=Path(__file__).resolve().parents[1]
def main():
    values=dotenv_values(ROOT/'.env',interpolate=False);s=get_settings()
    s.payu_mode=values.get('PAYU_MODE') or 'test'
    s.payu_merchant_key=values.get('PAYU_MERCHANT_KEY') or ''
    s.payu_merchant_salt=SecretStr(values.get('PAYU_MERCHANT_SALT') or '')
    body,headers=payu_v2.encode({'txnId':['pbprobe'+uuid.uuid4().hex[:18]]})
    headers['Info-Command']='verify_payment'
    with httpx.Client(timeout=httpx.Timeout(12,connect=4),follow_redirects=False) as client:
        response=client.post(payu_v2.URLS[s.payu_mode]['verify'],content=body,headers=headers)
        if len(response.content)>262144:raise RuntimeError('Provider response exceeded bound.')
    try: data=response.json()
    except ValueError:data={}
    private=ROOT/'data/artifacts/verification/final-product/payu-v3-probe-private.json'
    private.write_text(json.dumps(data,indent=2)+'\n');private.chmod(0o600)
    # Do not expose provider messages/transaction data, authorization or key IDs.
    category='AUTHENTICATION_REJECTED' if response.status_code in (401,403) else 'ENDPOINT_NOT_FOUND' if response.status_code==404 else 'RESPONSE_REQUIRES_REVIEW'
    if response.status_code==200 and isinstance(data,dict):
        status=data.get('status');message=str(data.get('message',data.get('msg',''))).lower()
        if 'not found' in message or 'no transaction' in message or status in (0,'0'):
            category='EXPECTED_UNKNOWN_TRANSACTION' if not any(x in message for x in ('invalid key','invalid hash','unauthor','authentic','invalid salt')) else 'AUTHENTICATION_REJECTED'
    if response.status_code==200 and isinstance(data,dict) and data.get('status') in (1,'1') and isinstance(data.get('result'),list):
        rows=data['result']
        if len(rows)==1 and isinstance(rows[0],dict) and any(t in str(rows[0].get('message','')).lower() for t in ('not found','notfound','not exist')):
            category='EXPECTED_UNKNOWN_TRANSACTION'
    result={'provider':'payu','mode':s.payu_mode,'protocol':'v2 JSON / v3 verify_payment','http_status':response.status_code,'result':category,'charge_created':False,'currency_verified':False,'recurring_verified':False}
    destination=ROOT/'data/artifacts/verification/final-product/payu-v3-probe.json';destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
