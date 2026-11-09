"""One required schema-11 upgrade, with private rollback COPY and row preservation."""
import os,sys,json,zipfile,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.campaign_outreach_schema import normalize_legacy
from app.mail.config import mail_settings
from psycopg import sql
s=mail_settings();assert not(s.auto_scan_enabled or s.auto_email_enabled or s.sending_enabled)
state_path=Path('docs/campaign-operations-migration.json');c=get_connection(session_bound=True)
try:
 version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
 if version==11:
  assert state_path.exists() and json.loads(state_path.read_text()).get('passed')
  print(json.dumps({'schema':11,'already_verified':True}));raise SystemExit(0)
 assert version==10
 assert not c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED') OR lease_owner IS NOT NULL").fetchone()[0]
 assert not c.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')").fetchone()[0]
 controls=c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone();assert controls['scan_paused'] and controls['email_paused']
 c.commit();c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
 tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()]
 folder=Path('data/backups');folder.mkdir(parents=True,exist_ok=True);os.chmod(folder,0o700)
 archive=folder/('campaign-operations-schema10-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.zip')
 before={};manifest={}
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
  os.chmod(archive,0o600)
  for table in tables:
   rows=[dict(r) for r in c.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table)).as_string(c.raw)).fetchall()];before[table]=rows
   columns=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position",(table,)).fetchall()]
   digest=hashlib.sha256()
   with z.open('db/'+table+'.copybin','w') as out:
    with c.raw.cursor().copy(sql.SQL('COPY {} TO STDOUT (FORMAT BINARY)').format(sql.Identifier(table))) as copy:
     for block in copy:out.write(block);digest.update(block)
   manifest[table]={'count':len(rows),'columns':columns,'sha256':digest.hexdigest()}
  z.writestr('manifest.json',json.dumps({'schema':10,'tables':manifest},default=str))
 c.commit()
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for table,metadata in manifest.items():assert hashlib.sha256(z.read('db/'+table+'.copybin')).hexdigest()==metadata['sha256']
 record={'backup':str(archive.resolve()),'backup_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'backup_verified':True,'before_schema':10,'passed':False};state_path.write_text(json.dumps(record,indent=2))
 assert run_migrations(c)==1
 def normalized(table,r):
  r=dict(r)
  if table=='pipeline_runs':r.pop('campaign_id',None)
  if table=='workflow_runs':
   r.pop('campaign_id',None)
   if r['kind']=='OUTREACH':r.pop('status',None);r.pop('error',None)
  if table=='automation_schedules':r['configuration_json']=json.dumps(normalize_legacy(json.loads(r['configuration_json'])),sort_keys=True);r.pop('updated_at',None)
  if table=='shared_settings':
   cfg=json.loads(r['configuration_json'])
   if cfg.get('manual_defaults'):cfg['manual_defaults']=normalize_legacy(cfg['manual_defaults'])
   r['configuration_json']=json.dumps(cfg,sort_keys=True)
  if table=='email_accounts':
   for col in ('last_sync_at','smtp_health','imap_health','health_checked_at','updated_at'):r.pop(col,None)
  return hashlib.sha256(json.dumps(r,sort_keys=True,default=str).encode()).hexdigest()
 checks={}
 transient={'internal_request_nonces','email_sync_lock','email_sync_state'}
 for table,old in before.items():
  if table in transient:continue
  columns=manifest[table]['columns'];query=sql.SQL('SELECT {} FROM {}').format(sql.SQL(',').join(map(sql.Identifier,columns)),sql.Identifier(table))
  after=[dict(r) for r in c.execute(query.as_string(c.raw)).fetchall()]
  checks[table]=set(normalized(table,r) for r in old).issubset(normalized(table,r) for r in after)
 assert all(checks.values()),'Row preservation failed: '+','.join(t for t,ok in checks.items() if not ok)
 assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==11
 controls=c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone();assert controls['scan_paused'] and controls['email_paused']
 record.update(after_schema=11,applied=1,checks=checks,flags_disabled=True,operator_pauses_preserved=True,passed=True);state_path.write_text(json.dumps(record,indent=2));c.commit()
 print(json.dumps({'schema':11,'backup_verified':True,'preserved_tables':len(checks),'flags_disabled':True,'pauses_preserved':True,'passed':True}))
finally:c.close()
