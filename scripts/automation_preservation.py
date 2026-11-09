"""Read-only production preservation hashes; never export row contents or secrets."""
import sys,os,json,hashlib,argparse
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
TABLES=('scan_campaigns','pipeline_runs','prospects','prospect_observations','businesses','business_identities','lead_scores','opportunity_scores','social_profiles','client_reports','activities','followups','lead_lists','lead_list_members','email_accounts','email_threads','email_messages')
p=argparse.ArgumentParser();p.add_argument('stage',choices=['before','after']);a=p.parse_args()
result={'checked_at':datetime.now(timezone.utc).isoformat(),'read_only':True,'tables':{}}
with db_session() as c:
 c.execute('SET TRANSACTION READ ONLY')
 result['schema']=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
 for table in TABLES:
  rows=[dict(r) for r in c.execute('SELECT * FROM '+table).fetchall()]
  hashes=sorted(hashlib.sha256(json.dumps(r,sort_keys=True,default=str).encode()).hexdigest() for r in rows)
  result['tables'][table]={'count':len(rows),'row_hashes':hashes}
if a.stage=='after':
 before=json.loads(Path('docs/automation-preservation-before.json').read_text())
 result['checks']={t:{'count_preserved':r['count']>=before['tables'][t]['count'],'original_rows_unchanged':set(before['tables'][t]['row_hashes']).issubset(r['row_hashes'])} for t,r in result['tables'].items()}
Path('docs/automation-preservation-'+a.stage+'.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'schema':result['schema'],'counts':{t:r['count'] for t,r in result['tables'].items()},'checks':result.get('checks')}))
