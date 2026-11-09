import json
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from test_automation import db
from campaign_fixtures import campaign,lead
from app.api.permissions import authorize
from app.workflows.duplicates import merge
from app.workflows import service
from app.api.routes.workflows import Run
from app.workflows.campaigns import audience,batch_data,campaign_summary

def test_owner_pause_cannot_be_cleared_by_start(db):
    run=service.create(db,Run(kind='SCAN').model_dump(),'owner')
    with pytest.raises(HTTPException) as ex:service.start(db,run['id'])
    assert ex.value.status_code==409
    assert db.execute('SELECT scan_paused,email_paused FROM automation_controls').fetchone()[0]==1
    db.execute('UPDATE automation_controls SET scan_paused=0')
    assert service.start(db,run['id'])['status']=='RUNNING'
    assert db.execute('SELECT email_paused FROM automation_controls').fetchone()[0]==1

def test_roles_enforce_owner_actions_and_nested_recontact(db,monkeypatch):
    from app.platform.context import organization
    for member,role in [('owner@company.example','OWNER'),('operator@company.example','MEMBER'),('viewer@company.example','VIEWER')]:
        db.execute('INSERT INTO users(id,email,display_name) VALUES(?,?,?)',(member,member,member))
        db.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) VALUES(?,?,?,?,'ACTIVE','fixture','fixture')",(member,organization(),member,role))
    monkeypatch.setattr('app.api.permissions.get_settings',lambda:SimpleNamespace(allowed_emails=['owner@company.example','operator@company.example','viewer@company.example'],app_env='production'))
    db.execute("INSERT INTO account_roles VALUES('operator@company.example','OPERATOR','now','owner')")
    assert authorize(db,'viewer@company.example','GET','/api/operations/campaigns',{})=='VIEWER'
    for email,path,body in [('viewer@company.example','/api/workflow/runs',{}),('operator@company.example','/api/automation/controls',{}),('operator@company.example','/api/workflow/schedules',{'configuration':{'confirm_recontact':True}}),('operator@company.example','/api/deletions/campaign/id',{})]:
        with pytest.raises(HTTPException) as ex:authorize(db,email,'POST',path,body)
        assert ex.value.status_code==403
    assert authorize(db,'owner@company.example','PUT','/api/automation/controls',{})=='OWNER'

def test_explicit_merge_preserves_related_evidence_and_suppression(db):
    a=campaign(db,'First');b=campaign(db,'Second');first,source=lead(db,a,11);second,target=lead(db,b,12)
    db.execute("INSERT INTO prospect_notes(id,prospect_id,body,created_by,created_at,updated_at) VALUES('note',?,'Original note','owner','2026','2026')",(source,))
    db.execute("UPDATE prospects SET lead_status='DO_NOT_CONTACT' WHERE id=?",(source,))
    before=db.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]
    from app.platform.context import current
    result=merge(db,source,target,current().actor)
    assert result['merged'] and not result['automatic_sending_resumed']
    assert db.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==before
    assert db.execute('SELECT prospect_id FROM prospect_notes').fetchone()[0]==target
    assert db.execute('SELECT lead_status FROM prospects WHERE id=?',(target,)).fetchone()[0]=='DO_NOT_CONTACT'
    archived=json.loads(db.execute('SELECT archived_json FROM duplicate_resolutions').fetchone()[0])
    assert archived['source']['id']==source
    assert archived['related']['prospect_notes'][0]['body']=='Original note'
    assert db.execute('PRAGMA foreign_key_check').fetchall()==[]

def test_campaign_page_batch_uses_same_accounting_and_bounded_queries(db):
    cids=[campaign(db,'Campaign '+str(n)) for n in range(5)]
    for n,cid in enumerate(cids):lead(db,cid,n+100)
    queries=[];db.set_trace_callback(queries.append)
    batch=batch_data(db,cids)
    rows=[campaign_summary(db,cid,_batch=batch) for cid in cids]
    reads=sum(q.lstrip().upper().startswith('SELECT') for q in queries)
    db.set_trace_callback(None)
    assert reads<=13 # Two constant registry reads; no per-lead or per-campaign lookups.
    assert [r['qualified'] for r in rows]==[1]*5
    for cid,row in zip(cids,rows):
        direct=audience(db,cid)
        assert row['accounting']==direct['accounting']
        assert row['total_accounted']==direct['total_accounted']==1
