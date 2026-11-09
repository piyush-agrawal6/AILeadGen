from tests.workspace_fixtures import workspace_template
from app.platform.context import current
import asyncio,json,uuid
import pytest
from pydantic import ValidationError
from test_automation import db
from campaign_fixtures import campaign,lead,EVIDENCE
from app.api.routes.workflows import Run,Schedule,save_schedule
from app.workflows import service
from app.workflows.campaigns import audience
from app.database.prospects import now
from app.mail.config import MailSettings
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID


def test_campaign_required_no_count_and_explicit_recontact():
 for args in ({},{'campaign_id':'abc','emails':3},{'campaign_id':'abc','outreach_mode':'RECONTACT'}):
  with pytest.raises(ValidationError):Run(kind='OUTREACH',**args)
 assert Run(kind='OUTREACH',campaign_id='abc',outreach_mode='RECONTACT',confirm_recontact=True).max_day==100
 assert Run(kind='COMBINED').email_all_eligible is False


def test_entire_campaign_is_accounted_and_not_limited_by_daily_cap(db):
 cid=campaign(db);other=campaign(db,'Other')
 for n in range(107):lead(db,cid,n)
 lead(db,other,999)
 lead(db,cid,201,email=False);_,dnc=lead(db,cid,202);_,review=lead(db,cid,203,evidence=False)
 db.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT' WHERE id=?",(dnc,))
 from app.automation.service import reconcile
 reconcile(db)
 data=audience(db,cid,['WEBSITE','SECURITY'])
 assert data['qualified']==110 and data['total_accounted']==110
 assert data['will_queue']==108 and data['manual_contact']==1 and data['suppressed']==1 and data['needs_review']==0
 assert all(i['pitch_types']==['WORKSPACE'] for i in data['items'] if i['disposition']=='READY')
 options=Run(kind='OUTREACH',template_id=workspace_template(db),campaign_id=cid,max_day=20).model_dump()
 r=service.create(db,options,current().actor);assert r['requested']==108
 assert db.execute('SELECT COUNT(*) FROM outreach_run_items WHERE run_id=?',(r['id'],)).fetchone()[0]==110
 assert service.create(db,options,current().actor)['id']==r['id']
 d=service.detail(db,r['id'],page=4,page_size=25)
 assert d['items_total']==110 and len(d['items'])==25 and sum(d['counts'].values())==110
 assert audience(db,cid)['will_queue']==0 # open run reserves its audience
 assert audience(db,cid,run_id=r['id'])['will_queue']==108


def message(c,pid,status='SENT',test=0):
 from app.mail.templates import seed
 from app.mail import service as mail
 from app.mail.config import mail_settings
 # Persist realistic historical rows without transport.
 from app.mail.service import account
 aid=account(c,'system')['id']
 mid=str(uuid.uuid4());tid=str(uuid.uuid4())
 c.execute("INSERT INTO email_threads(id,prospect_id,account_id,subject,created_at,last_message_at,last_direction,organization_id) VALUES(?,?,?,'Prior',?,?,'OUTBOUND',?)",(tid,pid,aid,now(),now(),PLANEBYTE_ORGANIZATION_ID))
 c.execute("INSERT INTO email_messages(id,thread_id,prospect_id,account_id,direction,status,from_address,to_address,subject,body_text,created_at,sent_at,idempotency_key,test_mode,provider_message_id,message_type,organization_id) VALUES(?,?,?,?,'OUTBOUND',?,'planebyte@gmail.com','public@example.com','Prior','Prior',?,?,?,?,?, 'FIRST_CONTACT',?)",(mid,tid,pid,aid,status,now(),now(),mid,test,"<"+mid+"@example.com>",PLANEBYTE_ORGANIZATION_ID))
 return mid


def test_uncontacted_recontact_and_terminal_protections(db):
 cid=campaign(db);_,sent=lead(db,cid,1);_,test=lead(db,cid,2);_,uncertain=lead(db,cid,3);_,dnc=lead(db,cid,4);_,reply=lead(db,cid,5)
 message(db,sent);message(db,test,test=1);message(db,uncertain,status='SENDING')
 db.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT' WHERE id=?",(dnc,));db.execute("UPDATE prospects SET lead_status='REPLIED' WHERE id=?",(reply,))
 default={i['prospect_id']:i['disposition'] for i in audience(db,cid)['items']}
 assert default=={sent:'ALREADY_CONTACTED',test:'READY',uncertain:'NEEDS_REVIEW',dnc:'SUPPRESSED',reply:'REPLIED'}
 again={i['prospect_id']:i['disposition'] for i in audience(db,cid,mode='RECONTACT')['items']}
 assert again[sent]=='READY' and again[dnc]=='SUPPRESSED' and again[reply]=='REPLIED' and again[uncertain]=='NEEDS_REVIEW'


def test_pitch_scope_and_conservative_legacy_intent():
 from app.reports.opportunity import plan,pitch_support
 from app.database.campaign_outreach_schema import normalize_legacy
 data={'mode':'REACHABLE','primary':'WEBSITE','scores':{'WEBSITE':85,'SEO':65,'SECURITY':0},'evidence':EVIDENCE}
 assert pitch_support(data,['WEBSITE','SEO','SECURITY'])==['WEBSITE'] # unknown SEO codes cannot invent meaningful findings
 p=plan(data,allowed_kinds=['WEBSITE']);assert p['variant']=='website' and all(f['kind']=='WEBSITE' for f in p['findings'])
 for kind in ['OUTREACH','COMBINED']:
  old={'kind':kind,'emails_to_send':20,'target':50};converted=normalize_legacy(old)
  assert converted['email_all_eligible'] is False and converted['needs_owner_review'] is True and converted['legacy_email_limit']==20
  assert 'emails_to_send' not in converted
 assert not normalize_legacy({'kind':'COMBINED'})['email_all_eligible']


def test_completed_combined_scan_only_delegates_after_explicit_choice(db,monkeypatch):
 db.execute('UPDATE automation_controls SET scan_paused=0')
 s=MailSettings(_env_file=None,AUTO_SCAN_ENABLED=False,AUTO_EMAIL_ENABLED=False,EMAIL_SENDING_ENABLED=False)
 monkeypatch.setattr(service,'mail_settings',lambda:s)
 async def finish(c,rid):c.execute("UPDATE workflow_runs SET status='COMPLETED' WHERE id=?",(rid,))
 monkeypatch.setattr(service,'advance_scan',finish);monkeypatch.setattr(service,'prepare',lambda *args:None)
 for send in [False,True]:
  options=Run(kind='COMBINED',template_id=workspace_template(db),target=1,email_all_eligible=send,qualification_mode='BALANCED').model_dump();r=service.create(db,options,current().actor);service.start(db,r['id']);db.commit()
  asyncio.run(service.dispatch(db))
  rows=db.execute("SELECT * FROM workflow_runs WHERE campaign_id=? AND kind='OUTREACH'",(r['id'],)).fetchall()
  assert len(rows)==int(send)
  if send:assert json.loads(rows[0]['configuration_json'])['campaign_id']==r['id']


def migration_preservation(c,monkeypatch):
 import app.database.migrations as migrations
 full=migrations.MIGRATIONS
 monkeypatch.setattr(migrations,'MIGRATIONS',full[:10]);migrations.run_migrations(c)
 from app.database.models import PipelineRun,Business
 from app.database.repositories import PipelineRunRepository,BusinessRepository
 from app.database.prospects import ProspectRepository
 run=PipelineRun(market='Legacy London',vertical='hospitality',target=1,status='COMPLETED');PipelineRunRepository(c).create(run, organization=PLANEBYTE_ORGANIZATION_ID)
 b=Business(name='Legacy Hotel',normalized_name='legacy hotel',vertical='hospitality',run_id=run.id);BusinessRepository(c).insert(b)
 from tests.workspace_fixtures import historical_observation
 historical_observation(c,b)
 config={'kind':'COMBINED','name':'Legacy bounded audience','emails':20,'target':50}
 sid=str(uuid.uuid4());c.execute("INSERT INTO automation_schedules(id,name,kind,enabled,configuration_json,timezone,frequency,start_at,next_run_at,created_by,created_at,updated_at) VALUES(?,'Legacy','COMBINED',1,?,'Europe/London','daily',?,?, 'owner',?,?)",(sid,json.dumps(config),'2027-01-01T09:00:00+00:00','2027-01-01T09:00:00+00:00',now(),now()));c.commit()
 tables=['businesses','prospects','opportunity_scores','email_messages','email_threads','activities','client_reports','scan_markets','shared_settings']
 before={t:[dict(r) for r in c.execute('SELECT * FROM '+t).fetchall()] for t in tables}
 monkeypatch.setattr(migrations,'MIGRATIONS',full[:11]);assert migrations.run_migrations(c)==1
 assert all(before[t]==[dict(r) for r in c.execute('SELECT * FROM '+t).fetchall()] for t in tables)
 after=c.execute('SELECT * FROM automation_schedules WHERE id=?',(sid,)).fetchone();intent=json.loads(after['configuration_json'])
 assert after['enabled']==1 and intent['email_all_eligible'] is False and intent['needs_owner_review'] is True
 assert c.execute('SELECT campaign_id FROM pipeline_runs WHERE id=?',(run.id,)).fetchone()[0]
 assert migrations.run_migrations(c)==0


def test_schema11_preserves_rows_and_holds_ambiguous_schedules(monkeypatch):
 import sqlite3
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:migration_preservation(c,monkeypatch)
 finally:c.close()


def test_explicit_recontact_queue_survives_reconciliation_but_dnc_does_not(db):
 cid=campaign(db);b,pid=lead(db,cid,20);message(db,pid)
 from app.automation.service import reconcile
 reconcile(db)
 body=Run(kind='OUTREACH',template_id=workspace_template(db),campaign_id=cid,outreach_mode='RECONTACT',confirm_recontact=True).model_dump();r=service.create(db,body,current().actor)
 db.execute("UPDATE workflow_runs SET status='RUNNING' WHERE id=?",(r['id'],));db.execute("UPDATE outreach_run_items SET status='READY' WHERE run_id=?",(r['id'],))
 db.execute("INSERT INTO automation_email_queue(prospect_id,recipient,priority,queued_at,status,idempotency_key) VALUES(?,?,100,?,'QUEUED',?) ON CONFLICT(prospect_id) DO UPDATE SET status='QUEUED'",(pid,b.public_email,now(),'recontact-'+pid));reconcile(db)
 assert db.execute('SELECT status FROM automation_email_queue WHERE prospect_id=?',(pid,)).fetchone()[0]=='QUEUED'
 db.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT' WHERE id=?",(pid,));reconcile(db)
 assert db.execute('SELECT status FROM automation_email_queue WHERE prospect_id=?',(pid,)).fetchone()[0]=='CANCELED'


def test_preparation_does_not_starve_later_eligible_rows(db,monkeypatch):
 from fastapi import HTTPException
 cid=campaign(db)
 for n in range(12):lead(db,cid,400+n)
 r=service.create(db,Run(kind='OUTREACH',template_id=workspace_template(db),campaign_id=cid).model_dump(),current().actor)
 # Route early leads to review, then ensure the next eligible batch still prepares.
 ids=[x[0] for x in db.execute('SELECT id FROM outreach_run_items WHERE run_id=? ORDER BY created_at LIMIT 8',(r['id'],)).fetchall()]
 db.executemany("UPDATE outreach_run_items SET status='NEEDS_REVIEW' WHERE id=?",[(i,) for i in ids])
 from app.mail.config import MailSettings
 settings=MailSettings(_env_file=None,EMAIL_SENDING_ENABLED=False,EMAIL_SEND_MODE='test',EMAIL_TEST_RECIPIENT='controlled@example.test')
 monkeypatch.setattr('app.mail.service.mail_settings',lambda:settings)
 service.prepare(db,r['id'])
 assert db.execute("SELECT COUNT(*) FROM outreach_run_items WHERE run_id=? AND status='READY'",(r['id'],)).fetchone()[0]==4
 assert db.execute('SELECT COUNT(*) FROM client_reports').fetchone()[0]==0
