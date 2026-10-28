"""Prepare one evidence-based first-live draft; never sends or enables live mode."""
import os,sys,json,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.database.prospects import ProspectRepository,now
from app.config.settings import get_settings
from app.mail import service
from app.mail.config import mail_settings
s=mail_settings()
if s.mode!='test' or s.live_approved:raise SystemExit('Preparation must retain test mode and live approval false.')
file=Path('docs/phase41-first-live-draft.json')
if file.exists():raise SystemExit('Existing first-live draft retained; review it manually.')
actor='planebyte@gmail.com' if 'planebyte@gmail.com' in get_settings().allowed_emails else get_settings().allowed_emails[0]
with db_session() as c:
 b=c.execute("SELECT b.id,b.name,b.public_email,b.prospect_id,p.lead_status,i.commercial_fit FROM businesses b JOIN prospects p ON p.id=b.prospect_id JOIN business_intelligence i ON i.business_id=b.id WHERE b.id=509").fetchone()
 if not b or b['commercial_fit']!='HIGH' or b['lead_status'] not in ('NEW','SHORTLISTED','READY_TO_CONTACT') or service.suppressed(c,b['prospect_id']):raise SystemExit('Candidate must be reviewed again; no draft or send was created.')
 if b['public_email'].lower() not in service.recipients(c,b['prospect_id']):raise SystemExit('Stored public recipient is not usable.')
 report=c.execute("SELECT id FROM client_reports WHERE prospect_id=? AND status='READY' ORDER BY version DESC LIMIT 1",(b['prospect_id'],)).fetchone()
 template=c.execute("SELECT id FROM email_templates WHERE enabled=1 AND id='website'").fetchone()
 signature='\n'.join(x for x in [s.signature_name,s.signature_role,s.company,s.website,s.from_address] if x)
 body={'to_address':b['public_email'],'subject':'A practical website review for Skylark motel','body_text':'Hello Skylark team,\n\nI am reaching out from PlaneByte. In our recent review of the pages available to our scan, we did not observe a mobile viewport declaration or homepage title and description metadata. These are practical areas to check as part of a clearer mobile experience and booking journey.\n\nI have attached a short review of the recorded findings for your consideration. Would a brief conversation about the most useful next steps be helpful?\n\n'+signature,'report_id':report[0] if report else None,'thread_id':None,'followup_days':3,'override_declined':False,'track_opens':True,'track_clicks':True,'template_id':template[0] if template else None,'message_type':'FIRST_CONTACT'}
 if not report:raise SystemExit('A current client report is needed before preparing this draft.')
 if c.execute('SELECT 1 FROM email_drafts WHERE prospect_id=? AND actor=?',(b['prospect_id'],actor)).fetchone():raise SystemExit('An owner draft exists; it was preserved.')
 key=str(uuid.uuid4());c.execute('INSERT INTO email_drafts VALUES(?,?,?,?,?)',(key,b['prospect_id'],actor,json.dumps(body),now()))
 if b['lead_status']!='READY_TO_CONTACT':ProspectRepository(c).workflow(b['prospect_id'],actor,lead_status='READY_TO_CONTACT')
 result={'business_id':b['id'],'business_name':b['name'],'commercial_fit':'HIGH','lead_url':'https://leads.planebyte.com/leads/'+str(b['id']),'draft_id':key,'recipient_source':'Existing persisted public business contact','status':'READY_TO_CONTACT','send_mode':'test','live_approved':False,'sent':False,'owner_action':'Review intelligence and saved draft. Only after explicit live activation manually press Send Live Email.','draft':body}
 file.write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'business_id':b['id'],'business_name':b['name'],'draft_saved':True,'sent':False,'send_mode':'test'}))
