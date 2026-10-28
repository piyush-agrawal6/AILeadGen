"""Bounded ten-minute tracked-mail sync using the existing private worker."""
import json,subprocess
from pathlib import Path
project='querryside';region='asia-south1';name='leadengine-email-sync'
def run(args,missing=False):
    r=subprocess.run(['gcloud.cmd',*args],capture_output=True,text=True)
    if r.returncode and not missing:raise SystemExit('Scheduler configuration step failed: '+args[0]+' '+args[1])
    return r
run(['services','enable','cloudscheduler.googleapis.com','--project='+project,'--quiet'])
body=json.dumps({'overrides':{'taskCount':1,'timeout':'180s','containerOverrides':[{'env':[{'name':'LEADENGINE_EMAIL_SYNC','value':'1'}]}]}})
exists=run(['scheduler','jobs','describe',name,'--project='+project,'--location='+region,'--format=json'],True)
if exists.returncode and 'NOT_FOUND' not in exists.stderr:raise SystemExit('Could not establish scheduler state.')
verb='update' if exists.returncode==0 else 'create'
run(['scheduler','jobs',verb,'http',name,'--project='+project,'--location='+region,'--schedule=*/10 * * * *','--time-zone=Etc/UTC','--uri=https://run.googleapis.com/v2/projects/'+project+'/locations/'+region+'/jobs/leadengine-worker:run','--http-method=POST','--headers=Content-Type=application/json','--message-body='+body,'--oauth-service-account-email=leadengine-api-sa@'+project+'.iam.gserviceaccount.com','--oauth-token-scope=https://www.googleapis.com/auth/cloud-platform','--attempt-deadline=60s','--quiet'])
record={'job':name,'interval_minutes':10,'worker':'leadengine-worker','maximum_execution_seconds':180,'outbound_sending':False,'tracked_threads_only':True,'uses_existing_identity':True}
Path('docs/phase4-email-scheduler.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
