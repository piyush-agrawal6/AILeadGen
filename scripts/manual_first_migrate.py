"""Apply only required additive workflow migration and prove existing rows survive."""
import os,sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.database.migrations import run_migrations
from app.mail.config import mail_settings
s=mail_settings();assert not(s.auto_scan_enabled or s.auto_email_enabled or s.sending_enabled)
path=Path('docs/manual-first-migration.json')
if path.exists() and json.loads(path.read_text()).get('passed'):raise SystemExit('Migration already applied and verified; not rerunning.')
with db_session() as c:
 version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0];assert version==9
 tables=[r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name").fetchall()]
 before={}
 for t in tables:
  rows=[dict(r) for r in c.execute('SELECT * FROM '+t).fetchall()]
  cols=[r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position",(t,)).fetchall()]
  hashes=sorted(hashlib.sha256(json.dumps(r,sort_keys=True,default=str).encode()).hexdigest() for r in rows)
  before[t]={'count':len(rows),'columns':cols,'hashes':hashes}
 assert c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status IN ('RUNNING','QUEUED')").fetchone()[0]==0
 assert c.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')").fetchone()[0]==0
 record={'before_schema':9,'tables':before,'flags_disabled':True,'passed':False};path.write_text(json.dumps(record,indent=2))
 applied=run_migrations(c);assert applied==1
 checks={}
 for t,baseline in before.items():
  rows=[dict(r) for r in c.execute('SELECT '+','.join(baseline['columns'])+' FROM '+t).fetchall()]
  hashes=sorted(hashlib.sha256(json.dumps(r,sort_keys=True,default=str).encode()).hexdigest() for r in rows)
  checks[t]=set(baseline['hashes']).issubset(hashes) and len(rows)>=baseline['count']
 assert all(checks.values()),'Existing row preservation failed'
 assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==10
 assert c.execute('SELECT COUNT(*) FROM automation_schedules').fetchone()[0]==0
 record.update(after_schema=10,pending_migrations_applied=applied,checks=checks,passed=True);path.write_text(json.dumps(record,indent=2));print(json.dumps({'schema':10,'existing_tables_preserved':len(checks),'new_schedules':0,'passed':True}))
