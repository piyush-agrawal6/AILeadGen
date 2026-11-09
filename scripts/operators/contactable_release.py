"""Stage additive schema15; reset remains a separate, registry-verified operation."""
import os,json,hashlib,argparse
from pathlib import Path
from scripts.stage_acquisition_release import command,REGION
STATE=Path('deploy/contactable-release.json')
CONFIG={'LEAD_QUALIFICATION_MODE':'CONTACTABLE_ONLY','ENABLE_PRE_OUTREACH_ANALYSIS':'false','AUTO_SCAN_ENABLED':'false'}
def stage(buildfile):
 b=json.loads(Path(buildfile).read_text());build=command(['builds','describe',b['id'],'--region='+REGION]);assert build['status']=='SUCCESS'
 state={'build':build['id'],'schema_target':15,'runtimes':{},'nonsecret_config':CONFIG,'cleanup_performed':Path('docs/contactable-clean-reset.json').exists()}
 for kind,name,part in [('jobs','leadengine-worker','worker'),('jobs','leadengine-acquisition','acquisition'),('services','leadengine-api','api')]:
  d=command(['run',kind,'describe',name,'--region='+REGION]);s=d['spec']['template']['spec'];s=s if kind=='services' else s['template']['spec'];before=s['containers'][0];image=next(i for i in build['images'] if '/'+part+':' in i)
  args=['run',kind,'update',name,'--region='+REGION,'--image='+image,'--update-env-vars='+','.join(k+'='+v for k,v in CONFIG.items()),'--quiet']
  if kind=='services':args+=['--no-traffic','--tag=contactable']
  command(args);new=command(['run',kind,'describe',name,'--region='+REGION]);after=new['spec']['template']['spec'];after=after if kind=='services' else after['template']['spec'];env=after['containers'][0]['env']
  assert s['serviceAccountName']==after['serviceAccountName'];assert sorted([e for e in before['env'] if e['name'] not in CONFIG],key=lambda e:e['name'])==sorted([e for e in env if e['name'] not in CONFIG],key=lambda e:e['name'])
  state['runtimes'][name]={'image':image,'service_account':after['serviceAccountName'],'email_provider_and_secret_configuration_preserved':True}
  if kind=='services':state['staged_revision']=new['status']['latestCreatedRevisionName'];state['staged_url']=next(v['url'] for v in new['status']['traffic'] if v.get('tag')=='contactable')
  STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'staged':name,'provider_and_secrets_preserved':True}),flush=True)

def migrate():
 os.environ['DATABASE_BACKEND']='postgres'
 from app.database.connection import get_connection
 from app.database.contactable_schema import CONTACTABLE_SQL
 proof=json.loads(Path('data/backups/contactable-before-reset-20261103.json').read_text());assert proof['verified'] and proof['all_rows_compared']
 assert STATE.exists() and len(json.loads(STATE.read_text())['runtimes'])==3,'Compatible runtimes must stage first'
 c=get_connection(session_bound=True)
 try:
  version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
  if version==15:print('Schema15 already applied; no migration repeated');return
  assert version==14;controls=c.execute('SELECT scan_paused,email_paused FROM automation_controls').fetchone();assert controls[0] and controls[1]
  assert not c.execute("SELECT 1 FROM email_messages WHERE status IN ('SENDING','UNCERTAIN') LIMIT 1").fetchone()
  before={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('prospects','email_messages','scan_campaigns','email_address_suppressions','users')};c.commit()
  c.execute("SET LOCAL lock_timeout='3s';SET LOCAL statement_timeout='15s'");c.execute('SELECT pg_advisory_xact_lock(691944301)');c.raw.execute(CONTACTABLE_SQL+'\nINSERT INTO schema_migrations(version) VALUES(15);');c.commit()
  after={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in before};assert before==after
  Path('docs/contactable-additive-migration.json').write_text(json.dumps({'schema':15,'before':before,'after':after,'no_existing_rows_deleted':True},indent=2));print(json.dumps({'schema':15,'preserved':True}),flush=True)
 finally:c.close()

def upload_asset():
 os.environ['DATABASE_BACKEND']='postgres'
 from app.database.connection import get_connection
 from app.database.prospects import now
 from app.mail.contacted import organization
 from app.storage import R2ArtifactStorage
 from pypdf import PdfReader
 from app.outreach.fixed import ASSET_ID
 path=Path('output/pdf/planebyte-capabilities-v1.pdf');raw=path.read_bytes();pages=len(PdfReader(path).pages);assert pages==3
 key='audits/company-assets/planebyte-capabilities-v1.pdf';digest=hashlib.sha256(raw).hexdigest();c=get_connection(session_bound=True)
 try:
  prior=c.execute('SELECT sha256 FROM company_pdf_assets WHERE organization_id=? AND id=? AND version=?',(organization(),ASSET_ID,'v1')).fetchone()
  if prior:assert prior[0]==digest,'Existing approved version is immutable; create v2 instead';return
  storage=R2ArtifactStorage();storage.put(key,path,'application/pdf')
  with storage.get(key) as f:assert hashlib.sha256(f.read()).hexdigest()==digest
  c.execute('INSERT INTO company_pdf_assets(id,version,organization_id,filename,object_key,sha256,size_bytes,page_count,active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)',(ASSET_ID,'v1',organization(),'PlaneByte Capabilities & Services.pdf',key,digest,len(raw),pages,now()));c.commit();print(json.dumps({'shared_pdf_uploaded':True,'version':'v1','pages':pages,'size':len(raw),'sha256':digest}),flush=True)
 finally:c.close()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stage','migrate','asset']);p.add_argument('--build');a=p.parse_args();stage(a.build) if a.action=='stage' else migrate() if a.action=='migrate' else upload_asset()
