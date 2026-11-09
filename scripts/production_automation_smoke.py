"""Signed, bounded production smoke checks. Never sends mail or starts scans."""
import sys,json,time,hmac,hashlib,secrets,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
import requests
p=argparse.ArgumentParser();p.add_argument('--url',required=True);a=p.parse_args()
v=dotenv_values('.env');actor=v['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower();secret=v['LEADENGINE_API_SIGNING_SECRET']
def call(method,path,payload=None):
 body=json.dumps(payload,separators=(',',':')).encode() if payload is not None else b''
 stamp=str(int(time.time()));nonce=secrets.token_hex(16)
 canonical='\n'.join([stamp,nonce,method,path,hashlib.sha256(body).hexdigest(),actor])
 headers={'Content-Type':'application/json','X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(secret.encode(),canonical.encode(),hashlib.sha256).hexdigest()}
 r=requests.request(method,a.url.rstrip('/')+path,data=body or None,headers=headers,timeout=120,allow_redirects=False)
 if r.status_code!=200:raise RuntimeError('Smoke failed: '+method+' '+path+' HTTP '+str(r.status_code))
 return r.json()
result={}
for path in ['/api/health','/api/intelligence/overview','/api/automation/summary','/api/automation/master-leads','/api/automation/markets','/api/email/account']:
 data=call('GET',path)
 if path.endswith('/summary'):
  env=data['environment'];assert not env['scan_enabled'] and not env['auto_email_enabled'] and not env['sending_enabled']
  assert data['controls']['scan_paused'] and data['controls']['email_paused']
  result['automation']={'flags_disabled':True,'database_paused':True,'queue':data['queue']}
 elif path.endswith('/master-leads'):result['master_leads']=data['total']
 elif path.endswith('/markets'):result['markets_first_page']=len(data)
 elif path.endswith('/account'):
  assert data['provider']=='gmail' and not data['can_send']
  assert 'GMAIL_APP_PASSWORD' not in json.dumps(data)
 result[path]='PASS'
master=call('GET','/api/automation/master-leads?tab=all&page_size=1')
if 'counts' in master:
 assert 'today' in master['counts'] and 'dnc' in master['counts']
 result['master_tab_counts']='PASS'
 for path in ['/api/automation/master-leads?email_availability=no&page_size=1','/api/automation/markets/page?page=2&page_size=25','/api/automation/targets','/api/automation/email-history?page_size=5','/api/automation/identity-review']:
  call('GET',path);result[path]='PASS'
health=call('POST','/api/email/health',{})
assert health=={'smtp':'READY','imap':'READY'},'Gmail health is not ready'
result['gmail_health']=health;result['outbound_messages_sent']=0;result['scans_started']=0
Path('docs/automation-production-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
