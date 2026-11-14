"""Install the owner's existing PayU pair on the existing API/worker only.

Never prints values, changes OAuth/Gmail, enables checkout, or creates payments.
API configuration is staged without traffic; paid activation remains disabled.
"""
import json,os,subprocess
from pathlib import Path
from dotenv import dotenv_values
from scripts.deploy_beta_backend import command,CLI,PROJECT,REGION
from scripts.deploy_growth_release import spec
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/artifacts/verification/final-product'

def main():
    os.umask(0o077);values=dotenv_values(ROOT/'.env',interpolate=False)
    if values.get('PAYU_MODE')!='live':raise RuntimeError('Expected the owner-provided Live configuration.')
    for key in ('PAYU_MERCHANT_KEY','PAYU_MERCHANT_SALT'):
        if not values.get(key) or any(x in values[key] for x in ('\n','\r','|')):raise RuntimeError('PayU server credential is missing or malformed.')
    resources=[('services','leadengine-api'),('jobs','leadengine-worker')]
    before={name:command(['run',kind,'describe',name,'--region='+REGION]) for kind,name in resources}
    accounts={spec(before[name],kind)['serviceAccountName'] for kind,name in resources}
    references={}
    for variable,name in [('PAYU_MERCHANT_KEY','leadengine-payu-merchant-key'),('PAYU_MERCHANT_SALT','leadengine-payu-merchant-salt')]:
        found=subprocess.run([CLI,'secrets','describe',name,'--project='+PROJECT,'--format=json'],capture_output=True,text=True)
        if found.returncode:
            if 'NOT_FOUND' not in found.stderr:raise RuntimeError('PayU secret metadata is unavailable.')
            command(['secrets','create',name,'--replication-policy=automatic'])
        existing=subprocess.run([CLI,'secrets','versions','access','latest','--secret='+name,'--project='+PROJECT],capture_output=True,text=True)
        if existing.returncode or existing.stdout!=values[variable]:
            version=command(['secrets','versions','add',name,'--data-file=-'],data=values[variable])['name'].rsplit('/',1)[-1]
        else:
            version=command(['secrets','versions','describe','latest','--secret='+name])['name'].rsplit('/',1)[-1]
        references[variable]=name+':'+version
        for identity in sorted(accounts):command(['secrets','add-iam-policy-binding',name,'--member=serviceAccount:'+identity,'--role=roles/secretmanager.secretAccessor'])
    for kind,name in resources:
        args=['run',kind,'update',name,'--region='+REGION,'--update-secrets='+','.join(k+'='+v for k,v in references.items()),'--update-env-vars=PAYU_MODE=live,PAYU_BILLING_ENABLED=false']
        if kind=='services':args+=['--no-traffic']
        command(args)
    result={'provider':'payu','mode':'live','secret_references':references,'resources':[name for _,name in resources],'public_checkout_enabled':False,'payu_billing_enabled':False,'payment_created':False,'api_traffic_unchanged':True}
    (OUT/'payu-secret-install.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='secret_references'}))
if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'secret_values_disclosed':False}));raise SystemExit(1)
