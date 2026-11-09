from app.platform.context import current
import asyncio,json,uuid
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from test_automation import db
from app.experiments import content,service
from app.experiments.plan import segments,TEMPLATES,in_window
from app.reports.data import brand_config

@pytest.fixture
def brief_data():
 return {'business':{'name':'Homestay Hotels','vertical':'Hospitality','city':'London','country':'United Kingdom','website':'https://example.com','email':'office@example.com'},'mode':'REACHABLE','created_at':'2026-11-02T15:00:00+00:00','brand':brand_config(),'primary':'SEO','scores':{'WEBSITE':50,'SEO':60,'SECURITY':60},'evidence':{'SEO':[{'code':'MISSING_SCHEMA','detail':'Relevant structured business data was absent from the sampled HTML.','points':20},{'code':'MISSING_META_DESCRIPTION','detail':'The homepage response did not contain a meta description.','points':15}], 'SECURITY':[{'code':'NO_HSTS','detail':'The sampled HTTPS response did not expose Strict-Transport-Security.','points':15},{'code':'NO_CSP','detail':'The sampled response did not expose Content-Security-Policy.','points':10}], 'WEBSITE':[{'code':'NO_PRIMARY_CTA','detail':'No prominent enquiry action appeared in the sampled navigation.','points':25}]},'findings':[],'website':{'reachable':True},'lighthouse':{},'experiment':{'template_id':'AEO_CYBER','member_id':'fixture','brief_version':2}}


def test_exact_five_day_market_vertical_source_plan():
 rows=segments();assert len(rows)==25 and rows[0]['date']=='2026-11-02' and rows[-1]['date']=='2026-11-06'
 assert len({r['city'] for r in rows})==25 and sum(r['target'] for r in rows)==2500
 assert Counter(r['vertical'] for r in rows)=={k:5 for k in ('hospitality','dentists','legal','real_estate','home_services')}
 assert sum(r['sources']['OVERTURE'] for r in rows)==sum(r['sources']['FIRECRAWL'] for r in rows)==1250
 assert rows[0]['city']=='Austin' and rows[4]['city']=='Sydney'

@pytest.mark.parametrize('template',TEMPLATES)
def test_five_distinct_evidence_constrained_strategies(brief_data,template):
 message=content.render(brief_data,template)
 assert 70<=len(message['body_text'].split())<=140,(template,len(message['body_text'].split()))
 assert not content.email_issues(brief_data,message)
 assert message['body_text'].count(content.CTA)==1 and 'Homestay Hotels' in message['body_text']
 assert 'full website rebuild' not in message['body_text'] or 'without' in message['body_text']
 assert len(set(content.render(brief_data,t)['body_text'] for t in TEMPLATES))==5


def test_no_aeo_or_cyber_pitch_without_relevant_evidence(brief_data):
 brief_data['evidence']={'WEBSITE':brief_data['evidence']['WEBSITE']}
 assert content.eligible_templates(brief_data)==[]
 with pytest.raises(ValueError):content.render(brief_data,'CYBER_AUDIT')
 with pytest.raises(ValueError):content.render(brief_data,'AEO_READINESS')


def test_deterministic_balanced_assignment_does_not_adapt_to_winners(brief_data):
 counts=Counter();assigned=[]
 for n in range(500):
  t=content.assign_template(brief_data,'source-market-'+str(n),counts);counts[t]+=1;assigned.append(t)
 assert set(counts.values())=={100}
 assert content.assign_template(brief_data,'fixed')==content.assign_template(brief_data,'fixed')


def test_unapproved_ai_substitution_cannot_change_claims(brief_data):
 with pytest.raises(ValueError,match='Unapproved'):content.render(brief_data,'AEO_READINESS',generation={'subject':'Your business is invisible in ChatGPT','opening':'Guaranteed rankings'})

@pytest.mark.parametrize('zone,hour,expected',[('America/New_York',14,True),('Europe/London',14,True),('Australia/Sydney',14,False),('America/New_York',13,False)])
def test_recipient_local_windows_include_dst(zone,hour,expected):
 assert in_window(datetime(2026,11,2,hour,45,tzinfo=timezone.utc),zone)==expected


def test_additive_setup_idempotent_no_activation_and_no_catalog(db):
 service.setup(db,'owner');service.setup(db,'owner')
 assert db.execute('SELECT COUNT(*) FROM experiments').fetchone()[0]==1
 assert db.execute('SELECT COUNT(*) FROM experiment_segments').fetchone()[0]==25
 assert db.execute('SELECT COUNT(*) FROM experiment_sources').fetchone()[0]==50
 assert service.get(db)['status']=='SETUP'
 assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 from app.experiments.catalog import snapshot
 assert snapshot(db)=={'mode':'BRIEF_ONLY','catalog_attached':False}
 with pytest.raises(Exception):service.activate(db,'owner')

@pytest.mark.parametrize('template',['AEO_READINESS','CYBER_AUDIT','AEO_CYBER'])
def test_quick_brief_three_pages_evidence_and_clickable_links(brief_data,template,tmp_path):
 from app.experiments.brief import render_pdf,validate
 brief_data['experiment']['template_id']=template
 path=render_pdf(brief_data,tmp_path/(template+'.pdf'));assert validate(path.read_bytes())==3
 from pypdf import PdfReader
 pages=PdfReader(path).pages;text='\n'.join(p.extract_text() for p in pages)
 assert 'Not assessed' not in text and 'Digital Opportunity' in text and 'What We Found' in text
 assert sum(len(p.get('/Annots',[])) for p in pages)>=3


def test_full_report_generator_remains_eight_pages(brief_data,tmp_path):
 from app.reports.pdf import render_pdf
 from pypdf import PdfReader
 # Full report uses its existing data shape/renderer, independent of experiment metadata.
 path=render_pdf(brief_data,tmp_path/'full.pdf');assert len(PdfReader(path).pages)==8

@pytest.mark.parametrize('text,expected',[('Yes please, send the scope','POSITIVE'),('How long does this take?','QUESTION'),('Not now, next quarter','NOT_NOW'),('No thanks','NEGATIVE'),('Please unsubscribe','UNSUBSCRIBE'),('Out of office until Monday','OUT_OF_OFFICE'),('Thank you','UNKNOWN')])
def test_reply_classification_and_no_autoreply(text,expected):assert service.classify(text)==expected


def experiment_member(db,brief_data,monkeypatch,*,controlled=False,n=911):
 from campaign_fixtures import campaign,lead
 service.setup(db,'owner');cid=campaign(db);b,pid=lead(db,cid,n)
 data={**brief_data,'business':{**brief_data['business'],'name':b.name,'website':b.website,'email':b.public_email}}
 monkeypatch.setattr('app.reports.data.client_snapshot',lambda *args:data.copy())
 monkeypatch.setattr('app.reports.service.client_snapshot',lambda *args:data.copy())
 segment=dict(db.execute('SELECT * FROM experiment_segments ORDER BY day,city LIMIT 1').fetchone())
 assert service.admit(db,service.EXPERIMENT_ID,segment,'OVERTURE',cid,controlled=controlled)==1
 m=dict(db.execute('SELECT * FROM experiment_members WHERE prospect_id=?',(pid,)).fetchone())
 return m,data,segment


def test_archived_experiment_cannot_create_new_outreach_even_when_internal_reads_enabled(db,brief_data,monkeypatch):
 monkeypatch.setattr('app.platform.modules.legacy_enabled',lambda:True)
 from app.experiments import runtime
 from fastapi import HTTPException
 m,_,_=experiment_member(db,brief_data,monkeypatch,controlled=True)
 before=db.execute('SELECT COUNT(*) FROM experiment_members').fetchone()[0]
 with pytest.raises(HTTPException) as denied:runtime.ensure_run(db,m['experiment_id'],m['campaign_id'],'owner')
 assert denied.value.status_code==409
 assert db.execute('SELECT COUNT(*) FROM experiment_members').fetchone()[0]==before
 for table in ('email_messages','client_reports','automation_email_queue'):assert db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_experiment_dedupe_suppression_and_allocation_caps(db,brief_data,monkeypatch):
 from campaign_fixtures import lead
 m,data,segment=experiment_member(db,brief_data,monkeypatch)
 assert service.admit(db,m['experiment_id'],segment,'OVERTURE',m['campaign_id'])==0
 _,pid=lead(db,m['campaign_id'],912);db.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT' WHERE id=?",(pid,))
 assert service.admit(db,m['experiment_id'],segment,'OVERTURE',m['campaign_id'])==0
 assert service.allocation_remaining(db,m['experiment_id'],segment,'OVERTURE')==49
 db.execute("UPDATE experiment_sources SET target=1 WHERE segment_id=? AND source_type='OVERTURE'",(segment['id'],))
 assert service.allocation_remaining(db,m['experiment_id'],segment,'OVERTURE')==0


def test_date_source_schedules_and_bounded_shortfall(db):
 from app.experiments.runtime import create_schedules,reconcile_allocations
 service.setup(db,'owner');create_schedules(db,service.EXPERIMENT_ID,'owner');create_schedules(db,service.EXPERIMENT_ID,'owner')
 rows=db.execute('SELECT * FROM automation_schedules').fetchall();assert len(rows)==50
 assert Counter(json.loads(r['configuration_json'])['scan_source'] for r in rows)=={'OVERTURE':25,'FIRECRAWL':25}
 assert Counter(json.loads(r['configuration_json'])['experiment_day'] for r in rows)=={x:10 for x in range(1,6)}
 first=db.execute('SELECT id FROM experiment_segments ORDER BY day,city LIMIT 1').fetchone()[0]
 db.execute("UPDATE experiment_sources SET status='FAILED' WHERE segment_id=?",(first,));reconcile_allocations(db,service.EXPERIMENT_ID)
 assert db.execute('SELECT COUNT(*) FROM experiment_sources').fetchone()[0]==50
 s=db.execute('SELECT * FROM experiment_segments WHERE id=?',(first,)).fetchone();assert s['status']=='SHORTFALL' and json.loads(s['actual_source_mix'])=={'OVERTURE':0,'FIRECRAWL':0}


def test_reply_attribution_manual_correction_no_auto_reply_and_quoted_text(db,brief_data,monkeypatch):
 m,data,_=experiment_member(db,brief_data,monkeypatch)
 assert service.classify('How much would this cost?\n\nOn Monday, PlaneByte wrote:\nPlease unsubscribe')=='QUESTION'
 service.reply(db,m['id'],'POSITIVE','owner',manual=True)
 row=db.execute('SELECT * FROM experiment_members WHERE id=?',(m['id'],)).fetchone();assert row['conversion_status']=='POSITIVE_REPLY' and row['reply_disposition']=='POSITIVE'
 assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 from app.experiments.analytics import dashboard
 result=dashboard(db);assert result['totals']['sent']==0 and result['totals']['positive_replies']==0
 assert all(x['best_source'] is None for x in result['daily'])


def test_archived_experiment_copy_generation_is_blocked_without_provider_or_smtp(db,brief_data,monkeypatch):
 monkeypatch.setattr('app.platform.modules.legacy_enabled',lambda:True)
 from app.experiments import runtime
 from fastapi import HTTPException
 m,_,_=experiment_member(db,brief_data,monkeypatch)
 with pytest.raises(HTTPException) as denied:asyncio.run(runtime.prepare_copies(db,service.get(db),force_flush=True))
 assert denied.value.status_code==409
 assert db.execute('SELECT copy_attempts FROM experiment_members WHERE id=?',(m['id'],)).fetchone()[0]==0
 assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_provider_allowance_counts_other_account_traffic_and_never_uses_stale_quota(db):
 from app.mail.config import MailSettings
 from datetime import timedelta
 service.setup(db,'owner');at=datetime.now(timezone.utc)
 config=service.get(db)['configuration'];config.update(provider_preflight_at=at.isoformat(),provider_capacity_verified=True,untracked_sent_at=[at.isoformat()]*5)
 db.execute('UPDATE experiments SET configuration_json=?',(json.dumps(config),))
 settings=MailSettings(_env_file=None,EMAIL_PROVIDER='gmail',MAIL_FROM_ADDRESS='planebyte@gmail.com',MAX_EMAILS_PER_DAY=500,MAX_EMAILS_PER_HOUR=50)
 current=service.capacity(db,settings=settings,at=at);assert current['remaining_allowance']==495 and current['account_wide_count_fresh']
 assert not service.capacity(db,settings=settings,at=at+timedelta(hours=2))['account_wide_count_fresh']
 # The personal Gmail ceiling cannot be raised by a workspace target.
 assert current['daily_capacity_ceiling']==500


def test_successful_child_retry_closes_automatic_review_without_duplicate_scan(db,monkeypatch):
 from app.workflows import service as workflows
 from app.api.routes.workflows import Run
 from campaign_fixtures import lead
 from app.mail.config import MailSettings
 db.execute('UPDATE automation_controls SET scan_paused=0')
 rid=workflows.create(db,Run(kind='SCAN',scan_source='OVERTURE',target=1,countries=['United Kingdom'],cities=['London'],verticals=['hospitality']).model_dump(),current().actor)['id'];workflows.start(db,rid)
 b,_=lead(db,rid,9981);db.execute("UPDATE workflow_runs SET scan_run_id=?,status='NEEDS_REVIEW',error='Scan interrupted. Review and resume the saved run.' WHERE id=?",(b.run_id,rid));before=db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]
 monkeypatch.setattr(workflows,'mail_settings',lambda:MailSettings(_env_file=None,AUTO_SCAN_ENABLED=False,AUTO_EMAIL_ENABLED=False,EMAIL_SENDING_ENABLED=False));asyncio.run(workflows.dispatch(db))
 assert workflows.row(db,rid)['status']=='COMPLETED'
 assert db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==before and db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_source_resource_counts_use_actual_request_ledger_not_missing_summary(db):
 from app.acquisition import service as acquisition
 from app.experiments.analytics import dashboard
 from app.database.prospects import now
 service.setup(db,'owner');job=acquisition.create_job(db,'FIRECRAWL','owner','resource-fixture',{},{});db.execute("UPDATE acquisition_jobs SET counts_json=? WHERE id=?",(json.dumps({'businesses_found':5}),job['id']))
 source=db.execute("SELECT id FROM experiment_sources WHERE source_type='FIRECRAWL' LIMIT 1").fetchone()[0];db.execute('UPDATE experiment_sources SET acquisition_job_id=? WHERE id=?',(job['id'],source))
 for n,kind in enumerate(['search','search','search','scrape','scrape']):db.execute("INSERT INTO acquisition_requests(job_id,request_key,kind,status,created_at) VALUES(?,?,?,'COMPLETED',?)",(job['id'],str(n),kind,now()))
 result=dashboard(db);fire=next(r for r in result['sources'] if r['acquisition_source']=='FIRECRAWL')
 assert fire['discovered']==5 and fire['resource_usage']['searches']==3 and fire['resource_usage']['scraped_pages']==2
 assert result['segments'][0].get('provider_credits_used') is None
