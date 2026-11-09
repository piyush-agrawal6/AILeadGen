"""Saved search workflows, scope, criteria and pre-enrichment progressive results."""
import asyncio,json,uuid,sqlite3
import pytest
from fastapi import HTTPException
from test_prospecting_only import owned,company,batch,crawl
from app.platform.context import workspace_scope
from app.prospecting.searches import SaveSearch,save,get,list_searches,archive
from app.prospecting.criteria import evaluate,SearchCriteria
from app.database.models import Business
from app.pipeline.runner import PipelineRunner
from app.database.connection import db_session
from app.database import migrations


def test_saved_search_lifecycle_never_runs_jobs_and_guards_scope_revision_and_request(owned):
 c,path,org,other=owned;body=SaveSearch(name='Bristol dental',configuration={'kind':'SCAN','countries':['United Kingdom'],'verticals':['dentists'],'search_criteria':{'keywords':['clinic'],'employee_min':10}})
 with workspace_scope(c,'controlled@example.test',org):
  created=save(c,body);assert save(c,body)['id']==created['id']
  loaded=get(c,created['id']);assert loaded['configuration']['search_criteria']['employee_min']==10 and not loaded['configuration']['email_all_eligible']
  assert list_searches(c,'dental',page_size=1)['total']==1
  duplicate=save(c,SaveSearch(name='Copy',configuration=loaded['configuration']));assert duplicate['id']!=created['id']
  updated=save(c,SaveSearch(name='Updated',configuration=loaded['configuration'],revision=1),created['id']);assert updated['revision']==2
  with pytest.raises(HTTPException) as conflict:save(c,body.model_copy(update={'revision':1}),created['id'])
  assert conflict.value.status_code==409
  with pytest.raises(HTTPException):save(c,body.model_copy(update={'name':'Different'}))
  archive(c,created['id'],2);assert list_searches(c)['total']==1 and list_searches(c,archived=True)['total']==1
  for table in ('pipeline_runs','workflow_runs','email_messages'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
 with workspace_scope(c,'foreign@example.test',other):
  assert list_searches(c)['total']==0
  with pytest.raises(HTTPException) as denied:get(c,created['id'])
  assert denied.value.status_code==404
  with pytest.raises(HTTPException):archive(c,created['id'],3)
 c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=?",(org,));c.commit()
 with workspace_scope(c,'controlled@example.test',org):
  with pytest.raises(HTTPException) as denied:save(c,SaveSearch(name='Denied',configuration={'kind':'SCAN'}))
  assert denied.value.status_code==403
 with pytest.raises(HTTPException):list_searches(c)


def test_search_criteria_do_not_invent_employee_data_or_ignore_observed_exclusions():
 b=Business(name='Bristol Dental Clinic',normalized_name='bristol dental clinic',vertical='dentists',state='California',domain='dental.test')
 value=evaluate(b,{},SearchCriteria(keywords=['dental'],employee_min=10).model_dump());assert value['status']=='NEEDS_REVIEW'
 assert any(x['field']=='employee_min' and x['status']=='UNKNOWN' for x in value['criteria'])
 assert evaluate(b,{}, {'exclude_terms':['Dental']})['status']=='EXCLUDED'
 assert evaluate(b,{}, {'existing_companies':'EXCLUDE'},existing=True)['status']=='EXCLUDED'
 assert evaluate(b,{}, {'domains':['https://dental.test']})['status']=='MATCH'
 with pytest.raises(ValueError):SearchCriteria(domains=['http://127.0.0.1'])
 with pytest.raises(ValueError):SearchCriteria(employee_min=100,employee_max=10)


def test_source_results_are_visible_before_second_provider_and_resume_skips_finished_source(owned,tmp_path,monkeypatch,record_property):
 from app.discovery.resolver import DiscoveryCoordinator
 from app.config.markets import MarketInfo,BoundingBox
 from app.enrichment.crawler import WebsiteCrawler
 c,path,org,_=owned;calls=[];market=MarketInfo(query='Bristol, United Kingdom',city='Bristol',state='England',country='United Kingdom',country_code='GB',bbox=BoundingBox(min_lat=51.3,min_lon=-2.7,max_lat=51.6,max_lon=-2.4),center_lat=51.45,center_lon=-2.58);monkeypatch.setattr('app.discovery.resolver.resolve_market',lambda _:market)
 def business(n,source):return Business(name='Bristol Dental Clinic '+str(n),normalized_name='bristol dental clinic '+str(n),vertical='dentists',subcategory='dental_clinic',city='Bristol',country='United Kingdom',domain='dental'+str(n)+'.test',source_category='dentist',source_tags=json.dumps({'amenity':'dentist'}),external_overture_id='o-'+str(n) if source=='OVERTURE' else None,external_osm_id='node/'+str(n) if source=='OSM' else None,source_overture=source=='OVERTURE',source_osm=source=='OSM')
 def overture(*args,**kwargs):calls.append('OVERTURE');return [business(1,'OVERTURE')]
 first=[True]
 def osm(*args,**kwargs):
  calls.append('OSM')
  # This independent connection observes a committed company before any crawl.
  with db_session(path) as other:
   assert other.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==1
   assert other.execute('SELECT COUNT(*) FROM prospects WHERE organization_id=?',(org,)).fetchone()[0]==1
   assert other.execute('SELECT COUNT(*) FROM website_profiles').fetchone()[0]==0
  if first[0]:first[0]=False;raise asyncio.CancelledError()
  return [business(2,'OSM')]
 monkeypatch.setattr('app.discovery.overture.OvertureDiscoveryProvider.search',overture);monkeypatch.setattr('app.discovery.osm.OSMDiscoveryProvider.search',osm)
 async def no_crawl(*args,**kwargs):raise AssertionError('Companies without websites must not crawl')
 monkeypatch.setattr(WebsiteCrawler,'crawl',no_crawl)
 with workspace_scope(c,'controlled@example.test',org):
  runner=PipelineRunner(db_path=path,output_dir=tmp_path/'out');run=asyncio.run(runner.run('Bristol, United Kingdom','dentists',2,run_configuration={'target':2,'max_candidates':5}))
  assert run.status=='CANCELLED'
  result=asyncio.run(PipelineRunner(db_path=path,output_dir=tmp_path/'out').run('Bristol, United Kingdom','dentists',2,run_id=run.id,run_configuration={'target':2,'max_candidates':5}))
  assert result.status=='COMPLETED' and result.qualified==2
  assert calls==['OVERTURE','OSM','OSM']
  metadata=json.loads(c.execute("SELECT metadata_json FROM pipeline_run_events WHERE event_type='SOURCE_BATCH_SAVED' ORDER BY id LIMIT 1").fetchone()[0]);assert metadata['time_to_first_result_seconds']>=0
  record_property('fixture_time_to_first_result_seconds',metadata['time_to_first_result_seconds'])
  assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==2
  for table in ('lighthouse_results','findings','client_reports','email_messages'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0


def test_schema29_upgrade_repeatability_and_rollback_preserve_company_history(tmp_path,monkeypatch):
 latest=migrations.MIGRATIONS;before=sqlite3.connect(tmp_path/'before.db');before.row_factory=sqlite3.Row
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:28]);migrations.run_migrations(before)
 counts={table:before.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('organizations','scan_markets','schema_migrations','contacted_recipients')};before.commit()
 backup=sqlite3.connect(tmp_path/'rollback.db');before.backup(backup)
 monkeypatch.setattr(migrations,'MIGRATIONS',latest[:29]);assert migrations.run_migrations(before)==1;assert migrations.run_migrations(before)==0
 for table,count in counts.items():assert before.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==count+(1 if table=='schema_migrations' else 0)
 assert before.execute('PRAGMA foreign_key_check').fetchall()==[]
 restored=sqlite3.connect(tmp_path/'restore.db');backup.backup(restored);assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==28;assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 before.close();backup.close();restored.close()


def test_custom_industries_and_seven_country_geography_are_honest_inputs():
 from app.acquisition.models import SearchIntent,ProcessingOptions
 from app.acquisition.imports import normalize_row
 from app.acquisition.search_plan import queries
 from app.prospecting.criteria import capabilities
 for code in ('US','GB','CA','AU','DE','FR','IN'):
  intent=SearchIntent(verticals=['software_services'],countries=[code],queries=['software development contact email'])
  assert len(intent.countries)==1 and queries(intent,2)
 b=normalize_row({'company_name':'Controlled Software','vertical':'Software services','country':'Germany'},ProcessingOptions(),'FILE_IMPORT')
 assert b.vertical=='software_services' and b.country=='Germany'
 assert all(not item['live_coverage_verified'] for item in capabilities()['countries'])
