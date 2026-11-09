"""Enabled queue acceptance against disposable SQLite; transport never leaves process."""
import json
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock
import pytest
from test_automation import db
from app.automation import service as automation
from app.mail import service as mail
from app.mail.config import MailSettings
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,now
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID

@pytest.fixture
def queue(db,monkeypatch):
    config=MailSettings(_env_file=None,EMAIL_PROVIDER='hostinger',EMAIL_SEND_MODE='test',EMAIL_TEST_RECIPIENT='contact@planebyte.com',EMAIL_SENDING_ENABLED=True,AUTO_EMAIL_ENABLED=True,MAIL_FROM_ADDRESS='planebyte@gmail.com',MAX_EMAILS_PER_DAY=100,DAILY_EMAIL_TARGET=100)
    monkeypatch.setattr(automation,'mail_settings',lambda:config);monkeypatch.setattr(mail,'mail_settings',lambda:config)
    at=datetime(2026,11,2,10,tzinfo=timezone.utc)
    monkeypatch.setattr(automation,'utc_now',lambda:at);monkeypatch.setattr(automation,'business_hours',lambda *args:True)
    transport=Mock();transport.send_message.return_value='accepted';monkeypatch.setattr(mail,'provider',lambda:transport)
    from campaign_fixtures import campaign,qualify
    cid=campaign(db)
    run=PipelineRun(market='Controlled',vertical='home_services',target=3,status='COMPLETED');rid=PipelineRunRepository(db).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    db.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,rid))
    ids=[]
    for i in range(3):
        b=Business(name=f'Controlled QA {i}',normalized_name=f'controlled qa {i}',vertical='home_services',city='London',run_id=rid,website=f'https://controlled-{i}.invalid',public_email='contact@planebyte.com',processing_status='QUALIFIED')
        BusinessRepository(db).insert(b);db.execute("INSERT INTO contacts(business_id,contact_type,contact_value,source_url,is_valid,is_public_business_contact) VALUES(?,'email',?,?,1,1)",(b.id,b.public_email,b.website+'/contact'));qualify(db,b);pid=ProspectRepository(db).observe(b, organization=PLANEBYTE_ORGANIZATION_ID);ids.append(pid)
        db.execute("INSERT INTO business_intelligence(business_id,prospect_id,classification_version,business_scale,scale_reason,scale_confidence,footprint_json,commercial_fit,commercial_reason,created_at) VALUES(?,?,'qa','SMALL_GROUP','fixture',1,'{}','HIGH','fixture',?)",(b.id,pid,now()))
        db.execute("INSERT INTO findings(business_id,finding_code,category,severity,title,description) VALUES(?,'qa','SEO','LOW','Controlled finding','Stored controlled finding')",(b.id,))
    db.execute('UPDATE automation_controls SET email_paused=0');automation.reconcile(db);db.commit()
    from app.mail.templates import seed
    seed(db)
    stamp=now()
    db.execute("INSERT INTO workflow_runs(id,name,kind,status,configuration_json,created_by,created_at,requested,request_key,campaign_id,organization_id) VALUES('explicit-run','Controlled','OUTREACH','RUNNING',?,'system',?,3,'explicit-run',?,?)",(json.dumps({'campaign_id':cid,'pitch_types':['WEBSITE'],'outreach_mode':'UNCONTACTED','max_hour':10,'max_day':100,'window_start':'00:00','window_end':'23:59','recipient_timezone':False}),stamp,cid,PLANEBYTE_ORGANIZATION_ID))
    for pid in ids:
        queued='run-item-'+pid
        bid=db.execute('SELECT id FROM businesses WHERE prospect_id=?',(pid,)).fetchone()[0]
        body={'campaign_id':cid,'pitch_types':['WEBSITE'],'to_address':'contact@planebyte.com','subject':'Controlled queue transport','body_text':'Controlled transport fixture','confirmation':'SEND','idempotency_key':queued,'message_type':'MANUAL_REPLY'}
        body['preview_token']=mail.preview(db,pid,'system',body)['preview_token']
        db.execute("INSERT INTO outreach_run_items(id,run_id,prospect_id,business_id,status,payload_json,idempotency_key,created_at,updated_at,organization_id) VALUES(?,'explicit-run',?,?,'READY',?,?,?,?,?)",('item-'+pid,pid,bid,json.dumps(body),queued,stamp,stamp,PLANEBYTE_ORGANIZATION_ID))
    automation.reconcile(db);db.commit()
    return db,config,transport,ids,at


def test_enabled_send_spacing_and_duplicate_tick(queue):
    c,_,transport,ids,at=queue
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='SENT'
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='PAUSED_OR_WAITING'
    assert transport.send_message.call_count==1
    assert transport.send_message.call_args[0][0]['To']=='contact@planebyte.com'
    next_at=datetime.fromisoformat(c.execute('SELECT next_send_at FROM automation_controls').fetchone()[0])
    assert (next_at-at).total_seconds()>=360
    assert c.execute("SELECT COUNT(*) FROM email_messages WHERE status='SENT'").fetchone()[0]==1

@pytest.mark.parametrize('n,age,expected',[(10,0,'HOUR_LIMIT'),(100,2,'DAY_LIMIT')])
def test_hard_hour_and_day_caps_do_not_contact_anyone(queue,n,age,expected):
    c,_,transport,_,at=queue
    mail.account(c,'system');pid=c.execute('SELECT prospect_id FROM automation_email_queue LIMIT 1').fetchone()[0]
    c.execute("INSERT INTO email_threads(id,prospect_id,account_id,subject,last_message_at,last_direction,created_at,organization_id) VALUES('cap-thread',?,?,'cap',?,'OUTBOUND',?,?)",(pid,mail.ACCOUNT,now(),now(),PLANEBYTE_ORGANIZATION_ID))
    stamp=(at-timedelta(hours=age)).isoformat()
    for i in range(n):c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,created_at,sent_at,organization_id) VALUES(?,?,?,'cap-thread',?,'OUTBOUND','SENT','planebyte@gmail.com','contact@planebyte.com','controlled','controlled',?,?,?)",(str(i),pid,mail.ACCOUNT,f'<{i}@qa.invalid>',stamp,stamp,PLANEBYTE_ORGANIZATION_ID))
    c.commit();assert automation.outreach_tick(c,execution_id='explicit-run')['status']==expected
    transport.send_message.assert_not_called()


def test_provider_failure_pauses_and_never_retries(queue):
    c,_,transport,_,_=queue
    from app.mail.providers import SendFailed
    transport.send_message.side_effect=SendFailed('CONTROLLED_FAILURE')
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='PAUSED_FOR_REVIEW'
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='PAUSED_OR_WAITING'
    assert transport.send_message.call_count==1
    assert c.execute('SELECT email_paused FROM automation_controls').fetchone()[0]==1


def test_restart_before_smtp_reservation_requeues_without_duplicate(queue):
    c,_,transport,ids,at=queue
    c.execute("UPDATE automation_email_queue SET status='ATTEMPTING',attempted_at=? WHERE prospect_id=?",((at-timedelta(minutes=15)).isoformat(),ids[0]));c.commit()
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='SENT'
    assert transport.send_message.call_count==1


def test_restart_uncertain_smtp_reservation_requires_review(queue):
    c,_,transport,ids,at=queue
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='SENT'
    sent=c.execute("SELECT prospect_id,idempotency_key FROM automation_email_queue WHERE status='SENT'").fetchone()
    c.execute("UPDATE email_messages SET status='SENDING' WHERE idempotency_key=?",(sent['idempotency_key'],))
    c.execute("UPDATE automation_email_queue SET status='ATTEMPTING',attempted_at=? WHERE prospect_id=?",((at-timedelta(minutes=15)).isoformat(),sent['prospect_id']))
    c.execute('UPDATE automation_controls SET next_send_at=NULL');c.commit()
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='PAUSED_FOR_REVIEW'
    assert transport.send_message.call_count==1


def test_restart_after_smtp_accepted_recovers_record_without_sending(queue):
    c,_,transport,_,at=queue
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='SENT'
    pid=c.execute("SELECT prospect_id FROM automation_email_queue WHERE status='SENT'").fetchone()[0]
    c.execute("UPDATE automation_email_queue SET status='ATTEMPTING',attempted_at=? WHERE prospect_id=?",((at-timedelta(minutes=15)).isoformat(),pid))
    # No other queued work: restart only reconciles the accepted durable message.
    c.execute("UPDATE automation_email_queue SET status='CANCELED' WHERE prospect_id<>?",(pid,))
    c.execute('UPDATE automation_controls SET next_send_at=NULL');c.commit()
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='EMPTY'
    assert c.execute('SELECT status FROM automation_email_queue WHERE prospect_id=?',(pid,)).fetchone()[0]=='SENT'
    assert transport.send_message.call_count==1


def test_confirmed_high_bounce_rate_pauses_before_any_send(queue):
    c,config,transport,_,at=queue
    config.bounce_min_sample=1;config.high_bounce_rate=0.2
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='SENT'
    message=c.execute('SELECT id FROM email_messages').fetchone()[0]
    from app.mail import tracking
    tracking.event(c,message,'BOUNCED_HARD',metadata={'confirmed':True},occurred_at=at.isoformat())
    c.execute('UPDATE email_messages SET sent_at=?',(at.isoformat(),));c.execute('UPDATE automation_controls SET next_send_at=NULL');c.commit()
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='HIGH_BOUNCE_RATE'
    assert transport.send_message.call_count==1


def test_simultaneous_scheduler_ticks_reserve_only_one_message(queue,tmp_path):
    import sqlite3
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    original,_,transport,_,_=queue
    path=tmp_path/'concurrent.db'
    mirror=sqlite3.connect(path);original.backup(mirror);mirror.close()
    barrier=Barrier(2)
    def tick():
        c=sqlite3.connect(path,timeout=10);c.row_factory=sqlite3.Row
        try:
            from app.platform.context import workspace_scope
            actor=c.execute('SELECT created_by_user_id FROM organizations WHERE id=?',(PLANEBYTE_ORGANIZATION_ID,)).fetchone()[0]
            with workspace_scope(c,actor,PLANEBYTE_ORGANIZATION_ID):
                barrier.wait();return automation.outreach_tick(c,execution_id='explicit-run')['status']
        finally:c.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:tick(),range(2)))
    assert sorted(results)==['PAUSED_OR_WAITING','SENT']
    assert transport.send_message.call_count==1


def approve_requested_limits(c,config):
    config.max_hour=50;config.max_day=500;config.daily_email_target=500
    row=c.execute("SELECT configuration_json FROM workflow_runs WHERE id='explicit-run'").fetchone()
    options=json.loads(row[0]);options.update(max_hour=50,max_day=500,spacing_minutes=1.2)
    c.execute("UPDATE workflow_runs SET configuration_json=? WHERE id='explicit-run'",(json.dumps(options),));c.commit()

def test_owner_approved_fifty_hour_spacing(queue):
    c,config,transport,_,at=queue;approve_requested_limits(c,config)
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='SENT'
    next_at=datetime.fromisoformat(c.execute('SELECT next_send_at FROM automation_controls').fetchone()[0])
    assert (next_at-at).total_seconds()==72
    assert automation.outreach_tick(c,execution_id='explicit-run')['status']=='PAUSED_OR_WAITING'
    assert transport.send_message.call_count==1

@pytest.mark.parametrize('n,age,expected',[(50,0,'HOUR_LIMIT'),(500,2,'DAY_LIMIT')])
def test_owner_approved_fifty_and_five_hundred_caps(queue,n,age,expected):
    c,config,transport,_,at=queue;approve_requested_limits(c,config)
    mail.account(c,'system');pid=c.execute('SELECT prospect_id FROM automation_email_queue LIMIT 1').fetchone()[0]
    c.execute("INSERT INTO email_threads(id,prospect_id,account_id,subject,last_message_at,last_direction,created_at,organization_id) VALUES('approved-cap',?,?,'cap',?,'OUTBOUND',?,?)",(pid,mail.ACCOUNT,now(),now(),PLANEBYTE_ORGANIZATION_ID))
    stamp=(at-timedelta(hours=age)).isoformat()
    c.executemany("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,created_at,sent_at,organization_id) VALUES(?,?,?,'approved-cap',?,'OUTBOUND','SENT','planebyte@gmail.com','contact@planebyte.com','controlled','controlled',?,?,?)",[(str(i),pid,mail.ACCOUNT,f'<{i}@qa.invalid>',stamp,stamp,PLANEBYTE_ORGANIZATION_ID) for i in range(n)])
    c.commit();assert automation.outreach_tick(c,execution_id='explicit-run')['status']==expected
    transport.send_message.assert_not_called()
