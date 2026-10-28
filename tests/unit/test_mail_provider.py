"""Offline tests for the actual Hostinger transport; never connect or send mail."""
from datetime import datetime, timezone
from email.message import EmailMessage
from unittest.mock import Mock

import pytest

from app.mail.config import MailSettings
from app.mail.providers import HostingerEmailProvider


def transport():
    return HostingerEmailProvider(MailSettings(
        _env_file=None, MAIL_PASSWORD='offline-fixture',
        MAIL_SMTP_HOST='smtp.hostinger.com', MAIL_SMTP_PORT=465,
        MAIL_SMTP_SECURE=True, MAIL_IMAP_HOST='imap.hostinger.com',
        MAIL_IMAP_PORT=993, MAIL_IMAP_SECURE=True,
    ))


@pytest.mark.parametrize('smtp_code,imap_status,expected', [
    (250, 'OK', {'smtp': 'READY', 'imap': 'READY'}),
    (421, 'NO', {'smtp': 'UNAVAILABLE', 'imap': 'UNAVAILABLE'}),
])
def test_health_requires_successful_protocol_responses(smtp_code, imap_status, expected):
    provider=transport(); smtp=Mock(); imap=Mock()
    smtp.noop.return_value=(smtp_code, b'health')
    imap.select.return_value=(imap_status, [b'0'])
    provider.smtp=Mock(return_value=smtp); provider.imap=Mock(return_value=imap)
    assert provider.health_check()==expected
    smtp.send_message.assert_not_called()
    imap.select.assert_called_once_with('INBOX', readonly=True)
    smtp.quit.assert_called_once(); imap.logout.assert_called_once()


def test_sync_rejects_failed_inbox_selection_without_searching():
    provider=transport(); imap=Mock(); imap.select.return_value=('NO', [b'unavailable'])
    provider.imap=Mock(return_value=imap)
    with pytest.raises(RuntimeError, match='IMAP_INBOX_UNAVAILABLE'):
        provider.sync_messages({'<outbound@example.com>'}, {'last_uid': 10})
    imap.uid.assert_not_called(); imap.logout.assert_called_once()


def test_sync_resets_changed_uidvalidity_and_only_loads_tracked_bodies():
    provider=transport(); imap=Mock(); provider.imap=Mock(return_value=imap)
    imap.select.return_value=('OK', [b'2'])
    imap.response.return_value=('UIDVALIDITY', [b'new-validity'])
    message=EmailMessage()
    for key,value in {
        'Message-ID':'<reply@example.com>', 'From':'controlled@example.com',
        'To':'rajendra@planebyte.com', 'Subject':'Re: controlled review',
        'References':'<outbound@example.com>',
        'Date':datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000'),
    }.items():message[key]=value
    message.set_content('<p>Thanks</p><script>bad()</script><img src="https://example.com/pixel">', subtype='html')
    raw=message.as_bytes()
    unrelated=b'Message-ID: <unrelated@example.com>\r\nReferences: <other@example.com>\r\n\r\n'
    def uid(command,*args):
        if command=='search':return 'OK',[b'1 2']
        if args[0]=='1':return 'OK',[(b'1 (RFC822.SIZE 100)',unrelated)]
        if args[1]=='(BODY.PEEK[])':return 'OK',[(b'2',raw)]
        return 'OK',[(b'2 (RFC822.SIZE '+str(len(raw)).encode()+b')',raw.split(b'\n\n')[0]+b'\n\n')]
    imap.uid.side_effect=uid
    messages,cursor=provider.sync_messages({'<outbound@example.com>'}, {'last_uid':99, 'uidvalidity':'old-validity'})
    assert cursor=={'last_uid':2, 'uidvalidity':'new-validity'}
    assert len(messages)==1 and messages[0]['body_text']=='Thanks'
    assert not any(call.args==('fetch','1','(BODY.PEEK[])') for call in imap.uid.call_args_list)
    assert all('BODY.PEEK' in call.args[2] for call in imap.uid.call_args_list if call.args[0]=='fetch')
    imap.logout.assert_called_once()
