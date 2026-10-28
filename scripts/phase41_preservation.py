"""Read-only identity and immutable-record preservation for Phase 4.1."""
import os,json,hashlib,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
baseline=json.loads(Path('docs/phase41-before.json').read_text(encoding='utf-8'))
result={'checked_at':datetime.now(timezone.utc).isoformat(),'tables':{},'read_only':True,'concurrent_list_removals':[]}
mutable={'email_accounts','prospects','followups'}
with db_session() as c:
 c.execute('SET TRANSACTION READ ONLY');migration=c.execute('SELECT applied_at AT TIME ZONE current_setting($$TimeZone$$) FROM schema_migrations WHERE version=8').fetchone();migration_time=datetime.fromisoformat(str(migration[0]).replace('Z','+00:00')) if migration else None;result['schema']=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
 for table,before in baseline['tables'].items():
  rows=[dict(r) for r in c.execute('SELECT * FROM '+table).fetchall()]
  ids={str(r.get('id',r.get('business_id'))) for r in rows};original=[r for r in rows if str(r.get('id',r.get('business_id'))) in before['ids']]
  if table=='email_messages':
   for row in original:
    for column in ('template_id','message_type','track_opens','track_clicks'):row.pop(column,None)
  digest=hashlib.sha256(json.dumps(sorted(json.dumps(r,sort_keys=True,default=str) for r in original)).encode()).hexdigest()
  missing=set(before['ids'])-ids
  if table=='lead_lists':
   for missing_id in missing:
    evidence=[dict(r) for r in c.execute("SELECT event_at,actor_user_id,metadata_json FROM activities WHERE event_type='LIST_REMOVED' ORDER BY event_at").fetchall() if json.loads(r['metadata_json']).get('list_id')==missing_id and r['event_at']>=baseline['checked_at'] and migration_time and datetime.fromisoformat(r['event_at'])<=migration_time]
    if evidence:result['concurrent_list_removals'].append({'list_id':missing_id,'events':evidence,'source':'Existing authenticated list-delete route; predates Phase 4.1 migration; migration contains no lead-list deletion.'})
  result['tables'][table]={'count':len(rows),'missing_original_ids':sorted(missing),'baseline_count':before['count'],'original_ids_retained':set(before['ids']).issubset(ids),'original_fields_unchanged':digest==before['hash']}
 result['runs']=[dict(r) for r in c.execute('SELECT id,status,market,vertical FROM pipeline_runs ORDER BY id').fetchall()]
accounted={r['list_id'] for r in result['concurrent_list_removals']}
result['all_original_rows_retained']=all(v['original_ids_retained'] for v in result['tables'].values())
result['checks']={'all_original_leads_scans_reports_mail_retained':all(v['original_ids_retained'] for k,v in result['tables'].items() if k!='lead_lists'),'only_missing_rows_are_accounted_list_removals':set(result['tables']['lead_lists']['missing_original_ids'])==accounted,'immutable_original_fields_preserved':all(v['original_fields_unchanged'] for k,v in result['tables'].items() if k not in mutable and k!='lead_lists'),'original_scans_unchanged':result['runs']==baseline['runs']}
# Keep the original strict result visible; preserve evidence of concurrent app edits. Never restore a user-deleted list to make counts match.
Path('docs/phase41-after.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'schema':result['schema'],'checks':result['checks'],'counts':{k:v['count'] for k,v in result['tables'].items()}}))
if not all(result['checks'].values()):raise SystemExit('Production preservation requires review; do not reset or delete data.')
