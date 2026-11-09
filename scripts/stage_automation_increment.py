"""Image-only incremental staging. No migrations, credential edits or activation."""
import json,subprocess,shutil,argparse,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--outreach-identity',action='store_true');p.add_argument('--api',action='store_true');p.add_argument('--worker',action='store_true');a=p.parse_args()
cli=shutil.which('gcloud') or str(Path.home()/'Downloads/google-cloud-sdk/bin/gcloud')
manifest_path=Path('deploy/automation-builds.json');m=json.loads(manifest_path.read_text())
def command(args):
 r=subprocess.run([cli,*args,'--project=querryside','--format=json'],capture_output=True,text=True)
 if r.returncode:raise SystemExit('Incremental staging step failed: '+args[0]+' '+args[1])
 return json.loads(r.stdout) if r.stdout.strip() else {}
def current(kind):
 d=command(['run','services' if kind=='api' else 'jobs','describe','leadengine-'+kind if kind=='api' else 'leadengine-worker','--region=asia-south1'])
 inner=d['spec']['template']['spec']
 if kind=='worker':inner=inner['template']['spec']
 return d,inner['containers'][0]
for kind,selected in [('api',a.api),('worker',a.worker)]:
 if not selected:continue
 build=command(['builds','describe',m['builds'][kind],'--region=asia-south1'])
 if build.get('status')!='SUCCESS':raise SystemExit(kind+' build is not successful')
 before,container=current(kind);env=container.get('env',[])
 for key in ('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED'):
  assert next(e.get('value') for e in env if e['name']==key)=='false'
 args=['run','services' if kind=='api' else 'jobs','update','leadengine-api' if kind=='api' else 'leadengine-worker','--region=asia-south1','--image='+m['images'][kind],'--quiet']
 if a.outreach_identity:
  from dotenv import dotenv_values
  identity={k:(dotenv_values('.env').get(k) or '') for k in ('OUTREACH_SENDER_NAME','OUTREACH_SENDER_ROLE')}
  assert all('~' not in v and '\n' not in v and '\r' not in v for v in identity.values())
  args.append('--update-env-vars=^~^'+'~'.join(k+'='+v for k,v in identity.items()))
 if kind=='api':args.append('--no-traffic')
 else:args.append('--update-env-vars=LEADENGINE_WORKER_IMAGE='+m['images'][kind])
 command(args)
 after,newcontainer=current(kind)
 ignored={'LEADENGINE_WORKER_IMAGE'} if kind=='worker' else set()
 if a.outreach_identity:
  ignored.update(identity)
  assert all(next(e.get('value','') for e in newcontainer['env'] if e['name']==k)==v for k,v in identity.items())
 normalize=lambda entries:sorted([e for e in entries if e['name'] not in ignored],key=lambda e:e['name'])
 assert normalize(env)==normalize(newcontainer.get('env',[])),'Unexpected environment change'
 if kind=='api':m['prepared_api_revision']=after['status']['latestCreatedRevisionName']
 m.setdefault('incremental_staging',{})[kind]={'image':m['images'][kind],'environment_preserved':True,'secrets_preserved':True}
 manifest_path.write_text(json.dumps(m,indent=2));print(json.dumps({kind:m['incremental_staging'][kind],'revision':m.get('prepared_api_revision') if kind=='api' else None}))
