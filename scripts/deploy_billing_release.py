"""Recovery-gated billing rollout on existing resources; no live/public payments.

First promote a schema-45/46 compatible, billing-disabled bridge. Only then apply
one additive migration. Every rollback keeps a compatible binary and stored data.
"""
import argparse,hashlib,hmac,json,os,secrets,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import dotenv_values
import httpx
from app.database.postgres import PostgresConnection
from app.database.migrations import run_migrations,verify_schema
from scripts.deploy_beta_backend import command,CLI,PROJECT,REGION
from scripts.deploy_growth_release import spec
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/artifacts/verification/razorpay'
STATE=ROOT/'data/backups/billing-release-20261113'
ORG='e5ffc3dc-241e-5558-acd4-84f5fe354ca7'
RESOURCES=[('services','leadengine-api','api'),('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','worker'),('jobs','leadengine-quota-canary','worker')]
ORIGIN='https://leadengine-api-befca7xg4a-el.a.run.app'
GUARDS=('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED','HEYSOW_PUBLIC_REGISTRATION_ENABLED')
FLAGS={'BILLING_ENABLED':'true','BILLING_PROVIDER':'razorpay','BILLING_TEST_MODE':'true','BILLING_PUBLIC_CHECKOUT_ENABLED':'false','BILLING_TEST_WORKSPACES':ORG,'RAZORPAY_MODE':'test','LEAD_ENGINE_PUBLIC_ENABLED':'false'}

def save(name,data):
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700);p=STATE/name;p.write_text(json.dumps(data,indent=2));p.chmod(0o600)

def gates():
    suites=ET.parse(OUT.parent/'billing-backend-final.xml').getroot()
    suites=list(suites) if suites.tag=='testsuites' else [suites]
    if sum(int(s.get('tests',0)) for s in suites)<950 or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('The final full billing/backend suite must pass.')
    for name in ('billing-browser-results.json','phase4-browser-results.json'):
        report=json.loads((OUT.parent/name).read_text())['stats']
        if report.get('unexpected',1) or report.get('expected',0)<2:raise RuntimeError('Browser regression gate failed.')
    if '148 passed' not in (OUT.parent/'billing-frontend-units-final.log').read_text():raise RuntimeError('Full frontend unit gate is missing.')
    if 'Compiled successfully' not in (OUT.parent/'billing-handoff-build.log').read_text():raise RuntimeError('Final isolated production build is missing.')
    recovery=sorted((ROOT/'data/backups').glob('beta-recovery-*/recovery-result.json'))[-1]
    record=json.loads(recovery.read_text());history=json.loads((recovery.parent/'history-preservation.json').read_text())
    if record['source_schema']!=45 or record['target_schema']!=46 or record['migrations_applied']!=1 or record['second_migration_run']!=0 or not history['original_columns_preserved'] or history['source_backup_sha256']!=record['backup_sha256']:raise RuntimeError('Exact schema 45→46 backup/restore preservation is required.')
    if hashlib.sha256(Path(record['backup']).read_bytes()).hexdigest()!=record['backup_sha256']:raise RuntimeError('Rollback snapshot checksum changed.')
    build=json.loads((OUT/'build.json').read_text())
    verified=command(['builds','describe',build['build_id']])
    if verified['status']!='SUCCESS' or verified['substitutions']['_SOURCE_REV']!=build['source_commit']:raise RuntimeError('Exact committed images are not verified.')
    return record,build

def update(kind,name,image,flags,bindings=None,tag=None):
    before=command(['run',kind,'describe',name,'--region='+REGION]);old=spec(before,kind);oldenv={x['name']:x for x in old['containers'][0].get('env',[])}
    for guard in GUARDS:
        if oldenv.get(guard,{}).get('value')!='false':raise RuntimeError('A production delivery/registration guard changed: '+guard)
    args=['run',kind,'update',name,'--region='+REGION,'--image='+image,'--update-env-vars=^~^'+'~'.join(k+'='+v for k,v in flags.items())]
    if bindings:args.append('--update-secrets='+','.join(k+'='+v for k,v in bindings.items()))
    if kind=='services':args+=['--no-traffic','--tag='+tag]
    result=command(args);new=spec(result,kind);newenv={x['name']:x for x in new['containers'][0].get('env',[])}
    if old['serviceAccountName']!=new['serviceAccountName'] or old['containers'][0].get('command')!=new['containers'][0].get('command') or old['containers'][0].get('args')!=new['containers'][0].get('args'):raise RuntimeError('An existing runtime identity or command changed.')
    changed=set(flags)|set(bindings or {})
    if {k:v for k,v in oldenv.items() if k not in changed}!={k:v for k,v in newenv.items() if k not in changed}:raise RuntimeError('Unrelated environment/secret references changed.')
    save(name+'-'+(tag or 'worker')+'.json',result);return result

def read_smoke(origin):
    values=dotenv_values(ROOT/'.env',interpolate=False);checks={}
    with httpx.Client(base_url=origin,timeout=90,follow_redirects=False) as client:
        for path in ('/api/health','/api/organization/products','/api/intent-radar/capabilities','/api/intent-radar/growth/overview?days=0','/api/workflow/safety'):
            headers={}
            if path!='/api/health':
                stamp=str(int(time.time()));nonce=secrets.token_hex(24);actor='planebyte@gmail.com';canonical='\n'.join((stamp,nonce,'GET',path,hashlib.sha256(b'').hexdigest(),actor))
                headers={'x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':hmac.new(values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical.encode(),hashlib.sha256).hexdigest()}
            r=client.get(path,headers=headers);checks[path]=r.status_code
            if r.status_code!=200:raise RuntimeError('Controlled read smoke failed at '+path)
            if path.endswith('/safety') and r.json().get('sending_enabled'):raise RuntimeError('Sending must remain disabled.')
    return checks

def prepare():
    os.umask(0o077)
    if STATE.exists():raise RuntimeError('A billing checkpoint exists; inspect and reuse it.')
    STATE.mkdir(parents=True,mode=0o700)
    for kind,name,_ in RESOURCES:save(name+'-before.json',command(['run',kind,'describe',name,'--region='+REGION]))
    save('schedulers-before.json',command(['scheduler','jobs','list','--location='+REGION]))
    print(json.dumps({'snapshots_saved':True,'production_changed':False}))

def bridge():
    record,build=gates()
    if not (STATE/'schedulers-before.json').is_file():raise RuntimeError('Capture existing infrastructure before rollout.')
    jobs=json.loads((STATE/'schedulers-before.json').read_text())
    for job in jobs:
        if job['name'].endswith('/leadengine-intent-radar-dispatch') and job['state']=='ENABLED':command(['scheduler','jobs','pause',job['name'],'--location='+REGION])
    result=update('services','leadengine-api',build['api_image'],{'BILLING_ENABLED':'false','LEAD_ENGINE_PUBLIC_ENABLED':'false'},tag='billing-bridge')
    checks=read_smoke('https://billing-bridge---leadengine-api-befca7xg4a-el.a.run.app')
    for kind,name,image in RESOURCES:
        if kind=='jobs':update(kind,name,build['worker_image'],{'BILLING_ENABLED':'false','LEAD_ENGINE_PUBLIC_ENABLED':'false'})
    revision=result['status']['latestReadyRevisionName']
    if revision!=result['status']['latestCreatedRevisionName']:raise RuntimeError('Bridge revision did not become ready.')
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+revision+'=100'])
    save('compatible-bridge.json',{'revision':revision,'source_commit':build['source_commit'],'billing_enabled':False,'schema_support':[45,46],'smoke':checks})
    print(json.dumps({'compatible_bridge_promoted':revision,'billing_enabled':False}))

def secrets_config():
    values=dotenv_values(ROOT/'.env',interpolate=False)
    names={'RAZORPAY_KEY_ID':'leadengine-razorpay-test-key-id','RAZORPAY_KEY_SECRET':'leadengine-razorpay-test-key-secret','RAZORPAY_WEBHOOK_SECRET':'leadengine-razorpay-test-webhook-secret'}
    if not values.get('RAZORPAY_KEY_ID','').startswith('rzp_test_') or not values.get('RAZORPAY_KEY_SECRET') or not values.get('RAZORPAY_WEBHOOK_SECRET') or values['RAZORPAY_KEY_SECRET']==values['RAZORPAY_WEBHOOK_SECRET']:raise RuntimeError('Separate Test Mode credentials and webhook secret are required.')
    known={row['name'].rsplit('/',1)[-1] for row in command(['secrets','list'])};bindings={}
    for variable,name in names.items():
        if name not in known:command(['secrets','create',name,'--replication-policy=automatic'])
        old=subprocess.run([CLI,'secrets','versions','access','latest','--secret='+name,'--project='+PROJECT],capture_output=True,text=True,timeout=30)
        version='latest'
        if old.returncode or not hmac.compare_digest(old.stdout,values[variable]):version=command(['secrets','versions','add',name,'--data-file=-'],data=values[variable])['name'].rsplit('/',1)[-1]
        identities=['leadengine-api-sa']+(['leadengine-worker-sa'] if variable!='RAZORPAY_WEBHOOK_SECRET' else [])
        for identity in identities:command(['secrets','add-iam-policy-binding',name,'--member=serviceAccount:'+identity+'@querryside.iam.gserviceaccount.com','--role=roles/secretmanager.secretAccessor'])
        bindings[variable]=name+':'+version
    save('secret-references.json',bindings);return bindings

def activate():
    record,build=gates()
    if not (STATE/'compatible-bridge.json').is_file():raise RuntimeError('Promote the compatible flag-off bridge before migrating.')
    values=dotenv_values(ROOT/'.env',interpolate=False);c=PostgresConnection(values['DATABASE_URL'],session_bound=True)
    try:
        before=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        if before not in (45,46):raise RuntimeError('Unexpected production schema.')
        owner=c.execute("SELECT 1 FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id JOIN organization_products p ON p.organization_id=o.id AND p.product='INTENT_RADAR' WHERE m.organization_id=? AND m.user_id='planebyte@gmail.com' AND m.role='OWNER' AND m.status='ACTIVE' AND o.status='ACTIVE' AND p.enabled=1",(ORG,)).fetchone()
        if not owner:raise RuntimeError('The approved beta workspace ownership cannot be verified.')
        applied=run_migrations(c) if before==45 else 0;verify_schema(c,minimum_version=46);c.commit()
    except Exception:c.rollback();raise
    finally:c.close()
    save('migration.json',{'before':before,'after':46,'applied':applied,'backup_sha256':record['backup_sha256'],'original_columns_preserved':True})
    bindings=secrets_config()
    for kind,name,image in RESOURCES:
        if kind!='jobs':continue
        subset={k:v for k,v in bindings.items() if name=='leadengine-worker' and k!='RAZORPAY_WEBHOOK_SECRET'}
        update(kind,name,build['worker_image'],FLAGS,subset)
    result=update('services','leadengine-api',build['api_image'],FLAGS,bindings,tag='billing')
    revision=result['status']['latestReadyRevisionName']
    if revision!=result['status']['latestCreatedRevisionName']:raise RuntimeError('Billing revision did not become ready.')
    save('ready-to-promote.json',{'revision':revision,'source_commit':build['source_commit'],'workspace':ORG,'mode':'test','public_checkout':False})
    print(json.dumps({'ready_revision':revision,'schema':46,'mode':'test','public_checkout':False,'traffic_promoted':False}))

def promote():
    gates();state=json.loads((STATE/'ready-to-promote.json').read_text())
    checks=read_smoke('https://billing---leadengine-api-befca7xg4a-el.a.run.app')
    values=dotenv_values(ROOT/'.env',interpolate=False)
    body=json.dumps({'event':'subscription.activated','payload':{'subscription':{'entity':{'id':'sub_unlinkedcontrolledprobe'}}}},separators=(',',':')).encode()
    with httpx.Client(base_url='https://billing---leadengine-api-befca7xg4a-el.a.run.app',timeout=60,follow_redirects=False) as c:
        path='/api/billing/webhooks/razorpay'
        rejected=c.post(path,content=body,headers={'x-razorpay-signature':'0'*64,'x-razorpay-event-id':'controlled-invalid-signature'})
        signature=hmac.new(values['RAZORPAY_WEBHOOK_SECRET'].encode(),body,hashlib.sha256).hexdigest()
        accepted=c.post(path,content=body,headers={'x-razorpay-signature':signature,'x-razorpay-event-id':'controlled-unlinked-signature-probe'})
        if rejected.status_code!=400 or accepted.status_code!=202 or not accepted.json().get('ignored'):raise RuntimeError('The exact raw webhook security check failed.')
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+state['revision']+'=100'])
    for job in json.loads((STATE/'schedulers-before.json').read_text()):
        if job['name'].endswith('/leadengine-intent-radar-dispatch') and job['state']=='ENABLED':command(['scheduler','jobs','resume',job['name'],'--location='+REGION])
    save('promoted.json',{**state,'smoke':checks,'invalid_signature_http':400,'valid_unlinked_signature_http':202,'merchant_webhook_delivery_verified':False,'webhook_url':ORIGIN+'/api/billing/webhooks/razorpay'})
    print(json.dumps({'promoted':state['revision'],'mode':'test','webhook_url':ORIGIN+'/api/billing/webhooks/razorpay','signed_endpoint_probe_passed':True,'real_razorpay_transaction_verified':False}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','bridge','activate','promote']);a=p.parse_args()
    try:globals()[a.action]()
    except Exception as error:print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect restricted release evidence; credentials withheld.'}));raise SystemExit(1)
