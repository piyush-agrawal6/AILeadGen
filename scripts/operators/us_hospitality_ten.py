"""Owner-requested one-time US hospitality scan; activation remains separately gated."""
import sys,json,time,secrets,hmac,hashlib,uuid,argparse
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import requests
from dotenv import dotenv_values
from app.api.routes.workflows import Run,Schedule
root=Path(__file__).resolve().parents[2];state_path=root/'docs/owner-us-hospitality-10.json'
v=dotenv_values(root/'.env');base='https://leadengine-api-befca7xg4a-el.a.run.app';actor=v['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower()
def call(method,path,payload=None,expected=200):
 body=json.dumps(payload,separators=(',',':')).encode() if payload is not None else b'';stamp=str(int(time.time()));nonce=secrets.token_hex(16)
 canonical='\n'.join([stamp,nonce,method,path,hashlib.sha256(body).hexdigest(),actor])
 headers={'Content-Type':'application/json','X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(v['LEADENGINE_API_SIGNING_SECRET'].encode(),canonical.encode(),hashlib.sha256).hexdigest()}
 r=requests.request(method,base+path,data=body or None,headers=headers,timeout=180)
 if r.status_code!=expected:raise RuntimeError(f'{method} {path}: HTTP {r.status_code}; '+r.text[:300])
 return r.json()
def persist(state):state_path.write_text(json.dumps(state,indent=2))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--start-scan',action='store_true');args=parser.parse_args()
 state=json.loads(state_path.read_text()) if state_path.exists() else {'owner_request':'Start now: one-time scan + outreach, 10 qualified leads, United States, hospitality','request_id':str(uuid.uuid4()),'created_at':datetime.now(timezone.utc).isoformat(),'activation_approval_pending':True}
 if not args.start_scan:
  for path in ['/api/workflow/safety','/api/automation/summary','/api/operations/runs?status=RUNNING','/api/workflow/schedules']:
   data=call('GET',path)
   if path.endswith('summary'):data={k:data[k] for k in ('controls','environment')}
   print(json.dumps({'path':path,'data':data}),flush=True)
  return
 if 'schedule_id' not in state:
  plan=Run(request_id=state['request_id'],name='US Hospitality · 10 qualified · Owner one-time',kind='COMBINED',target=10,countries=['United States'],cities=[],verticals=['hospitality'],pitch_types=['WEBSITE','SEO','SECURITY'],opportunities=['WEBSITE','SEO','SECURITY'],email_all_eligible=True,outreach_mode='UNCONTACTED',confirm_recontact=False,max_hour=5,max_day=10,spacing_minutes=12,window_start='09:00',window_end='17:00',recipient_timezone=True)
  payload=Schedule(name=plan.name,configuration=plan,enabled=False,timezone='America/New_York',frequency='once',start_at=(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()).model_dump()
  state['schedule_configuration']=payload;persist(state)
  result=call('POST','/api/workflow/schedules',payload,201);state['schedule_id']=result['id'];persist(state);print(json.dumps({'schedule_created':state['schedule_id'],'enabled':False,'target':10}),flush=True)
 if 'run_id' not in state:
  result=call('POST',f"/api/workflow/schedules/{state['schedule_id']}/run-now")
  state['run_id']=result['run_id'];state['scan_triggered_at']=datetime.now(timezone.utc).isoformat();persist(state)
 result=call('GET','/api/workflow/runs/'+state['run_id'])
 state['last_status']={'status':result['status'],'qualified':result['result_count'],'target':result['requested'],'scan_ids':[s['id'] for s in result['scans']],'scans':result['scans'],'error':result.get('error')};persist(state)
 print(json.dumps({'schedule_id':state['schedule_id'],'run_id':state['run_id'],'status':state['last_status'],'outreach_held_for_activation':True}),flush=True)
if __name__=='__main__':main()
