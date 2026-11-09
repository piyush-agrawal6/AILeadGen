"""Simulated Gmail DSNs only. SMTP transport is mocked by the sent fixture."""
from datetime import datetime, timezone
import pytest
from test_phase4 import workspace
from test_phase41 import sent
from app.mail import bounces,service
from app.automation.service import reconcile


def gmail_dsn(result,config,status='5.1.1',mid='<gmail-dsn@example.com>'):
    return {'kind':'dsn','message_id':mid,'references':[result['provider_message_id']],
            'recipients':[{'recipient':'public@hotel.example','action':'failed' if status.startswith('5') else 'delayed','status':status}],
            'to':config.from_address,'from':'Mail Delivery Subsystem <mailer-daemon@googlemail.com>',
            'date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),
            'authentication':'mx.google.com; dmarc=pass header.from=googlemail.com'}


def test_gmail_hard_bounce_is_idempotent_and_routes_to_manual_contact(sent):
    c,pid,config,transport,result=sent
    config.from_address='planebyte@gmail.com'
    c.execute("UPDATE email_messages SET test_mode=0,to_address='public@hotel.example',from_address=? WHERE id=?",(config.from_address,result['id']))
    c.execute("UPDATE businesses SET processing_status='QUALIFIED',phone='+12025550123' WHERE prospect_id=?",(pid,))
    incoming=gmail_dsn(result,config)
    assert bounces.process(c,incoming)==1
    assert bounces.process(c,incoming)==0
    assert service.recipients(c,pid)==[]
    assert c.execute('SELECT source,status FROM email_address_suppressions').fetchone()['status']=='INVALID'
    reconcile(c)
    assert c.execute('SELECT contact_state FROM master_lead_state WHERE prospect_id=?',(pid,)).fetchone()[0]=='MANUAL_CONTACT_REQUIRED'
    assert c.execute('SELECT phone FROM businesses WHERE prospect_id=?',(pid,)).fetchone()[0]=='+12025550123'
    assert c.execute("SELECT COUNT(*) FROM email_engagement_events WHERE event_type='BOUNCED_HARD'").fetchone()[0]==1
    transport.send_message.assert_called_once()  # Mocked original fixture send; no bounce retries.


@pytest.mark.parametrize('status',['4.2.2','5.2.2'])
def test_gmail_soft_bounces_remain_separate_and_apply_configured_threshold(sent,status):
    c,_,config,transport,result=sent
    c.execute("UPDATE email_messages SET test_mode=0,to_address='public@hotel.example' WHERE id=?",(result['id'],))
    for i in range(config.soft_bounce_threshold):
        assert bounces.process(c,gmail_dsn(result,config,status,f'<gmail-soft-{i}@example.com>'))==1
    row=c.execute('SELECT status,source,soft_bounce_count FROM email_address_suppressions').fetchone()
    assert row['status']=='TEMPORARILY_UNUSABLE' and row['source']!='HARD_BOUNCE'
    assert row['soft_bounce_count']==config.soft_bounce_threshold
    transport.send_message.assert_called_once()


def test_untrusted_gmail_dsn_cannot_suppress_address(sent):
    c,_,config,transport,result=sent
    c.execute("UPDATE email_messages SET test_mode=0,to_address='public@hotel.example' WHERE id=?",(result['id'],))
    incoming=gmail_dsn(result,config)
    incoming['authentication']='attacker.example; dmarc=pass header.from=googlemail.com'
    assert bounces.process(c,incoming)==1
    assert c.execute('SELECT COUNT(*) FROM email_address_suppressions').fetchone()[0]==0
    transport.send_message.assert_called_once()
