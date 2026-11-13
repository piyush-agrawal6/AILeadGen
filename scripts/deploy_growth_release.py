"""Recovery-gated additive rollout to the existing API and worker resources.

Never creates frontend infrastructure, rotates secrets, grants IAM, resets data,
changes identities, enables public signup or enables email sending.
"""
import argparse,json,os,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from dotenv import dotenv_values
from app.database.postgres import PostgresConnection
from app.database.migrations import run_migrations,verify_schema
from scripts.deploy_beta_backend import command,PROJECT,REGION

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'data/artifacts/verification'
STATE=ROOT/'data/backups/growth-release-20261113'
RESOURCES=[('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','worker'),('jobs','leadengine-quota-canary','worker'),('services','leadengine-api','api')]

def save(name,value):
    (STATE/name).write_text(json.dumps(value,indent=2));(STATE/name).chmod(0o600)

def spec(value,kind):
    result=value['spec']['template']['spec']
    return result if kind=='services' else result['template']['spec']

def prepare():
    os.umask(0o077);STATE.mkdir(mode=0o700,exist_ok=False)
    for kind,name,_ in RESOURCES:save(name+'.json',command(['run',kind,'describe',name,'--region='+REGION]))
    jobs=command(['scheduler','jobs','list','--location='+REGION]);save('schedulers.json',jobs)
    save('source-checkpoint.json',{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    print(json.dumps({'snapshots_saved':True,'production_changed':False}))

def gates():
    suites=ET.parse(EVIDENCE/'phase4-backend-full-running-pg.xml').getroot()
    suites=list(suites) if suites.tag=='testsuites' else [suites]
    if not suites or sum(int(s.get('tests',0)) for s in suites)<900 or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('Full backend security/regression gate is not passing.')
    browser=json.loads((EVIDENCE/'phase4-browser-results.json').read_text())
    stats=browser.get('stats',{})
    if stats.get('unexpected',1) or stats.get('expected',0)<2:raise RuntimeError('Growth browser gate is not passing.')
    recovery=sorted((ROOT/'data/backups').glob('beta-recovery-*/recovery-result.json'))[-1]
    record=json.loads(recovery.read_text());history=json.loads((recovery.parent/'history-preservation.json').read_text())
    if record['source_schema']!=44 or record['target_schema']!=45 or not history['original_columns_preserved'] or record['backup_sha256']!=history['source_backup_sha256']:raise RuntimeError('Exact schema 44→45 recovery preservation is required.')
    if not (STATE/'leadengine-api.json').exists():raise RuntimeError('Fresh runtime checkpoints are required.')
    return record

def release(api_image,worker_image):
    record=gates()
    for image,kind in ((api_image,'api'),(worker_image,'worker')):
        if not image.startswith('asia-south1-docker.pkg.dev/querryside/leadengine/'+kind+':growth-'):raise RuntimeError('Expected verified existing-project Growth image.')
    settings=dotenv_values(ROOT/'.env',interpolate=False)
    c=PostgresConnection(settings['DATABASE_URL'],session_bound=True)
    try:
        before=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        if before not in (44,45):raise RuntimeError('Unexpected production schema; stop for review.')
        owner=c.execute("SELECT m.organization_id FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id JOIN organization_products p ON p.organization_id=o.id AND p.product='INTENT_RADAR' WHERE m.user_id='planebyte@gmail.com' AND m.role='OWNER' AND m.status='ACTIVE' AND p.enabled=1 AND o.slug='planebyte'").fetchall()
        if len(owner)!=1 or owner[0][0]!='e5ffc3dc-241e-5558-acd4-84f5fe354ca7':raise RuntimeError('Existing owner-only beta grant could not be verified.')
        if c.execute("SELECT COUNT(*) FROM organization_products WHERE product='INTENT_RADAR' AND enabled=1").fetchone()[0]!=1:raise RuntimeError('Unexpected additional beta workspaces; no broad activation authorized.')
        applied=run_migrations(c) if before==44 else 0;verify_schema(c);c.commit()
    except Exception:c.rollback();raise
    finally:c.close()
    save('migration.json',{'before':before,'after':45,'applied':applied,'backup_sha256':record['backup_sha256'],'owner_beta_workspace':owner[0][0]})
    for kind,name,image_kind in RESOURCES:
        current=command(['run',kind,'describe',name,'--region='+REGION]);old=spec(current,kind)
        save(name+'-pre-update.json',current)
        env={r['name']:r for r in old['containers'][0].get('env',[])}
        for flag in ('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED','HEYSOW_PUBLIC_REGISTRATION_ENABLED'):
            if env.get(flag,{}).get('value')!='false':raise RuntimeError('Production sending/registration guard is not explicitly false: '+flag)
        args=['run',kind,'update',name,'--region='+REGION,'--image='+(api_image if image_kind=='api' else worker_image),'--update-env-vars=INTENT_RADAR_GROWTH_ENABLED=true']
        if kind=='services':args+=['--no-traffic','--tag=growth']
        updated=command(args);save(name+'-updated.json',updated);new=spec(updated,kind)
        if old['serviceAccountName']!=new['serviceAccountName']:raise RuntimeError('Runtime identity changed unexpectedly.')
        if old['containers'][0].get('command')!=new['containers'][0].get('command') or old['containers'][0].get('args')!=new['containers'][0].get('args'):raise RuntimeError('Existing worker command changed.')
        previous={k:v for k,v in env.items() if k!='INTENT_RADAR_GROWTH_ENABLED'}
        actual={r['name']:r for r in new['containers'][0].get('env',[]) if r['name']!='INTENT_RADAR_GROWTH_ENABLED'}
        if previous!=actual:raise RuntimeError('Unrelated environment or secret references changed.')
        print(json.dumps({'updated':name,'identity_and_unrelated_configuration_preserved':True}),flush=True)
    api=json.loads((STATE/'leadengine-api-updated.json').read_text());revision=api['status']['latestReadyRevisionName']
    if revision!=api['status']['latestCreatedRevisionName']:raise RuntimeError('New API revision did not become ready.')
    save('ready-to-promote.json',{'revision':revision,'url':api['status']['url'],'traffic_promoted':False})
    print(json.dumps({'ready_revision':revision,'traffic_promoted':False}),flush=True)

def promote():
    gates();record=json.loads((STATE/'ready-to-promote.json').read_text())
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+record['revision']+'=100'])
    save('promoted.json',{**record,'traffic_promoted':True});print(json.dumps({'promoted':record['revision'],'url':record['url']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','release','promote']);parser.add_argument('--api-image');parser.add_argument('--worker-image');args=parser.parse_args()
    try:
        if args.action=='prepare':prepare()
        elif args.action=='release':release(args.api_image or '',args.worker_image or '')
        else:promote()
    except Exception as error:
        print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect restricted release evidence. Credentials are never printed.'}));raise SystemExit(1)
