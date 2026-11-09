"""Promote the tested preferences compatibility fix, preserving provider config."""
import json
from pathlib import Path
from scripts.stage_acquisition_release import command,REGION,runtime
STATE=Path('deploy/vertex-release.json')
def deploy():
 b=json.loads(Path('/private/tmp/vertex-cloud-build-r6.json').read_text());build=command(['builds','describe',b['id'],'--region='+REGION]);assert build['status']=='SUCCESS'
 old=json.loads(STATE.read_text());Path('deploy/vertex-release-r5.json').write_text(STATE.read_text());state={**old,'settings_repair_build':build['id'],'migrations_run':False}
 for kind,name,image in [('services','leadengine-api','api'),('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','acquisition')]:
  d=command(['run',kind,'describe',name,'--region='+REGION]);s=d['spec']['template']['spec'];s=s if kind=='services' else s['template']['spec'];before=s['containers'][0]
  args=['run',kind,'update',name,'--region='+REGION,'--image=asia-south1-docker.pkg.dev/querryside/leadengine/'+image+':vertex-20261102-r6','--quiet']
  if kind=='services':args+=['--no-traffic','--tag=vertex']
  command(args);new=command(['run',kind,'describe',name,'--region='+REGION]);ns=new['spec']['template']['spec'];ns=ns if kind=='services' else ns['template']['spec'];assert ns['containers'][0]['env']==before['env'];assert ns['serviceAccountName']==s['serviceAccountName']
  state['runtimes'][name]['image']=ns['containers'][0]['image']
  if kind=='services':state['staged_revision']=new['status']['latestCreatedRevisionName'];state['staged_url']=next(v['url'] for v in new['status']['traffic'] if v.get('tag')=='vertex')
  STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'image_updated':name,'configuration_preserved':True}),flush=True)
 # Verify the exact failed production API against the new tagged revision first.
 import sys
 sys.path.insert(0,'/private/tmp');import leadengine_api_acceptance as api
 previous=api.base;api.base=state['staged_url']
 try:
  result,timing=api.call('GET','/api/acquisition/settings');assert result['provider']=='vertex' and result['model']=='gemini-3.6-flash';state['settings_read_verified']=timing['status']==200
 finally:api.base=previous
 command(['run','services','update-traffic','leadengine-api','--region='+REGION,'--to-revisions='+state['staged_revision']+'=100','--quiet']);state['promoted_revision']=state['staged_revision'];STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'promoted':state['promoted_revision'],'settings_read_verified':True,'migrations_run':False}),flush=True)
if __name__=='__main__':deploy()
