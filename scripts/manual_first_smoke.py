"""Read-only signed production checks: never starts scans, runs or sends mail."""
import sys,time,secrets,hmac,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
import requests
v=dotenv_values('.env');actor=v['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower();secret=v['LEADENGINE_API_SIGNING_SECRET'];base=sys.argv[1].rstrip('/')
def call(method,path,payload=None):
 body=json.dumps(payload,separators=(',',':')).encode() if payload is not None else b'';stamp=str(int(time.time()));nonce=secrets.token_hex(16)
 canonical='\n'.join([stamp,nonce,method,path,hashlib.sha256(body).hexdigest(),actor])
 headers={'Content-Type':'application/json','X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(secret.encode(),canonical.encode(),hashlib.sha256).hexdigest()}
 r=requests.request(method,base+path,data=body or None,headers=headers,timeout=90)
 assert r.status_code==200,(path,r.status_code)
 return r.json()
checks={}
for path in ('/api/health','/api/workflow/dashboard','/api/workflow/runs','/api/workflow/schedules','/api/workflow/defaults','/api/workflow/safety','/api/workflow/messages','/api/workflow/messages?direction=INBOUND','/api/automation/master-leads','/api/automation/summary','/api/email/leads/2/compose'):
 d=call('GET',path)
 if path.endswith('/schedules'):assert d==[],'No schedule may be silently created/enabled'
 if path.endswith('/summary'):
  assert not any(d['environment'][k] for k in ('scan_enabled','auto_email_enabled','sending_enabled'))
  assert d['controls']['scan_paused'] and d['controls']['email_paused']
 if path.endswith('/safety'):assert not d['sending_enabled'] and d['max_hour']<=10 and d['max_day']<=100
 checks[path]='PASS'
health=call('POST','/api/email/health',{});assert health=={'smtp':'READY','imap':'READY'}
checks['gmail_health']=health;checks.update(scans_started=0,emails_sent=0,scheduled_runs_created=0)
Path('docs/manual-first-production-smoke.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks))
