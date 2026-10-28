"""Add only Phase 4 mailbox configuration; never rotate existing platform secrets."""
import json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.mail.config import mail_settings
s=mail_settings()
if s.mode!='test' or s.provider!='hostinger' or s.from_address!='rajendra@planebyte.com' or s.username!=s.from_address:raise SystemExit('Expected the verified Hostinger identity in test mode.')
from app.mail.service import address
address(s.test_recipient)
project='querryside';region='asia-south1'
def run(args,data=None,allow_missing=False):
    result=subprocess.run(['gcloud.cmd',*args],input=data,capture_output=True,text=True)
    if result.returncode and not allow_missing:raise SystemExit('Cloud configuration step failed: '+args[0]+' '+args[1])
    return result
service=json.loads(run(['run','services','describe','leadengine-api','--project='+project,'--region='+region,'--format=json']).stdout)
container=service['spec']['template']['spec']['containers'][0]
existing=next((v.get('valueFrom',{}).get('secretKeyRef') for v in container.get('env',[]) if v['name']=='MAIL_PASSWORD'),None)
secret=existing['name'] if existing else 'leadengine-mail-password';version=existing.get('key','latest') if existing else 'latest'
check=run(['secrets','describe',secret,'--project='+project,'--format=json'],allow_missing=True)
created=False
if check.returncode:
    if 'NOT_FOUND' not in check.stderr:raise SystemExit('Could not establish whether the mailbox secret already exists.')
    run(['secrets','create',secret,'--project='+project,'--replication-policy=user-managed','--locations='+region,'--quiet'])
    run(['secrets','versions','add',secret,'--project='+project,'--data-file=-','--quiet'],s.password.get_secret_value());created=True
for identity in ('leadengine-api-sa','leadengine-worker-sa'):
    run(['secrets','add-iam-policy-binding',secret,'--project='+project,'--member=serviceAccount:'+identity+'@'+project+'.iam.gserviceaccount.com','--role=roles/secretmanager.secretAccessor','--quiet'])
values={}
for field,definition in type(s).model_fields.items():
    if field in ('password','gmail_enabled','live_approved'):continue
    value=getattr(s,field);values[definition.alias]=str(value).lower() if isinstance(value,bool) else str(value)
values.update(EMAIL_SEND_MODE='test',EMAIL_LIVE_APPROVED='false',GMAIL_ENABLED='false',PLANEBYTE_CONTACT_EMAIL=s.from_address)
delimiter='__PHASE4_VALUE__'
if any(delimiter in v for v in values.values()):raise SystemExit('Unsupported configuration separator.')
updates='^'+delimiter+'^'+delimiter.join(k+'='+v for k,v in values.items())
secret_arg='MAIL_PASSWORD='+secret+':'+version
run(['run','services','update','leadengine-api','--project='+project,'--region='+region,'--update-env-vars='+updates,'--update-secrets='+secret_arg,'--no-traffic','--quiet'])
run(['run','jobs','update','leadengine-worker','--project='+project,'--region='+region,'--update-env-vars='+updates,'--update-secrets='+secret_arg,'--quiet'])
record={'provider':'hostinger','send_mode':'test','mailbox':s.from_address,'mailbox_secret_created':created,'mailbox_secret_reused':not created,'platform_secrets_rotated':False,'password_in_output':False,'gmail_enabled':False}
Path('docs/phase4-mail-deployment.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
