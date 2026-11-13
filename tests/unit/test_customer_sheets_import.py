"""Customer-owned Sheets read -> reviewed mapping -> existing import worker, no mail."""
import asyncio,json,uuid,re
from urllib.parse import unquote
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from test_customer_integrations import workspace,OWNER,TOKENS,start
from app.platform.context import workspace_scope
from app.integrations import service,google_sheets
from app.acquisition import sheets
from app.acquisition import service as acquisition
from app.acquisition.models import ColumnMapping,ProcessingOptions
from app.acquisition.worker import execute
from app.acquisition.config import AcquisitionSettings


def provider(monkeypatch):
 config=AcquisitionSettings(_env_file=None,AUTH_GOOGLE_ID='fixture-client',AUTH_GOOGLE_SECRET='fixture-secret',GOOGLE_SHEETS_REDIRECT_URI='https://example.test/acquisition/sheets/callback',ENABLE_LEAD_IMPORT=True,ENABLE_GOOGLE_SHEETS_IMPORT=True)
 monkeypatch.setattr('app.acquisition.config.settings',lambda:config)
 monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value=TOKENS))
 rows=[['Company','Email','Website']]+[[f'Owner supplied company {n}',f'public{n}@controlled.example',''] for n in range(10)]
 async def read(token,path,params):
  assert token=='synthetic-access'
  if 'fields' in params:return {'spreadsheetId':'controlled-sheet-id','properties':{'title':'Controlled company source'},'sheets':[{'properties':{'sheetId':1,'title':'Business rows','gridProperties':{'rowCount':11,'columnCount':3}}}]}
  match=re.search(r'!A(\d+):AX(\d+)',unquote(path));assert match
  return {'values':rows[int(match[1])-1:int(match[2])]}
 reader=AsyncMock(side_effect=read);monkeypatch.setattr(sheets,'read_with_token',reader)
 return reader


def connect(c,first):
 state,row,_=start(c);asyncio.run(service.connect(c,state,'controlled-code'));c.commit();return row['id']


def test_customer_sheets_import_preserves_ten_leads_and_reuses_stage_id_without_internal_account(workspace,monkeypatch):
 c,first,second,path=workspace;reader=provider(monkeypatch)
 with workspace_scope(c,OWNER,first):
  key=connect(c,first);request=uuid.uuid4();job=asyncio.run(google_sheets.stage_import(c,key,'controlled-sheet-id','Business rows',request));c.commit()
  assert job['status']=='MAPPING_REVIEW' and job['manifest']['row_count']==10
  assert job['origin']['workspace_connection_id']==key
  calls=reader.await_count;assert asyncio.run(google_sheets.stage_import(c,key,'controlled-sheet-id','Business rows',request))['id']==job['id'];assert reader.await_count==calls
  assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM acquisition_google_connections').fetchone()[0]==0
  c.execute('UPDATE automation_controls SET scan_paused=0 WHERE id=1')
  approved=acquisition.approve_import(c,job['id'],OWNER,ColumnMapping(company_name='Company',email='Email',website='Website'),ProcessingOptions(), 'Reviewed customer sheet',str(uuid.uuid4()));c.commit()
  execute(job['id'],path);result=acquisition.detail(c,job['id'])
  assert result['status']=='COMPLETED' and result['counts']['qualified']==10 and result['counts']['valid_rows']==10
  assert c.execute("SELECT COUNT(*) FROM businesses WHERE processing_status='QUALIFIED'").fetchone()[0]==10
  calls=reader.await_count;execute(job['id'],path);assert reader.await_count==calls
  for table in ('email_messages','lighthouse_results','client_reports'):assert c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0
 with workspace_scope(c,OWNER,second):
  with pytest.raises(HTTPException) as denied:asyncio.run(google_sheets.stage_import(c,key,'controlled-sheet-id','Business rows',uuid.uuid4()))
  assert denied.value.status_code==404
  with pytest.raises(HTTPException):acquisition.detail(c,job['id'])


def test_disconnect_after_mapping_stops_provider_reads_and_import(workspace,monkeypatch):
 c,first,second,path=workspace;reader=provider(monkeypatch)
 with workspace_scope(c,OWNER,first):
  key=connect(c,first);job=asyncio.run(google_sheets.stage_import(c,key,'controlled-sheet-id','Business rows',uuid.uuid4()));c.commit()
  c.execute('UPDATE automation_controls SET scan_paused=0 WHERE id=1');acquisition.approve_import(c,job['id'],OWNER,ColumnMapping(company_name='Company'),ProcessingOptions(),'Revoked import',str(uuid.uuid4()));service.disconnect(c,key);c.commit()
  reader.reset_mock();execute(job['id'],path)
  assert acquisition.detail(c,job['id'])['status']=='FAILED' and reader.await_count==0
  assert c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0


def test_customer_sheets_http_mapping_and_owned_worker_are_connected(workspace,monkeypatch):
 from fastapi.testclient import TestClient
 from app.api.server import app
 from app.platform.workspaces import select_workspace
 from app.api.organization import complete_onboarding
 c,first,second,path=workspace;reader=provider(monkeypatch)
 # Existing customer integration remains authorized for Lead Engine.
 c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id IN (?,?) AND product='LEADGEN'",(first,second));c.commit()
 with workspace_scope(c,OWNER,first):key=connect(c,first)
 complete_onboarding(c,first);complete_onboarding(c,second);select_workspace(c,OWNER,first);c.execute('UPDATE automation_controls SET scan_paused=0 WHERE id=1');c.commit()
 launcher=AsyncMock();monkeypatch.setattr('app.api.routes.acquisition.launch',launcher)
 with TestClient(app) as http:
  response=http.post('/api/organization/integrations/'+key+'/sheets/import',json={'spreadsheet':'controlled-sheet-id','sheet':'Business rows','request_id':str(uuid.uuid4())})
  assert response.status_code==201,response.text;job=response.json()
  assert job['status']=='MAPPING_REVIEW' and c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0]==0
  proposal=http.post('/api/acquisition/imports/'+job['id']+'/mapping/suggest');assert proposal.status_code==200
  reviewed=http.post('/api/acquisition/imports/'+job['id']+'/approve',json={'mapping':proposal.json()['mapping'],'processing':{},'name':'Reviewed HTTP sheet','reviewed':True,'request_id':str(uuid.uuid4())});assert reviewed.status_code==200,reviewed.text
  assert launcher.await_count==1;execute(job['id'],path)
  progress=http.get('/api/acquisition/jobs/'+job['id']);assert progress.status_code==200 and progress.json()['counts']['qualified']==10
  assert http.put('/api/organization/active',json={'organization_id':second}).status_code==200
  calls=reader.await_count;denied=http.post('/api/organization/integrations/'+key+'/sheets/import',json={'spreadsheet':'controlled-sheet-id','sheet':'Business rows','request_id':str(uuid.uuid4())});assert denied.status_code==404
  assert http.get('/api/acquisition/jobs/'+job['id']).status_code==404 and reader.await_count==calls
  assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
