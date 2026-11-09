from unittest.mock import Mock
import pytest
from app.mail.providers import special_use_folder,GmailEmailProvider
from app.mail.config import MailSettings

@pytest.mark.parametrize('name',[b'"[Gmail]/Tous les messages"',b'"[Google Mail]/Gesendet"',b'"[Gmail]/&ZeVnLIqe-"',b'Archive'])
def test_special_use_uses_server_flag_not_english_name(name):
    client=Mock();client.list.return_value=('OK',[b'(\\HasNoChildren \\All) "/" '+name])
    assert special_use_folder(client,r'\All')==name.decode('ascii')


def test_sent_and_all_flags_are_not_interchangeable():
    client=Mock();client.list.return_value=('OK',[b'(\\Sent) "/" "Envoyes"',b'(\\All) "/" "Tous"'])
    assert special_use_folder(client,r'\Sent')=='"Envoyes"'
    assert special_use_folder(client,r'\All')=='"Tous"'


def test_list_literal_and_escaped_mailbox_names():
    client=Mock();client.list.return_value=('OK',[(b'(\\All) "/" {7}',b'A "box"')])
    assert special_use_folder(client,r'\All')=='"A \\"box\\""'

@pytest.mark.parametrize('rows',[[b'(\\All) "/" "evil\r\nSELECT other"'],[b'(\\All) "/" {99}'],[b'(\\Sent) "/" "All Mail"']])
def test_missing_or_unsafe_mailbox_fails_closed(rows):
    client=Mock();client.list.return_value=('OK',rows)
    with pytest.raises(RuntimeError):special_use_folder(client,r'\All')
