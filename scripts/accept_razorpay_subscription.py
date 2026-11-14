"""Owner-controlled Test Mode subscription acceptance, with stable request IDs.

No lead acquisition, outreach, real money, pricing approval or public enrollment.
"""
import argparse,asyncio,json,uuid
from pathlib import Path
from scripts.accept_growth_production import Acceptance
OUT=Path(__file__).resolve().parents[1]/'data/artifacts/verification/razorpay'
STATE=OUT/'subscription-acceptance-state.json'
async def run(action):
    a=Acceptance();state=json.loads(STATE.read_text()) if STATE.exists() else {}
    def save():STATE.write_text(json.dumps(state,indent=2));STATE.chmod(0o600)
    try:
        if action=='create':
            state.setdefault('request_id',str(uuid.uuid4()));save()
            body={'plan_code':'starter','request_id':state['request_id'],'confirm_test_mode':True}
            row=await a.request('POST','/api/organization/billing/subscriptions',body)
            state['subscription_id']=row['id'];state['created_status']=row['status'];save()
            duplicate=await a.request('POST','/api/organization/billing/subscriptions',body)
            if duplicate['id']!=row['id']:raise RuntimeError('Duplicate subscription request created another record.')
            state['creation_idempotency']=True
            checkout=await a.request('GET','/api/organization/billing/subscriptions/'+row['id']+'/checkout')
            if checkout['mode']!='test' or not checkout['key'].startswith('rzp_test_'):raise RuntimeError('Test checkout guard failed.')
            state['provider_subscription_id']=checkout['subscription_id'];state['checkout_url']='https://app.planebyte.com/billing/checkout?subscription='+row['id'];save()
            print(json.dumps({'mode':'test','created_status':row['status'],'idempotency_verified':True,'checkout_url':state['checkout_url'],'charges_created':False}))
        else:
            if not state.get('subscription_id'):raise RuntimeError('Create the controlled subscription first.')
            row=await a.request('POST','/api/organization/billing/subscriptions/'+state['subscription_id']+'/reconcile')
            state['reconciled']=row
            info=await a.request('GET','/api/organization/billing');state['payment_count']=len(info['payments']);save()
            print(json.dumps({'mode':'test','status':row['status'],'settled_current_period':row['settled_current_period'],'verified_payment_count':state['payment_count']}))
    finally:await a.client.aclose()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['create','reconcile']);args=p.parse_args()
    try:asyncio.run(run(args.action))
    except Exception as error:print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect private controlled state; no credentials printed.'}));raise SystemExit(1)
