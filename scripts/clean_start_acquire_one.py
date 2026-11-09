"""Re-query one genuine OSM business, then use the normal production pipeline."""
import os,sys,json,asyncio
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import certifi
os.environ.update(DATABASE_BACKEND='postgres',STORAGE_BACKEND='r2',APP_ENV='production',LEADENGINE_ROLE='worker',SCAN_EXECUTOR='gcp',GCP_PROJECT_ID='querryside',GCP_REGION='asia-south1',SSL_CERT_FILE=certifi.where())
from app.mail.config import mail_settings
from app.database.connection import db_session
from app.pipeline.runner import PipelineRunner
from app.discovery.osm import OSMDiscoveryProvider
statefile=Path('docs/clean-start-single-lead.json')
resume='--resume-official-source' in sys.argv
prior=json.loads(statefile.read_text()) if statefile.exists() else None
if prior and not resume:raise SystemExit('A clean-start acquisition was already attempted; inspect it before any additional discovery.')
if resume:assert prior and prior['raw_found']==0 and prior['qualified']==0
s=mail_settings();assert not (s.auto_scan_enabled or s.auto_email_enabled or s.sending_enabled)
assert json.loads(Path('docs/owner-clean-start.json').read_text())['cleared']
with db_session() as c:
 assert c.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==0
 assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==(1 if resume else 0)
class ExactPublicRecord(OSMDiscoveryProvider):
 def _fetch_overpass(self,ignored_query,url):
  # Same public provider and parser; narrow the query to one published business.
  if resume:
   data=json.loads(Path('data/cache/owner-exact-osm-record.json').read_text())
   assert len(data['elements'])==1 and data['elements'][0]['id']==617204465
   return data
  return super()._fetch_overpass('[out:json][timeout:30];way(617204465);out center;',url)
runner=PipelineRunner()
runner.discovery_coord.osm_provider=ExactPublicRecord()
runner.discovery_coord.overture_provider.search=lambda *args,**kwargs:[]
if not resume:statefile.write_text(json.dumps({'target':1,'public_source':'OpenStreetMap way/617204465','status':'STARTING','automatic_flags':False},indent=2))
run=asyncio.run(runner.run(market='Bristol, United Kingdom',vertical='dentists',target=1,run_id=prior['run_id'] if resume else None,enable_lighthouse=False,run_configuration={'target':1,'raw_budget':1,'exclude_chains':True,'lighthouse_enabled':False,'max_pages':8,'page_timeout':10,'site_timeout':45,'owner_controlled_acquisition':True}))
with db_session() as c:
 rows=c.execute("SELECT b.id,b.name,b.website,b.prospect_id,b.public_email,b.processing_status FROM businesses b WHERE b.run_id=?",(run.id,)).fetchall()
 result={'run_id':run.id,'target':1,'public_source':'OpenStreetMap way/617204465','status':run.status,'raw_found':run.raw_found,'qualified':run.qualified,'businesses':[dict(r) for r in rows],'automatic_flags':False}
statefile.write_text(json.dumps(result,indent=2));print(json.dumps(result))
if run.status!='COMPLETED' or run.qualified<1:raise SystemExit('The genuine single business did not qualify; do not send without further review.')
