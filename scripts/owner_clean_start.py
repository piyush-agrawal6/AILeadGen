"""Explicit owner-authorized operational reset, gated by a verified rollback archive."""
import os,sys,json,zipfile,hashlib,uuid,re
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import get_connection,db_session
from app.storage import R2ArtifactStorage,validate_key
from psycopg import sql

STATE=Path('docs/owner-clean-start.json')
if STATE.exists() and json.loads(STATE.read_text()).get('cleared'):raise SystemExit('Clean-start already completed; refusing to clear fresh acceptance data.')
PRESERVE={'schema_migrations','users','shared_settings','internal_request_nonces','scan_markets','automation_controls','email_accounts','email_templates','email_tracking_preferences','email_sync_state','email_sync_lock','saved_views'}
folder=Path('data/backups');folder.mkdir(parents=True,exist_ok=True);os.chmod(folder,0o700)
archive=folder/('owner-clean-start-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.zip')
if archive.exists():raise SystemExit('Backup path already exists')
manifest={'created_at':datetime.now(timezone.utc).isoformat(),'schema':9,'tables':{},'objects':{},'already_missing_object_references':[],'preserve':sorted(PRESERVE),'format':'PostgreSQL binary COPY plus exact private artifact bytes'}
storage=R2ArtifactStorage();keys=set()
for prefix in ('campaigns/','prospects/','audits/'):
 for page in storage.client.get_paginator('list_objects_v2').paginate(Bucket=storage.bucket,Prefix=prefix):
  keys.update(validate_key(r['Key']) for r in page.get('Contents',[]))
c=get_connection(session_bound=True)
try:
 c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
 assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==9
 assert not c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED') OR lease_owner IS NOT NULL").fetchone()[0]
 assert not c.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')").fetchone()[0]
 controls=c.execute('SELECT * FROM automation_controls WHERE id=1').fetchone();assert controls['scan_paused'] and controls['email_paused']
 tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()]
 assert PRESERVE.issubset(tables)
 keys.update(validate_key(r[0]) for r in c.execute('SELECT object_key FROM artifact_objects UNION SELECT object_key FROM client_reports WHERE object_key IS NOT NULL UNION SELECT object_key FROM website_captures WHERE object_key IS NOT NULL').fetchall())
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
  os.chmod(archive,0o600)
  for table in tables:
   assert re.fullmatch('[a-z_]+',table)
   count=c.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier('public',table)).as_string(c.raw)).fetchone()[0]
   digest=hashlib.sha256();size=0
   with z.open('db/'+table+'.copybin','w',force_zip64=True) as output:
    with c.raw.cursor().copy(sql.SQL('COPY {} TO STDOUT (FORMAT BINARY)').format(sql.Identifier('public',table))) as copy:
     for block in copy:
      output.write(block);digest.update(block);size+=len(block)
   manifest['tables'][table]={'count':count,'bytes':size,'sha256':digest.hexdigest()}
  manifest['sequences']=[dict(r) for r in c.execute("SELECT schemaname,sequencename,last_value FROM pg_sequences WHERE schemaname='public'").fetchall()]
  from botocore.exceptions import ClientError
  for key in sorted(keys):
   try:body=storage.get(key)
   except ClientError as exc:
    if exc.response.get('Error',{}).get('Code') in ('NoSuchKey','404','NotFound'):
     manifest['already_missing_object_references'].append(key);continue
    raise
   digest=hashlib.sha256();size=0
   with body,z.open('objects/'+key,'w',force_zip64=True) as output:
    while block:=body.read(1024*1024):output.write(block);digest.update(block);size+=len(block)
   manifest['objects'][key]={'bytes':size,'sha256':digest.hexdigest()}
  z.writestr('manifest.json',json.dumps(manifest,indent=2,default=str))
 c.commit()
finally:c.close()
# Verify every archived byte and perform a real binary-COPY restore in a disposable schema.
schema='cleanstart_verify_'+uuid.uuid4().hex
c=get_connection(session_bound=True)
try:
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for table,meta in manifest['tables'].items():assert hashlib.sha256(z.read('db/'+table+'.copybin')).hexdigest()==meta['sha256']
  for key,meta in manifest['objects'].items():assert hashlib.sha256(z.read('objects/'+key)).hexdigest()==meta['sha256']
  c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)).as_string(c.raw))
  for table,meta in manifest['tables'].items():
   c.execute(sql.SQL('CREATE TABLE {} (LIKE {} INCLUDING ALL)').format(sql.Identifier(schema,table),sql.Identifier('public',table)).as_string(c.raw))
   with c.raw.cursor().copy(sql.SQL('COPY {} FROM STDIN (FORMAT BINARY)').format(sql.Identifier(schema,table))) as copy:
    with z.open('db/'+table+'.copybin') as source:
     while block:=source.read(1024*1024):copy.write(block)
   assert c.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(schema,table)).as_string(c.raw)).fetchone()[0]==meta['count']
  c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)).as_string(c.raw));c.commit()
finally:c.close()
state={'backup':str(archive.resolve()),'backup_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'backup_verified':True,'restore_test_passed':True,'before':{t:r['count'] for t,r in manifest['tables'].items()},'private_objects_backed_up':len(manifest['objects']),'already_missing_object_references':len(manifest['already_missing_object_references']),'cleared':False}
STATE.write_text(json.dumps(state,indent=2));print(json.dumps({'backup_verified':True,'restore_test_passed':True,'archive':str(archive),'tables':len(tables),'objects':len(keys)}),flush=True)
operational=sorted(set(tables)-PRESERVE)
with db_session() as c:
 for lock in (691944511,691944307,691944410,691944303,691944302):c.execute('SELECT pg_advisory_xact_lock(?)',(lock,))
 assert not c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED') OR lease_owner IS NOT NULL").fetchone()[0]
 assert not c.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')").fetchone()[0]
 # Explicit list and RESTRICT: never cascade into configuration tables.
 c.execute('TRUNCATE TABLE '+','.join('"'+t+'"' for t in operational)+' RESTART IDENTITY RESTRICT')
 after={t:c.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0] for t in operational}
 assert not any(after.values())
 for t in PRESERVE-{'internal_request_nonces','email_sync_lock','email_sync_state'}:
  assert c.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0]==manifest['tables'][t]['count']
state.update(cleared=True,after=after,preserved=sorted(PRESERVE));STATE.write_text(json.dumps(state,indent=2))
# Delete only keys captured in this immutable rollback archive, never a new acceptance key.
if keys:storage.delete_many(sorted(keys))
state['private_artifact_cleanup_complete']=True;state['zero_checks']={key:after[table] for key,table in [('Master Leads','master_lead_state'),('Qualified Leads','businesses'),('Queued Leads','automation_email_queue'),('Prospect Email Threads','email_threads'),('Prospect Email Messages','email_messages')]};STATE.write_text(json.dumps(state,indent=2))
print(json.dumps({'cleared':True,'schema':9,'zero_checks':state['zero_checks'],'objects_removed':len(keys),'preserved':sorted(PRESERVE)}),flush=True)
