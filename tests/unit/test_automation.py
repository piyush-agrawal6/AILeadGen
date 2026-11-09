from datetime import datetime,timezone
import sqlite3
import pytest
from app.database.migrations import run_migrations
from app.automation.service import seed_markets,eligible_markets,business_hours,acquisition_tick,outreach_tick
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID

@pytest.fixture
def db(request):
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    run_migrations(c)
    from tests.workspace_fixtures import bind_internal_workspace
    bind_internal_workspace(c,request)
    yield c
    c.close()


def test_migration_seed_is_idempotent(db):
    before=db.execute('SELECT COUNT(*) FROM scan_markets').fetchone()[0]
    seed_markets(db);db.commit()
    assert run_migrations(db)==0
    assert before==304==db.execute('SELECT COUNT(*) FROM scan_markets').fetchone()[0]
    assert db.execute('PRAGMA foreign_key_check').fetchall()==[]


def test_rotation_prefers_untouched_and_obeys_cooldown(db):
    first=eligible_markets(db)[0]
    db.execute('UPDATE scan_markets SET last_scanned_at=?,priority=100 WHERE id=?',('2026-11-01T00:00:00+00:00',first['id']))
    choices=eligible_markets(db,datetime(2026,11,2,tzinfo=timezone.utc))
    assert first['id'] not in [r['id'] for r in choices]
    assert choices[0]['last_scanned_at'] is None


def test_default_controls_fail_closed(db,monkeypatch):
    from app.mail.config import MailSettings
    monkeypatch.setattr('app.automation.service.mail_settings',lambda:MailSettings(_env_file=None,AUTO_SCAN_ENABLED=False,AUTO_EMAIL_ENABLED=False,EMAIL_SENDING_ENABLED=False))
    assert acquisition_tick(db)=={'status':'DISABLED'}
    assert outreach_tick(db)=={'status':'DISABLED'}
    assert db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0


def test_business_hours_include_local_timezone_and_weekends():
    assert business_hours(datetime(2026,11,2,9,tzinfo=timezone.utc),'Europe/London')
    assert not business_hours(datetime(2026,11,1,9,tzinfo=timezone.utc),'Europe/London')
    assert not business_hours(datetime(2026,11,2,18,tzinfo=timezone.utc),'Europe/London')


def test_reconcile_keeps_no_email_lead_and_rediscovery_single(db):
    from app.database.models import Business,PipelineRun
    from app.database.repositories import BusinessRepository,PipelineRunRepository
    from app.database.prospects import ProspectRepository
    from app.automation.service import reconcile
    ids=[]
    for _ in range(2):
        run=PipelineRun(market='London',vertical='hospitality',target=1)
        rid=PipelineRunRepository(db).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
        b=Business(name='Controlled hotel',normalized_name='controlled hotel',city='London',country='United Kingdom',website='https://controlled.example',domain='controlled.example',address='1 Controlled Street',phone='+442000000001',vertical='hospitality',run_id=rid,processing_status='QUALIFIED')
        BusinessRepository(db).insert(b)
        ids.append(ProspectRepository(db).observe(b, organization=PLANEBYTE_ORGANIZATION_ID))
    reconcile(db)
    assert ids[0]==ids[1]
    assert db.execute('SELECT COUNT(*) FROM master_lead_state').fetchone()[0]==1
    row=db.execute('SELECT * FROM master_lead_state').fetchone()
    assert row['contact_state']=='MANUAL_CONTACT_REQUIRED'
    assert row['manual_reason']
    assert db.execute('SELECT COUNT(*) FROM prospect_observations').fetchone()[0]==2
    assert db.execute('SELECT COUNT(*) FROM automation_email_queue').fetchone()[0]==0


def test_migration_retains_existing_records_and_counts(db):
    from app.database.prospects import now
    stamp=now()
    db.execute("INSERT INTO prospects(id,first_seen_at,last_seen_at,updated_at) VALUES('preserved',?,?,?)",(stamp,stamp,stamp))
    db.commit()
    assert run_migrations(db)==0
    assert db.execute("SELECT id FROM prospects WHERE id='preserved'").fetchone()[0]=='preserved'


def test_queue_is_unique_and_cancels_rejected_lead(db):
    from app.database.models import Business,PipelineRun
    from app.database.repositories import BusinessRepository,PipelineRunRepository
    from app.database.prospects import ProspectRepository,now
    from app.automation.service import reconcile
    run=PipelineRun(market='London',vertical='hospitality',target=1);rid=PipelineRunRepository(db).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
    b=Business(name='Controlled business',normalized_name='controlled business',city='London',country='United Kingdom',website='https://controlled.example',public_email='controlled@example.com',vertical='hospitality',run_id=rid,processing_status='QUALIFIED')
    BusinessRepository(db).insert(b);pid=ProspectRepository(db).observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
    db.execute("INSERT INTO business_intelligence(business_id,prospect_id,classification_version,business_scale,scale_reason,scale_confidence,footprint_json,commercial_fit,commercial_reason,created_at) VALUES(?,?,'fixture','MID_MARKET','fixture',1,'{}','HIGH','fixture',?)",(b.id,pid,now()))
    from campaign_fixtures import campaign
    cid=campaign(db);db.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,rid))
    db.execute("INSERT INTO contacts(business_id,contact_type,contact_value,source_url,is_valid,is_public_business_contact) VALUES(?,'email',?,?,1,1)",(b.id,b.public_email,b.website+'/contact'))
    db.execute("INSERT INTO workflow_runs(id,name,kind,status,configuration_json,created_by,created_at,requested,request_key,campaign_id) VALUES('owner-run','Owner run','OUTREACH','RUNNING','{}','owner',?,1,'owner-run',?)",(now(),cid))
    db.execute("INSERT INTO outreach_run_items(id,run_id,prospect_id,business_id,status,idempotency_key,created_at,updated_at) VALUES('owner-item','owner-run',?,?,'READY','owner-approved-contact',?,?)",(pid,b.id,now(),now()))
    reconcile(db);reconcile(db)
    assert db.execute('SELECT COUNT(*) FROM automation_email_queue').fetchone()[0]==1
    assert db.execute('SELECT contact_state FROM master_lead_state').fetchone()[0]=='EMAIL_QUEUED'
    db.execute("UPDATE master_lead_state SET sales_state='REJECTED'")
    reconcile(db)
    assert db.execute('SELECT status FROM automation_email_queue').fetchone()[0]=='CANCELED'
    reconcile(db)
    assert db.execute('SELECT status FROM automation_email_queue').fetchone()[0]=='CANCELED'


def test_duplicate_scheduler_invocation_reuses_pending_scan(db,monkeypatch):
    from app.mail.config import MailSettings
    monkeypatch.setattr('app.automation.service.mail_settings',lambda:MailSettings(_env_file=None,AUTO_SCAN_ENABLED=True,DAILY_QUALIFIED_LEAD_TARGET=100))
    monkeypatch.setattr('app.api.services.cloud_executor.dispatch_queued',lambda:None)
    db.execute('UPDATE automation_controls SET scan_paused=0');db.commit()
    first=__import__('app.automation.service',fromlist=['legacy_acquisition_tick']).legacy_acquisition_tick(db)
    second=__import__('app.automation.service',fromlist=['legacy_acquisition_tick']).legacy_acquisition_tick(db)
    assert first['status']=='QUEUED'
    assert second['status']=='WAITING_SCAN'
    assert first['run_id']==second['run_id']
    assert db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==1
