from tests.workspace_fixtures import workspace_template
from app.platform.context import current
import asyncio,json
from datetime import datetime,timedelta,timezone
from fastapi.testclient import TestClient
from test_automation import db
from campaign_fixtures import campaign,lead
from app.api.server import app
from app.api.routes.workflows import Run,Schedule,save_schedule
from app.mail.config import MailSettings
from app.workflows import service

def test_requested_limits_save_and_roundtrip_without_activation(monkeypatch):
    settings=MailSettings(_env_file=None,MAX_EMAILS_PER_HOUR=50,MAX_EMAILS_PER_DAY=500,EMAIL_SENDING_ENABLED=False,AUTO_EMAIL_ENABLED=False,AUTO_SCAN_ENABLED=False)
    monkeypatch.setattr('app.api.routes.automation.mail_settings',lambda:settings)
    monkeypatch.setattr('app.automation.settings.mail_settings',lambda:settings)
    body={'daily_qualified_lead_target':500,'daily_email_target':500,'max_hour':50,'max_day':500,'followup_days':3,'automation_timezone':'Asia/Kolkata'}
    with TestClient(app) as client:
        response=client.put('/api/automation/targets',json=body)
        assert response.status_code==200,response.text
        assert client.get('/api/automation/targets').json()==body
        assert not settings.sending_enabled and not settings.auto_scan_enabled
        assert client.put('/api/automation/targets',json={**body,'max_hour':51}).status_code==422

def test_combined_schedule_starts_scan_while_email_stage_is_held(db,monkeypatch):
    s=MailSettings(_env_file=None,AUTO_SCAN_ENABLED=True,AUTO_EMAIL_ENABLED=False,EMAIL_SENDING_ENABLED=False)
    monkeypatch.setattr(service,'mail_settings',lambda:s)
    calls=[]
    async def executor(*args):calls.append(args)
    monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',executor)
    body=Schedule(name='Controlled combined',configuration=Run(kind='COMBINED',scan_source='OVERTURE',target=1,email_all_eligible=True),enabled=True,frequency='once',timezone='Asia/Kolkata',start_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat())
    sid=save_schedule(db,body,current().actor)['id']
    db.execute("UPDATE automation_schedules SET next_run_at='2000-01-01T00:00:00+00:00' WHERE id=?",(sid,))
    db.execute('UPDATE automation_controls SET scan_paused=0,email_paused=1');db.commit()
    asyncio.run(service.dispatch(db));asyncio.run(service.dispatch(db))
    assert len(calls)==1
    assert db.execute('SELECT COUNT(*) FROM workflow_runs WHERE schedule_id=?',(sid,)).fetchone()[0]==1
    assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0

def test_run_now_keeps_schedule_link_and_consumes_once_slot(monkeypatch):
    calls=[]
    async def executor(*args):calls.append(args)
    monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',executor)
    with TestClient(app) as client:
        client.put('/api/automation/controls',json={'scan_paused':False,'email_paused':True})
        body=Schedule(name='Owner run now',configuration=Run(kind='SCAN',scan_source='OVERTURE',target=1),enabled=False,frequency='once',timezone='Asia/Kolkata',start_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat())
        sid=client.post('/api/workflow/schedules',json=body.model_dump()).json()['id']
        r=client.post('/api/workflow/schedules/'+sid+'/run-now');assert r.status_code==200,r.text
        rid=r.json()['run_id'];detail=client.get('/api/workflow/runs/'+rid).json()
        assert detail['schedule_id']==sid and detail['configuration']['_schedule_trigger']=='RUN_NOW'
        assert client.post('/api/workflow/schedules/'+sid+'/run-now').json()['run_id']==rid
        assert len(calls)==1

def test_no_sendable_campaign_explains_review_instead_of_stalling(db):
    cid=campaign(db);lead(db,cid,992,email=False);lead(db,cid,993,email=False,evidence=False)
    r=service.create(db,Run(kind='OUTREACH',template_id=workspace_template(db),campaign_id=cid).model_dump(),current().actor)
    service.prepare(db,r['id']);detail=service.detail(db,r['id'])
    assert detail['status']=='COMPLETED'
    assert 'No sendable emails' in detail['error']
    assert detail['counts']['MANUAL_CONTACT']==2 and detail['counts'].get('NEEDS_REVIEW',0)==0
    assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
