"""Generate the one normal production client report; never send mail."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi
os.environ.update(DATABASE_BACKEND='postgres',STORAGE_BACKEND='r2',APP_ENV='production',LEADENGINE_ROLE='worker',SCAN_EXECUTOR='gcp',GCP_PROJECT_ID='querryside',GCP_REGION='asia-south1',SSL_CERT_FILE=certifi.where())
from app.database.connection import db_session
from app.mail.config import mail_settings
from app.reports.service import create_report,execute_report
from app.storage import artifact_storage
from app.config.settings import get_settings
s=mail_settings();assert not(s.auto_scan_enabled or s.auto_email_enabled or s.sending_enabled)
state=Path('docs/owner-clean-start-report.json')
if state.exists():raise SystemExit('Report already prepared; inspect existing evidence rather than regenerate.')
with db_session() as c:
 rows=c.execute("SELECT id,prospect_id,name FROM businesses WHERE processing_status='QUALIFIED'").fetchall()
 assert len(rows)==1,'Require exactly one genuinely qualified business'
 b=dict(rows[0]);assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 from app.automation.service import reconcile
 reconcile(c)
 actor=get_settings().allowed_emails[0]
 report=create_report(c,b['id'],b['prospect_id'],actor)
record={'business':b,'report':report};state.write_text(json.dumps(record,indent=2))
execute_report(report['id'])
with db_session() as c:
 row=c.execute('SELECT status,object_key FROM client_reports WHERE id=?',(report['id'],)).fetchone();assert row['status']=='READY'
 with artifact_storage().get(row['object_key']) as f:pdf=f.read()
dest=Path('output/pdf/PlaneByte digital review.pdf');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(pdf)
import hashlib
record.update(status='READY',path=str(dest.resolve()),size_bytes=len(pdf),sha256=hashlib.sha256(pdf).hexdigest())
state.write_text(json.dumps(record,indent=2));print(json.dumps(record))
