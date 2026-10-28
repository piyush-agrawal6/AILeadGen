import json,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,now
from app.database.phase4_schema import STATUSES
from app.sales.service import schedule,suppressed,dossier,member
from app.mail import service
from app.mail.config import MailSettings
from app.mail.providers import SendFailed,SendUncertain
from app.mail.templates import seed,render

@pytest.fixture
def workspace(tmp_path,monkeypatch):
    path=tmp_path/'phase4.db';c=get_connection(path);run_migrations(c)
    run=PipelineRun(market='London',vertical='hospitality',target=5);PipelineRunRepository(c).create(run)
    b=Business(name='Test hotel',normalized_name='test hotel',vertical='hospitality',run_id=run.id,city='London',website='https://hotel.example',domain='hotel.example',public_email='public@hotel.example',address='1 Test Street');BusinessRepository(c).insert(b)
    repo=ProspectRepository(c);pid=repo.observe(b);repo.workflow(pid,'founder@example.com',lead_status='READY_TO_CONTACT');c.commit()
    config=MailSettings(_env_file=None,EMAIL_SEND_MODE='test',EMAIL_TEST_RECIPIENT='controlled@example.com',MAIL_PASSWORD='unit-fixture-only',MAIL_FROM_ADDRESS='rajendra@planebyte.com')
    monkeypatch.setattr(service,'mail_settings',lambda:config);monkeypatch.setattr(service,'get_connection',lambda **kw:get_connection(path))
    mock=Mock();mock.send_message.return_value='accepted';monkeypatch.setattr(service,'provider',lambda:mock)
    yield c,b,pid,config,mock
    c.close()

def payload(c,pid):
    body={'to_address':'public@hotel.example','subject':'A considered review','body_text':'A factual, reviewed message.','report_id':None,'thread_id':None,'followup_days':3,'override_declined':False}
    review=service.preview(c,pid,'founder@example.com',body)
    return {**body,'confirmation':'SEND','preview_token':review['preview_token'],'idempotency_key':str(uuid.uuid4())}

def test_all_statuses_activity_and_suppression_survive_rediscovery(workspace):
    c,b,pid,_,_=workspace;repo=ProspectRepository(c)
    for status in STATUSES:repo.workflow(pid,'founder@example.com',lead_status=status)
    assert suppressed(c,pid)
    duplicate=b.model_copy(update={'id':None});BusinessRepository(c).insert(duplicate);assert repo.observe(duplicate)==pid
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='DO_NOT_CONTACT'
    assert any(a['event_type']=='DO_NOT_CONTACT' for a in dossier(c,pid)['activities'])
    with pytest.raises(HTTPException):schedule(c,pid,'founder@example.com',now())

def test_followups_lists_and_notes(workspace):
    c,_,pid,_,_=workspace;due=(datetime.now(timezone.utc)+timedelta(days=3)).isoformat();fid=schedule(c,pid,'founder@example.com',due)
    c.execute('INSERT INTO lead_lists VALUES(?,?,?,?,?,?)',('test-list','Priority','','founder@example.com',now(),now()))
    member(c,pid,'test-list','founder@example.com');member(c,pid,'test-list','founder@example.com')
    ProspectRepository(c).add_note(pid,'founder@example.com','Acceptance fixture')
    data=dossier(c,pid);assert len(data['lists'])==1 and data['followups'][0]['id']==fid
    assert {'FOLLOW_UP_CREATED','LIST_ADDED','NOTE_ADDED'}<={a['event_type'] for a in data['activities']}
    member(c,pid,'test-list','founder@example.com',True);assert not dossier(c,pid)['lists']

def test_reviewed_test_send_is_redirected_persisted_and_idempotent(workspace):
    c,_,pid,_,mock=workspace;body=payload(c,pid);result=service.send(c,pid,'founder@example.com',body)
    assert result['status']=='SENT' and result['test_mode']
    sent=mock.send_message.call_args[0][0];assert sent['To']=='controlled@example.com' and '[TEST]' in sent['Subject']
    assert service.send(c,pid,'founder@example.com',body)['duplicate_prevented'];mock.send_message.assert_called_once()
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='CONTACTED'
    assert c.execute("SELECT COUNT(*) FROM followups WHERE status='OPEN'").fetchone()[0]==1

@pytest.mark.parametrize('field,value',[('to_address','bad\r\nBcc:x@example.com'),('subject','Subject\nBcc:x@example.com')])
def test_header_injection_is_rejected(workspace,field,value):
    c,_,pid,_,mock=workspace;body=payload(c,pid);body[field]=value
    with pytest.raises(HTTPException):service.send(c,pid,'founder@example.com',body)
    mock.send_message.assert_not_called()

def test_wrong_recipient_and_cross_prospect_attachment_rejected(workspace):
    c,_,pid,_,_=workspace;body=payload(c,pid);body['to_address']='guessed@hotel.example'
    with pytest.raises(HTTPException):service.preview(c,pid,'founder@example.com',body)
    body['to_address']='public@hotel.example';body['report_id']='not-this-prospects-pdf'
    with pytest.raises(HTTPException):service.preview(c,pid,'founder@example.com',body)

@pytest.mark.parametrize('error,status',[(SendFailed('rejected'),'FAILED'),(SendUncertain('uncertain'),'SENDING')])
def test_failure_does_not_change_status_or_duplicate_send(workspace,error,status):
    c,_,pid,_,mock=workspace;mock.send_message.side_effect=error;body=payload(c,pid)
    assert service.send(c,pid,'founder@example.com',body)['status']==status
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='READY_TO_CONTACT'
    service.send(c,pid,'founder@example.com',body);assert mock.send_message.call_count==1

def test_reply_matching_dedup_status_and_later_stage_preservation(workspace):
    c,_,pid,_,mock=workspace;sent=service.send(c,pid,'founder@example.com',payload(c,pid));outbound=c.execute('SELECT provider_message_id FROM email_messages WHERE id=?',(sent['id'],)).fetchone()[0]
    incoming={'message_id':'<reply-one@example.com>','from':'controlled@example.com','to':'rajendra@planebyte.com','subject':'Re: review','body_text':'Thanks for the review.','references':[outbound],'date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),'authentication':'mx1.hostinger.com; dkim=pass header.d=example.com'}
    mock.sync_messages.return_value=([incoming],{'last_uid':1,'uidvalidity':'test'})
    assert service.sync_mailbox()['received']==1
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='REPLIED'
    assert service.sync_mailbox()['received']==0
    c.execute("UPDATE prospects SET lead_status='MEETING' WHERE id=?",(pid,));c.commit();incoming['message_id']='<reply-two@example.com>'
    assert service.sync_mailbox()['received']==1
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='MEETING'
    incoming['from']='spoof@example.net';incoming['message_id']='<spoof@example.net>'
    assert service.sync_mailbox()['received']==0

def test_templates_are_deterministic_and_unknown_variables_fail(workspace):
    c,_,_,_,_=workspace;seed(c);assert c.execute('SELECT COUNT(*) FROM email_templates').fetchone()[0]>=11
    assert render('Hello {{business_name}} {{sender_name}}',{'business_name':'Hotel'})=='Hello Hotel'
    with pytest.raises(ValueError):render('{{credential}}',{})

def test_limits_are_reserved_before_smtp(workspace):
    c,_,pid,config,mock=workspace;config.max_hour=1
    service.send(c,pid,'founder@example.com',payload(c,pid))
    with pytest.raises(HTTPException) as error:service.send(c,pid,'founder@example.com',payload(c,pid))
    assert error.value.status_code==429 and mock.send_message.call_count==1

def test_authentication_alignment_and_receiver_are_required():
    assert not service.authenticated_reply({'from':'controlled@example.com','authentication':'evil.example; dkim=pass header.d=example.com'})
    assert not service.authenticated_reply({'from':'controlled@example.com','authentication':'mx1.hostinger.com; dkim=pass header.d=unrelated.example'})

def test_unverified_matched_message_cannot_change_status_or_reply_count(workspace):
    c,_,pid,_,mock=workspace;sent=service.send(c,pid,'founder@example.com',payload(c,pid));mid=sent['provider_message_id']
    mock.sync_messages.return_value=([{'message_id':'<unverified@example.com>','from':'controlled@example.com','to':'rajendra@planebyte.com','subject':'Re: review','body_text':'Unverified','references':[mid],'date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),'authentication':''}],{'last_uid':2,'uidvalidity':'test'})
    assert service.sync_mailbox()['received']==1
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='CONTACTED'
    assert c.execute('SELECT unread_replies FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0]==0


def test_actual_hostinger_receiver_domain_and_spoof_boundary():
    good={'from':'controlled@gmail.com','authentication':'fr-int-smtpin16.hostinger.io; dkim=pass header.d=gmail.com; dmarc=pass header.from=gmail.com'}
    assert service.authenticated_reply(good)
    assert not service.authenticated_reply({**good,'authentication':good['authentication'].replace('hostinger.io','hostinger.io.evil.example')})
    assert not service.authenticated_reply({**good,'authentication':good['authentication'].replace('hostinger.io','fakehostinger.io')})


def test_recheck_can_verify_stored_reply_once_without_duplicate_counts(workspace):
    c,_,pid,_,mock=workspace
    sent=service.send(c,pid,'founder@example.com',payload(c,pid))
    incoming={'message_id':'<recheck@example.com>','from':'controlled@example.com','to':'rajendra@planebyte.com','subject':'Re: review','body_text':'Genuine reply','references':[sent['provider_message_id']],'date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),'authentication':''}
    mock.sync_messages.return_value=([incoming],{'last_uid':5,'uidvalidity':'test'})
    assert service.sync_mailbox()['received']==1
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='CONTACTED'
    incoming['authentication']='fr-int-smtpin16.hostinger.io; dkim=pass header.d=example.com'
    mock.sync_messages.return_value=([incoming],{'last_uid':2,'uidvalidity':'test'})
    assert service.sync_mailbox(recheck=True)['received']==0
    assert c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]=='REPLIED'
    assert service.sync_mailbox(recheck=True)['received']==0
    assert c.execute('SELECT unread_replies FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0]==1
    assert c.execute("SELECT COUNT(*) FROM activities WHERE event_type='REPLY_DETECTED'").fetchone()[0]==1
    assert c.execute("SELECT last_uid FROM email_sync_state").fetchone()[0]==5
    assert len(c.execute("SELECT id FROM email_messages WHERE direction='INBOUND'").fetchall())==1
