"""Signed production read/validation checks. Never starts acquisition or SMTP."""
import sys,time,secrets,hmac,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
import requests
from concurrent.futures import ThreadPoolExecutor
v=dotenv_values('.env');actor=v['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower();secret=v['LEADENGINE_API_SIGNING_SECRET'];base=sys.argv[1].rstrip('/')
def call(method,path,payload=None,expected=200):
 body=json.dumps(payload,separators=(',',':')).encode() if payload is not None else b'';stamp=str(int(time.time()));nonce=secrets.token_hex(16)
 canonical='\n'.join([stamp,nonce,method,path,hashlib.sha256(body).hexdigest(),actor])
 headers={'Content-Type':'application/json','X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(secret.encode(),canonical.encode(),hashlib.sha256).hexdigest()}
 r=requests.request(method,base+path,data=body or None,headers=headers,timeout=120)
 assert r.status_code==expected,(path,r.status_code)
 return r.json()
checks={};campaigns=[]
paths=('/api/health','/api/operations/dashboard','/api/operations/campaigns','/api/operations/runs','/api/operations/messages','/api/operations/messages?direction=INBOUND','/api/operations/schedules','/api/operations/reports','/api/operations/exports','/api/operations/files','/api/operations/views','/api/workflow/safety','/api/automation/master-leads','/api/automation/summary')
# Settle the existing reconciliation view first, then parallelize independent reads.
call('GET','/api/operations/dashboard');checks['/api/operations/dashboard']='PASS'
def read(path):
 data=call('GET',path);print('PASS '+path,flush=True);return path,data
with ThreadPoolExecutor(max_workers=4) as pool:
 results=list(pool.map(read,[path for path in paths if path!='/api/operations/dashboard']))
for path,data in results:
 checks[path]='PASS'
 if path=='/api/operations/campaigns':campaigns=data['items']
 if path.endswith('/summary'):
  assert not any(data['environment'][k] for k in ('scan_enabled','auto_email_enabled','sending_enabled'))
  assert data['controls']['scan_paused'] and data['controls']['email_paused']
 if path.endswith('/safety'):assert not data['sending_enabled'] and data['max_hour']<=10 and data['max_day']<=100
for item in campaigns:
 cid=item['id'];data=call('GET','/api/operations/campaigns/'+cid)
 assert data['qualified']==data['total_accounted'];checks['campaign:'+cid]={'qualified':data['qualified'],'accounted':data['total_accounted'],'status':data['status']}
 page=call('GET','/api/operations/campaigns/'+cid+'/leads');assert page['qualified']==data['qualified']
 if data['status'] not in ('RUNNING','QUEUED','PAUSED','DRAFT','PREPARING'):
  options={'kind':'OUTREACH','campaign_id':cid,'pitch_types':['WEBSITE','SEO','SECURITY']}
  plan=call('POST','/api/workflow/eligible',options);assert plan['total']==plan['will_queue'] and plan['qualified']==plan['total_accounted']
  assert 'items' not in plan
call('POST','/api/workflow/runs',{'kind':'OUTREACH'},expected=422)
if campaigns:call('POST','/api/workflow/runs',{'kind':'OUTREACH','campaign_id':campaigns[0]['id'],'emails':1},expected=422)
result={'checks':checks,'flags_disabled':True,'operator_pauses_preserved':True,'scans_started':0,'emails_sent':0,'schedules_created':0,'passed':True}
Path('docs/campaign-operations-production-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
