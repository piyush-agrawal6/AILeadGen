"""Owner-authorized schema14 operational reset; verified private rollback first.

Preserves Gmail, security, suppression, market/experiment configuration and IAM.
Private report/artifact objects remain intact for rollback; only live references clear.
"""
import argparse,hashlib,json,os,uuid
from datetime import datetime,timezone
from pathlib import Path
from psycopg import sql

PRESERVE=set('account_roles acquisition_google_connections acquisition_oauth_states acquisition_preferences acquisition_provider_health audit_log automation_controls email_accounts email_address_suppressions email_sync_lock email_sync_state email_templates email_tracking_preferences experiment_catalog experiment_segments experiments internal_request_nonces provider_rate_limits recovery_checkpoints saved_market_groups saved_views scan_markets schema_migrations shared_settings users worker_health'.split())
OPERATIONAL=set('acquisition_ai_cache acquisition_batches acquisition_events acquisition_issues acquisition_jobs acquisition_requests activities analysis_cache analysis_operations artifact_objects automation_email_queue automation_runs automation_scans automation_schedule_runs automation_schedules business_identities business_intelligence businesses campaign_business_snapshots campaign_settings_snapshots client_reports contact_evidence contact_people contacts deletion_batches deletion_targets duplicate_resolutions email_drafts email_engagement_events email_messages email_threads email_tracking_rate_limits email_tracking_tokens experiment_events experiment_members experiment_replies experiment_sources findings followups identity_resolutions lead_list_members lead_lists lead_scores lead_source_evidence lighthouse_results master_lead_state opportunity_scores outreach_run_items pipeline_run_events pipeline_runs prospect_notes prospect_observations prospect_sales prospects review_cases scan_campaigns social_profile_sources social_profiles website_captures website_profiles worker_attempts workflow_runs'.split())
STATE=Path('data/backups/owner-fresh-500-20261102.json')

def connection():
 os.environ['DATABASE_BACKEND']='postgres'
 from app.database.connection import get_connection
 return get_connection(session_bound=True)

def scope(c):
 tables={r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()}
 assert not PRESERVE&OPERATIONAL
 assert tables==PRESERVE|OPERATIONAL,{'unclassified':sorted(tables-PRESERVE-OPERATIONAL),'missing':sorted((PRESERVE|OPERATIONAL)-tables)}
 assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==14
 controls=c.execute('SELECT * FROM automation_controls WHERE id=1').fetchone();assert controls['scan_paused'] and controls['email_paused']
 assert not c.execute("SELECT 1 FROM email_messages WHERE status='SENDING' LIMIT 1").fetchone(),'SMTP reservation unresolved; do not clear'
 return tables

def snapshot():
 assert not STATE.exists(),'A snapshot already exists; inspect it rather than repeat the reset.'
 c=connection();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');schema='owner_fresh500_'+stamp.lower()
 try:
  c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ');c.execute("SET LOCAL statement_timeout='180s'; SET LOCAL lock_timeout='3s'")
  tables=scope(c);c.raw.execute(sql.SQL('CREATE SCHEMA {}; REVOKE ALL ON SCHEMA {} FROM PUBLIC').format(sql.Identifier(schema),sql.Identifier(schema)))
  steps=[]
  for t in sorted(tables):
   steps.extend([sql.SQL('CREATE TABLE {} (LIKE {} INCLUDING ALL)').format(sql.Identifier(schema,t),sql.Identifier('public',t)),sql.SQL('INSERT INTO {} SELECT * FROM {}').format(sql.Identifier(schema,t),sql.Identifier('public',t))])
  c.raw.execute(sql.SQL(';').join(steps))
  checks=[]
  for t in sorted(tables):
   a,b=sql.Identifier(schema,t),sql.Identifier('public',t)
   checks.append(sql.SQL('SELECT {} table_name,(SELECT COUNT(*) FROM {}) row_count,EXISTS((TABLE {} EXCEPT ALL TABLE {}) UNION ALL (TABLE {} EXCEPT ALL TABLE {})) differs').format(sql.Literal(t),a,a,b,b,a))
  rows=c.raw.execute(sql.SQL(' UNION ALL ').join(checks)).fetchall();assert all(not r['differs'] for r in rows)
  record={'created_at':datetime.now(timezone.utc).isoformat(),'schema':14,'rollback_schema':schema,'verified':True,'all_rows_compared':True,'tables':{r['table_name']:r['row_count'] for r in rows},'preserve':sorted(PRESERVE),'clear':sorted(OPERATIONAL),'private_artifacts':'Existing R2 objects retained unchanged for rollback; live references cleared.','cleared':False,'owner_request':'clear data and start fresh today500 qualified+email, portfolio https://planebyte.com/projects'}
  c.commit();STATE.parent.mkdir(parents=True,exist_ok=True);STATE.write_text(json.dumps(record,indent=2));os.chmod(STATE,0o600)
  print(json.dumps({'backup_verified':True,'table_count':len(rows),'rollback_schema':schema}),flush=True)
 except Exception:c.rollback();raise
 finally:c.close()

def clear():
 record=json.loads(STATE.read_text());assert record['verified'] and record['all_rows_compared'] and not record['cleared']
 c=connection()
 try:
  scope(c);c.execute("SET LOCAL lock_timeout='5s'; SET LOCAL statement_timeout='90s'")
  # Global send/queue/source locks: no stale reservation may pass the reset.
  for key in (691944511,691944307,691944410,691944303,691944302,691945601,691945602):c.execute('SELECT pg_advisory_xact_lock(?)',(key,))
  from app.database.prospects import now
  stamp=now();addresses=set()
  for r in c.execute("SELECT DISTINCT LOWER(to_address) address FROM email_messages WHERE direction='OUTBOUND' AND test_mode=0 AND status IN ('SENT','SENDING','UNCERTAIN') UNION SELECT DISTINCT LOWER(public_email) address FROM businesses WHERE prospect_id IN (SELECT prospect_id FROM prospect_sales WHERE suppressed_at IS NOT NULL UNION SELECT prospect_id FROM master_lead_state WHERE contact_state IN ('DO_NOT_CONTACT','UNSUBSCRIBED','BOUNCED')) AND public_email IS NOT NULL").fetchall():
   if r['address']:addresses.add(r['address'])
  suppressed_ids="SELECT prospect_id FROM prospect_sales WHERE suppressed_at IS NOT NULL UNION SELECT prospect_id FROM master_lead_state WHERE contact_state IN ('DO_NOT_CONTACT','UNSUBSCRIBED','BOUNCED') UNION SELECT id FROM prospects WHERE lead_status='DO_NOT_CONTACT'"
  for r in c.execute("SELECT DISTINCT LOWER(contact_value) address FROM contacts WHERE contact_type='email' AND business_id IN (SELECT id FROM businesses WHERE prospect_id IN ("+suppressed_ids+")) UNION SELECT DISTINCT LOWER(to_address) address FROM email_messages WHERE test_mode=0 AND prospect_id IN ("+suppressed_ids+")").fetchall():
   if r['address']:addresses.add(r['address'])
  for address in addresses:c.execute("INSERT INTO email_address_suppressions(address,source,status,updated_at) VALUES(?,'OWNER_RESET_RETAINED_CONTACT_OR_SUPPRESSION','INVALID',?) ON CONFLICT(address) DO NOTHING",(address,stamp))
  c.raw.execute(sql.SQL('TRUNCATE TABLE {} CONTINUE IDENTITY RESTRICT').format(sql.SQL(',').join(sql.Identifier('public',t) for t in sorted(OPERATIONAL))))
  c.execute("UPDATE experiment_segments SET actual_source_mix='{}',shortfall_reason=NULL,status='PLANNED'")
  c.execute("UPDATE experiments SET status='READY',send_approved=0,updated_at=? WHERE id=?",(stamp,'planebyte-2026-11-02-06'))
  r=c.execute('SELECT configuration_json FROM experiments WHERE id=?',('planebyte-2026-11-02-06',)).fetchone();cfg=json.loads(r[0]);cfg['copy_rollout_stage']='FIRST10';cfg['fresh_start_at']=stamp;cfg['portfolio_url']='https://planebyte.com/projects';cfg['provider_capacity_verified']=False
  c.execute('UPDATE experiments SET configuration_json=? WHERE id=?',(json.dumps(cfg),'planebyte-2026-11-02-06'))
  c.execute('UPDATE scan_markets SET last_scanned_at=NULL,last_qualified_count=0,total_scans=0,total_candidates=0,total_qualified=0,updated_at=?',(stamp,))
  checks=sql.SQL(' UNION ALL ').join(sql.SQL('SELECT {} table_name,COUNT(*) row_count FROM {}').format(sql.Literal(t),sql.Identifier('public',t)) for t in sorted(OPERATIONAL));counts={r['table_name']:r['row_count'] for r in c.raw.execute(checks).fetchall()};assert not any(counts.values())
  # Security/configuration cardinality must survive; expected safety ledger additions are explicit.
  preserved=sql.SQL(' UNION ALL ').join(sql.SQL('SELECT {} table_name,COUNT(*) row_count FROM {}').format(sql.Literal(t),sql.Identifier('public',t)) for t in sorted(PRESERVE));actual={r['table_name']:r['row_count'] for r in c.raw.execute(preserved).fetchall()}
  for t in PRESERVE-{'internal_request_nonces','email_sync_lock','email_address_suppressions'}:assert actual[t]==record['tables'][t],t
  c.execute("INSERT INTO audit_log(id,actor,action,entity,result,created_at) VALUES(?,?,'OWNER_FRESH_500_OPERATIONAL_RESET','workspace','SUCCESS',?)",(str(uuid.uuid4()),'owner-authorized-session',stamp));c.commit()
  record.update(cleared=True,cleared_at=stamp,after=counts,retained_contact_suppression_addresses=len(addresses),zero_checks={'Master Leads':counts['master_lead_state'],'Qualified Leads':counts['businesses'],'Queued Leads':counts['automation_email_queue'],'Prospect Email Threads':counts['email_threads'],'Prospect Email Messages':counts['email_messages']});STATE.write_text(json.dumps(record,indent=2));Path('docs/owner-fresh-500-reset.json').write_text(json.dumps({k:record[k] for k in ('created_at','rollback_schema','verified','cleared','cleared_at','zero_checks','retained_contact_suppression_addresses','private_artifacts')},indent=2));print(json.dumps({'cleared':True,'zero_checks':record['zero_checks'],'suppression_preserved':True,'schema':14}),flush=True)
 except Exception:c.rollback();raise
 finally:c.close()

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['snapshot','clear']);parser.add_argument('--confirm',choices=['OWNER_FRESH_500']);args=parser.parse_args();assert args.confirm=='OWNER_FRESH_500';snapshot() if args.action=='snapshot' else clear()
