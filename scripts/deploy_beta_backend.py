"""Explicit, recovery-gated rollout to existing backend and worker resources only."""
import argparse,json,os,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import dotenv_values
from app.database.postgres import PostgresConnection
from app.database.migrations import run_migrations,verify_schema
from scripts.activate_owner_radar_beta import grant

ROOT=Path(__file__).resolve().parents[1]
CLI='/Users/planebyte/Downloads/google-cloud-sdk/bin/gcloud'
PROJECT='querryside';REGION='asia-south1'
EVIDENCE=ROOT/'data/artifacts/verification/beta-activation-20261113'
STATE=ROOT/'data/backups/beta-production-rollout-20261113'
FLAGS={key:'true' for key in ('HEYSOW_WORKSPACE_MANAGEMENT_ENABLED','HEYSOW_COMPANY_DISCOVERY_ENABLED','HEYSOW_COMPANY_AI_ENABLED','HEYSOW_ICP_AI_ENABLED','HEYSOW_LEAD_ASSISTANT_ENABLED','HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED','HEYSOW_CUSTOMER_GMAIL_ENABLED','HEYSOW_WEBHOOKS_ENABLED','HEYSOW_DEVELOPER_API_ENABLED','HEYSOW_MCP_ENABLED','ENABLE_AI_ACQUISITION','ENABLE_FIRECRAWL_ACQUISITION','ENABLE_LEAD_IMPORT','ENABLE_GOOGLE_SHEETS_IMPORT')}
FLAGS.update({key:'false' for key in ('HEYSOW_PUBLIC_REGISTRATION_ENABLED','HEYSOW_INVITED_REGISTRATION_ENABLED','HEYSOW_CUSTOMER_ACCESS_ENABLED','HEYSOW_INTERNAL_EXPERIMENTS_ENABLED','HEYSOW_CUSTOMER_MAIL_SENDING_ENABLED','HEYSOW_CUSTOMER_MAIL_LIVE_APPROVED','AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED','LIGHTHOUSE_ENABLED','INTENT_RADAR_STACKEXCHANGE_ENABLED')})
FLAGS.update(ALLOWED_USER_EMAILS='planebyte@gmail.com',INTENT_RADAR_STAGE='Beta',INTENT_RADAR_AI_ENABLED='true',INTENT_RADAR_SCHEDULES_ENABLED='true',INTENT_RADAR_MIN_SCHEDULE_HOURS='6',INTENT_RADAR_AI_DAILY_CALLS='50',INTENT_RADAR_AI_DAILY_TOKENS='100000',MCP_ALLOWED_HOSTS='leadengine-api-befca7xg4a-el.a.run.app',MCP_ALLOWED_ORIGINS='https://app.planebyte.com',HEYSOW_CUSTOMER_GMAIL_REDIRECT_URI='https://app.planebyte.com/settings/integrations/gmail-callback')

def command(args,*,data=None):
    p=subprocess.run([CLI,*args,'--project='+PROJECT,'--format=json','--quiet'],input=data,capture_output=True,text=True,timeout=420)
    if p.returncode:raise RuntimeError('Cloud operation failed: '+' '.join(args[:4]))
    return json.loads(p.stdout) if p.stdout.strip() else {}

def save(name,value):
    (STATE/name).write_text(json.dumps(value,indent=2));(STATE/name).chmod(0o600)

def prepare():
    os.umask(0o077);STATE.mkdir(mode=0o700,exist_ok=False)
    for kind,name in [('services','leadengine-api'),('jobs','leadengine-worker'),('jobs','leadengine-acquisition'),('jobs','leadengine-quota-canary')]:
        save(name+'.json',command(['run',kind,'describe',name,'--region='+REGION]))
    jobs=command(['scheduler','jobs','list','--location='+REGION]);save('schedulers.json',jobs)
    for job in jobs:
        name=job['name'].rsplit('/',1)[-1]
        if job['state']=='ENABLED' and name in ('leadengine-hourly-outreach','leadengine-inbox-sync'):
            command(['scheduler','jobs','pause',name,'--location='+REGION])
    print(json.dumps({'snapshots_saved':True,'maintenance_schedulers_paused':True,'outreach_remains_disabled':True}),flush=True)

def encryption_secret():
    values=dotenv_values(ROOT/'.env',interpolate=False);value=values.get('HEYSOW_INTEGRATION_ENCRYPTION_KEY','')
    from cryptography.fernet import Fernet
    Fernet(value.encode())
    name='leadengine-integration-encryption-key'
    found=subprocess.run([CLI,'secrets','describe',name,'--project='+PROJECT,'--format=json'],capture_output=True,text=True)
    if found.returncode:
        if 'NOT_FOUND' not in found.stderr:raise RuntimeError('Secret metadata unavailable.')
        command(['secrets','create',name,'--replication-policy=automatic'])
    current=subprocess.run([CLI,'secrets','versions','access','latest','--secret='+name,'--project='+PROJECT],capture_output=True,text=True)
    if current.returncode or current.stdout!=value:
        version=command(['secrets','versions','add',name,'--data-file=-'],data=value)['name'].rsplit('/',1)[-1]
    else:version='latest'
    for identity in ('leadengine-api-sa','leadengine-worker-sa','leadengine-acquisition-sa'):
        command(['secrets','add-iam-policy-binding',name,'--member=serviceAccount:'+identity+'@querryside.iam.gserviceaccount.com','--role=roles/secretmanager.secretAccessor'])
    return name+':'+version

def release():
    tests=ET.parse(EVIDENCE/'backend-locked-pg18-final.xml').getroot()
    suites=list(tests) if tests.tag=='testsuites' else [tests]
    if not suites or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('Critical regression gate failed.')
    result=json.loads((EVIDENCE/'recovery-history-final.json').read_text())
    if result.get('original_columns_preserved') is not True:raise RuntimeError('Recovery preservation gate failed.')
    if not (STATE/'leadengine-api.json').is_file():raise RuntimeError('Production snapshots and maintenance pause required.')
    values=dotenv_values(ROOT/'.env',interpolate=False)
    c=PostgresConnection(values['DATABASE_URL'],session_bound=True)
    try:
        if c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED')").fetchone()[0]:raise RuntimeError('An existing scan is active; drain it before migration.')
        before=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        if before not in (15,44):raise RuntimeError('Unexpected production schema.')
        applied=run_migrations(c) if before==15 else 0;verify_schema(c)
        access=grant(c,'planebyte@gmail.com',apply=True);c.commit()
    except Exception:c.rollback();raise
    finally:c.close()
    save('migration-and-grant.json',{'schema_before':before,'migrations_applied':applied,'schema_after':44,'verified_beta_grant':access})
    print(json.dumps({'schema':44,'migrations_applied':applied,'verified_beta_workspace':access['organization_id']}),flush=True)
    secret=encryption_secret();environment='^~^'+'~'.join(key+'='+value for key,value in FLAGS.items())
    for kind,name,image in [('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','worker'),('jobs','leadengine-quota-canary','worker'),('services','leadengine-api','api')]:
        old=json.loads((STATE/(name+'.json')).read_text());spec=old['spec']['template']['spec'];spec=spec if kind=='services' else spec['template']['spec']
        oldenv={r['name']:r for r in spec['containers'][0].get('env',[])}
        args=['run',kind,'update',name,'--region='+REGION,'--image=asia-south1-docker.pkg.dev/querryside/leadengine/'+image+':beta-20261113-r1','--update-env-vars='+environment,'--update-secrets=HEYSOW_INTEGRATION_ENCRYPTION_KEY='+secret]
        if 'valueFrom' in oldenv.get('ALLOWED_USER_EMAILS',{}):args+=['--remove-secrets=ALLOWED_USER_EMAILS']
        if name=='leadengine-acquisition':args+=['--command=python','--args=-m,app.acquisition.worker']
        if kind=='services':args+=['--no-traffic','--tag=beta']
        updated=command(args);save(name+'-updated.json',updated)
        now=updated['spec']['template']['spec'];now=now if kind=='services' else now['template']['spec']
        if now['serviceAccountName']!=spec['serviceAccountName']:raise RuntimeError('Runtime identity changed.')
        ignored=set(FLAGS)|{'HEYSOW_INTEGRATION_ENCRYPTION_KEY'}
        if {k:v for k,v in oldenv.items() if k not in ignored}!={r['name']:r for r in now['containers'][0].get('env',[]) if r['name'] not in ignored}:raise RuntimeError('Unrelated runtime configuration changed.')
        print(json.dumps({'updated':name,'existing_identity_preserved':True}),flush=True)
    api=json.loads((STATE/'leadengine-api-updated.json').read_text());revision=api['status']['latestReadyRevisionName']
    if revision!=api['status']['latestCreatedRevisionName']:raise RuntimeError('New API revision is not ready.')
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+revision+'=100'])
    save('promoted.json',{'revision':revision,'url':api['status']['url'],'outreach_enabled':False})
    print(json.dumps({'promoted':revision,'url':api['status']['url'],'outreach_enabled':False}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','release']);args=p.parse_args()
    try:prepare() if args.action=='prepare' else release()
    except Exception as error:
        print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'safe_error':str(error) if isinstance(error,RuntimeError) else 'Inspect restricted rollout state; no credentials printed.'}));raise SystemExit(1)
