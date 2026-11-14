"""Stage/promote the verified non-chargeable product release on existing resources.

No migrations, financial writes, data cleanup, IAM changes, secret replacement,
signup activation, scheduler changes or frontend hosting changes are performed.
Staging and promotion are separate so real read/worker acceptance can intervene.
"""
import argparse,copy,hashlib,hmac,json,os,secrets,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
import httpx
from dotenv import dotenv_values
from scripts.deploy_beta_backend import command,REGION
from scripts.deploy_growth_release import spec
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/artifacts/verification/final-product'
RESOURCES=[('services','leadengine-api','api'),('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','worker'),('jobs','leadengine-quota-canary','worker')]
ORIGIN='https://leadengine-api-befca7xg4a-el.a.run.app'

def app_hash():
    digest=hashlib.sha256()
    for p in sorted((ROOT/'app').rglob('*')):
        if p.is_file() and p.suffix in ('.py','.json'):digest.update(str(p.relative_to(ROOT)).encode()+b'\0'+p.read_bytes()+b'\0')
    return digest.hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,indent=2));path.chmod(0o600)

def gate():
    frozen=json.loads((OUT/'frozen-source.json').read_text())
    if app_hash()!=frozen['app_sha256']:raise RuntimeError('Backend changed after the frozen test run.')
    report=ET.parse(OUT/'backend-verified.xml').getroot();suites=list(report) if report.tag=='testsuites' else [report]
    if sum(int(s.get('tests',0)) for s in suites)<998 or any(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites):raise RuntimeError('Full backend gate is not passing.')
    browser=json.loads((OUT/'browser-results.json').read_text())['stats']
    if browser.get('unexpected',1) or browser.get('expected')!=7:raise RuntimeError('Product assistant and six-viewport browser gate is not passing.')
    if 'Compiled successfully' not in (OUT/'frontend-verified.log').read_text():raise RuntimeError('Verified frontend build missing.')
    for name in ('types-final.log',):
        if (OUT/name).read_text().strip():raise RuntimeError('Frontend type gate is not passing.')
    if 'failed' in (OUT/'units-verified.log').read_text().lower():raise RuntimeError('Frontend unit gate is not passing.')
    if subprocess.check_output(['git','status','--porcelain','--','app'],cwd=ROOT,text=True).strip():raise RuntimeError('Backend application must be committed exactly before staging.')
    if subprocess.check_output(['git','diff','--diff-filter=D','--name-only','a608210','HEAD'],cwd=ROOT,text=True).strip():raise RuntimeError('Unexpected source deletion requires investigation.')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def signed(client,path,method='GET',body=None):
    raw=json.dumps(body,separators=(',',':')).encode() if body is not None else b''
    values=dotenv_values(ROOT/'.env',interpolate=False);stamp=str(int(time.time()));nonce=secrets.token_hex(24);actor='planebyte@gmail.com'
    canonical='\n'.join((stamp,nonce,method,path,hashlib.sha256(raw).hexdigest(),actor))
    headers={'x-le-user':actor,'x-le-timestamp':stamp,'x-le-nonce':nonce,'x-le-signature':hmac.new(values['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical.encode(),hashlib.sha256).hexdigest()}
    if raw:headers['content-type']='application/json'
    return client.request(method,path,headers=headers,content=raw)

def smoke(origin):
    checks={};paths={'/api/health':200,'/api/organization/products':200,'/api/organization/usage':200,'/api/organization/profile':200,'/api/organization/icps':200,'/api/intent-radar/overview':200,'/api/intent-radar/sources/health':200,'/api/intent-radar/alerts?alert_kind=Source%20issues':200,'/api/intent-radar/alerts?alert_kind=Monitor%20activity':200,'/api/intent-radar/assistant/conversations':200,'/api/intent-radar/growth/overview?days=0':200,'/api/organization/developer/status':200,'/api/workflow/safety':404,'/api/email/account':404,'/api/acquisition/providers':404}
    with httpx.Client(base_url=origin,timeout=65,follow_redirects=False) as client:
        for path,expected in paths.items():
            started=time.monotonic();r=client.get(path) if path=='/api/health' else signed(client,path)
            checks[path]={'http':r.status_code,'seconds':round(time.monotonic()-started,3),'server_timing':r.headers.get('server-timing','')}
            if r.status_code!=expected:raise RuntimeError('Read-only smoke failed at '+path+' (HTTP '+str(r.status_code)+').')
            if path.endswith('/products'):
                data=r.json()
                if data['lead_engine'] or data['lead_engine_available'] or not data['intent_radar']['enabled']:raise RuntimeError('Product availability policy mismatch.')
            if path.endswith('/usage'):
                data=r.json()
                if data['live_payments_enabled'] or data['commercial']['checkout_enabled'] or data['commercial']['catalog']['list_currency']!='USD':raise RuntimeError('Non-chargeable catalog policy mismatch.')
    return checks

def checkpoint(source):return ROOT/'data/backups'/('product-'+source[:10])

def stage():
    source=gate();build=json.loads((ROOT/'data/artifacts/verification/intent-only/build.json').read_text());remote=command(['builds','describe',build['build_id']])
    if build['source_commit']!=source or remote['status']!='SUCCESS' or remote['substitutions']['_SOURCE_REV']!=source:raise RuntimeError('Exact source images are not verified.')
    folder=checkpoint(source);folder.mkdir(mode=0o700,exist_ok=False)
    previous={name:command(['run',kind,'describe',name,'--region='+REGION]) for kind,name,_ in RESOURCES}
    for name,value in previous.items():save(folder/(name+'-before.json'),value)
    save(folder/'schedulers-before.json',command(['scheduler','jobs','list','--location='+REGION]))
    for kind,name,image in RESOURCES:
        before=copy.deepcopy(spec(previous[name],kind));env={e['name']:e for e in before['containers'][0].get('env',[])}
        for flag in ('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED','HEYSOW_PUBLIC_REGISTRATION_ENABLED','BILLING_PUBLIC_CHECKOUT_ENABLED','LEAD_ENGINE_AVAILABLE'):
            if env.get(flag,{}).get('value')!='false':raise RuntimeError('A production safety flag is not explicitly false.')
        args=['run',kind,'update',name,'--region='+REGION,'--image='+build[image+'_image']]
        if kind=='services':args+=['--no-traffic','--tag=intent-only']
        updated=command(args);after=copy.deepcopy(spec(updated,kind))
        for runtime in (before,after):runtime['containers'][0].pop('image',None)
        if before!=after:raise RuntimeError('Unexpected runtime setting change; previous traffic remains unchanged.')
        save(folder/(name+'-staged.json'),updated)
        if kind=='services':
            revision=updated['status']['latestReadyRevisionName']
            if revision!=updated['status']['latestCreatedRevisionName']:raise RuntimeError('Staged API is not ready.')
            # Read smoke is complete before changing any worker image.
            save(folder/'staged-read-smoke.json',smoke('https://intent-only---leadengine-api-befca7xg4a-el.a.run.app'))
    result={'source_commit':source,'revision':revision,'schema':46,'migration_run':False,'production_traffic_promoted':False,'checkpoint':str(folder)}
    save(OUT/'staged-release.json',result);print(json.dumps(result))

def promote():
    source=gate();staged=json.loads((OUT/'staged-release.json').read_text());folder=checkpoint(source)
    if source!=staged['source_commit']:raise RuntimeError('Source changed after staging.')
    acceptance=json.loads((OUT/'staged-functional-acceptance.json').read_text())
    if acceptance.get('source_commit')!=source or acceptance.get('critical_failures') or not acceptance.get('worker_verified'):raise RuntimeError('Controlled staged worker acceptance is missing or failing.')
    revision=staged['revision'];original=json.loads((folder/'leadengine-api-before.json').read_text())
    checks=smoke('https://intent-only---leadengine-api-befca7xg4a-el.a.run.app')
    tags=sorted({row['tag'] for row in original['status']['traffic'] if row.get('tag')})
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+revision+'=100','--update-tags='+','.join(tag+'='+revision for tag in tags)])
    current=command(['run','services','describe','leadengine-api','--region='+REGION]);save(folder/'leadengine-api-final.json',current)
    if any(row.get('revisionName')!=revision for row in current['status']['traffic']):raise RuntimeError('Traffic/tag versions do not match the verified release.')
    before=json.loads((folder/'schedulers-before.json').read_text());after=command(['scheduler','jobs','list','--location='+REGION])
    clean=lambda rows:{r['name']:{k:v for k,v in r.items() if k not in ('lastAttemptTime','status','scheduleTime','userUpdateTime')} for r in rows}
    if clean(before)!=clean(after):raise RuntimeError('Scheduler settings changed concurrently.')
    proof={**staged,'production_traffic_promoted':True,'checks':checks,'schedulers_unchanged':True,'runtime_settings_preserved':True};save(OUT/'backend-promoted.json',proof);print(json.dumps(proof))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('stage','promote','smoke'));args=p.parse_args();os.umask(0o077)
    try:
        if args.action=='stage':stage()
        elif args.action=='promote':promote()
        else:save(OUT/'production-smoke.json',smoke(ORIGIN));print('Production read-only smoke passed.')
    except Exception as error:
        print(json.dumps({'status':'BLOCKED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect the private checkpoint; credentials withheld.'}));raise SystemExit(1)
