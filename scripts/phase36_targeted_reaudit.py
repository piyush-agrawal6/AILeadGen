"""Bounded re-audit of genuine records from the London acceptance discovery."""
import os,json,sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_BACKEND']='postgres'
from app.database.connection import db_session
from app.database.models import PipelineRun
from app.database.repositories import PipelineRunRepository,BusinessRepository
from app.database.prospects import ProspectRepository,now
from app.discovery.source_metadata import optional_text
from app.scoring.commercial import professional_domain
from app.api.services import cloud_executor
from app.cloud_doctor import authorized_session

path=Path('docs/phase36-targeted-reaudit.json')
if path.exists():raise SystemExit('Targeted re-audit already exists; reuse its recorded run.')
source=json.loads(Path('docs/phase36-production.json').read_text(encoding='utf-8'))['campaign']['runs'][0]['id']
cid=str(uuid.uuid4());config={'cities':['London, United Kingdom'],'verticals':['dentists'],'opportunities':['WEBSITE','SEO','SECURITY'],'quality':'balanced','business_scales':['LOCAL','SMALL_GROUP','MID_MARKET'],'results':'all','target':5,'lighthouse_enabled':True,'social_enrichment_enabled':True,'social_activity_enabled':True,'request_id':cid,'fixture':False}
with db_session() as c:
    candidates=c.execute("SELECT b.id,b.domain FROM businesses b JOIN website_profiles w ON w.business_id=b.id JOIN opportunity_scores o ON o.business_id=b.id LEFT JOIN lighthouse_results l ON l.business_id=b.id WHERE b.run_id=? AND w.reachable=1 AND (o.website_opportunity_score>=40 OR o.seo_opportunity_score>=40 OR o.security_opportunity_score>=40) AND o.contactability_level<>'LOW' ORDER BY CASE WHEN l.business_id IS NOT NULL THEN 0 ELSE 1 END,o.website_opportunity_score DESC,b.id",(source,)).fetchall()
    ids=[r['id'] for r in candidates if professional_domain(r['domain'])][:3]
    if not ids:raise RuntimeError('No genuine reachable source businesses qualify for the re-audit.')
    missing=c.execute("SELECT id FROM businesses WHERE run_id=? AND domain='nan' ORDER BY id LIMIT 1",(source,)).fetchone()
    if missing:ids.append(missing[0])
    c.execute("INSERT INTO scan_campaigns(id,created_by,status,configuration_json,target_total,created_at) VALUES(?,'planebyte@gmail.com','QUEUED',?,5,?)",(cid,json.dumps(config),now()))
    run=PipelineRun(market='London, United Kingdom',vertical='dentists',target=5,status='QUEUED',run_configuration={**config,'created_by':'planebyte@gmail.com','lighthouse_budget':1,'raw_budget':len(ids),'reaudit_source_run':source})
    PipelineRunRepository(c).create(run);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run.id))
    observations=[]
    for source_id in ids:
        b=BusinessRepository(c).get_by_id(source_id).model_copy(deep=True,update={'id':None,'run_id':run.id,'processing_status':'NORMALIZED','is_duplicate':False,'is_rejected':False,'rejection_reason':None,'created_at':None,'updated_at':None})
        b.phone=optional_text(b.phone);b.public_email=optional_text(b.public_email)
        b.address=optional_text(b.address);b.postcode=optional_text(b.postcode)
        if not professional_domain(b.domain):b.website=None;b.domain=None
        BusinessRepository(c).insert(b);ProspectRepository(c).observe(b,cid,'planebyte@gmail.com');observations.append({'source_business_id':source_id,'business_id':b.id,'name':b.name})
record={'campaign_id':cid,'run_id':run.id,'source_run_id':source,'purpose':'Bounded re-audit of genuine source observations; no synthetic business records; Local included to exercise screenshot/report generation after the stricter group-only campaign found no size matches.','observations':observations}
path.write_text(json.dumps(record,indent=2),encoding='utf-8')
session=authorized_session();original=cloud_executor.run_job
cloud_executor.run_job=lambda run_id,**kwargs:original(run_id,session=session,**kwargs)
cloud_executor.dispatch_queued()
print(json.dumps(record))
