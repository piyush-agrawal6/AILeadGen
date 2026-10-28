"""All mail is mocked. Production mode here never contacts a real recipient."""
import hashlib,json,re
from datetime import datetime,timezone
from unittest.mock import Mock
from email.message import EmailMessage
from email.mime.message import MIMEMessage
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_phase4 import workspace,payload
from app.mail import tracking,bounces,service
from app.sales.service import suppressed
from app.database.prospects import ProspectRepository
from app.api.server import app
from app.api.dependencies import get_db

@pytest.fixture
def sent(workspace,monkeypatch):
    c,b,pid,config,transport=workspace
    monkeypatch.setattr(tracking,'mail_settings',lambda:config)
    monkeypatch.setattr(bounces,'mail_settings',lambda:config)
    body=payload(c,pid);body['body_text']='A review: https://planebyte.com/services and https://planebyte.com/contact'
    body['preview_token']=service.preview(c,pid,'founder@example.com',body)['preview_token']
    result=service.send(c,pid,'founder@example.com',body)
    yield c,pid,config,transport,result


def test_opaque_tokens_html_and_pdf_safe_render(sent):
    c,pid,config,mock,result=sent
    raw=mock.send_message.call_args[0][0]
    rich=raw.get_body(preferencelist=('html',)).get_content()
    links=re.findall(r'https://leads.planebyte.com/t/([ocu])/([A-Za-z0-9_-]{43})',rich)
    assert {a for a,_ in links}=={'o','c','u'}
    assert all(pid not in token and result['id'] not in token for _,token in links)
    assert all(c.execute('SELECT 1 FROM email_tracking_tokens WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone() for _,token in links)
    assert raw['List-Unsubscribe-Post']=='List-Unsubscribe=One-Click'
    assert 'javascript:' not in rich

@pytest.mark.parametrize('url',['javascript:alert(1)','data:text/html,x','file:///tmp/x','http://localhost/','http://127.0.0.1','http://10.0.0.1','http://[::1]/','http://169.254.169.254','https://user:password@planebyte.com','http://2130706433','http://0x7f000001','http://0177.0.0.1','http://foo.local','https://planebyte.com\\@127.0.0.1','https://planebyte.com\r\nX:bad'])
def test_private_and_unsafe_redirects_rejected(url):assert tracking.allowed_url(url) is None


def test_open_dedup_and_scanner_classification(sent):
    c,_,_,_,result=sent
    link=tracking.issue_token(c,result['id'],'o');token=link.rsplit('/',1)[1][:-4]
    row=tracking.lookup(c,token,'o');assert row
    for _ in range(3):tracking.public_signal(c,row,'GET','Mozilla/5.0')
    summary=tracking.message_summary(c,result['id']);assert summary['open_signal_count']==1
    assert c.execute("SELECT request_count FROM email_engagement_events WHERE event_type='OPEN_SIGNAL'").fetchone()[0]==3
    tracking.public_signal(c,row,'HEAD','Mozilla/5.0')
    assert tracking.classify('GET','GoogleImageProxy')[0]=='AUTOMATED'
    assert tracking.classify('GET','Mozilla/5.0','?1')[0]=='LIKELY_HUMAN'
    assert tracking.lookup(c,'invalid','o') is None
    assert tracking.lookup(c,token,'c') is None


def test_public_routes_stored_redirect_and_post_only_unsubscribe(sent):
    c,pid,_,_,result=sent
    click=tracking.issue_token(c,result['id'],'c','https://planebyte.com/services').rsplit('/',1)[1]
    stop=tracking.issue_token(c,result['id'],'u').rsplit('/',1)[1]
    # Test production suppression on a fixture, never a production prospect.
    c.execute('UPDATE email_messages SET test_mode=0 WHERE id=?',(result['id'],));c.commit()
    app.dependency_overrides[get_db]=lambda:c
    try:
        with TestClient(app) as client:
            response=client.get('/api/tracking/c/'+click+'?url=https://evil.example',follow_redirects=False)
            assert response.status_code==302 and response.headers['location']=='https://planebyte.com/services'
            assert client.get('/api/tracking/o/invalid.gif').content.startswith(b'GIF89a')
            assert client.get('/api/tracking/u/'+stop).status_code==200 and not suppressed(c,pid)
            assert client.post('/api/tracking/u/'+stop,content='not-confirmed').status_code==400
            assert client.post('/api/tracking/u/'+stop,content='confirm=stop').status_code==200
            assert suppressed(c,pid)
            assert c.execute('SELECT suppression_source FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0]=='RECIPIENT_UNSUBSCRIBE'
            assert client.post('/api/tracking/u/'+stop,content='List-Unsubscribe=One-Click').status_code==200
            assert c.execute("SELECT COUNT(*) FROM email_engagement_events WHERE event_type='UNSUBSCRIBED'").fetchone()[0]==1
            assert not c.execute("SELECT 1 FROM followups WHERE prospect_id=? AND status='OPEN'",(pid,)).fetchone()
    finally:app.dependency_overrides.clear()


def test_test_message_optout_cannot_suppress_real_prospect(sent):
    c,pid,_,_,result=sent
    token=tracking.issue_token(c,result['id'],'u').rsplit('/',1)[1]
    tracking.unsubscribe(c,tracking.lookup(c,token,'u'))
    assert not suppressed(c,pid)

@pytest.mark.parametrize('enabled,mode,approved,allowed',[(True,'test',False,True),(False,'test',False,False),(True,'test',True,False),(True,'production',True,True),(True,'production',False,False),(False,'production',True,False),(False,'production',False,False),(True,'live',True,False)])
def test_live_gate_and_actual_recipient(workspace,enabled,mode,approved,allowed):
    c,_,pid,config,mock=workspace;config.sending_enabled=enabled;config.mode=mode;config.live_approved=approved
    body={'to_address':'public@hotel.example','subject':'Review','body_text':'A reviewed message.'}
    if allowed:
        result=service.preview(c,pid,'founder@example.com',body)
        assert result['to_address']==('controlled@example.com' if mode=='test' else 'public@hotel.example')
    else:
        with pytest.raises(HTTPException):service.preview(c,pid,'founder@example.com',body)
    mock.send_message.assert_not_called()


def test_tracking_preferences_and_payload_are_review_bound(workspace):
    c,_,pid,_,mock=workspace;body=payload(c,pid)
    c.execute('UPDATE email_tracking_preferences SET track_opens=0')
    with pytest.raises(HTTPException):service.send(c,pid,'founder@example.com',body)
    mock.send_message.assert_not_called()


def test_production_send_requires_fresh_smtp_health(workspace):
    c,_,pid,config,mock=workspace;config.mode='production';config.live_approved=True
    body=payload(c,pid);mock.health_check.return_value={'smtp':'UNAVAILABLE','imap':'READY'}
    with pytest.raises(HTTPException):service.send(c,pid,'founder@example.com',body)
    mock.send_message.assert_not_called()
    assert c.execute("SELECT status FROM email_messages").fetchone()[0]=='FAILED'


def test_live_render_has_no_test_redirect_and_is_still_idempotent(workspace):
    c,_,pid,config,mock=workspace;config.mode='production';config.live_approved=True;mock.health_check.return_value={'smtp':'READY','imap':'READY'}
    body=payload(c,pid);result=service.send(c,pid,'founder@example.com',body)
    message=mock.send_message.call_args[0][0]
    assert message['To']=='public@hotel.example' and '[TEST]' not in message['Subject']
    assert 'TEST MODE' not in message.get_body(preferencelist=('plain',)).get_content()
    assert service.send(c,pid,'founder@example.com',body)['duplicate_prevented']
    mock.send_message.assert_called_once()


def dsn(result,status='5.1.1',recipient='controlled@example.com',mid='<dsn@example.com>'):
    return {'kind':'dsn','message_id':mid,'references':[result['provider_message_id']],'recipients':[{'recipient':recipient,'action':'failed' if status.startswith('5') else 'delayed','status':status}],'to':'rajendra@planebyte.com','from':'postmaster@example.com','date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),'authentication':'mx.hostinger.io; dkim=pass header.d=example.com'}


def test_hard_bounce_specific_address_suppression_and_dedup(sent):
    c,pid,_,_,result=sent
    c.execute('UPDATE email_messages SET test_mode=0,to_address=? WHERE id=?',('public@hotel.example',result['id']))
    incoming=dsn(result,recipient='public@hotel.example')
    assert bounces.process(c,incoming)==1 and bounces.process(c,incoming)==0
    assert 'public@hotel.example' not in service.recipients(c,pid)
    assert not suppressed(c,pid)
    assert c.execute('SELECT source FROM email_address_suppressions').fetchone()[0]=='HARD_BOUNCE'


def test_soft_bounce_threshold_and_wrong_message_rejection(sent):
    c,pid,_,_,result=sent
    c.execute('UPDATE email_messages SET test_mode=0,to_address=? WHERE id=?',('public@hotel.example',result['id']))
    wrong=dsn(result,recipient='someone@example.com');assert bounces.process(c,wrong)==0
    for i in range(3):assert bounces.process(c,dsn(result,status='4.2.2',recipient='public@hotel.example',mid=f'<dsn-{i}@example.com>'))==1
    assert c.execute('SELECT status FROM email_address_suppressions').fetchone()[0]=='TEMPORARILY_UNUSABLE'
    assert not suppressed(c,pid)


def test_unauthenticated_dsn_does_not_suppress(sent):
    c,pid,_,_,result=sent;c.execute('UPDATE email_messages SET test_mode=0 WHERE id=?',(result['id'],))
    incoming=dsn(result);incoming['authentication']='evil.example; dkim=pass header.d=example.com'
    assert bounces.process(c,incoming)==1
    assert c.execute('SELECT COUNT(*) FROM email_address_suppressions').fetchone()[0]==0


def test_structured_dsn_parsing_uses_recipient_status_not_subject(sent):
    c,_,_,mock,result=sent
    message=EmailMessage();message['Subject']='arbitrary text';message.set_type('multipart/report');message.set_param('report-type','delivery-status')
    status=EmailMessage();status.set_type('message/delivery-status')
    per_message=EmailMessage();per_message['Reporting-MTA']='dns; example.com'
    per_recipient=EmailMessage();per_recipient['Final-Recipient']='rfc822; controlled@example.com';per_recipient['Action']='failed';per_recipient['Status']='5.1.1'
    status.set_payload([per_message,per_recipient]);message.attach(status);message.attach(MIMEMessage(mock.send_message.call_args[0][0]))
    parsed=bounces.parse_dsn(message)
    assert result['provider_message_id'] in parsed['references']
    assert parsed['recipients'][0]['status']=='5.1.1'
    ordinary=EmailMessage();ordinary['Subject']='Mail Delivery Subsystem user unknown';ordinary.set_content('bounce')
    assert bounces.parse_dsn(ordinary) is None


def test_endpoint_budget_is_durable_and_no_ip_is_stored(sent):
    c,_,_,_,_=sent
    assert all(tracking.rate_allowed(c,'opaque','o') for _ in range(30))
    assert not tracking.rate_allowed(c,'opaque','o')
    columns={r[1] for r in c.execute('PRAGMA table_info(email_engagement_events)').fetchall()}
    assert 'ip_address' not in columns and 'user_agent' not in columns


def test_final_suppression_recheck_blocks_smtp(workspace,monkeypatch):
    c,_,pid,_,mock=workspace;body=payload(c,pid)
    # Initial preview passes, then suppression changes before SMTP reservation completes.
    monkeypatch.setattr(service,'suppressed',Mock(side_effect=[False,True]))
    with pytest.raises(HTTPException):service.send(c,pid,'founder@example.com',body)
    mock.send_message.assert_not_called()


def test_smtp_health_cannot_make_reviewed_recipient_stale(workspace):
    c,_,pid,config,mock=workspace;config.mode='production';config.live_approved=True
    body=payload(c,pid)
    def health():
        c.execute("UPDATE businesses SET public_email=NULL WHERE prospect_id=?",(pid,))
        return {'smtp':'READY','imap':'READY'}
    mock.health_check.side_effect=health
    with pytest.raises(HTTPException):service.send(c,pid,'founder@example.com',body)
    mock.send_message.assert_not_called()


def test_schema8_preserves_existing_phase4_mail_and_backfills_facts(tmp_path,monkeypatch):
    from app.database.connection import get_connection
    from app.database import migrations
    from app.database.models import Business,PipelineRun
    from app.database.repositories import BusinessRepository,PipelineRunRepository
    from app.database.prospects import now
    c=get_connection(tmp_path/'upgrade.db');all_migrations=migrations.MIGRATIONS
    with monkeypatch.context() as patch:
        patch.setattr(migrations,'MIGRATIONS',all_migrations[:7]);assert migrations.run_migrations(c)==7
    run=PipelineRun(market='London',vertical='hospitality',target=5);PipelineRunRepository(c).create(run)
    business=Business(name='Migration fixture',normalized_name='migration fixture',vertical='hospitality',run_id=run.id,public_email='public@example.com');BusinessRepository(c).insert(business);pid=ProspectRepository(c).observe(business)
    c.execute("INSERT INTO email_accounts(id,user_id,provider,email_address,display_name,status,created_at,updated_at) VALUES('account','founder@example.com','hostinger','rajendra@planebyte.com','PlaneByte','CONNECTED',?,?)",(now(),now()))
    c.execute("INSERT INTO email_threads VALUES('thread',?,'account','Retained subject',?,'OUTBOUND',?)",(pid,now(),now()))
    c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,created_at) VALUES('old-message',?,'account','thread','<old@example.com>','OUTBOUND','SENT','rajendra@planebyte.com','public@example.com','Retained subject','Retained body',?)",(pid,now()))
    old=dict(c.execute("SELECT * FROM email_messages WHERE id='old-message'").fetchone());c.commit()
    assert migrations.run_migrations(c)==1
    new=dict(c.execute("SELECT * FROM email_messages WHERE id='old-message'").fetchone())
    assert all(new[k]==v for k,v in old.items())
    assert c.execute("SELECT event_type FROM email_engagement_events WHERE message_id='old-message'").fetchone()[0]=='SMTP_ACCEPTED'
    assert migrations.run_migrations(c)==0
    c.close()
