"""Real-source/Vertex browser acceptance using only the disposable source-check DB."""
import asyncio,uuid,os
from pathlib import Path
from fastapi import Depends
from app.config.settings import get_settings
from app.database.connection import get_connection
from app.platform.context import workspace_scope
from app.intent_radar import models,service,schedules
from app.icp import models as im,service as icps

s=get_settings();path=Path(s.database_path).resolve()
base=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
assert s.app_env=='test' and path.is_relative_to(base) and path.name.startswith('intent-radar-23-') and path.suffix=='.db' and path.is_file()
assert os.environ.get('EMAIL_SENDING_ENABLED')=='false'
s.allowed_user_emails='radar23@example.test';s.intent_radar_stage='Beta';s.intent_radar_stackexchange_enabled=True
s.intent_radar_approved_feed_hosts='www.w3.org';s.intent_radar_schedules_enabled=True;s.intent_radar_ai_enabled=True
c=get_connection(path);org=c.execute("SELECT id,created_by_user_id FROM organizations WHERE name='Disposable Radar 23 acceptance'").fetchone();assert org
with workspace_scope(c,org['created_by_user_id'],org['id']):
    existing=icps.listing(c)['items']
    if not existing:icps.create(c,im.Create(name='Software services research',criteria=im.Criteria(intent=im.IntentCriteria(relevant_services=['custom software development','software engineering consulting'])),request_id=uuid.uuid4()))
    c.commit()
c.close()
from app.api.server import app
from app.api.dependencies import get_db

@app.post('/api/intent-radar/_test-live-tick/{key}')
async def advance_test_clock(key:uuid.UUID,c=Depends(get_db,scope='function')):
    old=service.get(c,'monitors',str(key))
    if old['status']=='Active':c.execute('UPDATE intent_monitors SET next_run_at=? WHERE id=? AND organization_id=?',('2000-01-01',old['id'],old['organization_id']));c.commit()
    pending=schedules.enqueue_due(c)
    from app.intelligence import jobs
    for job in pending:await asyncio.to_thread(jobs.execute,job['id'],path)
    return {'dispatched':len(pending)}
