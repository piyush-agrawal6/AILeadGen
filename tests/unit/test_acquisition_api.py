import asyncio,json,uuid
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.api.server import app
from app.acquisition.config import AcquisitionSettings
from app.acquisition.models import SearchIntent,ColumnMapping,ProcessingOptions
from app.acquisition import sheets,service
from app.database.migrations import MIGRATIONS
from test_automation import db
from test_acquisition_sources import INTENT,workbook


def enabled(monkeypatch):
 s=AcquisitionSettings(_env_file=None,ENABLE_AI_ACQUISITION=True,ENABLE_FIRECRAWL_ACQUISITION=True,ENABLE_LEAD_IMPORT=True,ENABLE_GOOGLE_SHEETS_IMPORT=True,GEMINI_API_KEY='server-ai',FIRECRAWL_API_KEY='server-firecrawl',AUTH_GOOGLE_ID='existing-client',AUTH_GOOGLE_SECRET='server-google')
 monkeypatch.setattr('app.acquisition.config.settings',lambda:s);monkeypatch.setattr('app.acquisition.ai.settings',lambda:s);monkeypatch.setattr('app.acquisition.sheets.settings',lambda:s)
 monkeypatch.setattr('app.api.routes.acquisition.launch',AsyncMock())
 return s

def test_intent_review_then_source_campaign_without_outreach(monkeypatch):
 enabled(monkeypatch)
 class Fake:
  parse_lead_search_intent=AsyncMock(return_value=SearchIntent.model_validate(INTENT))
 monkeypatch.setattr('app.acquisition.ai.provider',lambda c=None:Fake())
 with TestClient(app) as client:
  client.put('/api/automation/controls',json={'scan_paused':False,'email_paused':False})
  response=client.post('/api/acquisition/intent',json={'prompt':'Find 5 dentists in Bristol UK'});assert response.status_code==200,response.text
  assert response.json()['requires_review'] and not response.json()['acquisition_started']
  assert client.get('/api/operations/campaigns').json()['total']==0
  body={'intent':INTENT,'reviewed':False,'request_id':str(uuid.uuid4())};assert client.post('/api/acquisition/firecrawl',json=body).status_code==422
  body['reviewed']=True;r=client.post('/api/acquisition/firecrawl',json=body);assert r.status_code==201,r.text
  duplicate=client.post('/api/acquisition/firecrawl',json=body);assert duplicate.json()['id']==r.json()['id']
  processing=client.get('/api/acquisition/jobs/'+r.json()['id']).json()['configuration']['processing']
  assert processing['qualification_mode']=='CONTACTABLE_ONLY'
  assert not any(processing[k] for k in ('analyze_websites','analyze_seo','analyze_security','lighthouse'))
  page=client.get('/api/operations/campaigns?source_type=FIRECRAWL').json();assert page['total']==1 and page['items'][0]['source_type']=='FIRECRAWL'
  assert client.get('/api/operations/campaigns?source_type=OVERTURE').json()['total']==0
  assert client.get('/api/workflow/runs').json()['total']==0
  assert client.get('/api/operations/messages').json()['total']==0

def test_file_mapping_requires_review_then_same_campaign_model(monkeypatch):
 enabled(monkeypatch)
 mapping=ColumnMapping(company_name='Organisation',website='Site Address',email='Mail ID',phone='Telephone',city='Market',vertical='Category')
 class Fake:
  interpret_import_schema=AsyncMock(return_value=mapping)
 monkeypatch.setattr('app.acquisition.ai.provider',lambda c=None:Fake())
 with TestClient(app) as client:
  client.put('/api/automation/controls',json={'scan_paused':False,'email_paused':False})
  r=client.post('/api/acquisition/imports/files?filename=Unusual.xlsx&request_id='+str(uuid.uuid4()),content=workbook(),headers={'Content-Type':'application/octet-stream'});assert r.status_code==201,r.text
  jid=r.json()['id'];assert r.json()['status']=='MAPPING_REVIEW' and not r.json()['campaign_id']
  suggestion=client.post('/api/acquisition/imports/'+jid+'/mapping/suggest').json();assert suggestion['method']=='AI' and suggestion['rows_processed_by_ai']==0
  approval={'mapping':mapping.model_dump(),'processing':ProcessingOptions(default_vertical='dentists').model_dump(),'name':'Reviewed file campaign','request_id':str(uuid.uuid4()),'reviewed':True}
  r=client.post('/api/acquisition/imports/'+jid+'/approve',json=approval);assert r.status_code==200,r.text
  assert r.json()['campaign_id']
  assert client.get('/api/operations/campaigns?source_type=FILE_IMPORT').json()['total']==1
  assert client.get('/api/operations/messages').json()['total']==0
  assert client.post('/api/acquisition/imports/'+jid+'/approve',json=approval).status_code==200

def test_google_oauth_readonly_state_bound_actor_and_encrypted_tokens(db,monkeypatch):
 enabled(monkeypatch)
 from app.config.settings import get_settings
 monkeypatch.setattr(get_settings(),'api_signing_secret','test-server-encryption-key-at-least-32-characters')
 from urllib.parse import urlsplit,parse_qs
 flow=sheets.start(db,'owner');params=parse_qs(urlsplit(flow['authorization_url']).query)
 assert params['scope']==[sheets.SCOPE] and 'drive' not in params['scope'][0]
 assert params['code_challenge_method']==['S256']
 state=params['state'][0]
 monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value={'access_token':'secret-access-token','refresh_token':'secret-refresh-token','scope':sheets.SCOPE,'expires_in':3600}))
 import pytest
 from fastapi import HTTPException
 with pytest.raises(HTTPException):asyncio.run(sheets.connect(db,'other',state,'controlled-code'))
 result=asyncio.run(sheets.connect(db,'owner',state,'controlled-code'));assert result['connected']
 row=db.execute('SELECT * FROM acquisition_google_connections').fetchone();assert 'secret-refresh-token' not in row['tokens_ciphertext']
 assert sheets.decrypt(row['tokens_ciphertext'])['refresh_token']=='secret-refresh-token'
 with pytest.raises(HTTPException):asyncio.run(sheets.connect(db,'owner',state,'controlled-code'))

def test_google_sheet_batch_snapshot_mapping_no_write_api(db,monkeypatch):
 enabled(monkeypatch)
 async def meta(c,actor,value):return {'spreadsheet_id':'controlled-sheet-123','title':'Controlled Leads','tabs':[{'sheetId':0,'title':'Leads','gridProperties':{'rowCount':300,'columnCount':6}}]}
 reads=[]
 async def values(c,actor,sid,tab,start,end):
  reads.append((start,end))
  if start==1:return [['Organisation','Site Address','Mail ID','Telephone','Market','Category'],['Acme Dental','http://acme.test','info@acme.test','+441175551234','Bristol','Dental']]
  return [['Second Dental','http://second.test','','','Bristol','Dental']]
 monkeypatch.setattr(sheets,'metadata',meta);monkeypatch.setattr(sheets,'values',values)
 staged=asyncio.run(sheets.stage(db,'owner','controlled-sheet-123','Leads',str(uuid.uuid4())));assert staged['source_type']=='GOOGLE_SHEETS'
 r=service.job(db,staged['id']);asyncio.run(sheets.snapshot(db,r));r=service.job(db,staged['id']);book=service.source_book(r)
 assert book.inspect()['row_count']==2 and max(end-start for start,end in reads)<=249
 assert json.loads(r['manifest_json'])['snapshot_at']
 assert db.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]==0

def test_additive_schema_preserves_running_workflow(monkeypatch):
 import sqlite3
 from app.database import migrations
 from campaign_fixtures import campaign,lead
 c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
 full=list(migrations.MIGRATIONS);monkeypatch.setattr(migrations,'MIGRATIONS',full[:12]);migrations.run_migrations(c)
 cid=campaign(c);lead(c,cid,777);c.execute("UPDATE scan_campaigns SET status='RUNNING' WHERE id=?",(cid,));c.execute('UPDATE automation_controls SET scan_paused=0,email_paused=0');c.commit()
 baseline={t:[dict(r) for r in c.execute('SELECT * FROM '+t).fetchall()] for t in ('scan_campaigns','pipeline_runs','prospects','businesses','automation_controls')}
 monkeypatch.setattr(migrations,'MIGRATIONS',full);assert migrations.run_migrations(c)==len(full)-12
 for table,rows in baseline.items():
  after=[dict(r) for r in c.execute('SELECT * FROM '+table).fetchall()]
  assert [{k:r[k] for k in rows[0]} for r in after]==rows
 assert c.execute('SELECT source_type FROM scan_campaigns').fetchone()[0]=='OVERTURE'
 assert c.execute('SELECT COUNT(*) FROM acquisition_jobs').fetchone()[0]==0
 c.close()

def test_wrong_ai_target_fails_closed_before_cache_or_campaign(monkeypatch):
 enabled(monkeypatch)
 class WrongTarget:
  parse_lead_search_intent=AsyncMock(return_value=SearchIntent.model_validate({**INTENT,'targetQualifiedLeads':555}))
 monkeypatch.setattr('app.acquisition.ai.provider',lambda c=None:WrongTarget())
 with TestClient(app) as client:
  response=client.post('/api/acquisition/intent',json={'prompt':'Find 5 dentists in Bristol UK'})
  assert response.status_code==503 and 'changed the requested lead target' in response.json()['detail']['message']
  assert client.get('/api/operations/campaigns').json()['total']==0
  from app.database.connection import db_session
  with db_session() as c:assert c.execute('SELECT COUNT(*) FROM acquisition_ai_cache').fetchone()[0]==0
