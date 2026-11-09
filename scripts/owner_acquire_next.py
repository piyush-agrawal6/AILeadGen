"""Reacquire one published Overture seed; recompute every audit/qualification fact."""
import sys,os,json,asyncio
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi,requests
os.environ.update(DATABASE_BACKEND='postgres',STORAGE_BACKEND='r2',APP_ENV='production',LEADENGINE_ROLE='worker',SCAN_EXECUTOR='gcp',GCP_PROJECT_ID='querryside',GCP_REGION='asia-south1',SSL_CERT_FILE=certifi.where())
from app.database.connection import db_session
from app.database.models import Business
from app.pipeline.runner import PipelineRunner
from app.normalization.businesses import normalize_business
from app.mail.config import mail_settings
s=mail_settings();assert not(s.sending_enabled or s.auto_scan_enabled or s.auto_email_enabled)
p=Path('docs/owner-next-acquisition.json');assert not p.exists()
seed=json.loads(Path('data/cache/owner-next-business-seed.json').read_text())
r=requests.get(seed['website'],timeout=25);assert r.status_code==200
assert 'homestay' in r.text.lower()
b=normalize_business(Business(name=seed['name'],normalized_name='',vertical=seed['vertical'],external_overture_id=seed['external_overture_id'],website=r.url,city=seed['city'],country=seed['country'],country_code=seed['country_code'],address=seed['address'],source_category=seed['source_category'],source_tags=seed['source_tags_json'],source_overture=True,source_confidence=0.8,operating_status='active'))
with db_session() as c:
 assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==1
 assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
runner=PipelineRunner();runner.discovery_coord.overture_provider.search=lambda *a,**kw:[b];runner.discovery_coord.osm_provider.search=lambda *a,**kw:[]
p.write_text(json.dumps({'status':'STARTING','target':1,'discovery_seed':'previously published Overture place; live official website reconfirmed','restored_old_findings':False},indent=2))
run=asyncio.run(runner.run(market='London, United Kingdom',vertical='hospitality',target=1,enable_lighthouse=False,run_configuration={'target':1,'raw_budget':1,'quality':'high_intent','opportunities':['WEBSITE','SEO','SECURITY'],'business_scales':['LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL'],'results':'all','exclude_chains':True,'lighthouse_enabled':False,'max_pages':8,'site_timeout':45,'owner_controlled_acquisition':True}))
with db_session() as c:
 rows=c.execute('SELECT id,name,website,prospect_id,public_email,processing_status FROM businesses WHERE run_id=?',(run.id,)).fetchall()
 result={'run_id':run.id,'target':1,'raw_found':run.raw_found,'qualified':run.qualified,'status':run.status,'quality':'high_intent','businesses':[dict(x) for x in rows],'automatic_flags':False,'restored_old_findings':False}
p.write_text(json.dumps(result,indent=2));print(json.dumps(result))
