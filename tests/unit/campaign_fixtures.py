"""Campaign fixtures for isolated database tests; never network discovery or SMTP."""
import json,uuid
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository,now
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
EVIDENCE={'WEBSITE':[{'code':'HTTP_ONLY','detail':'Final page uses HTTP.','points':30},{'code':'NO_MOBILE_VIEWPORT','detail':'No viewport declaration observed.','points':20},{'code':'NO_PRIMARY_CTA','detail':'No enquiry action observed.','points':15}],'SEO':[{'code':'MISSING_META_DESCRIPTION','detail':'No description observed.','points':20},{'code':'NO_STRUCTURED_DATA','detail':'No structured data observed.','points':20}],'SECURITY':[]}
def campaign(c,name='London Hospitality',cid=None):
 version=c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
 if version<16:
  cid=cid or str(uuid.uuid4());c.execute("INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,status,completed_at) VALUES(?,'owner',?,?,1,'COMPLETED',?)",(cid,json.dumps({'name':name,'cities':['London'],'verticals':['hospitality']}),now(),now()));return cid
 cid=cid or str(uuid.uuid4());c.execute("INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,status,completed_at,organization_id) VALUES(?,'owner',?,?,1,'COMPLETED',?,?)",(cid,json.dumps({'name':name,'cities':['London'],'verticals':['hospitality']}),now(),now(),PLANEBYTE_ORGANIZATION_ID));return cid

def qualify(c,b):
 c.execute("UPDATE businesses SET website_status='REACHABLE' WHERE id=?",(b.id,))
 c.execute("INSERT INTO opportunity_scores(business_id,website_opportunity_score,seo_opportunity_score,security_opportunity_score,primary_opportunity,contactability_level,scoring_version,evidence_json,created_at) VALUES(?,85,65,0,'WEBSITE','HIGH','qa',?,?) ON CONFLICT(business_id) DO UPDATE SET evidence_json=excluded.evidence_json",(b.id,json.dumps(EVIDENCE),now()))

def lead(c,cid,n=0,email=True,evidence=True):
 run=PipelineRun(market='London, United Kingdom',vertical='hospitality',target=1,status='COMPLETED',started_at=now(),finished_at=now());PipelineRunRepository(c).create(run,organization=PLANEBYTE_ORGANIZATION_ID);c.execute('UPDATE pipeline_runs SET campaign_id=? WHERE id=?',(cid,run.id))
 b=Business(name=f'Hotel {n}',normalized_name=f'hotel {n}',vertical='hospitality',city='London',country='United Kingdom',website=f'http://hotel{n}.example',domain=f'hotel{n}.example',public_email=f'public@hotel{n}.example' if email else None,processing_status='QUALIFIED',run_id=run.id)
 BusinessRepository(c).insert(b)
 if (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)<16:
  from tests.workspace_fixtures import historical_observation
  pid=historical_observation(c,b)
 else:pid=ProspectRepository(c).observe(b,organization=PLANEBYTE_ORGANIZATION_ID)
 c.execute("INSERT INTO business_intelligence(business_id,prospect_id,classification_version,business_scale,scale_reason,scale_confidence,footprint_json,commercial_fit,commercial_reason,created_at) VALUES(?,?,'qa','LOCAL','fixture',1,'{}','HIGH','fixture',?)",(b.id,pid,now()))
 if email:c.execute("INSERT INTO contacts(business_id,contact_type,contact_value,source_url,source_type,confidence,is_public_business_contact,is_valid) VALUES(?,'email',?,?,'PUBLIC_WEBSITE',1,1,1)",(b.id,b.public_email,b.website+'/contact'))
 if evidence:qualify(c,b)
 return b,pid
