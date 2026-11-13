"""Workspace-scoped persisted operational reads and bounded source reservations."""
import json
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.intent_radar.permissions import context

CAPS={'hacker_news':22,'stack_exchange':3,'rss':4,'discourse':4}

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
    items=[]
    for provider in catalog(c):
        rows=c.execute('SELECT status,updated_at,result_json FROM intent_source_runs WHERE organization_id=? AND provider=? ORDER BY updated_at DESC,discovery_id DESC LIMIT 100',(org,provider['id'])).fetchall()
        success=c.execute("SELECT updated_at FROM intent_source_runs WHERE organization_id=? AND provider=? AND status IN ('COMPLETE','NO_RESULTS') ORDER BY updated_at DESC LIMIT 1",(org,provider['id'])).fetchone()
        latest=json.loads(rows[0]['result_json']) if rows else {}
        failures=0
        for row in rows:
            if row['status'] in ('COMPLETE','NO_RESULTS'):break
            failures+=1
        usage=c.execute('SELECT reserved_requests FROM intent_source_usage WHERE organization_id=? AND provider=? AND day=?',(org,provider['id'],now()[:10])).fetchone()
        items.append({'provider':provider['id'],'name':provider['name'],'availability':provider['state'],'state':rows[0]['status'] if rows else 'Never checked','last_check':rows[0]['updated_at'] if rows else None,'last_success':success[0] if success else None,'last_error':None if not rows or rows[0]['status'] in ('COMPLETE','NO_RESULTS') else {'code':rows[0]['status'],'errors':latest.get('errors',[])},'retry_at':latest.get('retry_at'),'quota_remaining':latest.get('quota_remaining'),'consecutive_failures':failures,'failure_count_capped':failures==100,'daily_requests_reserved':usage[0] if usage else 0,'daily_reservation_limit':get_settings().intent_radar_daily_searches*CAPS[provider['id']],'accounting_basis':'Upper-bound reserved requests; failed transport usage may be unknown.'})
    return {'items':items}

def overview(c):
    org=context(c).organization_id
    jobs=[dict(r) for r in c.execute("SELECT status,COUNT(*) count FROM intelligence_jobs WHERE organization_id=? AND kind='INTENT_DISCOVER' GROUP BY status",(org,)).fetchall()]
    heartbeat=c.execute('SELECT MAX(last_tick_at) FROM intent_worker_health WHERE state=?',('READY',)).fetchone()[0]
    recent=bool(heartbeat and heartbeat> (datetime.now(timezone.utc)-timedelta(seconds=180)).isoformat())
    return {'jobs_by_status':jobs,'backlog':sum(r['count'] for r in jobs if r['status']=='QUEUED'),'scheduler_heartbeat_at':heartbeat,'scheduler_heartbeat_fresh':recent,'worker_status_basis':'Running job records indicate leased work; scheduler heartbeat is not Cloud Run worker health.','sources':source_health(c)['items']}

def workspace_context(c):
    ctx=context(c)
    from app.intent_radar.intelligence import profile_context
    from app.intent_radar.service import preferences
    return {'organization_id':ctx.organization_id,'business_profile':profile_context(c),'default_icp_id':preferences(c)['default_icp_id'],'stage':get_settings().intent_radar_stage,'scope':'Verified current workspace; no buyer identity inference or credential access.'}
