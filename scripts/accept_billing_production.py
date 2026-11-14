"""Read-only financial/customer acceptance plus unlinked raw-signature probes.

Never creates a subscription, invoice, payment, lead, scan, campaign or email.
Provider authentication/lifecycle acceptance is recorded separately, never inferred.
"""
import asyncio,hashlib,hmac,json
from pathlib import Path
from scripts.accept_growth_production import Acceptance
OUT=Path(__file__).resolve().parents[1]/'data/artifacts/verification/razorpay'
async def main():
    a=Acceptance();proof={}
    try:
        products=await a.request('GET','/api/organization/products')
        billing=await a.request('GET','/api/organization/billing')
        safety=await a.request('GET','/api/workflow/safety')
        await a.request('GET','/api/organization/billing',actor='unapproved-billing-check@example.invalid',expected=(401,403))
        if not products.get('billing_enabled') or not products['intent_radar']['enabled'] or not products['lead_engine']:raise RuntimeError('The owner grant or billing module changed unexpectedly.')
        if billing['mode']!='test' or billing['public_checkout_enabled'] or not billing['controlled_workspace'] or safety.get('sending_enabled'):raise RuntimeError('A payment, tenant or mail safety guard failed.')
        path='/api/billing/webhooks/razorpay'
        raw=json.dumps({'event':'subscription.activated','payload':{'subscription':{'entity':{'id':'sub_unlinkedcontrolledprobe'}}}},separators=(',',':')).encode()
        bad=await a.client.post(path,content=raw,headers={'x-razorpay-signature':'0'*64,'x-razorpay-event-id':'production-invalid-signature-probe'})
        signature=hmac.new(a.values['RAZORPAY_WEBHOOK_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
        good=await a.client.post(path,content=raw,headers={'x-razorpay-signature':signature,'x-razorpay-event-id':'production-unlinked-controlled-probe'})
        other=await a.client.post(path+'/other',content=raw)
        if (bad.status_code,good.status_code,other.status_code)!=(400,202,401) or not good.json().get('ignored'):raise RuntimeError('Public raw-signature route isolation did not pass.')
        proof={'production_url':str(a.client.base_url).rstrip('/')+path,'invalid_signature_http':bad.status_code,'valid_unlinked_signature_http':good.status_code,'neighbor_route_auth_http':other.status_code,'mode':billing['mode'],'public_checkout':False,'owner_workspace_restricted':True,'existing_lead_engine_grant_preserved':True,'radar_enabled':True,'sending_enabled':False,'provider_credentials_present':billing['provider_configured'],'webhook_secret_configured':billing['webhook_configured'],'subscriptions':len(billing['subscriptions']),'verified_payments':len(billing['payments']),'mapped_test_plans':sum(bool(p['provider_plan_id']) for p in billing['plans']),'real_provider_transaction_verified':False,'merchant_webhook_delivery_verified':False}
        p=OUT/'production-endpoint-acceptance.json';p.write_text(json.dumps(proof,indent=2));p.chmod(0o600);print(json.dumps(proof))
    finally:await a.client.aclose()
if __name__=='__main__':
    try:asyncio.run(main())
    except Exception as error:print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect restricted acceptance evidence; credentials withheld.'}));raise SystemExit(1)
