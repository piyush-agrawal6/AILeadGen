"""Explicit opt-in: one Gmail send to the owner's controlled inbox, isolated DB.
Production environment flags/configuration are never edited.
"""
import os,json
from pathlib import Path
import pytest
from test_automation import db
from test_enabled_queue import queue
from app.mail import service as mail
from app.mail.config import MailSettings
from app.mail.providers import GmailEmailProvider
from app.automation import service as automation

@pytest.mark.skipif(os.environ.get('LEADENGINE_CONTROLLED_QUEUE_LIVE')!='1',reason='Explicit controlled live acceptance only')
def test_one_controlled_gmail_queue_send_and_duplicate_prevention(queue,monkeypatch):
    import certifi
    monkeypatch.setenv('SSL_CERT_FILE',certifi.where())
    c,_,_,_,_=queue
    base=MailSettings();assert not base.sending_enabled and not base.auto_email_enabled and not base.auto_scan_enabled
    config=base.model_copy(update={'mode':'test','test_recipient':'contact@planebyte.com','sending_enabled':True,'auto_email_enabled':True,'live_approved':False,'max_hour':10,'max_day':100,'daily_email_target':100})
    monkeypatch.setattr(automation,'mail_settings',lambda:config);monkeypatch.setattr(mail,'mail_settings',lambda:config)
    provider=GmailEmailProvider(config);calls=[]
    original=provider.send_message
    def send(message):
        assert message['To']=='contact@planebyte.com'
        assert len(calls)==0
        calls.append(1);return original(message)
    provider.send_message=send;monkeypatch.setattr(mail,'provider',lambda:provider)
    result=automation.outreach_tick(c);assert result['status']=='SENT'
    duplicate=automation.outreach_tick(c);assert duplicate['status']=='PAUSED_OR_WAITING'
    assert len(calls)==1
    record={'controlled_recipient':'contact@planebyte.com','queue_status':result['status'],'duplicate_tick':duplicate['status'],'smtp_calls':1,'database':'disposable SQLite','production_flags_changed':False,'prospect_addresses_used':False}
    Path('docs/controlled-live-queue-acceptance.json').write_text(json.dumps(record,indent=2))
