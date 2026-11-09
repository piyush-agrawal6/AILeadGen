"""Verify only the single redesigned owner email; no additional mail/reply actions."""
import os,sys,json,re,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi,requests
os.environ.update(DATABASE_BACKEND='postgres',SSL_CERT_FILE=certifi.where())
from email import policy
from email.parser import BytesParser
from app.mail.providers import GmailEmailProvider
from app.mail.config import mail_settings
from app.database.connection import db_session
state=Path('docs/final-content-acceptance.json');r=json.loads(state.read_text());assert r['status']=='SENT' and r['smtp_calls']==1
s=mail_settings();assert not(s.auto_scan_enabled or s.auto_email_enabled or s.sending_enabled)
p=GmailEmailProvider(s);client=p.imap()
try:
 assert client.select(p.sent_mailbox(client),readonly=True)[0]=='OK'
 matches=[]
 for _ in range(6):
  status,data=client.uid('search',None,'HEADER','Message-ID','"'+r['provider_message_id']+'"');assert status=='OK'
  matches=data[0].split() if data[0] else []
  if matches:break
  time.sleep(3)
 assert len(matches)==1
 status,data=client.uid('fetch',matches[0],'(BODY.PEEK[])');assert status=='OK'
 m=BytesParser(policy=policy.default).parsebytes(next(x[1] for x in data if isinstance(x,tuple)))
 assert str(m['To'])=='agrawaljoy1@gmail.com' and str(m['From'])=='PlaneByte <planebyte@gmail.com>'
 assert str(m['Subject'])==r['subject']
 plain=m.get_body(preferencelist=('plain',)).get_content();html=m.get_body(preferencelist=('html',)).get_content()
 assert 'TEST MODE' not in plain and 'acceptance' not in plain.lower()
 assert 'while researching' not in plain.lower() and 'viewport' not in plain.lower() and 'HTML' not in plain
 assert 'priority order and rough implementation scope' in plain
 if s.outreach_sender_name:assert s.outreach_sender_name+' | PlaneByte' in plain
 assert 'Homestay Hotels' in plain and 'Software Engineering · SEO · Security' in plain
 assert 'opt out here' in html.lower() and m['List-Unsubscribe'] and m['List-Unsubscribe-Post']
 attachments=list(m.iter_attachments());assert len(attachments)==1
 assert hashlib.sha256(attachments[0].get_payload(decode=True)).hexdigest()==r['attachment_sha256']
 r['gmail_sent_visible']=True;r['sent_mime_verified']=True
finally:client.logout()
urls={kind:url for url,kind in re.findall(r'(https://leads\.planebyte\.com/t/([ocu])/[A-Za-z0-9_-]{43}(?:\.gif)?)',html)}
assert set(urls)=={'o','c','u'}
headers={'User-Agent':'PlaneByte-Owner-QA-Scanner/1.0'}
tracking={}
for action in ('o','c','u'):
 response=requests.get(urls[action],headers=headers,allow_redirects=False,timeout=60);tracking[action]=response.status_code
 assert response.status_code==(302 if action=='c' else 200)
 if action=='c':assert requests.get(response.headers['Location'],headers=headers,timeout=30).status_code==200
r['tracking']={'open_http':tracking['o'],'click_http':tracking['c'],'unsubscribe_confirmation_http':tracking['u'],'unsubscribe_applied':False,'qa_signals_automated':True}
with db_session() as c:
 mid=r['result']['id'];row=c.execute('SELECT * FROM email_messages WHERE id=?',(mid,)).fetchone()
 assert row['message_type']=='OWNER_CONTROLLED_REDIRECT' and row['test_mode']==1 and row['to_address']=='agrawaljoy1@gmail.com'
 assert c.execute('SELECT last_contact_at FROM prospect_sales WHERE prospect_id=?',(row['prospect_id'],)).fetchone()[0] is None
 assert c.execute('SELECT COUNT(*) FROM email_messages WHERE idempotency_key=?',('final-content-owner-'+r['report']['id'],)).fetchone()[0]==1
 assert c.execute('SELECT COUNT(*) FROM automation_schedules WHERE enabled=1').fetchone()[0]==0
 r['timeline']=[x[0] for x in c.execute('SELECT event_type FROM email_engagement_events WHERE message_id=?',(mid,)).fetchall()]
 assert {'SMTP_ACCEPTED','OPEN_SIGNAL','CLICK_SIGNAL'}<=set(r['timeline'])
r.update(verified=True,real_prospect_contacted=False);state.write_text(json.dumps(r,indent=2))
print(json.dumps({k:r[k] for k in ('subject','pdf_pages','attachment_size_bytes','controlled_recipient','status','smtp_calls','gmail_sent_visible','sent_mime_verified','tracking','verified','real_prospect_contacted')}))
