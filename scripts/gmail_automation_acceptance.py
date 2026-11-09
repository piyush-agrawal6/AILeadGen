"""Explicit controlled mailbox probe. Never discovers or contacts prospects."""
import argparse,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi
os.environ.setdefault('SSL_CERT_FILE',certifi.where())
from email.message import EmailMessage
from email.utils import make_msgid,formatdate
from app.mail.providers import provider
from app.mail.config import mail_settings
p=argparse.ArgumentParser();p.add_argument('--send',action='store_true');a=p.parse_args()
path=Path('docs/gmail-automation-acceptance.json')
record=json.loads(path.read_text()) if path.exists() else {}
if record.get('message_id') and record.get('recipient')!='contact@planebyte.com':
    record={'superseded_acceptance':[record]}
record['recipient']='contact@planebyte.com'
s=mail_settings()
if s.provider!='gmail' or s.from_address!='planebyte@gmail.com':raise SystemExit('Unexpected acceptance sender')
transport=provider();health=transport.health_check();record.update(health=health)
if a.send and not record.get('message_id'):
    if health!={'smtp':'READY','imap':'READY'}:raise SystemExit('Mailbox health must pass first')
    message=EmailMessage();message['From']='PlaneByte <planebyte@gmail.com>';message['To']='contact@planebyte.com';message['Subject']='PlaneByte LeadEngine controlled Gmail acceptance';message['Message-ID']=make_msgid(domain='planebyte.com');message['Date']=formatdate(localtime=False)
    message.set_content('Controlled LeadEngine Gmail acceptance test. Please reply to this message with: LeadEngine acceptance reply. No prospect outreach is enabled.')
    # Persist intent before the network call to prevent an ambiguous attempt being repeated.
    record['message_id']=str(message['Message-ID']);record['send_status']='ATTEMPTING';path.write_text(json.dumps(record,indent=2))
    try:transport.send_message(message);record['send_status']='SMTP_ACCEPTED'
    except Exception:record['send_status']='REVIEW_REQUIRED'
if record.get('message_id'):
    client=transport.imap()
    try:
        status,_=client.select(transport.sent_mailbox(client),readonly=True)
        record['sent_folder']='READY' if status=='OK' else 'UNAVAILABLE'
        if status=='OK':
            status,data=client.uid('search',None,'HEADER','Message-ID','"'+record['message_id']+'"')
            record['sent_visible']=status=='OK' and bool(data[0])
    finally:client.logout()
if record.get('message_id'):
    from app.mail.service import authenticated_reply
    messages,_=transport.sync_messages({record['message_id']},{})
    record['verified_reply_seen']=record.get('verified_reply_seen',False) or any(record['message_id'] in item.get('references',[]) and authenticated_reply(item) for item in messages)
record['automatic_sending_enabled']=False
path.write_text(json.dumps(record,indent=2));print(json.dumps(record))
