"""Stage the validated foundation images with existing Gmail and infrastructure preserved."""
import json,subprocess,argparse
from pathlib import Path
from dotenv import dotenv_values
cli='/Users/planebyte/Downloads/google-cloud-sdk/bin/gcloud';project='querryside';region='asia-south1'
state_path=Path('deploy/foundation-release.json')
images={k:'asia-south1-docker.pkg.dev/querryside/leadengine/'+k+':foundation-20261102-repair2' for k in ('api','worker')}
def command(args,data=None,allow_missing=False):
    p=subprocess.run([cli,*args,'--project='+project,'--format=json'],input=data,capture_output=True,text=True)
    if p.returncode:
        if allow_missing and ('NOT_FOUND' in p.stderr or 'not found' in p.stderr):return None
        raise RuntimeError('GCP step failed: '+' '.join(args[:4])+' '+p.stderr[-600:])
    return json.loads(p.stdout) if p.stdout.strip() else {}
def runtime(kind):
    d=command(['run','services' if kind=='api' else 'jobs','describe','leadengine-api' if kind=='api' else 'leadengine-worker','--region='+region]);s=d['spec']['template']['spec'];s=s if kind=='api' else s['template']['spec'];return d,s

def stage():
    build=json.loads(Path('/private/tmp/leadengine-foundation-build.json').read_text());status=command(['builds','describe',build['id'],'--region='+region]);assert status['status']=='SUCCESS','Exact-lock build/tests must pass first'
    prior=json.loads(state_path.read_text()) if state_path.exists() else {}
    state={'build':build['id'],'images':images,'staged':{},'automation_enabled':False,'rollback':prior.get('rollback',{}),'prior_releases':[*prior.get('prior_releases',[]),*([{'build':prior.get('build'),'staged':prior.get('staged',{})}] if prior else [])]}
    values=dotenv_values('.env')
    secrets={k:'leadengine-'+k.lower().replace('_','-') for k in ('UPSTASH_REDIS_REST_URL','UPSTASH_REDIS_REST_TOKEN')}
    for env,sid in secrets.items():
        value=values.get(env);assert value and '\n' not in value,'Missing server-only Redis variable'
        existing=command(['secrets','describe',sid],allow_missing=True)
        if existing is None:
            command(['secrets','create',sid,'--replication-policy=automatic','--quiet'])
            command(['secrets','versions','add',sid,'--data-file=-','--quiet'],data=value)
    principals=set()
    for kind in ('api','worker'):
        d,s=runtime(kind);sa=s['serviceAccountName'];principals.add(sa)
        state.setdefault('rollback',{}).setdefault(kind,{'image':s['containers'][0]['image'],'revision':d.get('status',{}).get('latestReadyRevisionName')})
    for sid in secrets.values():
        for sa in principals:command(['secrets','add-iam-policy-binding',sid,'--member=serviceAccount:'+sa,'--role=roles/secretmanager.secretAccessor','--quiet'])
    for kind in ('worker','api'):
        before,s=runtime(kind);entries=s['containers'][0].get('env',[]);flags={'AUTO_SCAN_ENABLED':'false','AUTO_EMAIL_ENABLED':'false','EMAIL_SENDING_ENABLED':'false'}
        assert all(next(e.get('value') for e in entries if e['name']==k)==v for k,v in flags.items())
        changes=dict(flags)
        if kind=='worker':changes['LEADENGINE_WORKER_IMAGE']=images[kind]
        args=['run','jobs' if kind=='worker' else 'services','update','leadengine-worker' if kind=='worker' else 'leadengine-api','--region='+region,'--image='+images[kind],'--update-env-vars='+','.join(k+'='+v for k,v in changes.items()),'--update-secrets='+','.join(k+'='+sid+':latest' for k,sid in secrets.items()),'--quiet']
        if kind=='api':args.append('--no-traffic')
        command(args);after,new=runtime(kind);newenv=new['containers'][0].get('env',[])
        ignored=set(changes)|set(secrets)
        assert sorted([e for e in entries if e['name'] not in ignored],key=lambda e:e['name'])==sorted([e for e in newenv if e['name'] not in ignored],key=lambda e:e['name']),'Unexpected config/secret change'
        revision=after['status'].get('latestCreatedRevisionName') if kind=='api' else None
        state['staged'][kind]={'image':images[kind],'revision':revision,'other_configuration_preserved':True,'gmail_secret_preserved':True,'redis_server_secrets':True}
        state_path.write_text(json.dumps(state,indent=2));print(json.dumps({'staged':kind,'revision':revision,'three_flags':False}),flush=True)

def promote():
    state=json.loads(state_path.read_text());r=state['staged']['api']['revision'];d,s=runtime('api');assert d['status']['latestCreatedRevisionName']==r
    revision=command(['run','revisions','describe',r,'--region='+region]);assert any(c['type']=='Ready' and c['status']=='True' for c in revision['status']['conditions'])
    command(['run','services','update-traffic','leadengine-api','--region='+region,'--to-revisions='+r+'=100','--quiet']);state['promoted_revision']=r;state_path.write_text(json.dumps(state,indent=2));print(json.dumps({'promoted':r,'automation_enabled':False}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','promote']);a=p.parse_args();stage() if a.action=='stage' else promote()
