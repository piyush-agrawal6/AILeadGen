"""Workspace-scoped persisted operational reads and bounded source reservations."""
import json
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.intent_radar.permissions import context

CAPS={'hacker_news':30,'stack_exchange':8,'github':24,'youtube':14,'bluesky':14,'rss':4,'discourse':4,'atom':4}

def reserve_source(provider):
    from app.platform.context import current
    ctx=current();settings=get_settings();day=now()[:10];amount=CAPS[provider]
    with db_session() as c:
        context(c,True)
        from app.workflows.service import lock
        lock(c)
        owned=c.execute('SELECT reserved_requests FROM intent_source_usage WHERE organization_id=? AND provider=? AND day=?',(ctx.organization_id,provider,day)).fetchone()
        global_used=c.execute('SELECT COALESCE(SUM(reserved_requests),0) FROM intent_source_usage WHERE provider=? AND day=?',(provider,day)).fetchone()[0]
        if (owned[0] if owned else 0)+amount>settings.intent_radar_daily_searches*amount or global_used+amount>settings.intent_radar_global_daily_searches*amount:
            raise HTTPException(429,'Source request reservation quota exhausted; stored evidence remains available.')
        c.execute('INSERT INTO intent_source_usage(organization_id,provider,day,reserved_requests) VALUES(?,?,?,?) ON CONFLICT(organization_id,provider,day) DO UPDATE SET reserved_requests=intent_source_usage.reserved_requests+excluded.reserved_requests',(ctx.organization_id,provider,day,amount))

def source_health(c):
    org=context(c).organization_id
    from app.intent_radar.connectors import catalog
    # At most 100 persisted attempts per each of four supported providers.
    rows=c.execute("""SELECT provider,status,updated_at,result_json FROM (
        SELECT provider,status,updated_at,result_json,ROW_NUMBER() OVER(PARTITION BY provider ORDER BY updated_at DESC,discovery_id DESC) position
        FROM intent_source_runs WHERE organization_id=?) recent WHERE position<=100 ORDER BY provider,position""",(org,)).fetchall()
    history={}
    for row in rows:history.setdefault(row['provider'],[]).append(row)
    successes={row['provider']:row['last_success'] for row in c.execute("SELECT provider,MAX(updated_at) last_success FROM intent_source_runs WHERE organization_id=? AND status IN ('COMPLETE','NO_RESULTS') GROUP BY provider",(org,)).fetchall()}
    usage={row['provider']:row['reserved_requests'] for row in c.execute('SELECT provider,reserved_requests FROM intent_source_usage WHERE organization_id=? AND day=?',(org,now()[:10])).fetchall()}
    from app.intent_radar.source_runtime import health as runtime_health
    from app.intent_radar.bluesky_source import stream_health
    bsky_stream=None
    try:bsky_stream=stream_health(c)
    except Exception:pass
    items=[]
    for provider in catalog(c):
        attempts=history.get(provider['id'],[]);latest=json.loads(attempts[0]['result_json']) if attempts else {};failures=0
        for row in attempts:
            if row['status'] in ('COMPLETE','NO_RESULTS'):break
            failures+=1
        obs=runtime_health(c,provider['id'])
        entry={'provider':provider['id'],'name':provider['name'],'availability':provider['state'],'state':attempts[0]['status'] if attempts else 'Never checked','last_check':attempts[0]['updated_at'] if attempts else None,'last_success':successes.get(provider['id']),'last_error':None if not attempts or attempts[0]['status'] in ('COMPLETE','NO_RESULTS') else {'code':attempts[0]['status'],'errors':latest.get('errors',[])},'retry_at':latest.get('retry_at') or obs.get('retry_at'),'quota_remaining':latest.get('quota_remaining'),'consecutive_failures':failures,'failure_count_capped':failures==100,'daily_requests_reserved':usage.get(provider['id'],0),'daily_reservation_limit':get_settings().intent_radar_daily_searches*CAPS[provider['id']],'accounting_basis':'Upper-bound reserved requests; failed transport usage may be unknown.'}
        if provider['id']=='bluesky' and bsky_stream:entry['stream_health']=bsky_stream
        items.append(entry)
    return {'items':items}

def overview(c,*,include_sources=True):
    org=context(c).organization_id
    jobs=[dict(r) for r in c.execute("SELECT status,COUNT(*) count FROM intelligence_jobs WHERE organization_id=? AND kind='INTENT_DISCOVER' GROUP BY status",(org,)).fetchall()]
    heartbeat=c.execute('SELECT MAX(last_tick_at) FROM intent_worker_health WHERE state=?',('READY',)).fetchone()[0]
    recent=bool(heartbeat and heartbeat> (datetime.now(timezone.utc)-timedelta(seconds=180)).isoformat())
    return {'jobs_by_status':jobs,'backlog':sum(r['count'] for r in jobs if r['status']=='QUEUED'),'scheduler_heartbeat_at':heartbeat,'scheduler_heartbeat_fresh':recent,'worker_status_basis':'Running job records indicate leased work; scheduler heartbeat is not Cloud Run worker health.','sources':source_health(c)['items'] if include_sources else []}

def workspace_context(c):
    ctx=context(c)
    from app.intent_radar.intelligence import profile_context
    from app.intent_radar.service import preferences
    return {'organization_id':ctx.organization_id,'business_profile':profile_context(c),'default_icp_id':preferences(c)['default_icp_id'],'stage':get_settings().intent_radar_stage,'scope':'Verified current workspace; no buyer identity inference or credential access.'}
