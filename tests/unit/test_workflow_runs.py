from app.platform.context import current
import asyncio,json,uuid
from datetime import datetime,timezone
import pytest
from test_automation import db
from app.api.routes.workflows import Run,Schedule,save_schedule
from app.workflows import service
from app.workflows.calendar import next_due
from app.mail.config import MailSettings
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID


def options(kind='SCAN'):
 return Run(name='Owner manual run',kind=kind,target=2,campaign_id='controlled-campaign' if kind=='OUTREACH' else None).model_dump()

def test_capability_flags_cannot_start_legacy_background_work(db,monkeypatch):
 from app.automation import service as automation
 s=MailSettings(_env_file=None,AUTO_SCAN_ENABLED=True,AUTO_EMAIL_ENABLED=True,EMAIL_SENDING_ENABLED=True)
 monkeypatch.setattr(automation,'mail_settings',lambda:s)
 assert automation.acquisition_tick(db)['status']=='NO_EXPLICIT_RUN'
 assert automation.outreach_tick(db)['status']=='NO_EXPLICIT_RUN'
 assert db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0

def test_manual_scan_reuses_existing_executor_and_duplicate_start(db,monkeypatch):
 db.execute('UPDATE automation_controls SET scan_paused=0')
 called=[]
 async def start(*args):called.append(args)
 monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',start)
 o=options();r=service.create(db,o,'owner@example.com');assert service.create(db,o,'owner@example.com')['id']==r['id']
 service.start(db,r['id']);db.commit()
 asyncio.run(service.advance_scan(db,r['id']));asyncio.run(service.advance_scan(db,r['id']))
 assert len(called)==1
 assert db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==1
 assert service.detail(db,r['id'])['requested']==2


def test_schedule_disabled_then_duplicate_dispatch_has_one_run(db,monkeypatch):
 s=MailSettings(_env_file=None,AUTO_SCAN_ENABLED=True,AUTO_EMAIL_ENABLED=False,EMAIL_SENDING_ENABLED=False)
 monkeypatch.setattr(service,'mail_settings',lambda:s)
 async def start(*a):pass
 monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',start)
 schedule=Schedule(name='Weekday hotels',configuration=Run(**options()),enabled=False,timezone='Europe/London',frequency='daily',start_at='2026-01-01T06:00:00+00:00')
 sid=save_schedule(db,schedule,current().actor)['id'];db.commit()
 assert asyncio.run(service.dispatch(db))['scheduled_runs_started']==[]
 db.execute("UPDATE automation_schedules SET enabled=1,next_run_at='2026-01-01T06:00:00+00:00' WHERE id=?",(sid,));db.execute('UPDATE automation_controls SET scan_paused=0');db.commit()
 first=asyncio.run(service.dispatch(db));second=asyncio.run(service.dispatch(db))
 assert len(first['scheduled_runs_started'])==1 and second['scheduled_runs_started']==[]
 assert db.execute('SELECT COUNT(*) FROM automation_schedule_runs').fetchone()[0]==1
 assert db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==1


def test_schedule_timezone_weekdays_and_cron_validation():
 config={'start_at':'2026-10-30T09:00:00+00:00','timezone':'Europe/London','frequency':'weekdays'}
 assert next_due(config,datetime(2026,10,30,10,tzinfo=timezone.utc))=='2026-11-02T09:00:00+00:00'
 config.update(frequency='custom',cron_expression='0 6 * * 1-5')
 assert next_due(config,datetime(2026,10,30,10,tzinfo=timezone.utc))=='2026-11-02T06:00:00+00:00'
 with pytest.raises(ValueError):next_due({**config,'cron_expression':'* * * * 99'})
 with pytest.raises(ValueError):Run(name='unsafe',kind='OUTREACH',max_hour=11)


def test_email_run_prepares_workspace_copy_exact_preview_and_one_guarded_mock_send(db,monkeypatch,tmp_path):
 monkeypatch.setattr('app.platform.modules.legacy_enabled',lambda:True)  # Historical report-based preparation, not customer default.
 from unittest.mock import Mock
 from app.database.models import Business,WebsiteProfile,PipelineRun
 from app.database.repositories import BusinessRepository,WebsiteProfileRepository,PipelineRunRepository
 from app.database.prospects import ProspectRepository,now
 from app.reports.service import execute_report
 from app.mail import service as mail
 from app.automation import service as automation
 from app.mail.quality import issues
 s=MailSettings(_env_file=None,EMAIL_SENDING_ENABLED=True,EMAIL_SEND_MODE='production',EMAIL_LIVE_APPROVED=True,AUTO_EMAIL_ENABLED=False,MAIL_FROM_ADDRESS='planebyte@gmail.com')
 for module in (service,mail,automation):monkeypatch.setattr(module,'mail_settings',lambda:s)
 transport=Mock();transport.health_check.return_value={'smtp':'READY','imap':'READY'};monkeypatch.setattr(mail,'provider',lambda:transport)
 from campaign_fixtures import campaign
 cid=campaign(db,cid='controlled-campaign')
 run=PipelineRun(market='London',vertical='hospitality',target=1,status='COMPLETED');PipelineRunRepository(db).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
 b=Business(name='Controlled Hotel',normalized_name='controlled hotel',vertical='hospitality',city='London',country='United Kingdom',website='http://controlled.example',public_email='public@controlled.example',processing_status='QUALIFIED',run_id=run.id)
 db.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run.id))
 BusinessRepository(db).insert(b);db.execute("UPDATE businesses SET website_status='REACHABLE' WHERE id=?",(b.id,));pid=ProspectRepository(db).observe(b, organization=PLANEBYTE_ORGANIZATION_ID)
 WebsiteProfileRepository(db).upsert(WebsiteProfile(business_id=b.id,requested_url=b.website,reachable=True,https_enabled=False))
 db.execute("INSERT INTO contacts(business_id,contact_type,contact_value,source_url,source_type,confidence,is_public_business_contact,is_valid) VALUES(?,'email',?,?,'PUBLIC_WEBSITE',1,1,1)",(b.id,b.public_email,b.website+'/contact'))
 evidence={'WEBSITE':[{'code':'HTTP_ONLY','detail':'The final website response uses HTTP.','points':30},{'code':'NO_MOBILE_VIEWPORT','detail':'No viewport declaration in observed HTML.','points':20},{'code':'NO_PRIMARY_CTA','detail':'No enquiry action observed.','points':15}],'SEO':[{'code':'MISSING_META_DESCRIPTION','detail':'Description absent.','points':10}],'SECURITY':[]}
 db.execute("INSERT INTO opportunity_scores(business_id,website_opportunity_score,seo_opportunity_score,security_opportunity_score,primary_opportunity,contactability_level,scoring_version,evidence_json,created_at) VALUES(?,83,50,80,'WEBSITE','HIGH','qa',?,?)",(b.id,json.dumps(evidence),now()))
 db.execute("INSERT INTO business_intelligence(business_id,prospect_id,classification_version,business_scale,scale_reason,scale_confidence,footprint_json,commercial_fit,commercial_reason,created_at) VALUES(?,?,'qa','LOCAL','fixture',1,'{}','HIGH','fixture',?)",(b.id,pid,now()));db.commit()
 from app.database.connection import get_connection
 path=tmp_path/'workflow.db';mirror=get_connection(path);db.backup(mirror);mirror.close()
 # Report worker uses its ordinary independent database connection.
 monkeypatch.setattr('app.reports.service.get_connection',lambda **kwargs:get_connection(path))
 c=get_connection(path)
 try:
  from tests.workspace_fixtures import workspace_template
  r=service.create(c,{**options('OUTREACH'),'template_id':workspace_template(c)},current().actor);service.prepare(c,r['id']);c.commit()
  report_id=c.execute('SELECT report_id FROM outreach_run_items').fetchone()[0]
  assert report_id is None
  assert c.execute('SELECT COUNT(*) FROM client_reports').fetchone()[0]==0
  i=c.execute('SELECT * FROM outreach_run_items').fetchone();assert i['status']=='READY',i['error']
  payload=json.loads(i['payload_json']);preview=json.loads(i['preview_json'])
  assert not issues(c,pid,payload,settings=s)
  assert c.execute('SELECT COUNT(*) FROM email_tracking_tokens').fetchone()[0]==0
  c.execute('UPDATE automation_controls SET email_paused=0');c.commit()
  service.start(c,r['id']);c.commit()
  monkeypatch.setattr(automation,'utc_now',lambda:datetime(2026,11,2,10,tzinfo=timezone.utc))
  assert automation.outreach_tick(c,execution_id=r['id'])['status']=='SENT'
  sent=transport.send_message.call_args.args[0]
  assert sent.get_body(preferencelist=('plain',)).get_content().strip()==preview['rendered_text'].strip()
  assert sent.get_body(preferencelist=('html',)).get_content().strip()==preview['rendered_html'].strip()
  assert len(list(sent.iter_attachments()))==0
  assert automation.outreach_tick(c,execution_id=r['id'])['status']=='PAUSED_OR_WAITING'
  transport.send_message.assert_called_once()
 finally:c.close()
