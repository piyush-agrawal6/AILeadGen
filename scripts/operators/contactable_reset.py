"""Owner-authorized reset, gated on verified rollback and permanent sent history."""
import asyncio,json,uuid
from pathlib import Path
from psycopg import sql
from scripts.operators.owner_fresh_500 import PRESERVE,OPERATIONAL,connection

PERMANENT={'contacted_recipients','contacted_recipient_sends','contacted_unsubscribe_tokens','company_pdf_assets'}
CLEAR=OPERATIONAL|{'experiments','experiment_segments'}
KEEP=(PRESERVE-{'experiments','experiment_segments'})|PERMANENT
REPORT=Path('docs/contactable-clean-reset.json')

def reset():
 assert not REPORT.exists(),'Reset already recorded; inspect rather than repeat.'
 backup=json.loads(Path('data/backups/contactable-before-reset-20261103.json').read_text())
 history=json.loads(Path('docs/contacted-history-backfill.json').read_text())
 assert backup['verified'] and backup['all_rows_compared']
 assert history['applied'] and history['mismatch']==0
 c=connection()
 try:
  assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==15
  assert {r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()}==KEEP|CLEAR
  c.execute("SET LOCAL lock_timeout='5s';SET LOCAL statement_timeout='90s'")
  # Acquire the existing mailbox/send/source locks before checking and deleting.
  for key in (691944411,691944511,691944307,691944410,691944303,691944302,691945601,691945602):c.execute('SELECT pg_advisory_xact_lock(?)',(key,))
  controls=c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone();assert controls[0] and controls[1]
  assert not c.execute("SELECT 1 FROM email_messages WHERE status IN ('SENDING','UNCERTAIN') LIMIT 1").fetchone()
  assert not c.execute("SELECT 1 FROM client_reports WHERE status IN ('GENERATING','QUEUED') LIMIT 1").fetchone()
  counts=lambda tables:{t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in sorted(tables)}
  before=counts(KEEP);assert before['contacted_recipients']==history['unique_actual_recipients'];assert before['contacted_recipient_sends']==history['historical_actual_sends']
  assert c.execute('SELECT SUM(send_count) FROM contacted_recipients').fetchone()[0]==history['historical_actual_sends']
  from app.mail.contacted import normalize,organization
  from app.database.prospects import now
  stamp=now();suppressed_ids="SELECT prospect_id FROM prospect_sales WHERE suppressed_at IS NOT NULL UNION SELECT prospect_id FROM master_lead_state WHERE contact_state IN ('DO_NOT_CONTACT','UNSUBSCRIBED','BOUNCED') UNION SELECT id FROM prospects WHERE lead_status='DO_NOT_CONTACT'"
  addresses={normalize(r[0]) for r in c.execute("SELECT public_email FROM businesses WHERE prospect_id IN ("+suppressed_ids+") UNION SELECT contact_value FROM contacts WHERE contact_type='email' AND business_id IN (SELECT id FROM businesses WHERE prospect_id IN ("+suppressed_ids+")) UNION SELECT to_address FROM email_messages WHERE test_mode=0 AND prospect_id IN ("+suppressed_ids+")").fetchall()}
  for email in addresses-{None}:
   c.execute("INSERT INTO email_address_suppressions(address,source,status,updated_at) VALUES(?,'OWNER_RESET_RETAINED_SAFETY','INVALID',?) ON CONFLICT(address) DO NOTHING",(email,stamp))
   c.execute('UPDATE contacted_recipients SET do_not_contact=1,updated_at=? WHERE organization_id=? AND normalized_email=?',(stamp,organization(),email))
  # Historical event-derived unsubscribe/hard-bounce state remains actionable.
  for r in c.execute('SELECT normalized_email FROM contacted_recipients WHERE unsubscribed=1 OR hard_bounced=1 OR do_not_contact=1').fetchall():
   c.execute("INSERT INTO email_address_suppressions(address,source,status,updated_at) VALUES(?,'PERMANENT_CONTACTED_SAFETY','INVALID',?) ON CONFLICT(address) DO NOTHING",(r[0],stamp))
  safety={field:c.execute('SELECT COUNT(*) FROM contacted_recipients WHERE '+field+'=1').fetchone()[0] for field in ('ever_replied','ever_positive_reply','unsubscribed','hard_bounced','do_not_contact')}
  c.raw.execute(sql.SQL('TRUNCATE TABLE {} CONTINUE IDENTITY RESTRICT').format(sql.SQL(',').join(sql.Identifier('public',t) for t in sorted(CLEAR))))
  after=counts(CLEAR);assert not any(after.values())
  preserved=counts(KEEP)
  for t in KEEP-{'email_address_suppressions','internal_request_nonces','email_sync_lock'}:assert before[t]==preserved[t],t
  assert preserved['email_address_suppressions']>=before['email_address_suppressions']
  c.execute("INSERT INTO audit_log(id,actor,action,entity,result,created_at) VALUES(?,?,'CONTACTABLE_ONLY_CLEAN_RESET','workspace','SUCCESS',?)",(str(uuid.uuid4()),'owner-authorized-session',stamp))
  c.commit()
  result={'cleared_at':stamp,'rollback_schema':backup['rollback_schema'],'backup_verified':True,'schema':15,'registry_verified':history,'operational_zero_counts':after,'preserved_counts':preserved,'permanent_safety_flags':safety,'safety_addresses_retained':preserved['email_address_suppressions'],'old_live_threads_archived_not_in_live_ui':True,'private_artifacts':'Retained unchanged for rollback; active references cleared.','automatic_scanning_enabled':False,'sending_paused':True}
  REPORT.write_text(json.dumps(result,indent=2));print(json.dumps({'reset':True,'zero_tables':len(after),'contacted_recipients':preserved['contacted_recipients'],'actual_sends':preserved['contacted_recipient_sends'],'safety':safety}),flush=True)
  from app.api.read_cache import ReadCache
  asyncio.run(ReadCache().invalidate())
 except Exception:c.rollback();raise
 finally:c.close()

if __name__=='__main__':reset()
