"""Add an isolated source job and API revision, preserving live Maps/mail configuration."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from dotenv import dotenv_values
CLI='/Users/planebyte/Downloads/google-cloud-sdk/bin/gcloud'
PROJECT='querryside';REGION='asia-south1';STATE=Path('deploy/acquisition-release.json')
FLAGS={k:'false' for k in ('ENABLE_AI_ACQUISITION','ENABLE_FIRECRAWL_ACQUISITION','ENABLE_LEAD_IMPORT','ENABLE_GOOGLE_SHEETS_IMPORT')}
def command(args,data=None,missing=False):
    p=subprocess.run([CLI,*args,'--project='+PROJECT,'--format=json'],input=data,text=True,capture_output=True)
    if p.returncode:
        if missing and ('NOT_FOUND' in p.stderr or 'not found' in p.stderr):return None
        raise RuntimeError('GCP operation failed: '+' '.join(args[:4])+' '+p.stderr[-500:])
    return json.loads(p.stdout) if p.stdout.strip() else {}
def runtime(api):
    d=command(['run','services' if api else 'jobs','describe','leadengine-api' if api else 'leadengine-worker','--region='+REGION]);s=d['spec']['template']['spec'];return d,s if api else s['template']['spec']
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def stage(buildfile):
    build=json.loads(Path(buildfile).read_text());checked=command(['builds','describe',build['id'],'--region='+REGION]);assert checked['status']=='SUCCESS'
    images=checked['images'];api_image=next(i for i in images if '/api:' in i);job_image=next(i for i in images if '/acquisition:' in i)
    api,a=runtime(True);worker,w=runtime(False);before_worker=digest(worker['spec']);original=a['containers'][0].get('env',[]);values=dotenv_values('.env')
    state={'build':build['id'],'api_image':api_image,'acquisition_image':job_image,'previous_revision':api['status']['latestReadyRevisionName'],'existing_worker_spec_sha256':before_worker,'new_features_enabled':False,'existing_global_flags':{e['name']:e.get('value') for e in original if e['name'] in ('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED')}}
    source_sa='leadengine-acquisition-sa@'+PROJECT+'.iam.gserviceaccount.com'
    if command(['iam','service-accounts','describe',source_sa],missing=True) is None:
        command(['iam','service-accounts','create','leadengine-acquisition-sa','--display-name=LeadEngine isolated acquisition','--quiet'])
    principals={a['serviceAccountName'],source_sa};secret_refs={}
    for key in ('GEMINI_API_KEY','FIRECRAWL_API_KEY','AUTH_GOOGLE_SECRET'):
        assert values.get(key),'Missing server-only '+key
        sid='leadengine-acquisition-'+key.lower().replace('_','-')
        if command(['secrets','describe',sid],missing=True) is None:command(['secrets','create',sid,'--replication-policy=automatic','--quiet'])
        version=command(['secrets','versions','add',sid,'--data-file=-','--quiet'],values[key]);number=version['name'].rsplit('/',1)[1];secret_refs[key]=sid+':'+number
        for principal in principals:command(['secrets','add-iam-policy-binding',sid,'--member=serviceAccount:'+principal,'--role=roles/secretmanager.secretAccessor','--quiet'])
    additions={**FLAGS,'AI_PROVIDER':'gemini','GEMINI_MODEL':values.get('GEMINI_MODEL','gemini-3.8-flash'),'FIRECRAWL_API_URL':values.get('FIRECRAWL_API_URL','https://api.firecrawl.dev'),'GOOGLE_SHEETS_REDIRECT_URI':'https://leads.planebyte.com/acquisition/sheets/callback','AUTH_GOOGLE_ID':values['AUTH_GOOGLE_ID'],'ACQUISITION_CLOUD_RUN_JOB':'leadengine-acquisition'}
    # Copy only source-processing dependencies. No Gmail/SMTP credentials or mail ticks.
    allowed={'APP_ENV','DATABASE_URL','LEADENGINE_API_SIGNING_SECRET','ALLOWED_USER_EMAILS','GCP_PROJECT_ID','GCP_REGION','SCAN_EXECUTOR','R2_ENDPOINT','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET_NAME','R2_REGION','ARTIFACT_STORAGE','CRAWLER_USER_AGENT','CRAWLER_CONTACT_EMAIL'}
    inherited={e['name']:e for e in [*original,*w['containers'][0].get('env',[])] if e['name'] in allowed}
    assert {'DATABASE_URL','R2_ENDPOINT','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET_NAME','LEADENGINE_API_SIGNING_SECRET','ALLOWED_USER_EMAILS'}<=set(inherited)
    job_env=list(inherited.values())
    plain={**additions,'LEADENGINE_ROLE':'worker','AUTO_SCAN_ENABLED':'false','AUTO_EMAIL_ENABLED':'false','EMAIL_SENDING_ENABLED':'false','SOCIAL_ENRICHMENT_ENABLED':'false','SOCIAL_ACTIVITY_ENABLED':'false'}
    job_env.extend({'name':k,'value':v} for k,v in plain.items())
    job_env.extend({'name':k,'valueFrom':{'secretKeyRef':{'name':v.split(':')[0],'key':v.split(':')[1]}}} for k,v in secret_refs.items())
    job={'apiVersion':'run.googleapis.com/v1','kind':'Job','metadata':{'name':'leadengine-acquisition','namespace':PROJECT},'spec':{'template':{'spec':{'taskCount':1,'parallelism':1,'template':{'spec':{'serviceAccountName':source_sa,'maxRetries':0,'timeoutSeconds':'3600','containers':[{'image':job_image,'env':job_env,'resources':{'limits':{'cpu':'1','memory':'2Gi'}}}]}}}}}}
    path=Path('/private/tmp/leadengine-acquisition-job.json');path.write_text(json.dumps(job));path.chmod(0o600)
    # Explicit source-only dependency allowlist. Never grant Gmail credentials,
    # project-level secret access or additional access to the existing worker SA.
    source_secrets=('leadengine-database-url','leadengine-r2-endpoint','leadengine-r2-bucket','leadengine-allowed-users','leadengine-r2-key','leadengine-r2-secret','leadengine-api-signing')
    actual={e['valueFrom']['secretKeyRef']['name'] for e in job_env if 'valueFrom' in e}
    assert actual==set(source_secrets)|{v.split(':')[0] for v in secret_refs.values()}
    for sid in source_secrets:command(['secrets','add-iam-policy-binding',sid,'--member=serviceAccount:'+source_sa,'--role=roles/secretmanager.secretAccessor','--quiet'])
    command(['run','jobs','replace',str(path),'--region='+REGION,'--quiet'])
    for principal in principals:command(['run','jobs','add-iam-policy-binding','leadengine-acquisition','--region='+REGION,'--member=serviceAccount:'+principal,'--role=roles/run.jobsExecutorWithOverrides','--quiet'])
    command(['run','services','update','leadengine-api','--region='+REGION,'--image='+api_image,'--update-env-vars='+','.join(k+'='+v for k,v in additions.items()),'--update-secrets='+','.join(k+'='+v for k,v in secret_refs.items()),'--no-traffic','--quiet'])
    after,b=runtime(True);ignored=set(additions)|set(secret_refs)
    assert sorted([e for e in original if e['name'] not in ignored],key=lambda e:e['name'])==sorted([e for e in b['containers'][0].get('env',[]) if e['name'] not in ignored],key=lambda e:e['name'])
    assert digest(runtime(False)[0]['spec'])==before_worker
    state.update(staged_revision=after['status']['latestCreatedRevisionName'],existing_api_environment_preserved=True,existing_worker_unchanged=True,new_job_has_no_gmail_credentials=True,secret_references=secret_refs)
    STATE.write_text(json.dumps(state,indent=2));print(json.dumps({k:state[k] for k in ('staged_revision','existing_api_environment_preserved','existing_worker_unchanged','new_job_has_no_gmail_credentials','new_features_enabled')}))
def promote():
    state=json.loads(STATE.read_text());revision=state['staged_revision'];r=command(['run','revisions','describe',revision,'--region='+REGION]);assert any(x['type']=='Ready' and x['status']=='True' for x in r['status']['conditions'])
    assert digest(runtime(False)[0]['spec'])==state['existing_worker_spec_sha256']
    command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+revision+'=100','--quiet']);state['promoted_revision']=revision;STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'promoted':revision,'new_features_enabled':False,'existing_worker_unchanged':True}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','promote']);p.add_argument('--build');args=p.parse_args();stage(args.build) if args.action=='stage' else promote()
