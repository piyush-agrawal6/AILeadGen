"""Opt-in recurring discovery using the shared bounded intelligence dispatcher."""
import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.intent_radar import service, models, discovery
from app.intent_radar.permissions import context
from app.platform.context import workspace_scope

HOURS={'Daily':24,'12 hours':12,'6 hours':6}

def eligible_sql(alias,actor=None):
    """Prune unavailable history before bounded selection; never grant authority."""
    org=alias+'.organization_id'
    clauses=["EXISTS(SELECT 1 FROM organization_products grant_row WHERE grant_row.organization_id="+org+" AND grant_row.product='INTENT_RADAR' AND grant_row.enabled=1)"]
    args=[]
    if get_settings().billing_enabled or get_settings().payu_billing_enabled:
        from app.billing.service import eligibility_sql
        paid,values=eligibility_sql(org)
        clauses[0]='('+clauses[0]+' OR '+paid+')';args.extend(values)
    if get_settings().intent_radar_stage=='Internal Preview':
        approved=[value for value in get_settings().intent_radar_internal_workspaces.split(',') if value]
        clauses.append(org+' IN ('+','.join('?' for _ in approved)+')' if approved else '1=0');args.extend(approved)
    if actor:
        clauses.append("EXISTS(SELECT 1 FROM organization_memberships member_row WHERE member_row.organization_id="+org+" AND member_row.user_id="+alias+'.'+actor+" AND member_row.status='ACTIVE' AND member_row.role IN ('OWNER','ADMIN','MEMBER'))")
    return ' AND '.join(clauses),args

def next_run(key,frequency,zone='UTC',stamp=None):
    stamp=stamp or datetime.now(timezone.utc)
    # UTC intervals remain fixed across DST; timezone is retained for display.
    ZoneInfo(zone)
    jitter=int(hashlib.sha256(key.encode()).hexdigest()[:4],16)%300
    return (stamp+timedelta(hours=HOURS[frequency],seconds=jitter)).isoformat()

def update(c,key,body):
    ctx=context(c,True);old=service.get(c,'monitors',key)
    try:ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError,ValueError):raise HTTPException(422,'Choose a valid IANA timezone.') from None
    s=get_settings()
    if body.frequency!='Manual':
        if not s.intent_radar_schedules_enabled:raise HTTPException(409,'Scheduled monitoring is disabled by the platform operator.')
        from app.billing.commercial_usage import interval
        interval(c,HOURS[body.frequency])
        if HOURS[body.frequency]<s.intent_radar_min_schedule_hours:raise HTTPException(429,'This monitoring frequency exceeds the configured usage policy.')
        if old['status']!='Active':raise HTTPException(409,'Activate the monitor before enabling a schedule.')
    due=next_run(key,body.frequency,body.timezone) if body.frequency!='Manual' else None
    if not c.execute('UPDATE intent_monitors SET schedule_json=?,next_run_at=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(body.model_dump_json(exclude={'revision'}),due,now(),key,ctx.organization_id,body.revision)).rowcount:raise HTTPException(409,'Monitor changed; reload before scheduling.')
    service.audit(c,'SCHEDULE_UPDATED',key)
    return service.get(c,'monitors',key)

def enqueue_due(c):
    if not get_settings().intent_radar_schedules_enabled or get_settings().intent_radar_stage=='Disabled':return []
    # Selection never grants authority. Each persisted owner is reverified below.
    eligible,args=eligible_sql('m','created_by')
    candidates=c.execute("SELECT m.id,m.organization_id,m.created_by,m.next_run_at FROM intent_monitors m WHERE m.status='Active' AND m.next_run_at<=? AND "+eligible+" ORDER BY m.next_run_at,m.id LIMIT 10",[now(),*args]).fetchall()
    result=[]
    for candidate in candidates:
        try:
            with workspace_scope(c,candidate['created_by'],candidate['organization_id']):
                context(c,True)
                from app.workflows.service import lock
                lock(c);old=service.get(c,'monitors',candidate['id'])
                if not old['next_run_at'] or old['next_run_at']>now() or old['status']!='Active':c.rollback();continue
                schedule=old['schedule']
                if schedule.get('frequency') not in HOURS:c.rollback();continue
                from app.billing.commercial_usage import interval
                interval(c,HOURS[schedule['frequency']])
                if HOURS[schedule['frequency']]<get_settings().intent_radar_min_schedule_hours:c.rollback();continue
                if c.execute("SELECT 1 FROM intelligence_jobs WHERE organization_id=? AND id=? AND status IN ('QUEUED','RUNNING')",(candidate['organization_id'],old['last_job_id'])).fetchone():c.rollback();continue
                body=models.Discovery(configuration=old['configuration'],monitor_id=old['id'],request_id=uuid.uuid5(uuid.NAMESPACE_URL,old['id']+':scheduled:'+old['next_run_at']))
                job=discovery.create(c,body)
                due=next_run(old['id'],schedule['frequency'],schedule.get('timezone','UTC'))
                c.execute('UPDATE intent_monitors SET next_run_at=? WHERE id=? AND organization_id=? AND next_run_at=?',(due,old['id'],candidate['organization_id'],old['next_run_at']))
                c.commit();result.append({'id':job['id'],'actor':candidate['created_by'],'organization_id':candidate['organization_id']})
        except HTTPException as exc:
            c.rollback()
            if exc.status_code!=429:continue
            # Leave authority/quota failures visible and avoid hot-looping requests.
            try:
                with workspace_scope(c,candidate['created_by'],candidate['organization_id']):
                    context(c,True,True)
                    c.execute('UPDATE intent_monitors SET next_run_at=? WHERE id=? AND organization_id=? AND next_run_at=?',((datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),candidate['id'],candidate['organization_id'],candidate['next_run_at']))
                    c.commit()
            except HTTPException:c.rollback()
    return result

async def tick():
    if get_settings().billing_enabled or get_settings().payu_billing_enabled:
        from app.billing.webhooks import tick as billing_tick
        await asyncio.to_thread(billing_tick,2)
    if get_settings().intent_radar_stage=='Disabled':return
    # Rotation prevents an abandoned workspace or a large nonexpiring prefix
    # from starving retention. Every candidate is reauthorized before writes.
    with db_session() as c:
        eligible,args=eligible_sql('m')
        candidates=c.execute("SELECT m.organization_id,MIN(m.user_id) actor FROM organization_memberships m LEFT JOIN intent_retention_cursors r ON r.organization_id=m.organization_id WHERE m.status='ACTIVE' AND m.role IN ('OWNER','ADMIN') AND "+eligible+" GROUP BY m.organization_id,r.updated_at ORDER BY COALESCE(r.updated_at,''),m.organization_id LIMIT 10",args).fetchall()
        for candidate in candidates:
            try:
                with workspace_scope(c,candidate['actor'],candidate['organization_id']):service.expire_content(c)
                c.commit()
            except HTTPException:c.rollback()
    with db_session() as c:pending=enqueue_due(c)
    # Recover queued dispatch and expired leases after process interruption.
    # Persisted job ownership is resolved again; no implicit workspace context.
    with db_session() as c:
        eligible,args=eligible_sql('j','created_by')
        kinds="('INTENT_DISCOVER','GROWTH_ANALYZE')" if get_settings().intent_radar_growth_enabled else "('INTENT_DISCOVER')"
        stalled=c.execute("SELECT j.id,j.kind,j.organization_id,j.created_by FROM intelligence_jobs j WHERE j.kind IN "+kinds+" AND j.attempts<3 AND (j.status='QUEUED' OR (j.status='RUNNING' AND j.lease_until<?)) AND "+eligible+" ORDER BY j.created_at,j.id LIMIT 2",[now(),*args]).fetchall()
        for row in stalled:
            try:
                with workspace_scope(c,row['created_by'],row['organization_id']):
                    context(c,True,manager=row['kind']=='GROWTH_ANALYZE')
                    c.execute("UPDATE intelligence_jobs SET status='QUEUED',execution_name=NULL,lease_owner=NULL,lease_until=NULL WHERE id=? AND organization_id=? AND (status='QUEUED' OR (status='RUNNING' AND lease_until<?))",(row['id'],row['organization_id'],now()))
                    c.commit();pending.append({'id':row['id'],'actor':row['created_by'],'organization_id':row['organization_id']})
            except HTTPException:c.rollback()
    from app.intelligence.dispatch import launch
    pending=list({item['id']:item for item in pending}.values())
    for item in pending:
        with db_session() as c:
            with workspace_scope(c,item['actor'],item['organization_id']):await launch(item['id'])
    with db_session() as c:
        c.execute('INSERT INTO intent_worker_health(worker_id,last_tick_at,state,detail_json) VALUES(?,?,?,?) ON CONFLICT(worker_id) DO UPDATE SET last_tick_at=excluded.last_tick_at,state=excluded.state,detail_json=excluded.detail_json',('intent-scheduler',now(),'READY',json.dumps({'dispatch_candidates':len(pending)})))

async def loop():
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception:
            import logging
            logging.getLogger(__name__).warning('Intent scheduler tick failed; will retry on next bounded tick.')
        await asyncio.sleep(60)
