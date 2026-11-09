"""Owner-authorized activation of existing deployment, with no campaign creation."""
import sys,json,subprocess,time,secrets,hmac,hashlib,argparse
from pathlib import Path
from datetime import datetime,timezone
import requests
from dotenv import dotenv_values
root=Path(__file__).resolve().parents[2];v=dotenv_values(root/'.env');flags={k:'true' for k in ('AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED')}
cli='/Users/planebyte/Downloads/google-cloud-sdk/bin/gcloud';actor=v['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower();record={'authorized_at':datetime.now(timezone.utc).isoformat(),'owner_request':'Enable outbound/outreach in production deployment','resources':{},'new_campaigns_created':0,'new_user_schedules_created':0}
def command(args):
 p=subprocess.run([cli,*args,'--project=querryside','--format=json'],capture_output=True,text=True)
 if p.returncode:raise RuntimeError('Production activation failed: '+' '.join(args[:4])+' '+p.stderr[-400:])
 return json.loads(p.stdout) if p.stdout.strip() else {}
def call(method,path,body=None):
 data=json.dumps(body,separators=(',',':')).encode() if body is not None else b'';stamp=str(int(time.time()));nonce=secrets.token_hex(16);canonical='\n'.join((stamp,nonce,method,path,hashlib.sha256(data).hexdigest(),actor));signature=hmac.new(v['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical.encode(),hashlib.sha256).hexdigest()
 r=requests.request(method,'https://leadengine-api-befca7xg4a-el.a.run.app'+path,data=data,headers={'Content-Type':'application/json','X-LE-User':actor,'X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-Signature':signature},timeout=90);assert r.ok,(path,r.status_code);return r.json()
def runtime(kind,name):
 d=command(['run',kind,'describe',name,'--region=asia-south1']);s=d['spec']['template']['spec'];s=s if kind=='services' else s['template']['spec'];return d,s['containers'][0]
def main():
 assert all(v.get(k,'').lower()=='true' for k in flags),'Owner must set root activation flags first'
 assert v.get('EMAIL_SEND_MODE')=='production' and v.get('EMAIL_LIVE_APPROVED','').lower()=='true'
 record['before']=call('GET','/api/automation/summary')
 for kind,name in [('jobs','leadengine-worker'),('services','leadengine-api')]:
  before,container=runtime(kind,name);entries=container['env'];mapping={e['name']:e for e in entries}
  assert mapping['EMAIL_SEND_MODE']['value']=='production' and mapping['EMAIL_LIVE_APPROVED']['value']=='true','Live mode approval must already exist'
  assert mapping['GMAIL_APP_PASSWORD'].get('valueFrom')
  command(['run',kind,'update',name,'--region=asia-south1','--update-env-vars='+','.join(k+'='+x for k,x in flags.items()),'--quiet'])
  after,new=runtime(kind,name);env={e['name']:e for e in new['env']};assert all(env[k].get('value')=='true' for k in flags)
  assert sorted([e for e in entries if e['name'] not in flags],key=lambda e:e['name'])==sorted([e for e in new['env'] if e['name'] not in flags],key=lambda e:e['name'])
  assert new['image']==container['image'],'Activation must not rebuild or change images'
  revision=None
  if kind=='services':
   revision=after['status']['latestCreatedRevisionName'];command(['run','services','update-traffic',name,'--region=asia-south1','--to-revisions='+revision+'=100','--quiet'])
  record['resources'][name]={'three_flags':True,'revision':revision,'image_preserved':True,'gmail_and_other_settings_preserved':True};Path(root/'docs/production-outreach-activation-20261102.json').write_text(json.dumps(record,indent=2));print(json.dumps({'resource':name,'three_flags':True,'revision':revision}),flush=True)
 call('PUT','/api/automation/controls',{'scan_paused':False,'email_paused':False})
 record['after']=call('GET','/api/automation/summary');s=record['after'];assert not s['controls']['scan_paused'] and not s['controls']['email_paused'];assert all(s['environment'][k] for k in ('scan_enabled','auto_email_enabled','sending_enabled'))
 record['passed']=True;Path(root/'docs/production-outreach-activation-20261102.json').write_text(json.dumps(record,indent=2));print(json.dumps({'enabled':True,'environment':s['environment'],'scan_paused':False,'email_paused':False,'new_campaigns_created':0}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--activate',action='store_true',required=True);p.parse_args();main()
