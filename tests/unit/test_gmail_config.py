"""Offline configuration and transport checks; no mailbox connection."""
from unittest.mock import Mock
import pytest
from app.mail.config import MailSettings
from app.mail.providers import GmailEmailProvider


def gmail(**overrides):
    values=dict(EMAIL_PROVIDER='gmail', GMAIL_APP_PASSWORD='offline-fixture',
                GMAIL_USERNAME='controlled@example.com', MAIL_FROM_ADDRESS='controlled@example.com')
    values.update(overrides)
    return MailSettings(_env_file=None, **values)


def test_gmail_uses_own_credentials_without_legacy_mail_password():
    settings=gmail(MAIL_PASSWORD='legacy-fixture')
    assert settings.password.get_secret_value()=='offline-fixture'
    assert settings.username=='controlled@example.com'
    assert settings.smtp_host=='smtp.gmail.com'
    assert settings.imap_host=='imap.gmail.com'
    assert 'offline-fixture' not in repr(settings)
    assert 'password' not in settings.model_dump()
    assert 'gmail_password' not in settings.model_dump()


@pytest.mark.parametrize('sending,automatic,expected',[(False,False,False),(False,True,False),(True,False,False),(True,True,True)])
def test_both_switches_required(sending,automatic,expected):
    assert gmail(EMAIL_SENDING_ENABLED=sending,AUTO_EMAIL_ENABLED=automatic).automatic_sending_enabled is expected


def test_gmail_health_does_not_send():
    provider=GmailEmailProvider(gmail());smtp=Mock();imap=Mock()
    smtp.noop.return_value=(250,b'OK');imap.select.return_value=('OK',[])
    provider.smtp=Mock(return_value=smtp);provider.imap=Mock(return_value=imap)
    assert provider.health_check()=={'smtp':'READY','imap':'READY'}
    smtp.send_message.assert_not_called()


@pytest.mark.parametrize('overrides',[{'GMAIL_SMTP_SECURE':False},{'GMAIL_IMAP_HOST':'localhost'},{'GMAIL_APP_PASSWORD':''},{'MAIL_FROM_ADDRESS':'other@example.com'}])
def test_gmail_rejects_unsafe_configuration(overrides):
    with pytest.raises(ValueError):GmailEmailProvider(gmail(**overrides))


def test_gmail_reply_requires_trusted_google_authentication_results():
    from app.mail.service import authenticated_reply
    incoming={'from':'Controlled <controlled@example.com>', 'authentication':'mx.google.com; dmarc=pass header.from=example.com'}
    assert authenticated_reply(incoming)
    assert not authenticated_reply({**incoming,'authentication':'attacker.example; dmarc=pass header.from=example.com'})
    assert not authenticated_reply({**incoming,'authentication':'mx.google.com; dmarc=fail header.from=example.com'})
