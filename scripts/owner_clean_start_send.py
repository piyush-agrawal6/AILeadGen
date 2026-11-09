"""Exactly one owner-authorized redirected send through the real mail service.

No persistent configuration override and no alternate subject/body/PDF template.
The durable state forbids retry after any SMTP attempt, including uncertain ones.
"""
import os,sys,json,uuid,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi
os.environ.update(DATABASE_BACKEND='postgres',STORAGE_BACKEND='r2',APP_ENV='production',LEADENGINE_ROLE='worker',SCAN_EXECUTOR='gcp',GCP_PROJECT_ID='querryside',GCP_REGION='asia-south1',SSL_CERT_FILE=certifi.where())
from app.database.connection import db_session
from app.config.settings import get_settings
from app.mail.config import mail_settings
from app.mail.providers import GmailEmailProvider
from app.mail.templates import render_client_template
from app.mail import service

TARGET='agrawaljoy1@gmail.com'
statefile=Path('docs/owner-clean-start-send.json')
assert '--send' in sys.argv,'Explicit --send required'
if statefile.exists():raise SystemExit('A send was already reserved/attempted. Verification only; never resend.')
report=json.loads(Path('docs/owner-clean-start-report.json').read_text())
assert report['status']=='READY' and report.get('visual_review_passed')
base=mail_settings();assert not(base.auto_scan_enabled or base.auto_email_enabled or base.sending_enabled)
assert base.from_address=='planebyte@gmail.com' and base.from_name=='PlaneByte'
assert base.tracking_enabled
# An in-process acceptance-only override; Cloud Run/root .env stay unchanged.
settings=base.model_copy(update={'mode':'production','live_approved':True,'sending_enabled':True})
service.mail_settings=lambda:settings
real=GmailEmailProvider(settings)
pdf=Path(report['path']).read_bytes();assert hashlib.sha256(pdf).hexdigest()==report['sha256']
record={'recipient':TARGET,'business':report['business'],'report_id':report['report']['id'],
        'attachment_filename':'PlaneByte digital review.pdf','attachment_size_bytes':len(pdf),
        'attachment_sha256':report['sha256'],'idempotency_key':str(uuid.uuid4()),
        'real_prospect_contacted':False,'global_automation_enabled':False,'status':'RESERVED'}
def save():statefile.write_text(json.dumps(record,indent=2))
class SingleRecipientTransport:
 calls=0
 def health_check(self):return real.health_check()
 def send_message(self,message):
  assert self.calls==0 and message['To']==TARGET
  assert message['From']=='PlaneByte <planebyte@gmail.com>'
  assert not message.get('Cc') and not message.get('Bcc')
  assert message['Subject']==record['subject'] and '[TEST]' not in message['Subject']
  plain=message.get_body(preferencelist=('plain',)).get_content()
  html=message.get_body(preferencelist=('html',)).get_content()
  assert 'TEST MODE' not in plain and 'acceptance' not in plain.lower()
  assert 'PlaneByte' in plain and 'planebyte@gmail.com' in plain
  assert 'Stop receiving emails' in html and message['List-Unsubscribe']
  attachments=list(message.iter_attachments());assert len(attachments)==1
  assert attachments[0].get_filename()==record['attachment_filename']
  assert attachments[0].get_payload(decode=True)==pdf
  dest=Path('output/owner-clean-start/outbound.eml');dest.parent.mkdir(parents=True,exist_ok=True)
  dest.write_bytes(message.as_bytes());dest.chmod(0o600)
  self.calls+=1;record.update(status='SMTP_ATTEMPTING',provider_message_id=message['Message-ID'],mime_path=str(dest.resolve()));save()
  return real.send_message(message)
transport=SingleRecipientTransport();service.provider=lambda:transport
with db_session() as c:
 assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0,'One-send safety gate'
 b=c.execute('SELECT * FROM businesses WHERE id=?',(report['business']['id'],)).fetchone()
 assert b['processing_status']=='QUALIFIED' and b['prospect_id']==report['business']['prospect_id']
 pid=b['prospect_id'];actor=get_settings().allowed_emails[0]
 recipients=service.recipients(c,pid);assert recipients and TARGET not in recipients
 template=render_client_template(c,b['id'],'website',settings)
 body={'to_address':recipients[0],'subject':template['rendered_subject'],'body_text':template['rendered_body'],
       'report_id':record['report_id'],'template_id':'website','message_type':'FIRST_CONTACT',
       'track_opens':True,'track_clicks':True,'followup_days':None,
       'confirmation':'SEND','idempotency_key':record['idempotency_key']}
 assert 'acceptance' not in body['body_text'].lower() and 'test' not in body['subject'].lower()
 record.update(subject=body['subject'],intended_recipient=body['to_address']);save()
 body['preview_token']=service.preview(c,pid,actor,body)['preview_token']
 result=service.send(c,pid,actor,body,controlled_envelope_to=TARGET,
                     controlled_authorization='Owner-authorized clean-start redirected acceptance, 2026-11-01')
 record.update(result=result,status=result['status'],smtp_calls=transport.calls);save()
 assert result['status']=='SENT','Do not retry: inspect the durable SMTP outcome'
 c.execute("UPDATE automation_email_queue SET status='CANCELED',error_code='OWNER_CONTROLLED_REDIRECT_ONLY' WHERE prospect_id=? AND status='QUEUED'",(pid,))
 assert c.execute('SELECT last_contact_at FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0] is None
 assert c.execute("SELECT COUNT(*) FROM email_messages WHERE direction='OUTBOUND'").fetchone()[0]==1
print(json.dumps({k:v for k,v in record.items() if k not in ('mime_path','intended_recipient','idempotency_key')}))
