from email.message import EmailMessage
from unittest.mock import Mock
import os,runpy,sys
from pathlib import Path
import pytest,dotenv
from app.config.settings import get_settings
from app.mail.config import MailSettings
from app.mail.providers import GmailEmailProvider,SendFailed


def test_local_transport_blocks_noncontrolled_recipient_before_smtp(monkeypatch):
    monkeypatch.setattr(get_settings(),'app_env','development');monkeypatch.setenv('HEYSOW_LOCAL_PREVIEW','true')
    config=MailSettings(_env_file=None,EMAIL_PROVIDER='gmail',GMAIL_USERNAME='planebyte@gmail.com',GMAIL_APP_PASSWORD='fixture-only',MAIL_FROM_ADDRESS='planebyte@gmail.com',EMAIL_SENDING_ENABLED=True,EMAIL_SEND_MODE='test',EMAIL_TEST_RECIPIENT='controlled@example.test')
    provider=GmailEmailProvider(config);provider.smtp=Mock();smtp=provider.smtp.return_value;smtp.send_message.return_value={}
    message=EmailMessage();message['To']='prospect@example.test';message['Message-ID']='<local@example.test>'
    with pytest.raises(SendFailed):provider.send_message(message)
    provider.smtp.assert_not_called()
    message.replace_header('To','controlled@example.test');message['Cc']='unapproved@example.test'
    assert provider.send_message(message)=='<local@example.test>'
    assert smtp.send_message.call_args.kwargs['to_addrs']==['controlled@example.test']


def test_mail_preview_optin_only_loads_secret_into_backend_and_forces_redirect(monkeypatch):
    script=Path(__file__).resolve().parents[2]/'scripts/local_preview.py';captured={}
    monkeypatch.setattr(dotenv,'dotenv_values',lambda path:{'GMAIL_APP_PASSWORD':'fixture-mail-secret','EMAIL_SEND_MODE':'production','EMAIL_LIVE_APPROVED':'true'})
    monkeypatch.setattr(sys,'argv',[str(script),'backend','--all-features','--mail-test-to','controlled@example.test']);monkeypatch.setattr(os,'chdir',lambda path:None)
    class Started(Exception):pass
    def launch(executable,args,env):captured.update(env);raise Started()
    monkeypatch.setattr(os,'execve',launch)
    with pytest.raises(Started):runpy.run_path(str(script),run_name='__main__')
    assert captured['EMAIL_SEND_MODE']=='test' and captured['EMAIL_TEST_RECIPIENT']=='controlled@example.test'
    assert captured['EMAIL_LIVE_APPROVED']=='false' and captured['EMAIL_SENDING_ENABLED']=='true'
    assert captured['GMAIL_APP_PASSWORD']=='fixture-mail-secret' and captured['SCAN_EXECUTOR']=='local'
    monkeypatch.setattr(sys,'argv',[str(script),'frontend','--all-features','--mail-test-to','controlled@example.test'])
    with pytest.raises(SystemExit):runpy.run_path(str(script),run_name='__main__')
