"""Verify the existing working dataset without modifying it."""
import os,json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
before=json.loads(Path('docs/phase4-before.json').read_text(encoding='utf-8'));result={}
with db_session() as c:
    result['counts']={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in before['counts']}
    result['statuses']=[dict(r) for r in c.execute('SELECT lead_status,COUNT(*) AS count FROM prospects GROUP BY lead_status').fetchall()]
    result['runs']=[dict(r) for r in c.execute('SELECT id,market,vertical,status,qualified,exported FROM pipeline_runs ORDER BY id').fetchall()]
    result['schema']=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
    result['data_hashes']={}
    for t in before['counts']:
        rows=[dict(r) for r in c.execute('SELECT * FROM '+t).fetchall()];result['data_hashes'][t]=hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()
    result['report_additions']=[dict(r) for r in c.execute('SELECT id,prospect_id,status,created_by,created_at FROM client_reports ORDER BY created_at').fetchall()] if before['counts']['client_reports']==0 else []
result['preserved_counts']=all(result['counts'][t]==before['counts'][t] for t in before['counts'])
result['existing_rows_identical']=result['data_hashes']==before['data_hashes']
unchanged=[t for t in before['counts'] if t!='client_reports']
# The baseline had no reports. Three authenticated user reports were generated
# while development was in progress; preserve them instead of deleting real work.
expected_reports={'20c3f265-cf4e-4ade-9f04-a671dfeb24b4','b9689c5a-262a-4cbe-8152-76e27ac76125','8347829d-7d02-45df-ab2f-aeda5188e97d'}
result['verified_concurrent_report_additions']=before['counts']['client_reports']==0 and {r['id'] for r in result['report_additions']}==expected_reports and all(r['status']=='READY' and r['created_by']=='planebyte@gmail.com' for r in result['report_additions'])
result['original_data_preserved']=all(result['counts'][t]==before['counts'][t] and result['data_hashes'][t]==before['data_hashes'][t] for t in unchanged) and (result['data_hashes']['client_reports']==before['data_hashes']['client_reports'] or result['verified_concurrent_report_additions'])
Path('docs/phase4-after.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8');print(json.dumps({'schema':result['schema'],'preserved_counts':result['preserved_counts'],'existing_rows_identical':result['existing_rows_identical']}))
if not result['original_data_preserved']:raise SystemExit('Data preservation check failed; traffic must not be routed.')
print(json.dumps({'original_data_preserved':True,'verified_concurrent_report_additions':result['verified_concurrent_report_additions']}))
