import asyncio,json,uuid
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_automation import db
from test_acquisition_sources import INTENT
from app.api.routes.workflows import Run
from app.workflows import service as workflow
from app.acquisition import scheduling,service
from app.mail.config import MailSettings
from app.database.prospects import now


def start(c,monkeypatch):
 monkeypatch.setattr(workflow,'mail_settings',lambda:MailSettings(_env_file=None,AUTO_SCAN_ENABLED=True))
 c.execute('UPDATE automation_controls SET scan_paused=0')
 config=Run(kind='COMBINED',scan_source='FIRECRAWL',target=5,ai_prompt='Find 5 dentists in Bristol',firecrawl_intent=INTENT,firecrawl_reviewed=True,email_all_eligible=True).model_dump()
 r=workflow.create(c,config,'owner');workflow.start(c,r['id']);return workflow.row(c,r['id'])


def test_firecrawl_schedule_dispatches_only_source_job_and_preserves_campaign(db,monkeypatch):
 r=start(db,monkeypatch);launch=AsyncMock();maps=AsyncMock(side_effect=AssertionError('Firecrawl must not invoke Maps'))
 monkeypatch.setattr(scheduling,'require',lambda *a:None);monkeypatch.setattr(scheduling,'launch',launch);monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',maps)
 asyncio.run(workflow.advance_scan(db,r['id']));asyncio.run(workflow.advance_scan(db,r['id']))
 assert launch.await_count==1 and maps.await_count==0
 j=db.execute('SELECT * FROM acquisition_jobs').fetchone();assert j['source_type']=='FIRECRAWL' and j['campaign_id']==r['id']
 assert json.loads(j['configuration_json'])['intent']['targetQualifiedLeads']==5
 assert db.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0
 service.refresh_counts(db,j['id'],{'qualified':3,'shortfall':2})
 # Counts derive from canonical rows. Use recorded source completion fixture for the adapter boundary.
 db.execute("UPDATE acquisition_jobs SET status='DEGRADED',counts_json=? WHERE id=?",(json.dumps({'qualified':3,'shortfall':2}),j['id']))
 asyncio.run(workflow.advance_scan(db,r['id']))
 updated=workflow.row(db,r['id']);assert updated['status']=='COMPLETED' and updated['result_count']==3 and 'shortfall' in updated['error']
 assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_disabled_firecrawl_never_falls_back_to_maps(db,monkeypatch):
 r=start(db,monkeypatch)
 def disabled(*a):raise HTTPException(503,'disabled')
 monkeypatch.setattr(scheduling,'require',disabled)
 maps=AsyncMock(side_effect=AssertionError('No silent fallback'));monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',maps)
 asyncio.run(workflow.advance_scan(db,r['id']))
 assert workflow.row(db,r['id'])['status']=='NEEDS_REVIEW' and not maps.called
 assert db.execute('SELECT COUNT(*) FROM acquisition_jobs').fetchone()[0]==0


def test_source_pause_resume_preserves_checkpoint_and_waits_for_live_lease(db,monkeypatch):
 r=start(db,monkeypatch);launch=AsyncMock();monkeypatch.setattr(scheduling,'launch',launch);monkeypatch.setattr(scheduling,'require',lambda *a:None)
 asyncio.run(workflow.advance_scan(db,r['id']));j=db.execute('SELECT * FROM acquisition_jobs').fetchone()
 db.execute('UPDATE acquisition_jobs SET cursor=20 WHERE id=?',(j['id'],))
 asyncio.run(scheduling.control(db,r,'pause'))
 assert service.job(db,j['id'])['status']=='PAUSED'
 r=workflow.row(db,r['id']);db.execute('UPDATE acquisition_jobs SET lease_owner=?,lease_until=? WHERE id=?',('old-worker','2099-01-01T00:00:00+00:00',j['id']))
 with pytest.raises(HTTPException,match='409'):asyncio.run(scheduling.control(db,r,'resume'))
 db.execute('UPDATE acquisition_jobs SET lease_owner=NULL,lease_until=NULL WHERE id=?',(j['id'],))
 asyncio.run(scheduling.control(db,r,'resume'))
 assert service.job(db,j['id'])['cursor']==20 and service.job(db,j['id'])['status']=='QUEUED' and launch.await_count==2


def test_switching_maps_draft_to_firecrawl_uses_reviewed_geography():
 r=Run(kind='SCAN',scan_source='FIRECRAWL',target=5,ai_prompt='Find 5 dentists in Bristol',firecrawl_intent=INTENT,firecrawl_reviewed=True,locations=[{'city':'Seattle','region':'Washington','country':'United States','country_code':'US','latitude':47.6062,'longitude':-122.3321,'label':'Seattle'}])
 assert r.countries==['United Kingdom'] and r.cities==['Bristol'] and r.locations==[]
