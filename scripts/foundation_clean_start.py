"""Explicit operational-only reset, gated by a current full restore-tested checkpoint."""
import os,sys,json,hashlib,zipfile,uuid,argparse,re
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from foundation_checkpoint import paused,ident
from app.database.connection import get_connection
from app.mail.config import mail_settings
PRESERVE=set('schema_migrations users shared_settings internal_request_nonces scan_markets automation_controls email_accounts email_templates email_tracking_preferences email_sync_state email_sync_lock saved_views email_address_suppressions account_roles audit_log recovery_checkpoints saved_market_groups provider_rate_limits worker_health'.split())
OPERATIONAL=set('activities artifact_objects automation_email_queue automation_runs automation_scans automation_schedule_runs automation_schedules business_identities business_intelligence businesses client_reports contacts deletion_batches deletion_targets email_drafts email_engagement_events email_messages email_threads email_tracking_rate_limits email_tracking_tokens findings followups lead_list_members lead_lists lead_scores lighthouse_results master_lead_state opportunity_scores outreach_run_items pipeline_run_events pipeline_runs prospect_notes prospect_observations prospect_sales prospects scan_campaigns social_profile_sources social_profiles website_captures website_profiles workflow_runs campaign_settings_snapshots campaign_business_snapshots analysis_cache analysis_operations worker_attempts review_cases contact_evidence contact_people identity_resolutions duplicate_resolutions'.split())

def clear(state):
    path=Path(state);record=json.loads(path.read_text());assert not record['cleared'],'This checkpoint already cleared; refusing repeat deletion'
    assert record['backup_verified'] and record['restore_test_passed'] and record['artifacts_included'] and record['schema']==12
    archive=Path(record['backup']);assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['backup_sha256']
    s=mail_settings();assert not(s.auto_scan_enabled or s.auto_email_enabled or s.sending_enabled)
    with zipfile.ZipFile(archive) as z:manifest=json.loads(z.read('manifest.json'));assert z.testzip() is None
    assert set(manifest['tables'])==PRESERVE|OPERATIONAL,'Unexpected schema; explicitly classify new tables before clearing'
    c=get_connection(session_bound=True)
    try:
        for key in (691944511,691944307,691944410,691944303,691944302):c.execute('SELECT pg_advisory_xact_lock(?)',(key,))
        paused(c);assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==12
        before={t:c.execute(ident(c,'SELECT COUNT(*) FROM {}',t)).fetchone()[0] for t in sorted(OPERATIONAL)}
        assert all(before[t]==record['before'][t] for t in OPERATIONAL),'Operational data changed since checkpoint'
        # Keep opt-out and confirmed delivery protections even after lead histories are removed.
        ids=[r[0] for r in c.execute("SELECT prospect_id FROM prospect_sales WHERE suppressed_at IS NOT NULL UNION SELECT prospect_id FROM master_lead_state WHERE contact_state IN ('DO_NOT_CONTACT','UNSUBSCRIBED','BOUNCED')").fetchall()]
        addresses=set()
        if ids:
            marks=','.join('?' for _ in ids)
            for r in c.execute('SELECT public_email FROM businesses WHERE prospect_id IN ('+marks+') AND public_email IS NOT NULL',ids).fetchall():addresses.add(r[0])
            for r in c.execute("SELECT to_address FROM email_messages WHERE prospect_id IN ("+marks+") AND direction='OUTBOUND' AND test_mode=0",ids).fetchall():addresses.add(r[0])
            for r in c.execute("SELECT contact_value FROM contacts WHERE business_id IN (SELECT id FROM businesses WHERE prospect_id IN ("+marks+")) AND contact_type='email'",ids).fetchall():addresses.add(r[0])
        stamp=datetime.now(timezone.utc).isoformat()
        addresses={v.strip().lower() for v in addresses if v and re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',v.strip())}
        for address in addresses:c.execute("INSERT INTO email_address_suppressions(address,source,status,updated_at) VALUES(?,'OWNER_CLEAN_START_RETAINED_SUPPRESSION','INVALID',?) ON CONFLICT(address) DO UPDATE SET status='INVALID',updated_at=excluded.updated_at",(address,stamp))
        preserved_before={t:c.execute(ident(c,'SELECT COUNT(*) FROM {}',t)).fetchone()[0] for t in PRESERVE}
        # One explicit RESTRICT truncate; configuration references cannot be cascaded away.
        c.execute('TRUNCATE TABLE '+','.join('"'+t+'"' for t in sorted(OPERATIONAL))+' CONTINUE IDENTITY RESTRICT')
        c.execute("UPDATE scan_markets SET last_scanned_at=NULL,last_qualified_count=0,total_scans=0,total_candidates=0,total_qualified=0,updated_at=?",(stamp,))
        c.execute("UPDATE automation_controls SET scan_paused=1,email_paused=1,pause_reason='OWNER_FRESH_START',next_send_at=NULL,updated_at=? WHERE id=1",(stamp,))
        after={t:c.execute(ident(c,'SELECT COUNT(*) FROM {}',t)).fetchone()[0] for t in sorted(OPERATIONAL)};assert not any(after.values())
        for t in PRESERVE-{'email_sync_state','email_sync_lock','internal_request_nonces','audit_log','recovery_checkpoints'}:assert c.execute(ident(c,'SELECT COUNT(*) FROM {}',t)).fetchone()[0]==preserved_before[t],t
        from app.automation.settings import effective_settings,TARGET_FIELDS
        settings=effective_settings(c);actual={k:getattr(settings,k) for k in TARGET_FIELDS};expected={'daily_qualified_lead_target':500,'daily_email_target':500,'max_hour':50,'max_day':500,'followup_days':3,'automation_timezone':'Asia/Kolkata'};assert actual==expected,actual
        c.execute("INSERT INTO recovery_checkpoints(id,created_at,schema_version,reason,status,artifact_path,manifest_json) VALUES(?,?,12,'OWNER_OPERATIONAL_CLEAN_START','RESTORE_VERIFIED',?,?)",(str(uuid.uuid4()),stamp,record['backup'],json.dumps({'sha256':record['backup_sha256']})))
        c.execute("INSERT INTO audit_log(id,actor,action,entity,result,created_at) VALUES(?,?,'OWNER_AUTHORIZED_OPERATIONAL_RESET','workspace','SUCCESS',?)",(str(uuid.uuid4()),'owner-authorized-session',stamp));c.commit()
        record.update(cleared=True,after=after,preserved=sorted(PRESERVE),suppression_addresses_retained=len(addresses),limits=actual,three_flags=False);path.write_text(json.dumps(record,indent=2))
    finally:c.close()
    from app.storage import R2ArtifactStorage
    keys=sorted(manifest['objects'])
    if keys:R2ArtifactStorage().delete_many(keys)
    record['artifact_cleanup_complete']=True;record['zero_checks']={k:after[t] for k,t in [('Master Leads','master_lead_state'),('Qualified Leads','businesses'),('Queued Leads','automation_email_queue'),('Prospect Email Threads','email_threads'),('Prospect Email Messages','email_messages'),('Campaigns','scan_campaigns'),('Schedules','automation_schedules')]};path.write_text(json.dumps(record,indent=2))
    print(json.dumps({'cleared':True,'zero_checks':record['zero_checks'],'limits':record['limits'],'private_artifacts_removed':len(keys),'configuration_preserved':True,'suppression_protections_retained':True,'three_flags':False}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--confirmation',required=True,choices=['CLEAR_OPERATIONAL_DATA']);a=p.parse_args();clear(a.state)
