"""Owner-approved one-key secret refresh and nonsecret Vertex runtime config."""
import json,subprocess
from pathlib import Path
from dotenv import dotenv_values
from scripts.stage_acquisition_release import command,CLI,PROJECT,REGION,runtime
VALUES={'AI_PRIMARY_PROVIDER':'vertex','VERTEX_AI_ENABLED':'true','VERTEX_AI_PROJECT_ID':'querryside','VERTEX_AI_LOCATION':'global','VERTEX_AI_MODEL':'gemini-3.6-flash','GEMINI_API_ENABLED':'true','AI_FALLBACK_ENABLED':'true','GEMINI_COPY_BATCH_SIZE':'40','GEMINI_MODEL':'gemini-3.6-flash'}
def activate():
 local=dotenv_values('.env');key=local.get('GEMINI_API_KEY');assert key and '\n' not in key,'A single secure root Gemini fallback key is required.'
 api,a=runtime(True);reference=next(e['valueFrom']['secretKeyRef'] for e in a['containers'][0]['env'] if e['name']=='GEMINI_API_KEY');sid=reference['name']
 current=subprocess.run([CLI,'secrets','versions','access',reference['key'],'--secret='+sid,'--project='+PROJECT],capture_output=True,text=True,check=True).stdout.strip()
 number=reference['key']
 if current!=key:
  version=command(['secrets','versions','add',sid,'--data-file=-','--quiet'],data=key);number=version['name'].rsplit('/',1)[1]
 result=[]
 for kind,name in (('services','leadengine-api'),('jobs','leadengine-worker'),('jobs','leadengine-acquisition')):
  d=command(['run',kind,'describe',name,'--region='+REGION]);s=d['spec']['template']['spec'];s=s if kind=='services' else s['template']['spec'];before=s['containers'][0].get('env',[])
  assert not any(e['name']=='GOOGLE_APPLICATION_CREDENTIALS' for e in before),'Production must use its attached identity.'
  args=['run',kind,'update',name,'--region='+REGION,'--update-env-vars='+','.join(k+'='+v for k,v in VALUES.items()),'--update-secrets=GEMINI_API_KEY='+sid+':'+number,'--quiet']
  command(args);new=command(['run',kind,'describe',name,'--region='+REGION]);ns=new['spec']['template']['spec'];ns=ns if kind=='services' else ns['template']['spec']
  untouched=lambda env:{e['name']:e for e in env if e['name'] not in set(VALUES)|{'GEMINI_API_KEY'}}
  assert untouched(before)==untouched(ns['containers'][0]['env']);assert ns['serviceAccountName']==s['serviceAccountName']
  result.append({'runtime':name,'service_account':s['serviceAccountName'],'other_env_preserved':True,'single_fallback_key_configured':True})
 Path('deploy/vertex-configuration.json').write_text(json.dumps({'nonsecret_config':VALUES,'secret_value_exposed':False,'service_account_json_created':False,'runtimes':result},indent=2));print(json.dumps(result))
if __name__=='__main__':activate()
