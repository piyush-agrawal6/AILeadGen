"""Deterministic prospecting data, refused outside isolated test mode."""
import json,re
from pathlib import Path
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.models import Business,PipelineRunEvent
from app.database.repositories import BusinessRepository,PipelineRunRepository,PipelineRunEventRepository
from app.database.prospects import ProspectRepository,now
from app.prospecting.intake import exports
from app.platform.context import organization


def run_fixture(run_id):
    if get_settings().app_env!='test':raise RuntimeError('Deterministic fixtures are forbidden outside test mode')
    with db_session() as c:
        runs=PipelineRunRepository(c);run=runs.get_by_id(run_id,organization=organization())
        if not run or run.status=='COMPLETED':return run
        campaign=c.execute('SELECT campaign_id FROM pipeline_runs WHERE id=? AND organization_id=?',(run_id,organization())).fetchone()[0]
        events=PipelineRunEventRepository(c);events.create(PipelineRunEvent(run_id=run_id,stage='DISCOVERY',event_type='FIXTURE_STARTED',message='Synthetic company evidence. No public site, provider or email was contacted.'))
        companies=[]
        for index in range(min(run.target,5)):
            if c.execute('SELECT cancellation_requested FROM pipeline_runs WHERE id=?',(run_id,)).fetchone()[0]:run.status='CANCELLED';runs.update(run);return run
            slug=re.sub(r'[^a-z0-9]+','-',run.market.lower())+'-'+run.vertical+'-'+str(index);source='fixture:'+slug
            existing=c.execute('SELECT id FROM businesses WHERE run_id=? AND external_osm_id=?',(run_id,source)).fetchone()
            b=BusinessRepository(c).get_by_id(existing[0]) if existing else Business(name=f'Fixture {run.vertical.replace("_"," ").title()} {index+1}',normalized_name=slug,vertical=run.vertical,city=run.market.split(',')[0],country='United States',country_code='US',phone='+15125550123',public_email='info@'+slug+'.example',website=None if index==0 else 'https://'+slug+'.example',domain=None if index==0 else slug+'.example',run_id=run_id,external_osm_id=source,processing_status='QUALIFIED',source_tags=json.dumps({'company_intelligence':{'status':'SYNTHETIC','summary':'Synthetic company fixture for isolated workflow verification.','pages':[]},'qualification':{'policy':'DISCOVERY_QUALIFIED','primary_reason':'QUALIFIED','analysis_status':'EXCLUDED_FROM_LEAD_ENGINE'}}))
            if not b.id:BusinessRepository(c).insert(b)
            ProspectRepository(c).observe(b,campaign,(run.run_configuration or {}).get('created_by'),organization=organization());companies.append(b)
        run.output_file,run.exported=exports(c,run,companies,Path('output/fixtures'))
        run.status='COMPLETED';run.raw_found=len(companies);run.qualified=len(companies);run.finished_at=now();runs.update(run)
        events.create(PipelineRunEvent(run_id=run_id,stage='COMPLETION',event_type='RUN_COMPLETED',message='Synthetic prospecting fixture completed without assessments.',completed=len(companies),total=len(companies)))
        return run
