"""Owner-invoked rollback of a clean-start archive. Plan-only unless --apply."""
import os,sys,argparse,json,zipfile,hashlib,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.storage import R2ArtifactStorage
from psycopg import sql
p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('--apply',action='store_true');a=p.parse_args()
with zipfile.ZipFile(a.archive) as z:
 m=json.loads(z.read('manifest.json'));tables=sorted(set(m['tables'])-set(m['preserve']))
 assert all(re.fullmatch('[a-z_]+',t) for t in tables)
 assert z.testzip() is None
 for t in tables:assert hashlib.sha256(z.read('db/'+t+'.copybin')).hexdigest()==m['tables'][t]['sha256']
 print(json.dumps({'archive_verified':True,'operational_tables':len(tables),'objects':len(m['objects']),'apply':a.apply}))
 if not a.apply:raise SystemExit(0)
 storage=R2ArtifactStorage()
 import tempfile
 with tempfile.TemporaryDirectory() as tmp:
  for key,meta in m['objects'].items():
   content=z.read('objects/'+key);assert hashlib.sha256(content).hexdigest()==meta['sha256']
   path=Path(tmp)/'artifact';path.write_bytes(content)
   import mimetypes
   storage.put(key,path,mimetypes.guess_type(key)[0] or 'application/octet-stream')
 with db_session() as c:
  assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==m['schema']
  assert c.execute('SELECT scan_paused FROM automation_controls WHERE id=1').fetchone()[0] and c.execute('SELECT email_paused FROM automation_controls WHERE id=1').fetchone()[0]
  for lock in (691944511,691944307,691944410,691944303,691944302):c.execute('SELECT pg_advisory_xact_lock(?)',(lock,))
  assert not c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED')").fetchone()[0]
  c.execute('TRUNCATE TABLE '+','.join('"'+t+'"' for t in tables)+' RESTART IDENTITY RESTRICT')
  for t in tables:
   with c.raw.cursor().copy(sql.SQL('COPY {} FROM STDIN (FORMAT BINARY)').format(sql.Identifier('public',t))) as copy:
    with z.open('db/'+t+'.copybin') as source:
     while block:=source.read(1024*1024):copy.write(block)
   assert c.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0]==m['tables'][t]['count']
  for s in m['sequences']:
   if s['last_value'] is not None:c.execute('SELECT setval(?::regclass,?,true)',('public.'+s['sequencename'],s['last_value']))
 print('Operational rollback restored; activation flags and configuration were not changed.')
