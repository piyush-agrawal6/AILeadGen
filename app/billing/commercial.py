"""Approved list prices, separate from historical sandbox contract snapshots.

This packaged JSON is the sole commercial catalog. Marketing receives a checked
copy, never a second hand-maintained price list. Null limits are not unlimited.
"""
import hashlib,json
from pathlib import Path
from fastapi import HTTPException

PATH=Path(__file__).with_name('commercial_catalog.json')

def catalog():
    data=json.loads(PATH.read_text())
    expected={'starter':5900,'growth':14900,'scale':37900,'enterprise':None}
    if {p['code']:p['monthly_minor'] for p in data['plans']}!=expected or data['list_currency']!='USD' or data['interval']!='monthly':
        raise RuntimeError('Approved commercial catalog contract is invalid.')
    # Opening checkout requires separate verified payment activation, not a
    # marketing file edit. Existing subscriptions retain their own plan snapshot.
    data['checkout_enabled']=False
    data['catalog_sha256']=hashlib.sha256(PATH.read_bytes()).hexdigest()
    return data

def plan(code):
    selected=next((p for p in catalog()['plans'] if p['code']==code),None)
    if selected is None:raise HTTPException(422,'Choose an approved Intent Radar plan.')
    return selected

def checkout_blockers():
    from app.billing.payu import configuration_status
    result=configuration_status()['blockers']
    if not catalog()['allowances_approved']:result.append('Commercial numeric allowances are awaiting owner approval.')
    result.extend(['Charge currency and tax disclosures are not yet approved.','Recurring payment acceptance and explicit public-checkout authorization are pending.'])
    return result
