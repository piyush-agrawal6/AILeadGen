"""Verified Intent-only release on existing Cloud Run resources, no data writes.

Availability is independent of persisted entitlement rows. Only the source image
and LEAD_ENGINE_AVAILABLE may change. Auth, mail, billing, identities, scheduler
configuration and secret references are compared before promotion.
"""
import argparse, copy, hashlib, hmac, json, os, secrets, subprocess, time
import xml.etree.ElementTree as ET
from pathlib import Path
import httpx
from dotenv import dotenv_values
from scripts.deploy_beta_backend import command, REGION
from scripts.deploy_growth_release import spec
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/artifacts/verification/intent-only'
RESOURCES=[('services','leadengine-api','api'),('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','worker'),('jobs','leadengine-quota-canary','worker')]
ORIGIN='https://leadengine-api-befca7xg4a-el.a.run.app'

def app_hash():
    digest=hashlib.sha256()
    for path in sorted((ROOT/'app').rglob('*.py')):digest.update(str(path.relative_to(ROOT)).encode()+b'\0'+path.read_bytes()+b'\0')
    return digest.hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,indent=2));path.chmod(0o600)

def gates():
    frozen=json.loads((OUT/'verified-source.json').read_text())
    suites=ET.parse(OUT/'backend-full.xml').getroot();suites=list(suites) if suites.tag=='testsuites' else [suites]
    if app_hash()!=frozen['app_sha256'] or sum(int(s.get('tests',0)) for s in suites)<970 or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('Exact backend regression gate is not passing.')
    browser=json.loads((OUT/'browser-results.json').read_text())['stats']
    if browser.get('unexpected',1) or browser.get('expected',0)!=4:raise RuntimeError('Desktop/tablet/mobile/restricted-access browser gate is not passing.')
    if 'Compiled successfully' not in (OUT/'frontend-build-final.log').read_text():raise RuntimeError('Verified frontend production build is missing.')
    baseline=json.loads((OUT/'source-baseline.json').read_text())
    deleted=subprocess.check_output(['git','diff','--diff-filter=D','--name-only',baseline['starting_commit'],'HEAD'],cwd=ROOT,text=True).strip()
    if deleted:raise RuntimeError('Unexpected tracked source deletion; no release performed.')
    from app.database.postgres import PostgresConnection
    c=PostgresConnection(dotenv_values(ROOT/'.env',interpolate=False)['DATABASE_URL'],session_bound=True)
    try:
        c.execute('BEGIN READ ONLY')
        if c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]!=46:raise RuntimeError('Unexpected production schema; no migration is authorized by this release.')
        stored=[dict(r) for r in c.execute("SELECT organization_id,product,enabled FROM organization_products WHERE product='LEADGEN' ORDER BY organization_id").fetchall()]
        if stored!=json.loads((OUT/'database-baseline.json').read_text())['stored_lead_engine_entitlements']:raise RuntimeError('Stored Lead Engine grants changed unexpectedly.')
    finally:c.rollback();c.close()
    return frozen

def smoke(origin):
    values=dotenv_values(ROOT/'.env',interpolate=False);checks={}
    paths={'/api/health':200,'/api/organization/products':200,'/api/organization/profile':200,'/api/organization/icps':200,'/api/intent-radar/capabilities':200,'/api/intent-radar/overview':200,'/api/intent-radar/growth/overview?days=0':200,'/api/organization/billing':200,'/api/workflow/safety':404,'/api/email/account':404,'/api/acquisition/providers':404,'/api/settings':404,'/api/assistant/status':404}
    with httpx.Client(base_url=origin,timeout=65) as client:
        for path,expected in paths.items():
            headers={};started=time.monotonic()
            if path!='/api/health':
                stamp=str(int(time.time()));nonce=secrets.token_hex(24);actor='planebyte@gmail.com';canonical='\n'.join((stamp,nonce,'GET',path,hashlib.sha256(b'').hexdigest(),actor))
                headers={'x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':hmac.new(values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical.encode(),hashlib.sha256).hexdigest()}
            response=client.get(path,headers=headers);checks[path]={'http':response.status_code,'seconds':round(time.monotonic()-started,2)}
            if response.status_code!=expected:raise RuntimeError('Read-only production smoke failed at '+path)
            if path.endswith('/products'):
                data=response.json()
                if data['lead_engine'] or data['lead_engine_available'] or not data['intent_radar']['enabled']:raise RuntimeError('Intent-only product policy did not apply.')
            if path.endswith('/billing'):
                data=response.json()
                if data['mode']!='test' or data['public_checkout_enabled']:raise RuntimeError('Billing Test Mode guard changed.')
    return checks

def release():
    frozen=gates();source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    build=json.loads((OUT/'build.json').read_text());verified=command(['builds','describe',build['build_id']])
    if build['source_commit']!=source or verified['status']!='SUCCESS' or verified['substitutions']['_SOURCE_REV']!=source:raise RuntimeError('Exact committed images are not ready.')
    checkpoint=ROOT/'data/backups'/('intent-only-'+source[:10]);checkpoint.mkdir(mode=0o700,exist_ok=False)
    previous={name:command(['run',kind,'describe',name,'--region='+REGION]) for kind,name,_ in RESOURCES}
    for name,value in previous.items():save(checkpoint/(name+'-before.json'),value)
    schedulers=command(['scheduler','jobs','list','--location='+REGION]);save(checkpoint/'schedulers-before.json',schedulers)
    def update(kind,name,image):
        before=copy.deepcopy(spec(previous[name],kind));env={e['name']:e for e in before['containers'][0].get('env',[])}
        for flag in ('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED','HEYSOW_PUBLIC_REGISTRATION_ENABLED','BILLING_PUBLIC_CHECKOUT_ENABLED'):
            if env.get(flag,{}).get('value')!='false':raise RuntimeError('A release safety guard is not explicitly false.')
        args=['run',kind,'update',name,'--region='+REGION,'--image='+image,'--update-env-vars=LEAD_ENGINE_AVAILABLE=false']
        if kind=='services':args+=['--no-traffic','--tag=intent-only']
        updated=command(args);after=copy.deepcopy(spec(updated,kind))
        for runtime in (before,after):
            runtime['containers'][0].pop('image',None)
            runtime['containers'][0]['env']=[e for e in runtime['containers'][0].get('env',[]) if e['name']!='LEAD_ENGINE_AVAILABLE']
        if before!=after:raise RuntimeError('Unrelated runtime configuration changed; inspect private checkpoint before promoting.')
        save(checkpoint/(name+'-updated.json'),updated);return updated
    api=update('services','leadengine-api',build['api_image']);revision=api['status']['latestReadyRevisionName']
    if revision!=api['status']['latestCreatedRevisionName']:raise RuntimeError('New API revision is not ready; previous traffic remains.')
    checks=smoke('https://intent-only---leadengine-api-befca7xg4a-el.a.run.app')
    for kind,name,image in RESOURCES:
        if kind=='jobs':update(kind,name,build[image+'_image'])
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+revision+'=100'])
    final_schedulers=command(['scheduler','jobs','list','--location='+REGION])
    def scheduler_settings(rows):return {r['name']:{k:v for k,v in r.items() if k not in ('lastAttemptTime','status','scheduleTime','userUpdateTime')} for r in rows}
    if scheduler_settings(schedulers)!=scheduler_settings(final_schedulers):raise RuntimeError('Scheduler configuration changed concurrently; inspect checkpoints.')
    proof={'source_commit':source,'revision':revision,'schema':46,'migration_run':False,'lead_engine_available':False,'stored_entitlements_preserved':True,'other_configuration_preserved':True,'checks':checks}
    save(checkpoint/'promoted.json',proof);save(OUT/'backend-promoted.json',proof);print(json.dumps(proof))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['release','smoke']);args=parser.parse_args()
    try:
        if args.action=='release':release()
        else:save(OUT/'production-after-smoke.json',smoke(ORIGIN));print('Production read-only smoke passed.')
    except Exception as error:
        print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect the private release checkpoint; credentials withheld.'}));raise SystemExit(1)
