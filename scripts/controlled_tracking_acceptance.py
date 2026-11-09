"""One controlled Gmail transport send with real production tracking capabilities.
Global switches remain false. Record is test-mode, never a qualified prospect.
"""
import sys,os,json,uuid,re,argparse,ssl
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi,requests
os.environ['SSL_CERT_FILE']=certifi.where();os.environ['DATABASE_BACKEND']='postgres'
from email.message import EmailMessage
from email.utils import make_msgid,formatdate
from app.database.connection import db_session
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository
from app.database.prospects import ProspectRepository,now
from app.mail.config import mail_settings
from app.mail.providers import provider
from app.mail import service,tracking
p=argparse.ArgumentParser();p.add_argument('--send',action='store_true');a=p.parse_args()
path=Path('docs/controlled-production-tracking.json');record=json.loads(path.read_text()) if path.exists() else {}
s=mail_settings();assert not(s.sending_enabled or s.auto_email_enabled or s.auto_scan_enabled)
assert s.from_address=='planebyte@gmail.com' and s.provider=='gmail'
if a.send and not record.get('message_id'):
 transport=provider();assert transport.health_check()=={'smtp':'READY','imap':'READY'}
 mid=str(uuid.uuid4());thread=str(uuid.uuid4());wire=make_msgid(domain='planebyte.com')
 with db_session() as c:
  b=Business(name='PlaneByte — controlled tracking acceptance',normalized_name='planebyte controlled tracking acceptance',vertical='home_services',website='https://planebyte.com',domain='planebyte.com',public_email='contact@planebyte.com',processing_status='DISCOVERED')
  BusinessRepository(c).insert(b);pid=ProspectRepository(c).observe(b)
  # This owned test record is deliberately not qualified and never enters automation queue.
  service.account(c,'system')
  c.execute("INSERT INTO email_threads VALUES(?,?,?,?,?,'OUTBOUND',?)",(thread,pid,service.ACCOUNT,'Controlled tracking acceptance',now(),now()))
  c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,created_at,test_mode,idempotency_key) VALUES(?,?,?,?,?,'OUTBOUND','SENDING',?,?,'PlaneByte controlled tracking acceptance','Controlled acceptance',?,1,?)",(mid,pid,service.ACCOUNT,thread,wire,s.from_address,'contact@planebyte.com',now(),'controlled-tracking-'+mid))
  plain,html,optout=tracking.render_message(c,mid,'Controlled PlaneByte tracking acceptance. Please reply: Tracking acceptance reply.\nhttps://planebyte.com',True,True)
 record={'message_id':mid,'provider_message_id':wire,'prospect_id':pid,'thread_id':thread,'recipient':'contact@planebyte.com','send_status':'ATTEMPTING','test_mode':True,'qualified':False}
 path.write_text(json.dumps(record,indent=2))
 message=EmailMessage();message['From']='PlaneByte <planebyte@gmail.com>';message['To']='contact@planebyte.com';message['Subject']='PlaneByte controlled tracking acceptance';message['Message-ID']=wire;message['Date']=formatdate();message['List-Unsubscribe']='<'+optout+'>';message.set_content(plain);message.add_alternative(html,subtype='html')
 try:transport.send_message(message)
 except Exception:raise SystemExit('Controlled SMTP outcome requires review; do not retry')
 with db_session() as c:
  c.execute("UPDATE email_messages SET status='SENT',sent_at=? WHERE id=?",(now(),mid));tracking.event(c,mid,'SMTP_ACCEPTED')
 record['send_status']='SMTP_ACCEPTED';path.write_text(json.dumps(record,indent=2))
 # Capabilities are used now but never written to docs/logs.
 urls={kind:url for url,kind,token in re.findall(r'(https://leads\.planebyte\.com/t/([ocu])/([A-Za-z0-9_-]{43})(?:\.gif)?)',html)}
 headers={'User-Agent':'PlaneByte-Controlled-Acceptance/1.0'}
 record['open_http']=requests.get(urls['o'],headers=headers,timeout=60).status_code
 record['click_http']=requests.get(urls['c'],headers=headers,timeout=60,allow_redirects=False).status_code
 record['unsubscribe_get_http']=requests.get(urls['u'],headers=headers,timeout=60).status_code
 record['unsubscribe_post_http']=requests.post(urls['u'],data='confirm=stop',headers=headers,timeout=60).status_code
 path.write_text(json.dumps(record,indent=2))
if record.get('message_id'):
 with db_session() as c:
  events={r[0] for r in c.execute('SELECT event_type FROM email_engagement_events WHERE message_id=?',(record['message_id'],)).fetchall()}
  record['events']=sorted(events)
  record['timeline_events']=[r[0] for r in c.execute('SELECT event_type FROM activities WHERE prospect_id=? ORDER BY event_at',(record['prospect_id'],)).fetchall()]
  record['global_sending_enabled']=False
 path.write_text(json.dumps(record,indent=2));print(json.dumps(record))
