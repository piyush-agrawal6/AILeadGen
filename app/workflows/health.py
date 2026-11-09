"""Persisted operational facts; live external checks remain explicit."""
import logging
from datetime import datetime,timedelta,timezone
from app.database.prospects import now

def record(name,status,error=None):
    from app.database.connection import db_session
    from app.database.foundation_schema import ready
    try:
        with db_session() as c:
            if not ready(c):return
            stamp=now();started=stamp if status=='RUNNING' else None;success=stamp if status=='READY' else None;failure=stamp if status=='FAILED' else None
            c.execute('''INSERT INTO worker_health(name,status,started_at,last_success_at,last_failure_at,last_error_code,updated_at)
              VALUES(?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET status=excluded.status,started_at=COALESCE(excluded.started_at,worker_health.started_at),last_success_at=COALESCE(excluded.last_success_at,worker_health.last_success_at),last_failure_at=COALESCE(excluded.last_failure_at,worker_health.last_failure_at),last_error_code=excluded.last_error_code,updated_at=excluded.updated_at''',(name,status,started,success,failure,(error or '')[:80] or None,stamp))
    except Exception:logging.getLogger(__name__).warning('Worker health recording unavailable')

def attention(c):
    stamp=datetime.now(timezone.utc);stale=(stamp-timedelta(minutes=20)).isoformat();lease=stamp.isoformat()
    result=[]
    for name,sql,args in [
      ('Failed scan',"SELECT id,market label,status,error_message detail FROM pipeline_runs WHERE status IN ('FAILED','INTERRUPTED') ORDER BY id DESC LIMIT 30",()),
      ('Stalled scan',"SELECT id,market label,status,'Heartbeat expired; explicit checkpoint resume required' detail FROM pipeline_runs WHERE status='RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at<? LIMIT 30",(lease,)),
      ('Email review',"SELECT id,prospect_id label,status,'Verify provider result; never retry uncertain SMTP automatically' detail FROM email_messages WHERE status='UNCERTAIN' OR (status='SENDING' AND created_at<?) LIMIT 30",(stale,)),
      ('Stalled preparation',"SELECT id,run_id label,status,'Review the workspace template and preparation worker' detail FROM outreach_run_items WHERE status='PREPARING' AND updated_at<? LIMIT 30",(stale,)),
      ('Stalled schedule',"SELECT id,schedule_id label,status,'Check linked workflow; no duplicate execution should be created' detail FROM automation_schedule_runs WHERE status='RUNNING' AND started_at<? LIMIT 30",((stamp-timedelta(hours=4)).isoformat(),)),
    ]:
        result.extend({'kind':name,**dict(r)} for r in c.execute(sql,args).fetchall())
    return result

def health(c):
    from app.api.read_cache import read_cache
    groups={'Application':[{'name':'API','status':'READY','detail':'Authenticated request completed'},{'name':'Database','status':'READY','detail':'Schema '+str(c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0])}, {'name':'Redis read cache',**read_cache.health()}],
            'Workers':[],'Email':[],'Providers':[]}
    workers={r['name']:dict(r) for r in c.execute('SELECT * FROM worker_health').fetchall()}
    for mode in ('scan','daily-acquisition','hourly-outreach','inbox-sync'):
        groups['Workers'].append(workers.get(mode,{'name':mode,'status':'UNVERIFIED','last_success_at':None,'last_failure_at':None}))
    for account in c.execute('SELECT smtp_health,imap_health,health_checked_at,last_sync_at FROM email_accounts').fetchall():
        groups['Email'].extend([{'name':'SMTP','status':account['smtp_health'],'last_success_at':account['health_checked_at'] if account['smtp_health']=='READY' else None},{'name':'IMAP','status':account['imap_health'],'last_success_at':account['health_checked_at'] if account['imap_health']=='READY' else None},{'name':'Reply / bounce sync','status':'OBSERVED' if account['last_sync_at'] else 'UNVERIFIED','last_success_at':account['last_sync_at']}])
    tracked=c.execute('SELECT MAX(occurred_at) FROM email_engagement_events').fetchone()[0]
    groups['Email'].append({'name':'Tracking','status':'OBSERVED' if tracked else 'UNVERIFIED','last_success_at':tracked})
    for name,sql in [('R2 artifacts','SELECT MAX(created_at) FROM artifact_objects')]:
        last=c.execute(sql).fetchone()[0];groups['Providers'].append({'name':name,'status':'OBSERVED' if last else 'UNVERIFIED','last_success_at':last})
    groups['Providers'].extend({'name':name,'status':'EXPLICIT_CHECK_REQUIRED','last_success_at':None} for name in ('Overture','Nominatim','OSM / Overpass'))
    return {'groups':groups,'attention':attention(c),'controls':dict(c.execute('SELECT scan_paused,email_paused,pause_reason FROM automation_controls WHERE id=1').fetchone()),'read_only':True}
