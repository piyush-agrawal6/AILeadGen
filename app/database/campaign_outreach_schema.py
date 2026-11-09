"""Minimal linkage plus conservative conversion of legacy bounded outreach intent."""
import json,uuid
from app.database.prospects import now
CAMPAIGN_OUTREACH_SQL='''
ALTER TABLE workflow_runs ADD COLUMN campaign_id TEXT REFERENCES scan_campaigns(id);
CREATE INDEX idx_workflow_campaign ON workflow_runs(campaign_id,kind,status);
'''

def normalize_legacy(options):
 result=dict(options);had_limit=any(k in result for k in ('emails','emails_to_send'))
 old_limit=result.pop('emails',result.pop('emails_to_send',None))
 result.pop('selected_ids',None);result.pop('scan_id',None);result.pop('require_selected',None)
 result.setdefault('pitch_types',list(result.get('opportunities') or ['WEBSITE','SEO','SECURITY']))
 result.setdefault('outreach_mode','UNCONTACTED');result.setdefault('confirm_recontact',False)
 if had_limit and result.get('kind') in ('OUTREACH','COMBINED'):
  result['legacy_email_limit']=old_limit;result['email_all_eligible']=False;result['needs_owner_review']=True
 else:result.setdefault('email_all_eligible',False)
 return result

def apply(c):
 c.executescript(CAMPAIGN_OUTREACH_SQL)
 # Promote orphan historical scans into the existing campaign table; preserve IDs,
 # findings and message/report relationships rather than creating parallel leads.
 for run in c.execute('SELECT * FROM pipeline_runs WHERE campaign_id IS NULL ORDER BY id').fetchall():
  cid=str(uuid.uuid5(uuid.NAMESPACE_URL,'leadengine:historical-scan:'+str(run['id'])))
  options=json.loads(run['run_configuration_json']) if 'run_configuration_json' in run.keys() and run['run_configuration_json'] else {}
  options.update(name=run['market']+' · '+run['vertical'],cities=[run['market']],verticals=[run['vertical']],target=run['target'],historical_scan_id=run['id'])
  c.execute('INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,status,completed_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',(cid,'system',json.dumps(options),run['started_at'] or now(),run['target'],run['status'],run['finished_at']))
  c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run['id']))
 for run in c.execute('SELECT * FROM workflow_runs').fetchall():
  options=json.loads(run['configuration_json']);cid=None
  if run['kind'] in ('SCAN','COMBINED') and c.execute('SELECT 1 FROM scan_campaigns WHERE id=?',(run['id'],)).fetchone():cid=run['id']
  elif options.get('campaign_id'):cid=options['campaign_id']
  elif options.get('scan_id'):
   found=c.execute('SELECT campaign_id FROM pipeline_runs WHERE id=?',(options['scan_id'],)).fetchone();cid=found[0] if found else None
  if cid:c.execute('UPDATE workflow_runs SET campaign_id=? WHERE id=?',(cid,run['id']))
  if run['kind']=='OUTREACH' and run['status'] in ('RUNNING','PREPARING','DRAFT','PAUSED'):
   c.execute("UPDATE workflow_runs SET status='NEEDS_REVIEW',error='Legacy outreach requires campaign and all-eligible audience review.' WHERE id=?",(run['id'],))
   c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE status='QUEUED' AND prospect_id IN (SELECT prospect_id FROM outreach_run_items WHERE run_id=?)",(run['id'],))
 for schedule in c.execute('SELECT id,configuration_json FROM automation_schedules').fetchall():
  options=normalize_legacy(json.loads(schedule['configuration_json']))
  c.execute('UPDATE automation_schedules SET configuration_json=?,updated_at=? WHERE id=?',(json.dumps(options),now(),schedule['id']))
 row=c.execute('SELECT configuration_json FROM shared_settings WHERE id=1').fetchone()
 if row:
  config=json.loads(row[0])
  if config.get('manual_defaults'):config['manual_defaults']=normalize_legacy(config['manual_defaults']);c.execute('UPDATE shared_settings SET configuration_json=? WHERE id=1',(json.dumps(config),))
