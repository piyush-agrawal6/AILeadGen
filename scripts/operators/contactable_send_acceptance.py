"""Exactly one owner-controlled redirected send; durable reservation forbids retries."""
import os,json,uuid,hashlib
from pathlib import Path
os.environ.update(DATABASE_BACKEND='postgres',STORAGE_BACKEND='r2',SSL_CERT_FILE='/etc/ssl/cert.pem')
from fastapi import HTTPException
from app.database.connection import db_session
from app.config.settings import get_settings
from app.mail import service,contacted
from app.mail.providers import provider
from app.outreach import fixed
STATE=Path('docs/contactable-owner-send.json')
TARGET='planebyte@gmail.com' # Existing owner-controlled sender mailbox, never a prospect.

def run(*,recipient=TARGET,output=STATE):
 TARGET=service.address(recipient);STATE=Path(output)
 assert not STATE.exists(),'A send was reserved/attempted. Verify it; never resend automatically.'
 transport=provider();calls=0;record={'actual_recipient':TARGET,'real_prospect_contacted':False,'status':'RESERVED','idempotency_key':str(uuid.uuid4())}
 def save():STATE.write_text(json.dumps(record,indent=2));STATE.chmod(0o600)
 class OwnerOnly:
  def health_check(self):return transport.health_check()
  def send_message(self,message):
   nonlocal calls
   assert calls==0 and str(message['To'])==TARGET and not message.get('Cc') and not message.get('Bcc')
   assert str(message['From'])=='PlaneByte <planebyte@gmail.com>'
   assert str(message['Subject'])==record['subject'] and message['List-Unsubscribe']
   parts=list(message.iter_attachments());assert len(parts)==1
   assert hashlib.sha256(parts[0].get_payload(decode=True)).hexdigest()==record['pdf_sha256']
   assert 'acceptance' not in message.get_body(preferencelist=('plain',)).get_content().lower()
   calls+=1;record['status']='SMTP_ATTEMPTING';record['provider_message_id']=str(message['Message-ID']);save()
   return transport.send_message(message)
 service.provider=lambda:OwnerOnly()
 with db_session() as c:
  assert not contacted.lookup(c,TARGET),'Permanent contacted history is never bypassed, including for controlled QA.'
  state=json.loads(Path('docs/contactable-source-acceptance.json').read_text());cid=state['campaign_id']
  row=c.execute("SELECT b.* FROM businesses b JOIN pipeline_runs p ON p.id=b.run_id WHERE p.campaign_id=? AND b.processing_status='QUALIFIED' ORDER BY b.id LIMIT 1",(cid,)).fetchone();assert row
  fixed.seed(c);asset=fixed.asset(c);body=fixed.render(row['name'],'PB_INTRO_01')|{'campaign_id':cid,'to_address':row['public_email'],'message_type':'FIRST_CONTACT','track_opens':True,'track_clicks':True,'followup_days':0,'confirmation':'SEND','preview_nonce':str(uuid.uuid4()),'idempotency_key':record['idempotency_key']}
  actor=get_settings().allowed_emails[0];preview=service.preview(c,row['prospect_id'],actor,body);assert not preview['quality_issues'];body['preview_token']=preview['preview_token']
  record.update(subject=body['subject'],body_text=body['body_text'],company=row['name'],template_id=body['template_id'],pdf_asset_id=asset['id'],pdf_version=asset['version'],pdf_sha256=asset['sha256'],pdf_size=asset['size_bytes'],pdf_page_count=asset['page_count']);save()
  result=service.send(c,row['prospect_id'],actor,body,controlled_envelope_to=TARGET,controlled_authorization='Owner-requested contactable-only permanent-registry acceptance, 2026-11-03')
  record.update(status=result['status'],result=result,smtp_calls=calls);save();assert result['status']=='SENT'
  assert contacted.lookup(c,TARGET)['send_count']==1
  again=service.send(c,row['prospect_id'],actor,body,controlled_envelope_to=TARGET,controlled_authorization='Owner-requested contactable-only permanent-registry acceptance, 2026-11-03');assert again['duplicate_prevented'] and calls==1
  try:contacted.ensure_new(c,TARGET)
  except HTTPException as e:assert e.status_code==409;record['second_send_blocked']=True
  else:raise AssertionError('Already contacted recipient was not blocked')
  assert not contacted.lookup(c,row['public_email']),'Redirected acceptance must never mark the intended prospect contacted.'
  record.update(registry_immediate=True,idempotent_retry_prevented=True,all_five_templates=[fixed.render(row['name'],tid) for tid in fixed.TEMPLATES]);save()
 client=transport.imap()
 try:
  assert client.select(transport.sent_mailbox(client),readonly=True)[0]=='OK'
  status,ids=client.uid('search',None,'HEADER','Message-ID',record['provider_message_id']);record['gmail_sent_visible']=status=='OK' and bool(ids and ids[0]);save()
 finally:client.logout()
 assert record['gmail_sent_visible'];print(json.dumps({k:record[k] for k in ('status','actual_recipient','subject','pdf_page_count','pdf_size','smtp_calls','gmail_sent_visible','registry_immediate','second_send_blocked','real_prospect_contacted')}))

if __name__=='__main__':run()
