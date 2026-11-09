"""Replay the real controlled SMTP record into an isolated DB, then sync live replies.
Does not send mail or write to production. The database path must be temporary.
"""
import os,sys,json,uuid,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi
os.environ['SSL_CERT_FILE']=certifi.where();os.environ['APP_ENV']='test'
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,now
from app.mail import service
from app.automation.service import reconcile
record=json.loads(Path('docs/gmail-automation-acceptance.json').read_text())
if record.get('recipient')!='contact@planebyte.com' or record.get('send_status')!='SMTP_ACCEPTED':raise SystemExit('Current controlled SMTP evidence required')
with tempfile.TemporaryDirectory(prefix='leadengine-gmail-acceptance-') as directory:
 path=Path(directory)/'acceptance.db';c=get_connection(path);run_migrations(c)
 run=PipelineRun(market='Controlled acceptance',vertical='home_services',target=1);rid=PipelineRunRepository(c).create(run)
 b=Business(name='PlaneByte controlled acceptance',normalized_name='planebyte controlled acceptance',vertical='home_services',run_id=rid,public_email=record['recipient'],processing_status='QUALIFIED')
 BusinessRepository(c).insert(b);pid=ProspectRepository(c).observe(b);c.execute("UPDATE prospects SET lead_status='CONTACTED' WHERE id=?",(pid,));reconcile(c)
 acc=service.account(c,'system');thread=str(uuid.uuid4());mid=str(uuid.uuid4());stamp=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()
 c.execute("INSERT INTO email_threads VALUES(?,?,?,?,?,'OUTBOUND',?)",(thread,pid,acc['id'],'Controlled acceptance',stamp,stamp))
 c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,created_at,sent_at,test_mode) VALUES(?,?,?,?,?,'OUTBOUND','SENT',?,?,'Controlled acceptance','Controlled SMTP record',?,?,1)",(mid,pid,acc['id'],thread,record['message_id'],'planebyte@gmail.com',record['recipient'],stamp,stamp));c.commit();c.close()
 # Start the isolated parser at the known controlled reply rather than walking the owner's mailbox history.
 from app.mail.providers import provider
 mailbox=provider().imap()
 try:
  folder=provider().sync_mailbox(mailbox)
  mailbox.select(folder,readonly=True)
  import hashlib
  raw_validity=(mailbox.response('UIDVALIDITY')[1] or [b''])[0].decode('ascii')
  validity=hashlib.sha256((folder+'|'+raw_validity).encode()).hexdigest()
  _,data=mailbox.uid('search',None,'HEADER','References','"'+record['message_id']+'"')
  ids=[int(value) for value in (data[0] or b'').split()]
  if ids:
   c=get_connection(path);c.execute("INSERT INTO email_sync_state VALUES(?,'ALL_MAIL',?,?)",(acc['id'],validity,min(ids)-1));c.commit();c.close()
 finally:mailbox.logout()
 service.get_connection=lambda **kw:get_connection(path)
 for _ in range(10):
  service.sync_mailbox()
  c=get_connection(path)
  count=c.execute("SELECT COUNT(*) FROM activities WHERE prospect_id=? AND event_type='REPLY_DETECTED'",(pid,)).fetchone()[0];c.close()
  if count:break
 service.sync_mailbox()
 c=get_connection(path)
 result={'thread_matched':bool(c.execute("SELECT 1 FROM email_messages WHERE thread_id=? AND direction='INBOUND'",(thread,)).fetchone()),'reply_activities':c.execute("SELECT COUNT(*) FROM activities WHERE prospect_id=? AND event_type='REPLY_DETECTED'",(pid,)).fetchone()[0],'contact_state':c.execute('SELECT contact_state FROM master_lead_state WHERE prospect_id=?',(pid,)).fetchone()[0],'sales_state':c.execute('SELECT sales_state FROM master_lead_state WHERE prospect_id=?',(pid,)).fetchone()[0],'production_database_written':False,'additional_mail_sent':False};c.close()
 Path('docs/gmail-reply-activity-acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 if result['reply_activities']!=1 or not result['thread_matched']:raise SystemExit('Controlled reply acceptance is incomplete')
