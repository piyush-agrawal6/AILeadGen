"""Read-only Gmail Sent verification and controlled public tracking requests.
Never sends or retries email; unsubscribe GET only, preserving owner's inspection.
"""
import os,sys,json,re,time,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi,requests
os.environ.update(DATABASE_BACKEND='postgres',SSL_CERT_FILE=certifi.where())
from email import policy
from email.parser import BytesParser
from app.database.connection import db_session
from app.mail.config import mail_settings
from app.mail.providers import GmailEmailProvider
state=Path('docs/owner-clean-start-send.json');record=json.loads(state.read_text())
assert record['status']=='SENT'
s=mail_settings();assert not(s.sending_enabled or s.auto_scan_enabled or s.auto_email_enabled)
p=GmailEmailProvider(s);client=p.imap()
try:
 folder=p.sent_mailbox(client)
 assert client.select(folder,readonly=True)[0]=='OK'
 found=[]
 for attempt in range(6):
  status,data=client.uid('search',None,'HEADER','Message-ID','"'+record['provider_message_id']+'"')
  assert status=='OK';found=data[0].split() if data and data[0] else []
  if found:break
  time.sleep(3)
 assert len(found)==1,'Expected precisely one matching Gmail Sent message'
 status,data=client.uid('fetch',found[0],'(BODY.PEEK[])');assert status=='OK'
 wire=next(x[1] for x in data if isinstance(x,tuple))
 message=BytesParser(policy=policy.default).parsebytes(wire)
 assert str(message['To'])=='agrawaljoy1@gmail.com'
 assert str(message['From'])=='PlaneByte <planebyte@gmail.com>'
 assert str(message['Subject'])==record['subject']
 plain=message.get_body(preferencelist=('plain',)).get_content()
 html=message.get_body(preferencelist=('html',)).get_content()
 assert 'TEST MODE' not in plain and 'acceptance' not in plain.lower()
 assert record['business']['name'] in plain and 'planebyte@gmail.com' in plain
 assert 'Stop receiving emails' in html and message['List-Unsubscribe']
 attachments=list(message.iter_attachments());assert len(attachments)==1
 attachment=attachments[0];assert attachment.get_filename()==record['attachment_filename']
 assert hashlib.sha256(attachment.get_payload(decode=True)).hexdigest()==record['attachment_sha256']
 record['gmail_sent_visible']=True
 record['mime_verified']={'recipient':True,'sender':True,'production_subject':True,'production_html_text':True,'pdf_exact_bytes':True,'signature':True,'unsubscribe_footer':True}
finally:client.logout()
# Explicit automated signal; never misrepresent endpoint QA as a human open.
urls={kind:url for url,kind in re.findall(r'(https://leads\.planebyte\.com/t/([ocu])/[A-Za-z0-9_-]{43}(?:\.gif)?)',html)}
assert set(urls)=={'o','c','u'}
headers={'User-Agent':'PlaneByte-Owner-Controlled-QA-Scanner/1.0'}
opened=requests.get(urls['o'],headers=headers,timeout=60);assert opened.status_code==200 and opened.headers['content-type'].startswith('image/gif')
clicked=requests.get(urls['c'],headers=headers,timeout=60,allow_redirects=False)
assert clicked.status_code in (302,303,307) and clicked.headers['Location'].rstrip('/')=='https://planebyte.com'
landing=requests.get(clicked.headers['Location'],headers=headers,timeout=60);assert landing.status_code==200
optout=requests.get(urls['u'],headers=headers,timeout=60);assert optout.status_code==200
record['tracking']={'open_http':opened.status_code,'click_http':clicked.status_code,'click_destination_http':landing.status_code,'unsubscribe_confirmation_http':optout.status_code,'unsubscribe_applied':False,'qa_signals_automated':True}
with db_session() as c:
 row=c.execute('SELECT * FROM email_messages WHERE id=?',(record['result']['id'],)).fetchone()
 assert row['status']=='SENT' and row['to_address']=='agrawaljoy1@gmail.com'
 assert row['test_mode']==1 and row['message_type']=='OWNER_CONTROLLED_REDIRECT'
 assert row['intended_to']==record['intended_recipient']
 assert c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND'").fetchone()[0]==1
 assert c.execute('SELECT last_contact_at FROM prospect_sales WHERE prospect_id=?',(row['prospect_id'],)).fetchone()[0] is None
 events=[r[0] for r in c.execute('SELECT event_type FROM email_engagement_events WHERE message_id=?',(row['id'],)).fetchall()]
 assert {'SMTP_ACCEPTED','OPEN_SIGNAL','CLICK_SIGNAL'}<=set(events)
 record['tracking']['events']=sorted(set(events))
 record['verified']=True
state.write_text(json.dumps(record,indent=2))
print(json.dumps({k:record[k] for k in ('subject','business','recipient','attachment_filename','attachment_size_bytes','status','gmail_sent_visible','mime_verified','tracking','real_prospect_contacted','global_automation_enabled','verified')}))
