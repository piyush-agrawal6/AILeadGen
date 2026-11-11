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
        if HOURS[body.frequency]<s.intent_radar_min_schedule_hours:raise HTTPException(429,'This monitoring frequency exceeds the configured usage policy.')
        if old['status']!='Active':raise HTTPException(409,'Activate the monitor before enabling a schedule.')
    due=next_run(key,body.frequency,body.timezone) if body.frequency!='Manual' else None
    if not c.execute('UPDATE intent_monitors SET schedule_json=?,next_run_at=?,revision=revision+1,updated_at=? WHERE id=? AND organization_id=? AND revision=?',(body.model_dump_json(exclude={'revision'}),due,now(),key,ctx.organization_id,body.revision)).rowcount:raise HTTPException(409,'Monitor changed; reload before scheduling.')
    service.audit(c,'SCHEDULE_UPDATED',key)
    return service.get(c,'monitors',key)

def enqueue_due(c):
    if not get_settings().intent_radar_schedules_enabled or get_settings().intent_radar_stage=='Disabled':return []
    # Selection never grants authority. Each persisted owner is reverified below.
    candidates=c.execute("SELECT id,organization_id,created_by FROM intent_monitors WHERE status='Active' AND next_run_at<=? ORDER BY next_run_at LIMIT 10",(now(),)).fetchall()
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
            c.execute('UPDATE intent_monitors SET next_run_at=? WHERE id=? AND organization_id=?',( (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),candidate['id'],candidate['organization_id']))
            c.commit()
    return result

async def tick():
    with db_session() as c:pending=enqueue_due(c)
    # Recover queued dispatch and expired leases after process interruption.
    # Persisted job ownership is resolved again; no implicit workspace context.
    with db_session() as c:
        stalled=c.execute("SELECT id,organization_id,created_by FROM intelligence_jobs WHERE kind='INTENT_DISCOVER' AND attempts<3 AND (status='QUEUED' OR (status='RUNNING' AND lease_until<?)) ORDER BY created_at LIMIT 2",(now(),)).fetchall()
        for row in stalled:
            try:
                with workspace_scope(c,row['created_by'],row['organization_id']):
                    context(c,True)
                    c.execute("UPDATE intelligence_jobs SET status='QUEUED',execution_name=NULL,lease_owner=NULL,lease_until=NULL WHERE id=? AND organization_id=? AND (status='QUEUED' OR (status='RUNNING' AND lease_until<?))",(row['id'],row['organization_id'],now()))
                    c.commit();pending.append({'id':row['id'],'actor':row['created_by'],'organization_id':row['organization_id']})
            except HTTPException:c.rollback()
    from app.intelligence.dispatch import launch
    for item in pending:
        with db_session() as c:
            with workspace_scope(c,item['actor'],item['organization_id']):await launch(item['id'])

async def loop():
    while True:
        try:await tick()
        except asyncio.CancelledError:raise
        except Exception:
            import logging
            logging.getLogger(__name__).warning('Intent scheduler tick failed; will retry on next bounded tick.')
        await asyncio.sleep(60)
