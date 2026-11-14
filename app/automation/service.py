from app.mail.limits import MAX_PER_HOUR,MAX_PER_DAY,MIN_SPACING_SECONDS
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import uuid
import json
from app.database.prospects import now
from app.mail.config import mail_settings

CONTACT_STATES = ('NOT_CONTACTED','READY_TO_EMAIL','EMAIL_QUEUED','EMAILED','WAITING_REPLY','REPLIED','MANUAL_CONTACT_REQUIRED','CONNECTED_MANUALLY','EMAIL_BOUNCED','UNSUBSCRIBED','DO_NOT_CONTACT','NEEDS_REVIEW')
SALES_STATES = ('NEW','QUALIFIED','CONTACTED','REPLIED','MEETING','PROPOSAL','WON','LOST','NOT_INTERESTED','REJECTED')
CITIES = {
 'United States': ['New York','Los Angeles','Chicago','Houston','Dallas','Miami','Austin','Seattle','Boston','Denver'],
 'United Kingdom': ['London','Manchester','Birmingham','Leeds','Liverpool','Bristol','Glasgow','Edinburgh'],
 'Canada': ['Toronto','Vancouver','Calgary','Montreal','Ottawa'],
 'Australia': ['Sydney','Melbourne','Brisbane','Perth','Adelaide'],
 'Germany': ['Berlin','Hamburg','Munich','Frankfurt','Cologne'],
 'France': ['Paris','Lyon','Marseille','Toulouse','Bordeaux'],
}
VERTICALS = ('hospitality','real_estate','restaurant','dentists','home_services','auto_repair','legal','veterinary')


def lock(c):
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944511)')
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')


def seed_markets(c):
    stamp=now()
    values=[(str(uuid.uuid5(uuid.NAMESPACE_URL,country+'/'+city+'/'+vertical)),country,city,vertical,stamp,stamp)
            for country,cities in CITIES.items() for city in cities for vertical in VERTICALS]
    c.executemany('INSERT INTO scan_markets(id,country,city,vertical,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(country,city,vertical) DO NOTHING',values)


def eligible_markets(c,at=None):
    at=at or datetime.now(timezone.utc)
    rows=c.execute('SELECT * FROM scan_markets WHERE enabled=1 ORDER BY CASE WHEN last_scanned_at IS NULL THEN 0 ELSE 1 END,priority DESC,last_scanned_at,last_qualified_count DESC,id').fetchall()
    return [dict(r) for r in rows if not r['last_scanned_at'] or datetime.fromisoformat(r['last_scanned_at'])+timedelta(days=r['cooldown_days'])<=at]


def reconcile(c):
    """Reconcile canonical prospects with bounded SQL round trips, never send mail."""
    from app.mail.service import address
    from app.database.phase4_schema import ready
    version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
    org=None
    if version>=16:
        from app.platform.context import organization
        org=organization()
    stamp=now()
    rows=c.execute("SELECT p.id,p.lead_status,p.first_seen_at FROM prospects p WHERE EXISTS(SELECT 1 FROM businesses b WHERE b.prospect_id=p.id AND b.processing_status='QUALIFIED' AND b.is_rejected=0)"+(" AND p.organization_id=?" if org else ""),(org,) if org else ()).fetchall()
    if not rows:return
    ids={r['id'] for r in rows}
    marks=','.join('?' for _ in ids);args=list(ids)
    blocked_addresses={r[0].lower() for r in c.execute("SELECT address FROM email_address_suppressions WHERE status IN ('INVALID','TEMPORARILY_UNUSABLE')"+(' AND organization_id=?' if org else ''),(org,) if org else ()).fetchall()}
    emails={}
    for r in c.execute("SELECT prospect_id,public_email AS email FROM businesses WHERE prospect_id IN ("+marks+") AND public_email IS NOT NULL UNION SELECT b.prospect_id,x.contact_value AS email FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE b.prospect_id IN ("+marks+") AND x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1",args+args).fetchall():
        if r['prospect_id'] not in ids:continue
        try:value=address(r['email'])
        except Exception:continue
        if value not in blocked_addresses:emails.setdefault(r['prospect_id'],set()).add(value)
    states={r['prospect_id']:dict(r) for r in c.execute('SELECT * FROM master_lead_state WHERE prospect_id IN ('+marks+')',args).fetchall()}
    trusted={(r['prospect_id'],r['email'].lower()) for r in c.execute("SELECT b.prospect_id,x.contact_value email FROM contacts x JOIN businesses b ON b.id=x.business_id WHERE x.contact_type='email' AND x.is_valid=1 AND x.is_public_business_contact=1 AND x.source_url IS NOT NULL AND x.source_url<>'' AND b.prospect_id IN ("+marks+")",args).fetchall()}
    from app.acquisition.policy import owner_imported_emails
    trusted|=owner_imported_emails(c)
    suppressed={r[0] for r in c.execute('SELECT prospect_id FROM prospect_sales WHERE suppressed_at IS NOT NULL AND prospect_id IN ('+marks+')',args).fetchall()}
    history={r[0] for r in c.execute("SELECT DISTINCT prospect_id FROM email_messages WHERE direction='OUTBOUND' AND status IN ('SENT','SENDING','UNCERTAIN') AND message_type<>'OWNER_CONTROLLED_REDIRECT' AND prospect_id IN ("+marks+")",args).fetchall()}
    recontact=set();authorized={}
    for reservation in c.execute("SELECT i.prospect_id,i.idempotency_key,r.configuration_json FROM outreach_run_items i JOIN workflow_runs r ON r.id=i.run_id WHERE r.kind='OUTREACH' AND r.status='RUNNING' AND i.status='READY' AND r.campaign_id IS NOT NULL AND i.prospect_id IN ("+marks+")",args).fetchall():
        intent=json.loads(reservation['configuration_json'])
        authorized[reservation['prospect_id']]=reservation['idempotency_key']
        if intent.get('outreach_mode')=='RECONTACT' and intent.get('confirm_recontact'):recontact.add(reservation['prospect_id'])
    queue={r['prospect_id']:r['status'] for r in c.execute('SELECT prospect_id,status FROM automation_email_queue WHERE prospect_id IN ('+marks+')',args).fetchall()}
    fits={}
    for r in c.execute("SELECT b.prospect_id,i.commercial_fit FROM businesses b JOIN business_intelligence i ON i.business_id=b.id WHERE b.processing_status='QUALIFIED' AND b.prospect_id IN ("+marks+") ORDER BY b.id DESC",args).fetchall():fits.setdefault(r['prospect_id'],r['commercial_fit'])
    inserts=[];updates=[];queued=[];canceled=[];events=[]
    for r in rows:
        pid=r['id'];known=sorted(emails.get(pid,set()));usable=[email for email in known if (pid,email) in trusted]
        state=states.get(pid,{'sales_state':'QUALIFIED','contact_state':'NOT_CONTACTED'})
        inserts.append((pid,stamp,stamp))
        events.append((str(uuid.uuid4()),pid,'system','LEAD_QUALIFIED',stamp,'{}',stamp,'qualified-'+pid))
        blocked=r['lead_status'] in ('DO_NOT_CONTACT','NOT_INTERESTED','REPLIED','MEETING','PROPOSAL','WON','LOST') or state['sales_state'] in ('REJECTED','NOT_INTERESTED','REPLIED','MEETING','PROPOSAL','WON','LOST')
        terminal=state['contact_state'] in ('UNSUBSCRIBED','DO_NOT_CONTACT','CONNECTED_MANUALLY','REPLIED','EMAIL_BOUNCED')
        if blocked or pid in suppressed or (pid in history and pid not in recontact):
            canceled.append((pid,))
            if pid in suppressed or r['lead_status']=='DO_NOT_CONTACT':contact='DO_NOT_CONTACT'
            elif r['lead_status']=='REPLIED':contact='REPLIED'
            elif pid in history:contact='WAITING_REPLY' if usable else 'MANUAL_CONTACT_REQUIRED'
            else:contact=state['contact_state']
        elif terminal:
            canceled.append((pid,));continue
        elif state['contact_state']=='MANUAL_CONTACT_REQUIRED' and states.get(pid,{}).get('manual_reason')=='Owner requested manual contact':
            canceled.append((pid,));continue
        elif state['contact_state']=='NEEDS_REVIEW' and states.get(pid,{}).get('manual_reason')=='Owner requested review':
            canceled.append((pid,));continue
        elif not usable and known:contact='NEEDS_REVIEW';canceled.append((pid,))
        elif not usable:contact='MANUAL_CONTACT_REQUIRED'
        else:contact='READY_TO_EMAIL'
        if contact=='READY_TO_EMAIL' and fits.get(pid) in ('HIGH','MEDIUM') and pid in authorized:
            if pid not in queue:
                queued.append((pid,usable[0],100 if fits[pid]=='HIGH' else 50,stamp,authorized[pid]))
            if queue.get(pid,'QUEUED')=='QUEUED':
                contact='EMAIL_QUEUED'
                events.append((str(uuid.uuid4()),pid,'system','EMAIL_QUEUED',stamp,'{}',stamp,'auto-queued-'+pid))
        updates.append((contact,'UNVERIFIED_EMAIL' if contact=='NEEDS_REVIEW' else 'No usable public business email' if not usable else None,stamp,pid))
    if org:c.executemany('INSERT INTO master_lead_state(prospect_id,qualified_at,updated_at,organization_id) VALUES(?,?,?,?) ON CONFLICT(prospect_id) DO NOTHING',[(*r,org) for r in inserts])
    else:c.executemany('INSERT INTO master_lead_state(prospect_id,qualified_at,updated_at) VALUES(?,?,?) ON CONFLICT(prospect_id) DO NOTHING',inserts)
    if updates:c.executemany('UPDATE master_lead_state SET contact_state=?,manual_reason=?,updated_at=? WHERE prospect_id=?',updates)
    if queued:c.executemany('INSERT INTO automation_email_queue(prospect_id,recipient,priority,queued_at,idempotency_key) VALUES(?,?,?,?,?) ON CONFLICT(prospect_id) DO NOTHING',queued)
    if canceled:c.executemany("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id=? AND status='QUEUED'",canceled)
    if events and ready(c):
        if org:c.executemany('INSERT INTO activities(id,prospect_id,actor_user_id,event_type,event_at,metadata_json,created_at,dedup_key,organization_id) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(dedup_key) DO NOTHING',[(*r,org) for r in events])
        else:c.executemany('INSERT INTO activities(id,prospect_id,actor_user_id,event_type,event_at,metadata_json,created_at,dedup_key) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(dedup_key) DO NOTHING',events)


def business_hours(at,zone):
    local=at.astimezone(ZoneInfo(zone))
    minutes=local.hour*60+local.minute
    return local.weekday()<5 and 510<=minutes<1050


def utc_now():return datetime.now(timezone.utc)


def recover_attempts(c,at):
    """Durable SMTP reservation decides recovery; ambiguous outcomes never resend."""
    stale=(at-timedelta(minutes=10)).isoformat()
    recovered=0;review=False
    for row in c.execute("SELECT * FROM automation_email_queue WHERE status='ATTEMPTING' AND (attempted_at IS NULL OR attempted_at<?)",(stale,)).fetchall():
        message=c.execute('SELECT id,status FROM email_messages WHERE idempotency_key=?',(row['idempotency_key'],)).fetchone()
        if message and message['status']=='SENT':
            c.execute("UPDATE automation_email_queue SET status='SENT',message_id=?,error_code=NULL WHERE prospect_id=?",(message['id'],row['prospect_id']))
            c.execute("UPDATE master_lead_state SET contact_state=CASE WHEN contact_state IN ('READY_TO_EMAIL','EMAIL_QUEUED','NOT_CONTACTED') THEN 'WAITING_REPLY' ELSE contact_state END,sales_state=CASE WHEN sales_state IN ('NEW','QUALIFIED') THEN 'CONTACTED' ELSE sales_state END,updated_at=? WHERE prospect_id=?",(at.isoformat(),row['prospect_id']))
        elif message or row['attempted_at'] is None:
            review=True
            c.execute("UPDATE automation_email_queue SET status='REVIEW',error_code='UNCERTAIN_RESTART_REQUIRES_REVIEW' WHERE prospect_id=?",(row['prospect_id'],))
        else:
            c.execute("UPDATE automation_email_queue SET status='QUEUED',attempted_at=NULL,error_code=NULL WHERE prospect_id=?",(row['prospect_id'],))
        recovered+=1
    if review:c.execute("UPDATE automation_controls SET email_paused=1,pause_reason='UNCERTAIN_RESTART_REQUIRES_REVIEW',updated_at=? WHERE id=1",(at.isoformat(),))
    return recovered,review


def outreach_tick(c,*,execution_id=None):
    """One durable attempt per tick. Ambiguous failures require operator review."""
    from app.config.settings import get_settings
    if not get_settings().lead_engine_available:return {'status':'PRODUCT_UNAVAILABLE'}
    from app.platform.context import organization
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    if organization()!=PLANEBYTE_ORGANIZATION_ID:
        from app.mail.customer import outreach_tick as customer_tick
        return customer_tick(c,execution_id)
    from app.platform.context import require_internal_mailbox
    org=require_internal_mailbox().organization_id
    from app.mail import service as mail
    from app.mail.templates import seed,render_client_template
    from app.automation.settings import effective_settings
    s=effective_settings(c,mail_settings())
    if not s.sending_enabled:return {'status':'DISABLED'}
    if not execution_id:return {'status':'NO_EXPLICIT_RUN'}
    execution=c.execute("SELECT * FROM workflow_runs WHERE id=? AND organization_id=? AND kind='OUTREACH' AND status='RUNNING'",(execution_id,org)).fetchone()
    if not execution:return {'status':'NO_EXPLICIT_RUN'}
    run_guard=json.loads(execution['configuration_json'])
    if run_guard.get('experiment_id'):
        from app.experiments.runtime import can_send
        if not can_send(c,run_guard['experiment_id']):return {'status':'EXPERIMENT_BLOCKED'}
    if execution['schedule_id'] and not s.auto_email_enabled:return {'status':'DISABLED'}
    run_options=json.loads(execution['configuration_json'])
    s=s.model_copy(update={'max_hour':min(s.max_hour,run_options.get('max_hour',10)), 'max_day':min(s.max_day,run_options.get('max_day',100))})
    lock(c)
    control=c.execute('SELECT * FROM automation_controls WHERE id=1').fetchone()
    at=utc_now()
    if control['email_paused'] or (control['next_send_at'] and control['next_send_at']>at.isoformat()):c.commit();return {'status':'PAUSED_OR_WAITING'}
    recovered,review=recover_attempts(c,at)
    if review:c.commit();return {'status':'PAUSED_FOR_REVIEW','recovered':recovered}
    # Same locks as manual mail prevent exceeding global caps across both paths.
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT pg_advisory_xact_lock(691944307)');c.execute('SELECT pg_advisory_xact_lock(691944410)')
    since=(at-timedelta(days=1)).isoformat()
    sent=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status='SENT' AND sent_at>=?",(since,)).fetchone()[0]
    events=c.execute("SELECT message_id,metadata_json FROM email_engagement_events WHERE event_type IN ('BOUNCED_HARD','BOUNCED_SOFT') AND occurred_at>=? LIMIT 1000",(since,)).fetchall()
    bounced={r['message_id'] for r in events if json.loads(r['metadata_json']).get('confirmed')}
    if sent>=s.bounce_min_sample and len(bounced)/sent>=s.high_bounce_rate:
        c.execute("UPDATE automation_controls SET email_paused=1,pause_reason='HIGH_BOUNCE_RATE',updated_at=? WHERE id=1",(now(),));c.commit();return {'status':'HIGH_BOUNCE_RATE'}
    for span,maximum,status in [(timedelta(hours=1),min(MAX_PER_HOUR,s.max_hour),'HOUR_LIMIT'),(timedelta(days=1),min(MAX_PER_DAY,s.max_day),'DAY_LIMIT')]:
        from app.mail.contacted import usage
        count=usage(c,(at-span).isoformat())
        if count>=maximum:c.commit();return {'status':status}
    reconcile(c)
    candidates=c.execute("SELECT q.*,b.name,b.city,b.country,b.id AS business_id FROM automation_email_queue q JOIN businesses b ON b.id=(SELECT MAX(id) FROM businesses WHERE prospect_id=q.prospect_id AND processing_status='QUALIFIED') WHERE q.status='QUEUED' AND EXISTS(SELECT 1 FROM outreach_run_items i WHERE i.run_id=? AND i.prospect_id=q.prospect_id AND i.status='READY' AND i.idempotency_key=q.idempotency_key) ORDER BY q.priority DESC,q.queued_at LIMIT 100",(execution_id,)).fetchall()
    if not candidates:c.commit();return {'status':'EMPTY'}
    zones={'United Kingdom':'Europe/London','Germany':'Europe/Berlin','France':'Europe/Paris'}
    city_zones={'New York':'America/New_York','Los Angeles':'America/Los_Angeles','Chicago':'America/Chicago','Houston':'America/Chicago','Dallas':'America/Chicago','Miami':'America/New_York','Austin':'America/Chicago','Seattle':'America/Los_Angeles','Boston':'America/New_York','Denver':'America/Denver','Toronto':'America/Toronto','Vancouver':'America/Vancouver','Calgary':'America/Edmonton','Montreal':'America/Toronto','Ottawa':'America/Toronto','Sydney':'Australia/Sydney','Melbourne':'Australia/Melbourne','Brisbane':'Australia/Brisbane','Perth':'Australia/Perth','Adelaide':'Australia/Adelaide'}
    def within_window(r):
        zone=city_zones.get(r['city'],zones.get(r['country'],s.automation_timezone)) if run_options.get('recipient_timezone',True) else s.automation_timezone
        if run_options.get('experiment_id'):
            from app.experiments.plan import ZONES
            zone=ZONES.get(r['city'],zone)
        local=at.astimezone(ZoneInfo(zone));current=local.strftime('%H:%M')
        return local.weekday()<5 and run_options.get('window_start','09:00')<=current<run_options.get('window_end','17:00')
    row=next((r for r in candidates if within_window(r)),None)
    if row is None:c.commit();return {'status':'OUTSIDE_BUSINESS_HOURS'}
    day_start=at.astimezone(ZoneInfo(s.automation_timezone)).replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc).isoformat()
    count=c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND' AND status IN ('SENT','SENDING') AND created_at>=?",(day_start,)).fetchone()[0]
    if count>=min(MAX_PER_DAY,s.daily_email_target,s.max_day):c.commit();return {'status':'DAILY_LIMIT'}
    item=c.execute("SELECT * FROM outreach_run_items WHERE run_id=? AND prospect_id=? AND status='READY'",(execution_id,row['prospect_id'])).fetchone()
    if not item or not item['payload_json']:c.commit();return {'status':'NEEDS_REVIEW'}
    body=json.loads(item['payload_json'])
    c.execute("UPDATE automation_email_queue SET status='ATTEMPTING',attempted_at=? WHERE prospect_id=?",(now(),row['prospect_id']))
    c.execute('UPDATE automation_controls SET next_send_at=?,updated_at=? WHERE id=1',((at+timedelta(seconds=max(MIN_SPACING_SECONDS,run_options.get('spacing_minutes',1.2)*60,3600/min(MAX_PER_HOUR,s.max_hour)))).isoformat(),now()))
    c.commit()
    try:
        # Recheck environment and operator pause immediately before the existing send guard.
        if not mail_settings().sending_enabled or (execution['schedule_id'] and not mail_settings().auto_email_enabled) or not c.execute("SELECT 1 FROM workflow_runs WHERE id=? AND status='RUNNING'",(execution_id,)).fetchone() or c.execute('SELECT email_paused FROM automation_controls WHERE id=1').fetchone()[0]:raise RuntimeError('PAUSED')
        reconcile(c)
        current=c.execute('SELECT contact_state,sales_state FROM master_lead_state WHERE prospect_id=?',(row['prospect_id'],)).fetchone()
        if current['sales_state'] in ('REJECTED','NOT_INTERESTED','REPLIED','MEETING','PROPOSAL','WON','LOST') or current['contact_state'] in ('DO_NOT_CONTACT','UNSUBSCRIBED','REPLIED','CONNECTED_MANUALLY','EMAIL_BOUNCED'):raise RuntimeError('SUPPRESSED')
        if execution['campaign_id']:
            from app.workflows.campaigns import audience
            if run_options.get('experiment_id'):
                from app.experiments.service import audience
            latest=audience(c,execution['campaign_id'],run_options.get('pitch_types'),run_options.get('outreach_mode','UNCONTACTED'),run_id=execution_id,require_complete=True)
            member=next((b for b in latest['items'] if b['prospect_id']==row['prospect_id']),None)
            if not member or member['disposition']!='READY':
                c.execute('UPDATE outreach_run_items SET status=?,error=? WHERE id=?',(member['disposition'] if member else 'NEEDS_REVIEW',member['reason'] if member else 'Campaign membership changed.',item['id']))
                c.execute("UPDATE automation_email_queue SET status='CANCELED',error_code='CAMPAIGN_ELIGIBILITY_CHANGED' WHERE prospect_id=?",(row['prospect_id'],));c.commit();return {'status':'SKIPPED'}
        else:raise RuntimeError('CAMPAIGN_REQUIRED')
        if not body.get('preview_token'):raise RuntimeError('PREVIEW_REQUIRED')
        result=mail.send(c,row['prospect_id'],'system',body)
        if result['status']!='SENT':raise RuntimeError('PROVIDER_FAILURE')
        c.execute("UPDATE automation_email_queue SET status='SENT',message_id=? WHERE prospect_id=?",(result['id'],row['prospect_id']))
        c.execute("UPDATE master_lead_state SET contact_state=CASE WHEN contact_state IN ('REPLIED','UNSUBSCRIBED','DO_NOT_CONTACT') THEN contact_state ELSE 'WAITING_REPLY' END,sales_state=CASE WHEN sales_state IN ('MEETING','PROPOSAL','WON','LOST','REPLIED','NOT_INTERESTED','REJECTED') THEN sales_state ELSE 'CONTACTED' END,updated_at=? WHERE prospect_id=?",(now(),row['prospect_id']))
    except Exception as exc:
        c.rollback()
        from fastapi import HTTPException
        if isinstance(exc,HTTPException) and exc.status_code==409 and str(exc.detail).startswith('ALREADY_CONTACTED'):
            c.execute("UPDATE outreach_run_items SET status='ALREADY_CONTACTED',error=? WHERE id=?",(str(exc.detail),item['id']));c.execute("UPDATE automation_email_queue SET status='CANCELED',error_code='ALREADY_CONTACTED' WHERE prospect_id=?",(row['prospect_id'],));c.commit();return {'status':'SKIPPED'}
        if isinstance(exc,HTTPException) and exc.status_code==429:
            prior=c.execute('SELECT status FROM email_messages WHERE idempotency_key=?',(row['idempotency_key'],)).fetchone()
            c.execute('UPDATE automation_email_queue SET status=?,error_code=? WHERE prospect_id=?',('REVIEW' if prior else 'QUEUED','RATE_LIMIT' if prior else None,row['prospect_id']))
            c.commit();return {'status':'RATE_LIMITED'}
        c.execute("UPDATE outreach_run_items SET status='NEEDS_REVIEW',error='Send requires review.',updated_at=? WHERE id=?",(now(),item['id']))
        if isinstance(exc,HTTPException) and exc.status_code==422:
            c.execute("UPDATE automation_email_queue SET status='REVIEW',error_code='NEEDS_CONTENT_REVIEW' WHERE prospect_id=?",(row['prospect_id'],));c.commit();return {'status':'NEEDS_REVIEW'}
        c.execute("UPDATE automation_controls SET email_paused=1,pause_reason='SEND_REQUIRES_REVIEW',updated_at=? WHERE id=1",(now(),))
        c.execute("UPDATE automation_email_queue SET status='REVIEW',error_code='SEND_REQUIRES_REVIEW' WHERE prospect_id=?",(row['prospect_id'],))
        c.commit();return {'status':'PAUSED_FOR_REVIEW'}
    c.commit();return {'status':'SENT'}


def acquisition_tick(c):
    return {'status':'NO_EXPLICIT_RUN' if mail_settings().auto_scan_enabled else 'DISABLED'}

def legacy_acquisition_tick(c):
    """Schedule at most one existing scan; subsequent ticks reconcile its result."""
    from app.config.settings import get_settings
    if not get_settings().lead_engine_available:return {'status':'PRODUCT_UNAVAILABLE'}
    from app.platform.context import require_internal_mailbox
    org=require_internal_mailbox().organization_id
    from app.database.models import PipelineRun
    from app.database.repositories import PipelineRunRepository
    from app.automation.settings import effective_settings
    s=effective_settings(c,mail_settings())
    if not s.auto_scan_enabled:return {'status':'DISABLED'}
    lock(c)
    if c.execute('SELECT scan_paused FROM automation_controls WHERE id=1').fetchone()[0]:c.commit();return {'status':'PAUSED'}
    day=utc_now().astimezone(ZoneInfo(s.automation_timezone)).date().isoformat()
    stamp=now()
    c.execute("INSERT INTO automation_runs(day,status,started_at,target) VALUES(?,'RUNNING',?,?) ON CONFLICT(day) DO NOTHING",(day,stamp,s.daily_qualified_lead_target))
    run=c.execute('SELECT * FROM automation_runs WHERE day=?',(day,)).fetchone()
    if run['status'] in ('COMPLETE','SHORTFALL'):c.commit();return {'status':run['status']}
    pending=c.execute("SELECT a.*,r.status AS run_status,r.raw_found FROM automation_scans a JOIN pipeline_runs r ON r.id=a.run_id WHERE a.day=? AND a.status='PENDING'",(day,)).fetchall()
    for scan in pending:
        if scan['run_status'] in ('QUEUED','RUNNING'):
            c.commit()
            if scan['run_status']=='QUEUED':
                from app.api.services.cloud_executor import dispatch_queued
                dispatch_queued()
            return {'status':'WAITING_SCAN','run_id':scan['run_id']}
        count=c.execute("SELECT COUNT(DISTINCT p.id) FROM prospects p JOIN businesses b ON b.prospect_id=p.id WHERE b.run_id=? AND b.processing_status='QUALIFIED' AND p.first_seen_at>=?",(scan['run_id'],run['started_at'])).fetchone()[0]
        c.execute("UPDATE automation_scans SET status=? WHERE run_id=?",(scan['run_status'],scan['run_id']))
        c.execute('UPDATE scan_markets SET last_qualified_count=?,total_qualified=total_qualified+?,total_candidates=total_candidates+? WHERE id=?',(count,count,scan['raw_found'],scan['market_id']))
    reconcile(c)
    count=c.execute("SELECT COUNT(DISTINCT m.prospect_id) FROM master_lead_state m JOIN prospects p ON p.id=m.prospect_id JOIN businesses b ON b.prospect_id=p.id JOIN automation_scans a ON a.run_id=b.run_id WHERE a.day=? AND b.processing_status='QUALIFIED' AND p.first_seen_at>=? AND m.qualified_at>=?",(day,run['started_at'],run['started_at'])).fetchone()[0]
    updated=c.execute('SELECT COUNT(DISTINCT o.prospect_id) FROM prospect_observations o JOIN automation_scans a ON a.run_id=o.run_id JOIN prospects p ON p.id=o.prospect_id WHERE a.day=? AND p.first_seen_at<?',(day,run['started_at'])).fetchone()[0]
    raw=c.execute('SELECT COALESCE(SUM(r.raw_found),0) FROM pipeline_runs r JOIN automation_scans a ON a.run_id=r.id WHERE a.day=?',(day,)).fetchone()[0]
    c.execute('UPDATE automation_runs SET new_qualified=?,updated_leads=?,raw_candidates=?,shortfall=? WHERE day=?',(count,updated,raw,max(0,run['target']-count),day))
    choices=[m for m in eligible_markets(c) if not c.execute('SELECT 1 FROM automation_scans WHERE day=? AND market_id=?',(day,m['id'])).fetchone()]
    if count>=run['target'] or not choices:
        status='COMPLETE' if count>=run['target'] else 'SHORTFALL'
        c.execute('UPDATE automation_runs SET status=?,completed_at=? WHERE day=?',(status,stamp,day));c.commit();return {'status':status}
    m=choices[0]
    scan=PipelineRun(market=m['city']+', '+m['country'],vertical=m['vertical'],target=run['target']-count,status='QUEUED',started_at=stamp,run_configuration={'target':run['target']-count,'automation_day':day,'quality':'high_intent','opportunities':['WEBSITE','SEO','SECURITY'],'business_scales':['LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL'],'results':'all','exclude_chains':True})
    rid=PipelineRunRepository(c).create(scan,organization=org)
    c.execute("INSERT INTO automation_scans(day,market_id,run_id,status) VALUES(?,?,?,'PENDING')",(day,m['id'],rid))
    c.execute('UPDATE scan_markets SET last_scanned_at=?,total_scans=total_scans+1,updated_at=? WHERE id=?',(stamp,stamp,m['id']))
    c.commit()
    from app.api.services.cloud_executor import dispatch_queued
    dispatch_queued()
    return {'status':'QUEUED','run_id':rid}
