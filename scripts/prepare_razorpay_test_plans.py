"""Create/reuse exactly three internal sandbox plans; never a subscription/charge.

Credentials remain in memory. A restricted journal prevents blind POST retries;
provider notes and full price/period checks are required before reusing a plan.
"""
import hashlib,json,os
from pathlib import Path
from dotenv import dotenv_values
import httpx
from app.billing.catalog import plans
from app.billing.provider import verify_plan
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/artifacts/verification/razorpay'

def main():
    os.umask(0o077);OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
    values=dotenv_values(ROOT/'.env',interpolate=False)
    key,secret=values.get('RAZORPAY_KEY_ID',''),values.get('RAZORPAY_KEY_SECRET','')
    if not key.startswith('rzp_test_') or not secret:raise RuntimeError('Razorpay Test Mode credentials are not configured.')
    file=OUT/'test-plan-mappings.json';state=json.loads(file.read_text()) if file.exists() else {}
    def save():file.write_text(json.dumps(state,indent=2));file.chmod(0o600)
    with httpx.Client(base_url='https://api.razorpay.com/v1/',auth=(key,secret),timeout=15,follow_redirects=False) as client:
        def api(method,path,**kwargs):
            response=client.request(method,path,**kwargs)
            if response.status_code>=300:raise RuntimeError('Razorpay rejected a bounded test-plan operation (HTTP '+str(response.status_code)+').')
            if len(response.content)>500000:raise RuntimeError('Provider response is too large.')
            return response.json()
        existing=[]
        for offset in range(0,500,100):
            page=api('GET','plans',params={'count':100,'skip':offset})['items'];existing.extend(page)
            if len(page)<100:break
        else:raise RuntimeError('Plan history exceeds the bounded reconciliation window; no new plans created.')
        for code,p in plans().items():
            if code=='enterprise':continue
            digest=hashlib.sha256(p.model_copy(update={'provider_plan_id':None}).model_dump_json().encode()).hexdigest()
            candidates=[row for row in existing if (row.get('notes') or {}).get('planebyte_catalog_hash')==digest and (row.get('notes') or {}).get('product')=='INTENT_RADAR' and (row.get('notes') or {}).get('mode')=='test']
            mapped=p.provider_plan_id or state.get(code,{}).get('provider_plan_id')
            if mapped:candidates=[api('GET','plans/'+mapped)]
            if len(candidates)>1:raise RuntimeError('Duplicate matching provider plans require review.')
            if candidates:remote=candidates[0]
            else:
                if state.get(code,{}).get('status')=='CREATING':raise RuntimeError('A previous plan POST outcome is unknown; no blind retry.')
                state[code]={'status':'CREATING','catalog_hash':digest};save()
                remote=api('POST','plans',json={'period':p.period,'interval':p.interval,'item':{'name':'Intent Radar '+code.title()+' — internal test only','description':'Sandbox integration fixture. Not approved commercial pricing. No live charges.','amount':p.amount,'currency':p.currency},'notes':{'product':'INTENT_RADAR','mode':'test','planebyte_catalog_hash':digest}})
            verified=p.model_copy(update={'provider_plan_id':remote['id']});verify_plan(verified,remote)
            state[code]={'status':'VERIFIED','provider_plan_id':remote['id'],'catalog_hash':digest,'plan':verified.model_dump(),'test_only':True};save()
    print(json.dumps({'test_api_authenticated':True,'verified_test_plans':list(state),'plans_created_or_reused':3,'charges_created':0,'credentials_printed':False}))
if __name__=='__main__':
    try:main()
    except Exception as error:print(json.dumps({'status':'BLOCKED','error':str(error) if isinstance(error,RuntimeError) else type(error).__name__,'credentials_printed':False}));raise SystemExit(1)
