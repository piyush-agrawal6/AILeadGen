"""Controlled SMTP/tracking acceptance. Never sends to a discovered prospect."""
import os,sys,json,re,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres';os.environ['STORAGE_BACKEND']='r2'
from app.database.connection import db_session
from app.mail import service,tracking
from app.mail.config import mail_settings
from app.mail.providers import provider as actual_provider
import httpx
sys.excepthook=lambda kind,value,tb:sys.stderr.write('Controlled acceptance did not finish. Inspect provider health and the persisted reservation; do not automatically resend.\n')
statefile=Path('docs/phase41-controlled.json');state=json.loads(statefile.read_text(encoding='utf-8')) if statefile.exists() else {'checks':{}}
def save():statefile.write_text(json.dumps(state,indent=2),encoding='utf-8')
s=mail_settings()
if s.mode!='test' or s.live_approved or not s.sending_enabled:raise SystemExit('Controlled acceptance requires enabled test mode with live approval false.')
if not s.test_recipient or s.test_recipient.lower()==s.from_address.lower():raise SystemExit('A separately controlled test recipient is required.')
action=sys.argv[1] if len(sys.argv)>1 else 'verify'
if action=='send':
 with db_session() as c:
  if state.get('sent'):raise SystemExit('Existing controlled send retained. Use verify; no resend.')
  state.setdefault('idempotency_key',str(uuid.uuid4()));state.setdefault('subject','PlaneByte Phase 4.1 controlled tracking '+uuid.uuid4().hex[:8]);save()
  prior=c.execute('SELECT id,status FROM email_messages WHERE idempotency_key=?',(state['idempotency_key'],)).fetchone()
  if prior:raise SystemExit('A previous reservation exists. Review it before any deliberate new send.')
  pid=c.execute('SELECT prospect_id FROM businesses WHERE id=517').fetchone()[0]
  targets=service.recipients(c,pid)
  if not targets:raise SystemExit('No approved public contact is available.')
  report=c.execute("SELECT id FROM client_reports WHERE prospect_id=? AND status='READY' ORDER BY version DESC LIMIT 1",(pid,)).fetchone()
  body={'to_address':targets[0],'subject':state['subject'],'body_text':'Controlled PlaneByte tracking acceptance. This is redirected to the controlled mailbox; no discovered prospect is being contacted.\n\nPlease reply normally with Phase 4.1 reply test. Automated endpoint checks are labeled as scanner activity and do not represent human engagement.\n\nPlaneByte\nhttps://planebyte.com\nrajendra@planebyte.com','report_id':report[0] if report else None,'thread_id':None,'followup_days':None,'override_declined':False,'track_opens':True,'track_clicks':True,'template_id':None,'message_type':'FIRST_CONTACT'}
  review=service.preview(c,pid,'planebyte@gmail.com',body)
  transport=actual_provider();captured={}
  class Capture:
   def send_message(self,message):
    captured['html']=message.get_body(preferencelist=('html',)).get_content();captured['unsubscribe']=str(message['List-Unsubscribe']).strip('<>')
    assert str(message['To']).lower()==s.test_recipient.lower() and '[TEST]' in str(message['Subject'])
    return transport.send_message(message)
  service.provider=lambda:Capture()
  state['sent']=service.send(c,pid,'planebyte@gmail.com',{**body,'confirmation':'SEND','preview_token':review['preview_token'],'idempotency_key':state['idempotency_key']});save()
  if state['sent']['status']!='SENT':raise SystemExit('Controlled SMTP acceptance is incomplete; no automatic resend.')
  state['checks']['smtp_accepted']=True;state['checks']['test_redirect']=True;state['checks']['pdf_attached']=bool(report)
  urls=re.findall(r'https://[^"\s<>]+',captured['html']);pixel=next(u for u in urls if '/t/o/' in u);click=next(u for u in urls if '/t/c/' in u);optout=captured['unsubscribe']
  original_status=c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]
 with httpx.Client(timeout=30,follow_redirects=False,headers={'User-Agent':'LeadEngine-Controlled-QA scanner'}) as client:
  a=client.get(pixel);b=client.get(pixel);state['checks']['pixel_endpoint']=a.status_code==200 and a.content.startswith(b'GIF89a');state['checks']['duplicate_pixel_safe']=b.status_code==200
  r=client.get(click);state['checks']['stored_redirect']=r.status_code==302 and r.headers.get('location')=='https://planebyte.com'
  state['checks']['unsubscribe_confirmation']=client.get(optout).status_code==200
  state['checks']['test_unsubscribe_post']=client.post(optout,content='confirm=stop',headers={'Content-Type':'application/x-www-form-urlencoded'}).status_code==200
 with db_session() as c:
  events=[dict(r) for r in c.execute('SELECT event_type,suspected_bot,request_count FROM email_engagement_events WHERE message_id=?',(state['sent']['id'],)).fetchall()]
  state['checks']['scanner_labeled']=any(r['event_type']=='CLICK_SIGNAL' and r['suspected_bot'] for r in events)
  state['checks']['deduplicated_open']=len([r for r in events if r['event_type']=='OPEN_SIGNAL' and r['suspected_bot']])==1
  state['checks']['test_optout_preserves_prospect']=c.execute('SELECT lead_status FROM prospects WHERE id=?',(pid,)).fetchone()[0]==original_status and not service.suppressed(c,pid)
  state['checks']['outbound_persisted']=bool(c.execute("SELECT 1 FROM email_messages WHERE id=? AND status='SENT' AND test_mode=1",(state['sent']['id'],)).fetchone())
 save()
else:
 state['sync']=service.sync_mailbox()
 with db_session() as c:
  state['checks']['verified_reply']=bool(c.execute("SELECT 1 FROM email_engagement_events WHERE message_id=? AND event_type='REPLIED_VERIFIED'",(state['sent']['id'],)).fetchone())
  state['checks']['reply_status_preserved']=c.execute('SELECT p.lead_status FROM prospects p JOIN email_messages m ON m.prospect_id=p.id WHERE m.id=?',(state['sent']['id'],)).fetchone()[0]=='REPLIED'
 save()
print(json.dumps({'subject':state.get('subject'),'checks':state['checks'],'send_mode':'test'}))
