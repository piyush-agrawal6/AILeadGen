"""Owner acceptance of the real redesigned content. Exactly one redirected SMTP call.
Prepare once, visually inspect the production PDF, then --send. No lead discovery.
"""
import os,sys,json,uuid,hashlib,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi
os.environ.update(DATABASE_BACKEND='postgres',STORAGE_BACKEND='r2',APP_ENV='production',LEADENGINE_ROLE='worker',SCAN_EXECUTOR='gcp',GCP_PROJECT_ID='querryside',GCP_REGION='asia-south1',SSL_CERT_FILE=certifi.where())
from app.database.connection import db_session
from app.config.settings import get_settings
from app.mail.config import mail_settings
from app.mail import service
from app.mail.templates import seed,COMMERCIAL_BODY,render_client_template
from app.mail.providers import GmailEmailProvider
from app.reports.service import create_report,execute_report
from app.reports.opportunity import plan,report_issues,why_planebyte
from app.storage import artifact_storage
TARGET='agrawaljoy1@gmail.com';statefile=Path('docs/final-content-acceptance.json')
base=mail_settings();assert not(base.auto_scan_enabled or base.auto_email_enabled or base.sending_enabled)
assert base.from_address=='planebyte@gmail.com' and base.from_name=='PlaneByte'
record=json.loads(statefile.read_text()) if statefile.exists() else {}
def save():statefile.write_text(json.dumps(record,indent=2))
if '--prepare' in sys.argv:
 if record:raise SystemExit('Preparation already reserved; inspect saved report instead of regenerating.')
 with db_session() as c:
  assert c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==10
  b=c.execute("SELECT id,prospect_id,name FROM businesses WHERE name='Homestay Hotels' AND processing_status='QUALIFIED'").fetchone();assert b
  seed(c)
  # The shipped combined row was temporarily disabled for old-version compatibility.
  c.execute("UPDATE email_templates SET enabled=1 WHERE id='combined' AND body_text=?",(COMMERCIAL_BODY,))
  r=create_report(c,b['id'],b['prospect_id'],get_settings().allowed_emails[0]);record.update(company=dict(b),report=r,status='PREPARING');save()
 execute_report(r['id'])
 with db_session() as c:
  report=c.execute('SELECT * FROM client_reports WHERE id=?',(r['id'],)).fetchone();assert report['status']=='READY'
  snapshot=json.loads(report['snapshot_json']);p=plan(snapshot);assert not report_issues(snapshot,p)
  t=render_client_template(c,b['id'],p['variant'],base)
  with artifact_storage().get(report['object_key']) as f:pdf=f.read()
 dest=Path('output/pdf/PlaneByte opportunity review.pdf');dest.write_bytes(pdf)
 from pypdf import PdfReader
 record.update(status='PREPARED',subject=t['rendered_subject'],body=t['rendered_body'],variant=p['variant'],pdf_path=str(dest.resolve()),pdf_pages=len(PdfReader(dest).pages),attachment_filename='PlaneByte digital review.pdf',attachment_size_bytes=len(pdf),attachment_sha256=hashlib.sha256(pdf).hexdigest(),top_findings=p['top'],primary_service=p['service_title'],included_value=p['included'],cta=p['cta'],why_planebyte=why_planebyte(p),sender_name=base.outreach_sender_name,sender_role=base.outreach_sender_role,controlled_recipient=TARGET,real_prospect_contacted=False,all_global_flags_false=True)
 # Compare with the deployed composer's actual stored-template rendering.
 import requests,time,secrets,hmac
 from dotenv import dotenv_values
 values=dotenv_values('.env');actor=values['ALLOWED_USER_EMAILS'].split(',')[0].strip().lower();secret=values['LEADENGINE_API_SIGNING_SECRET'];stamp=str(int(time.time()));nonce=secrets.token_hex(16)
 api_path='/api/email/leads/'+str(b['id'])+'/compose'
 canonical='\n'.join([stamp,nonce,'GET',api_path,hashlib.sha256(b'').hexdigest(),actor])
 response=requests.get('https://leadengine-api-befca7xg4a-el.a.run.app'+api_path,headers={'X-LE-Timestamp':stamp,'X-LE-Nonce':nonce,'X-LE-User':actor,'X-LE-Signature':hmac.new(secret.encode(),canonical.encode(),hashlib.sha256).hexdigest()},timeout=90)
 assert response.status_code==200
 deployed=next(t for t in response.json()['templates'] if t['id']==p['variant'])
 assert deployed['rendered_subject']==record['subject'] and deployed['rendered_body']==record['body'],'Local and deployed client content must match exactly'
 record['deployed_composer_content_exact_match']=True
 save();print(json.dumps({k:record[k] for k in ('status','subject','body','pdf_pages','primary_service','included_value','cta','controlled_recipient')}));raise SystemExit(0)
if '--send' in sys.argv:
 assert record.get('status')=='PREPARED' and record.get('visual_review_passed'),'Require prepared, visually approved normal report; never retry SMTP.'
 settings=base.model_copy(update={'mode':'production','live_approved':True,'sending_enabled':True});service.mail_settings=lambda:settings
 real=GmailEmailProvider(settings)
 class OneRecipient:
  calls=0
  def health_check(self):return real.health_check()
  def send_message(self,message):
   assert self.calls==0 and message['To']==TARGET and not message.get('Cc') and not message.get('Bcc')
   assert message['From']=='PlaneByte <planebyte@gmail.com>' and message['Subject']==record['subject']
   plain=message.get_body(preferencelist=('plain',)).get_content();html=message.get_body(preferencelist=('html',)).get_content()
   assert 'TEST MODE' not in plain and 'acceptance' not in plain.lower()
   assert 'Software Engineering · SEO · Security' in plain and 'opt out here' in html.lower()
   parts=list(message.iter_attachments());assert len(parts)==1
   assert hashlib.sha256(parts[0].get_payload(decode=True)).hexdigest()==record['attachment_sha256']
   path=Path('output/owner-final-content/outbound.eml');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(message.as_bytes());path.chmod(0o600)
   self.calls+=1;record.update(status='SMTP_ATTEMPTING',provider_message_id=message['Message-ID'],mime_path=str(path.resolve()));save()
   return real.send_message(message)
 transport=OneRecipient();service.provider=lambda:transport
 with db_session() as c:
  assert not c.execute("SELECT 1 FROM email_messages WHERE idempotency_key=?",('final-content-owner-'+record['report']['id'],)).fetchone()
  pid=record['company']['prospect_id'];addresses=service.recipients(c,pid);assert addresses and TARGET not in addresses
  body={'to_address':addresses[0],'subject':record['subject'],'body_text':record['body'],'report_id':record['report']['id'],'template_id':record['variant'],'message_type':'FIRST_CONTACT','track_opens':True,'track_clicks':True,'followup_days':None,'confirmation':'SEND','idempotency_key':'final-content-owner-'+record['report']['id'],'preview_nonce':str(uuid.uuid4())}
  body['preview_token']=service.preview(c,pid,'system',body)['preview_token']
  record['status']='SMTP_RESERVED';save()
  result=service.send(c,pid,'system',body,controlled_envelope_to=TARGET,controlled_authorization='Owner-authorized final-polish Homestay email and client PDF acceptance, 2026-11-01')
  record.update(status=result['status'],result=result,smtp_calls=transport.calls);save()
  assert result['status']=='SENT','Uncertain/failed outcome: do not retry'
  assert c.execute('SELECT last_contact_at FROM prospect_sales WHERE prospect_id=?',(pid,)).fetchone()[0] is None
 print(json.dumps({'status':record['status'],'smtp_calls':transport.calls,'recipient':TARGET,'subject':record['subject']}))
