"""Deploy only backed-up additive experiment images; never activate its sends."""
import json,sys,subprocess,hashlib,os
from pathlib import Path
from scripts.stage_acquisition_release import command,REGION,PROJECT,runtime,digest
STATE=Path('deploy/experiment-release.json');TAG='experiment-20261102-r18'
def describe_job(name):
 d=command(['run','jobs','describe',name,'--region='+REGION]);return d,d['spec']['template']['spec']['template']['spec']
def stage():
 b=json.loads(Path('/private/tmp/experiment-cloud-build-r18.json').read_text());build=command(['builds','describe',b['id'],'--region='+REGION]);assert build['status']=='SUCCESS','Exact Linux tests must pass before release.'
 backup=json.loads(Path('data/backups/experiment-schema13-20261102T152525Z.json').read_text());assert backup['restore_verified']
 if STATE.exists():Path('deploy/experiment-release-r17.json').write_text(STATE.read_text())
 os.environ['DATABASE_BACKEND']='postgres'
 from app.database.connection import get_connection
 c=get_connection();schema_before=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0];c.close();assert schema_before in (13,14)
 api,a=runtime(True);worker,w=runtime(False);source,s=describe_job('leadengine-acquisition')
 state={'build_id':build['id'],'api_image':'asia-south1-docker.pkg.dev/querryside/leadengine/api:'+TAG,'maps_image':'asia-south1-docker.pkg.dev/querryside/leadengine/worker:'+TAG,'source_image':'asia-south1-docker.pkg.dev/querryside/leadengine/acquisition:'+TAG,'previous_api_revision':api['status']['latestReadyRevisionName'],'previous_maps_image':w['containers'][0]['image'],'previous_source_image':s['containers'][0]['image'],'schema_before':schema_before,'backup':backup['backup'],'rollback_schema':backup['rollback_schema'],'experiment_activated':False}
 env=a['containers'][0]['env'];gemini=next(e for e in env if e['name']=='GEMINI_API_KEY')['valueFrom']['secretKeyRef'];model=next(e['value'] for e in env if e['name']=='GEMINI_MODEL');sa=w['serviceAccountName']
 # Exact existing secret, restricted to the existing scheduler/mail worker identity.
 command(['secrets','add-iam-policy-binding',gemini['name'],'--member=serviceAccount:'+sa,'--role=roles/secretmanager.secretAccessor','--quiet'])
 command(['run','services','update','leadengine-api','--region='+REGION,'--image='+state['api_image'],'--no-traffic','--tag=experiment','--quiet'])
 after,new=runtime(True);assert new['containers'][0]['env']==env
 state['staged_api_revision']=after['status']['latestCreatedRevisionName'];state['staged_url']=next(x['url'] for x in after['status']['traffic'] if x.get('tag')=='experiment');STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'staged_revision':state['staged_api_revision'],'experiment_activated':False}),flush=True)
 if schema_before==13:subprocess.run([sys.executable,'scripts/experiment_migrate.py','migrate','--state','data/backups/experiment-schema13-20261102T152525Z.json'],check=True)
 else:state['no_migration_run']=True
 for name,prior,container,image in [('leadengine-worker',worker,w,state['maps_image']),('leadengine-acquisition',source,s,state['source_image'])]:
  args=['run','jobs','update',name,'--region='+REGION,'--image='+image,'--quiet']
  additions=set()
  if name=='leadengine-worker':args.extend(['--update-secrets=GEMINI_API_KEY='+gemini['name']+':'+gemini['key'],'--update-env-vars=AI_PROVIDER=gemini,GEMINI_MODEL='+model]);additions={'GEMINI_API_KEY','AI_PROVIDER','GEMINI_MODEL'}
  command(args);_,current=describe_job(name)
  before_env={e['name']:e for e in container['containers'][0]['env'] if e['name'] not in additions};after_env={e['name']:e for e in current['containers'][0]['env'] if e['name'] not in additions};assert before_env==after_env,'Unexpected worker configuration change.'
  assert current['serviceAccountName']==container['serviceAccountName'];assert current['containers'][0].get('resources')==container['containers'][0].get('resources')
  state[name]={'image':image,'existing_environment_preserved':True,'resources_preserved':True,'no_execution_cancelled':True};STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'updated':name,'existing_flags_and_gmail_preserved':True}),flush=True)
 # Verify the staged revision against actual schema14 before routing public traffic.
 import requests
 health=requests.get(state['staged_url']+'/api/health',timeout=60);assert health.ok,health.status_code
 command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+state['staged_api_revision']+'=100','--quiet']);state.update(promoted_revision=state['staged_api_revision'],schema_after=14,existing_controls_preserved=True);STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'promoted':state['promoted_revision'],'schema':14,'experiment_activated':False}),flush=True)
if __name__=='__main__':stage()
