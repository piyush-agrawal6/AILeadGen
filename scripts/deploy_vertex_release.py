"""Image/config-only Vertex release; preserves schema14, SMTP, schedules and identity."""
import json,subprocess
from pathlib import Path
from dotenv import dotenv_values
from scripts.stage_acquisition_release import command,CLI,PROJECT,REGION,runtime
from scripts.activate_vertex_configuration import VALUES
STATE=Path('deploy/vertex-release.json')
def stage():
 b=json.loads(Path('/private/tmp/vertex-cloud-build-r5.json').read_text());build=command(['builds','describe',b['id'],'--region='+REGION]);assert build['status']=='SUCCESS'
 local=dotenv_values('.env');key=local.get('GEMINI_API_KEY');assert key and '\n' not in key
 api,a=runtime(True);ref=next(e['valueFrom']['secretKeyRef'] for e in a['containers'][0]['env'] if e['name']=='GEMINI_API_KEY');sid=ref['name']
 current=subprocess.run([CLI,'secrets','versions','access',ref['key'],'--secret='+sid,'--project='+PROJECT],capture_output=True,text=True,check=True).stdout.strip();number=ref['key']
 if current!=key:number=command(['secrets','versions','add',sid,'--data-file=-','--quiet'],data=key)['name'].rsplit('/',1)[1]
 tag='vertex-20261102-r5';state={'build':build['id'],'previous_revision':api['status']['latestReadyRevisionName'],'schema':14,'migrations_run':False,'json_service_account_key_created':False,'new_single_gemini_fallback_key_configured':True,'experiment_activated':False,'nonsecret_config':VALUES,'runtimes':{}}
 for kind,name,image in [('services','leadengine-api','api'),('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','acquisition')]:
  d=command(['run',kind,'describe',name,'--region='+REGION]);spec=d['spec']['template']['spec'];s=spec if kind=='services' else spec['template']['spec'];before=s['containers'][0].get('env',[])
  assert not any(e['name']=='GOOGLE_APPLICATION_CREDENTIALS' for e in before)
  args=['run',kind,'update',name,'--region='+REGION,'--image=asia-south1-docker.pkg.dev/querryside/leadengine/'+image+':'+tag,'--update-env-vars='+','.join(k+'='+v for k,v in VALUES.items()),'--update-secrets=GEMINI_API_KEY='+sid+':'+number,'--quiet']
  if kind=='services':args+=['--no-traffic','--tag=vertex']
  command(args);updated=command(['run',kind,'describe',name,'--region='+REGION]);ns=updated['spec']['template']['spec'];ns=ns if kind=='services' else ns['template']['spec']
  ignore=set(VALUES)|{'GEMINI_API_KEY'};assert {e['name']:e for e in before if e['name'] not in ignore}=={e['name']:e for e in ns['containers'][0]['env'] if e['name'] not in ignore};assert ns['serviceAccountName']==s['serviceAccountName'];assert ns['containers'][0].get('resources')==s['containers'][0].get('resources')
  state['runtimes'][name]={'image':ns['containers'][0]['image'],'service_account':ns['serviceAccountName'],'environment_preserved':True,'no_execution_cancelled':True}
  if kind=='services':state['staged_revision']=updated['status']['latestCreatedRevisionName'];state['staged_url']=next(v['url'] for v in updated['status']['traffic'] if v.get('tag')=='vertex')
  STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'updated':name,'identity_preserved':True,'experiment_activated':False}),flush=True)
 import requests
 assert requests.get(state['staged_url']+'/api/health',timeout=60).ok
 command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+state['staged_revision']+'=100','--quiet']);state['promoted_revision']=state['staged_revision'];STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'promoted':state['promoted_revision'],'schema':14,'migrations_run':False}),flush=True)
if __name__=='__main__':stage()
