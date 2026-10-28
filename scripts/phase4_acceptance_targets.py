"""Select existing real prospects from both accepted scans; never invent leads."""
import os,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.mail.service import address
record=Path('docs/phase4-acceptance-targets.json')
if record.exists():raise SystemExit('Acceptance targets already recorded; reuse them.')
targets=[]
with db_session() as c:
    for run_id in (1,2):
        rows=c.execute("SELECT b.id,b.name,b.public_email,b.prospect_id,p.lead_status,p.assigned_to FROM businesses b JOIN prospects p ON p.id=b.prospect_id JOIN opportunity_scores o ON o.business_id=b.id LEFT JOIN business_intelligence i ON i.business_id=b.id LEFT JOIN lighthouse_results l ON l.business_id=b.id WHERE b.run_id=? AND b.processing_status='QUALIFIED' AND b.is_rejected=0 AND b.public_email IS NOT NULL AND p.lead_status<>'DO_NOT_CONTACT' ORDER BY CASE WHEN i.commercial_fit='HIGH' THEN 0 ELSE 1 END,CASE WHEN l.business_id IS NOT NULL THEN 0 ELSE 1 END,o.website_opportunity_score DESC LIMIT 100",(run_id,)).fetchall()
        selected=None
        for row in rows:
            try:address(row['public_email']);selected=row;break
            except Exception:continue
        if not selected:raise RuntimeError('No valid stored public contact found for an existing scan.')
        targets.append({k:selected[k] for k in ('id','name','prospect_id','lead_status','assigned_to')}|{'run_id':run_id})
record.write_text(json.dumps(targets,indent=2),encoding='utf-8');print(json.dumps(targets))
