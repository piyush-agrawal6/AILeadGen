import asyncio,io,json,uuid
from unittest.mock import AsyncMock
import httpx,pytest
from openpyxl import Workbook
from pydantic import ValidationError
from fastapi.testclient import TestClient
from test_automation import db
from app.acquisition.models import SearchIntent,ColumnMapping,ProcessingOptions
from app.acquisition.config import AcquisitionSettings
from app.acquisition.ai import GeminiInstructionProvider,AiUnavailable,sanitized_sample,cached
from app.acquisition.firecrawl import FirecrawlLeadSource,SourceUnavailable
from app.acquisition.imports import Spreadsheet,normalize_row,ImportInvalid
from app.acquisition import service
from app.api.server import app

INTENT={'targetQualifiedLeads':5,'verticals':['dentists'],'countries':['United Kingdom'],'cities':['Bristol'],'businessSizes':['LOCAL','SMALL_GROUP','MID_MARKET'],'opportunities':['WEBSITE','SEO'],'contactRequired':True,'source':'FIRECRAWL','queries':['dentists Bristol UK']}

def test_new_flags_independent_and_secret_fields_not_serialized():
 s=AcquisitionSettings(_env_file=None,GEMINI_API_KEY='private-gemini',FIRECRAWL_API_KEY='private-firecrawl')
 assert not any((s.enable_ai,s.enable_firecrawl,s.enable_import,s.enable_sheets))
 assert 'private-' not in str(s) and 'gemini_key' not in s.model_dump() and 'firecrawl_key' not in s.model_dump()
 with pytest.raises(ValidationError):SearchIntent.model_validate({**INTENT,'targetQualifiedLeads':'5'})
 with pytest.raises(ValidationError):SearchIntent.model_validate({**INTENT,'emails':['invented@example.com']})

def test_gemini_strict_planning_and_failure_isolation():
 seen=[]
 def transport(request):
  body=json.loads(request.content);seen.append(body)
  assert 'responseFormat' in body['generationConfig']
  return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(INTENT)}]}}]})
 provider=GeminiInstructionProvider(AcquisitionSettings(_env_file=None,GEMINI_API_KEY='server-secret'),httpx.MockTransport(transport))
 result=asyncio.run(provider.parse_lead_search_intent('Find 5 dentists in Bristol UK'))
 assert result.targetQualifiedLeads==5 and result.cities==['Bristol'] and len(seen)==1
 failing=GeminiInstructionProvider(provider.config,httpx.MockTransport(lambda _:httpx.Response(503,json={'error':'unavailable'})))
 with pytest.raises(AiUnavailable,match='unavailable'):asyncio.run(failing.parse_lead_search_intent('Find dentists'))
 malformed=GeminiInstructionProvider(provider.config,httpx.MockTransport(lambda _:httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"business":"invented"}'}]}}]})))
 with pytest.raises(AiUnavailable):asyncio.run(malformed.parse_lead_search_intent('Find dentists'))

def test_cached_plans_do_not_call_ai_per_row(db):
 produced=[]
 async def produce():produced.append(1);return SearchIntent.model_validate(INTENT)
 async def run():
  a,hit=await cached(db,'owner','intent',{'prompt':'same'},produce,SearchIntent);assert not hit
  b,hit=await cached(db,'owner','intent',{'prompt':'same'},produce,SearchIntent);assert hit and a==b
  await cached(db,'other','intent',{'prompt':'same'},produce,SearchIntent)
 asyncio.run(run());assert len(produced)==2
 sample=sanitized_sample([['Person Name','private.person@business.com','+44 123456789','https://site.test/private?token=secret']] * 10000)
 assert len(sample)==3 and 'private.person' not in json.dumps(sample) and 'Person Name' not in json.dumps(sample) and 'token' not in json.dumps(sample)

def test_firecrawl_bounded_search_and_observation_validation():
 requests=[]
 def handler(request):
  body=json.loads(request.content);requests.append(body);assert body['limit']<=50
  return httpx.Response(200,json={'success':True,'data':{'web':[{'url':'https://acme.test','title':'Acme Dental'}]}})
 source=FirecrawlLeadSource(AcquisitionSettings(_env_file=None,FIRECRAWL_API_KEY='server-only'),httpx.MockTransport(handler))
 assert len(asyncio.run(source.search('dentists Bristol UK',100))['items'])==1
 page={'json':{'company_name':'Acme Dental','email':'invented@acme.test','city':'Bristol'},'html':'<html><h1>Acme Dental</h1><p>Bristol</p><a href="mailto:info@acme.test">Email</a></html>','metadata':{'sourceURL':'https://acme.test'}}
 row,error=source.candidate('https://acme.test',page);assert not error and row['email']=='info@acme.test'
 assert 'invented@' not in json.dumps(row)
 assert source.candidate('https://acme.test',{**page,'json':{'company_name':'An Invented Company'}})[0] is None
 assert source.candidate('https://booking.com/hotel',page)[0] is None
 with pytest.raises(SourceUnavailable):asyncio.run(source.scrape('http://169.254.169.254/latest/meta-data'))

def workbook():
 wb=Workbook();ws=wb.active;ws.title='Unusual headings';ws.append(['Organisation','Site Address','Mail ID','Telephone','Market','Category'])
 ws.append(['Acme Dental','http://acme.test','info@acme.test','+44 117 555 1234','Bristol','Dental']);ws.append(['Broken URL','http://127.0.0.1','wrong email','','Bristol','Dental']);ws.append(['Acme Dental','http://acme.test','info@acme.test','+44 117 555 1234','Bristol','Dental'])
 out=io.BytesIO();wb.save(out);return out.getvalue()

def test_unusual_excel_headers_mapping_and_partial_invalid_rows():
 book=Spreadsheet(workbook(),'Unusual.xlsx');manifest=book.inspect();assert manifest['row_count']==3
 mapping=ColumnMapping(company_name='Organisation',website='Site Address',email='Mail ID',phone='Telephone',city='Market',vertical='Category')
 parsed=[];invalid=[]
 for row,data in book.mapped_rows(manifest['sheet'],mapping):
  try:parsed.append(normalize_row(data,ProcessingOptions(default_vertical='dentists'),'FILE_IMPORT'))
  except ImportInvalid:invalid.append(row)
 assert len(parsed)==2 and invalid==[3] and parsed[0].subcategory=='dental_clinic'
 assert parsed[0].normalized_name=='acme dental'
 with pytest.raises(ValueError):ColumnMapping(company_name='invented').validate_headers(manifest['headers'])
 with pytest.raises(ImportInvalid):Spreadsheet(b'x'*1_000_001,'huge.csv')
 with pytest.raises(ImportInvalid):Spreadsheet(b'not zip','invalid.xlsx')

def test_staged_file_does_not_write_master_leads_until_review(db):
 r=service.stage_file(db,'owner','Unusual.xlsx',workbook(),str(uuid.uuid4()))
 assert r['status']=='MAPPING_REVIEW' and not r['campaign_id']
 assert db.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==0
 assert db.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
 assert service.source_book(service.job(db,r['id'])).inspect()['row_count']==3

def test_features_disabled_do_not_affect_existing_outreach_or_scans(monkeypatch):
 s=AcquisitionSettings(_env_file=None)
 monkeypatch.setattr('app.acquisition.config.settings',lambda:s)
 monkeypatch.setattr('app.api.routes.acquisition.settings',lambda:s)
 with TestClient(app) as client:
  response=client.post('/api/acquisition/intent',json={'prompt':'Find dentists in Bristol'})
  assert response.status_code==503 and response.json()['detail']['code']=='ACQUISITION_FEATURE_DISABLED'
  assert client.get('/api/workflow/safety').status_code==200
  assert client.get('/api/operations/campaigns').status_code==200
  status=client.get('/api/acquisition/settings').json();assert not any(status['features'].values())
  assert 'gemini_key' not in json.dumps(status) and 'firecrawl_key' not in json.dumps(status)

def test_optional_contact_crawl_honors_durable_page_budget(db,tmp_path):
 from app.acquisition.enrichment import optional_contacts
 from app.acquisition.models import Budgets
 from app.database.connection import db_session
 import sqlite3
 path=tmp_path/'crawl.db'
 r=service.create_job(db,'FIRECRAWL','owner',str(uuid.uuid4()),{},{});db.commit()
 disk=sqlite3.connect(path);db.backup(disk);disk.close()
 source=type('Source',(),{'bounded_crawl':AsyncMock(return_value=[{'html':'<a href="mailto:office@acme.test">Email</a>','metadata':{'sourceURL':'https://acme.test/contact'}}])})()
 data={'website':'https://acme.test','contact_page':'https://acme.test/contact','field_sources':{}}
 budget=Budgets(max_crawl_pages=1)
 result=asyncio.run(optional_contacts(r['id'],dict(data),source,budget,path));assert result['email']=='office@acme.test'
 asyncio.run(optional_contacts(r['id'],dict(data),source,budget,path));assert source.bounded_crawl.await_count==1
 other={**data,'contact_page':'https://acme.test/about'}
 result=asyncio.run(optional_contacts(r['id'],other,source,budget,path));assert 'email' not in result and source.bounded_crawl.await_count==1
 with db_session(path) as c:assert c.execute("SELECT COUNT(*) FROM acquisition_requests WHERE kind='crawl'").fetchone()[0]==1


def test_source_execution_deadline_covers_all_import_stages(db,monkeypatch):
 from contextlib import contextmanager
 from types import SimpleNamespace
 from app.acquisition import worker
 r=service.create_job(db,'FILE_IMPORT','owner',str(uuid.uuid4()),{},{});db.commit()
 @contextmanager
 def session(*args):yield db
 async def slow_import(*args):await asyncio.sleep(1)
 monkeypatch.setattr(worker,'db_session',session)
 monkeypatch.setattr(worker,'import_job',slow_import)
 monkeypatch.setattr(worker,'Budgets',SimpleNamespace(model_validate=lambda _:SimpleNamespace(max_runtime_seconds=0.01)))
 with pytest.raises(SourceUnavailable,match='runtime budget reached'):asyncio.run(worker.process(r['id']))

def test_gemini_retries_explicit_transient_rejection_with_bounded_attempts(monkeypatch):
 delays=[];attempts=[]
 async def pause(seconds):delays.append(seconds)
 monkeypatch.setattr('app.acquisition.ai.asyncio.sleep',pause)
 def transport(request):
  attempts.append(request)
  if len(attempts)<2:return httpx.Response(503)
  return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(INTENT)}]}}]})
 config=AcquisitionSettings(_env_file=None,GEMINI_API_KEY='server-only')
 provider=GeminiInstructionProvider(config,httpx.MockTransport(transport))
 assert asyncio.run(provider.parse_lead_search_intent('Find 5 dentists Bristol')).targetQualifiedLeads==5
 assert len(attempts)==2 and delays==[1]
 attempts.clear();delays.clear()
 def failing(request):attempts.append(request);return httpx.Response(503)
 provider=GeminiInstructionProvider(config,httpx.MockTransport(failing))
 with pytest.raises(AiUnavailable,match='HTTP 503'):asyncio.run(provider.parse_lead_search_intent('Find dentists'))
 assert len(attempts)==3 and delays==[1,2]

@pytest.mark.parametrize('status',[400,401,403,429])
def test_gemini_does_not_retry_permission_quota_or_invalid_requests(status):
 requests=[]
 def transport(request):requests.append(request);return httpx.Response(status)
 provider=GeminiInstructionProvider(AcquisitionSettings(_env_file=None,GEMINI_API_KEY='server-only'),httpx.MockTransport(transport))
 with pytest.raises(AiUnavailable):asyncio.run(provider.parse_lead_search_intent('Find dentists'))
 assert len(requests)==1

def test_gemini_does_not_repeat_uncertain_timeout():
 requests=[]
 def transport(request):requests.append(request);raise httpx.ReadTimeout('uncertain',request=request)
 provider=GeminiInstructionProvider(AcquisitionSettings(_env_file=None,GEMINI_API_KEY='server-only'),httpx.MockTransport(transport))
 with pytest.raises(AiUnavailable):asyncio.run(provider.parse_lead_search_intent('Find dentists'))
 assert len(requests)==1

def test_gemini_total_deadline_covers_provider_read(monkeypatch):
 from app.acquisition import ai
 deadline=asyncio.timeout;attempts=[]
 monkeypatch.setattr(ai.asyncio,'timeout',lambda _:deadline(0.01))
 async def transport(request):
  attempts.append(request)
  await asyncio.sleep(1)
  return httpx.Response(200,json={})
 provider=GeminiInstructionProvider(AcquisitionSettings(_env_file=None,GEMINI_API_KEY='server-only'),httpx.MockTransport(transport))
 with pytest.raises(AiUnavailable):asyncio.run(provider.parse_lead_search_intent('Find dentists'))
 assert len(attempts)==1

def test_explicit_target_mismatch_is_rejected_even_with_valid_json_schema():
 from app.acquisition.ai import explicit_target
 payloads=[]
 def transport(request):
  payloads.append(json.loads(request.content))
  return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps({**INTENT,'targetQualifiedLeads':555})}]}}]})
 provider=GeminiInstructionProvider(AcquisitionSettings(_env_file=None,GEMINI_API_KEY='server-only'),httpx.MockTransport(transport))
 with pytest.raises(AiUnavailable,match='changed the requested lead target'):asyncio.run(provider.parse_lead_search_intent('Find 5 dentists in Bristol UK'))
 schema=payloads[0]['generationConfig']['responseFormat']['text']['schema']
 assert schema['properties']['targetQualifiedLeads']['enum']==[5] and 'targetQualifiedLeads' in schema['required']
 assert explicit_target('Find 1,000 qualified businesses in London')==1000
 assert explicit_target('Find dentists in Bristol founded in 1985') is None
 with pytest.raises(AiUnavailable):explicit_target('Find 5 dentists; target 50 leads')


def test_intent_cache_revalidates_target_and_never_caches_invalid_generation(db):
 from app.acquisition.ai import validate_intent
 produced=[]
 async def valid():produced.append(1);return SearchIntent.model_validate(INTENT)
 validator=lambda result:validate_intent('Find 5 dentists Bristol',result)
 async def run():
  await cached(db,'owner','LEAD_INTENT',{'prompt':'Find 5 dentists Bristol'},valid,SearchIntent,validator)
  db.execute('UPDATE acquisition_ai_cache SET result_json=?',(json.dumps({**INTENT,'targetQualifiedLeads':555}),));db.commit()
  result,hit=await cached(db,'owner','LEAD_INTENT',{'prompt':'Find 5 dentists Bristol'},valid,SearchIntent,validator)
  assert not hit and result.targetQualifiedLeads==5
  async def bad():return SearchIntent.model_validate({**INTENT,'targetQualifiedLeads':555})
  with pytest.raises(AiUnavailable):await cached(db,'owner','LEAD_INTENT',{'prompt':'different invalid request'},bad,SearchIntent,validator)
 asyncio.run(run());assert len(produced)==2
 assert db.execute('SELECT COUNT(*) FROM acquisition_ai_cache').fetchone()[0]==1

def test_contactable_identity_ignores_embedded_widget_brand():
 from bs4 import BeautifulSoup
 from app.acquisition.firecrawl import public_company_name
 html='<html><head><title>Queen Square Dental Clinic | Bristol Dentist</title></head><body><meta property="og:site_name" content="Working Feedback"><meta property="og:url" content="https://workingfeedback.co.uk/reviews"></body></html>'
 assert public_company_name(BeautifulSoup(html,'html.parser'),'https://queensquareclinic.com/')=='Queen Square Dental Clinic'
 html='<title>Home | Dentist</title><script type="application/ld+json">{"@type":"Dentist","name":"Redland Dental","url":"https://redlanddental.co.uk"}</script><meta property="og:site_name" content="Facebook">'
 assert public_company_name(BeautifulSoup(html,'html.parser'),'https://redlanddental.co.uk/')=='Redland Dental'

def test_embedded_titles_and_directory_results_are_not_company_identity():
 from bs4 import BeautifulSoup
 from app.acquisition.firecrawl import public_company_name,discovery_url_allowed
 html='<title>Instagram photos for @oldlanddental</title><title>Contact Us | Oldland Dental Practice</title>'
 assert public_company_name(BeautifulSoup(html,'html.parser'),'https://oldlanddental.co.uk/contact-us')=='Oldland Dental Practice'
 assert public_company_name(BeautifulSoup('<title>Copy link</title>','html.parser'),'https://clinic.example/')==''
 assert not discovery_url_allowed('https://www.bradleystokejournal.co.uk/healthcare/dentists')
 assert not discovery_url_allowed('https://www.cqc.org.uk/location/1/contact')
 assert discovery_url_allowed('https://oldlanddental.co.uk/contact-us')
