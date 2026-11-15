"""One owner-authorized real setup-guidance worker; no profile/ICP mutations."""
import hashlib,json,time,uuid
from pathlib import Path
import httpx,psycopg
from dotenv import dotenv_values
from scripts.deploy_product_release import signed,ROOT
from app.database.postgres import session_url
OUT=ROOT/'data/artifacts/verification/final-remediation'
def main():
 release=json.loads((OUT/'staged-release.json').read_text());source=release['source_commit']
 state_path=OUT/'setup-provider-acceptance.json'
 if state_path.exists():
  prior=json.loads(state_path.read_text())
  if prior['source_commit']!=source:raise RuntimeError('Use the matching setup acceptance checkpoint.')
  if prior.get('status')=='PASS':print(json.dumps(prior));return
 request_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'planebyte:setup-guidance:'+source))
 state={'source_commit':source,'request_id':request_id,'status':'RUNNING','profile_changed':False,'icp_created':False,'outreach_sent':False,'payment_initiated':False}
 with httpx.Client(base_url='https://intent-only---leadengine-api-befca7xg4a-el.a.run.app',timeout=75,follow_redirects=False) as client:
  before=signed(client,'/api/organization/profile');before.raise_for_status();profile=before.json();org=profile['organization_id']
  body={'prompt':'What should I review about the business needs behind my saved offerings before choosing an ideal customer profile? Give qualitative guidance from the saved workspace context; do not change anything.','request_id':request_id}
  created=signed(client,'/api/organization/onboarding/assistant','POST',body)
  if created.status_code!=202:raise RuntimeError('Setup guidance was not accepted: HTTP '+str(created.status_code))
  job=created.json().get('job')
  if not job or not job.get('id'):raise RuntimeError('Expected an asynchronous setup guidance job.')
  state['job_id']=job['id'];state_path.write_text(json.dumps(state,indent=2))
  deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   response=signed(client,'/api/organization/onboarding/reviews/'+job['id']);response.raise_for_status();detail=response.json()
   if detail['status'] not in ('QUEUED','RUNNING'):break
   time.sleep(2)
  else:raise RuntimeError('Setup guidance exceeded its controlled acceptance deadline.')
  if detail['status']!='READY' or not detail.get('preview',{}).get('answer'):raise RuntimeError('Real setup guidance worker did not return a reviewable result.')
  after=signed(client,'/api/organization/profile');after.raise_for_status()
  if after.json()!=profile:raise RuntimeError('Guidance unexpectedly changed the saved company profile.')
  conf=dotenv_values(ROOT/'.env',interpolate=False)
  with psycopg.connect(session_url(conf['DATABASE_URL']),options='-c default_transaction_read_only=on',connect_timeout=15) as c:
   row=c.execute('SELECT status,execution_name,source_kind,created_at FROM organization_profile_jobs WHERE id=%s AND organization_id=%s',(job['id'],org)).fetchone()
   usage=c.execute("SELECT provider,model,usage_basis,input_tokens,output_tokens FROM ai_request_usage WHERE organization_id=%s AND operation='ONBOARDING_GUIDANCE' AND created_at>=%s ORDER BY created_at DESC LIMIT 1",(org,row[3])).fetchone()
  if not row or row[0]!='READY' or row[2]!='ONBOARDING_ADVICE' or not row[1] or not row[1].startswith('projects/querryside/locations/asia-south1/operations/') or not usage or usage[0]!='VERTEX_AI':raise RuntimeError('Actual cloud dispatch/provider accounting was not verified.')
  state.update(status='PASS',cloud_execution=row[1],provider=usage[0],model=usage[1],usage_basis=usage[2],input_tokens=usage[3],output_tokens=usage[4],answer_sha256=hashlib.sha256(detail['preview']['answer'].encode()).hexdigest())
 state_path.write_text(json.dumps(state,indent=2));state_path.chmod(0o600);print(json.dumps(state))
if __name__=='__main__':
 try:main()
 except Exception as error:print(json.dumps({'status':'FAILED','error_type':type(error).__name__,'detail':str(error) if isinstance(error,RuntimeError) else 'Inspect the restricted acceptance checkpoint.'}));raise SystemExit(1)
