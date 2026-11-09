"""Explicit owner-approved one-time campaign activation; preserves Gmail secrets."""
import os,sys,json,uuid,subprocess,argparse
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root));os.environ['DATABASE_BACKEND']='postgres'
from dotenv import dotenv_values,set_key
from app.database.connection import db_session
from app.database.prospects import now
from app.api.routes.workflows import Run,Schedule,save_schedule
from app.workflows.service import lock
cli='/Users/planebyte/Downloads/google-cloud-sdk/bin/gcloud';path=root/'docs/owner-us-hospitality-10.json';v=dotenv_values(root/'.env');actor=v['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower()
CHANGES={'AUTO_SCAN_ENABLED':'true','AUTO_EMAIL_ENABLED':'true','EMAIL_SENDING_ENABLED':'true','EMAIL_SEND_MODE':'production','EMAIL_LIVE_APPROVED':'true'}
def command(args):
 r=subprocess.run([cli,*args,'--project=querryside','--format=json'],capture_output=True,text=True)
 if r.returncode:raise RuntimeError('GCP action failed: '+' '.join(args[:4])+' '+r.stderr[-350:])
 return json.loads(r.stdout) if r.stdout.strip() else {}
def runtime(kind):
 d=command(['run','services' if kind=='api' else 'jobs','describe','leadengine-api' if kind=='api' else 'leadengine-worker','--region=asia-south1']);inner=d['spec']['template']['spec'];container=(inner if kind=='api' else inner['template']['spec'])['containers'][0];return d,container
state=json.loads(path.read_text()) if path.exists() else {'request_id':str(uuid.uuid4()),'created_at':now(),'owner_request':'Start now: one-time scan + outreach; 10 qualified leads; United States; hospitality'}
state.update(activation_approval_pending=False,owner_activation_approval='Yes—activate this one-time campaign',approval_received_at=state.get('approval_received_at') or now())
def persist():path.write_text(json.dumps(state,indent=2))
p=argparse.ArgumentParser();p.add_argument('stage',choices=['create','environment','start']);args=p.parse_args();persist()
if args.stage=='create':
 with db_session() as c:
  lock(c)
  active=c.execute("SELECT COUNT(*) FROM workflow_runs WHERE status IN ('RUNNING','PREPARING')").fetchone()[0]
  other=c.execute('SELECT COUNT(*) FROM automation_schedules WHERE enabled=1 AND deleted_at IS NULL').fetchone()[0]
  if not state.get('schedule_id'):
   assert active==0 and other==0,'Review unrelated active work before enabling global capabilities.'
   plan=Run(request_id=state['request_id'],name='US Hospitality · 10 qualified · Owner one-time',kind='COMBINED',target=10,countries=['United States'],cities=[],verticals=['hospitality'],email_all_eligible=True,pitch_types=['WEBSITE','SEO','SECURITY'],max_hour=5,max_day=10,spacing_minutes=12,window_start='09:00',window_end='17:00',recipient_timezone=True)
   payload=Schedule(name=plan.name,configuration=plan,enabled=False,timezone='America/New_York',frequency='once',start_at=now())
   saved=save_schedule(c,payload,actor);state.update(schedule_id=saved['id'],schedule_configuration=payload.model_dump());c.commit();persist()
 print(json.dumps({'schedule_id':state['schedule_id'],'enabled':False,'target':10,'country':'United States','vertical':'hospitality'}),flush=True)
elif args.stage=='environment':
 for kind in ['worker','api']:
  before,container=runtime(kind);entries=container['env'];mapping={e['name']:e for e in entries}
  assert mapping['EMAIL_PROVIDER']['value']=='gmail' and mapping['MAIL_FROM_ADDRESS']['value']=='planebyte@gmail.com'
  assert mapping['GMAIL_APP_PASSWORD'].get('valueFrom'),'Keep existing Secret Manager reference.'
  changes={k:value for k,value in CHANGES.items() if mapping.get(k,{}).get('value')!=value}
  if changes:command(['run','jobs' if kind=='worker' else 'services','update','leadengine-worker' if kind=='worker' else 'leadengine-api','--region=asia-south1','--update-env-vars='+','.join(k+'='+value for k,value in changes.items()),'--quiet'])
  after,new=runtime(kind);newmap={e['name']:e for e in new['env']}
  assert all(newmap[k].get('value')==value for k,value in CHANGES.items())
  assert sorted([e for e in entries if e['name'] not in CHANGES],key=lambda e:e['name'])==sorted([e for e in new['env'] if e['name'] not in CHANGES],key=lambda e:e['name'])
  if kind=='api':
   revision=after['status']['latestCreatedRevisionName'];command(['run','services','update-traffic','leadengine-api','--region=asia-south1','--to-revisions='+revision+'=100','--quiet']);state['api_revision']=revision
  state.setdefault('activation',{})[kind]={'settings':CHANGES,'gmail_secret_reference_preserved':True,'other_environment_preserved':True};persist();print(json.dumps({'runtime':kind,'live_capabilities_enabled':True,'gmail_secret_preserved':True}),flush=True)
 for key,value in CHANGES.items():set_key(str(root/'.env'),key,value,quote_mode='never')
 state['root_env_synchronized']=True;persist()
elif args.stage=='start':
 assert state.get('root_env_synchronized') and len(state.get('activation',{}))==2
 with db_session() as c:
  lock(c);sid=state['schedule_id'];row=c.execute('SELECT * FROM automation_schedules WHERE id=?',(sid,)).fetchone();assert row and row['kind']=='COMBINED'
  assert c.execute("SELECT COUNT(*) FROM automation_schedules WHERE enabled=1 AND deleted_at IS NULL AND id<>?",(sid,)).fetchone()[0]==0
  if not state.get('dispatch_requested_at'):
   stamp=now();c.execute('UPDATE automation_schedules SET enabled=1,next_run_at=?,start_at=?,updated_at=? WHERE id=?',(stamp,stamp,stamp,sid))
   c.execute('UPDATE automation_controls SET scan_paused=0,email_paused=0,pause_reason=NULL,updated_at=? WHERE id=1',(stamp,));c.commit();state['dispatch_requested_at']=stamp;persist()
 for name in ['leadengine-daily-acquisition','leadengine-hourly-outreach']:
  job=command(['scheduler','jobs','describe',name,'--location=asia-south1'])
  if job['state']=='PAUSED':command(['scheduler','jobs','resume',name,'--location=asia-south1','--quiet'])
 command(['scheduler','jobs','run','leadengine-daily-acquisition','--location=asia-south1','--quiet'])
 state['scheduler_triggered_at']=now();persist();print(json.dumps({'schedule_id':state['schedule_id'],'one_time_enabled':True,'dispatch_triggered':True,'target':10,'limits':{'hour':5,'day':10,'spacing_minutes':12},'recipient_local_window':'09:00–17:00 weekdays'}),flush=True)
