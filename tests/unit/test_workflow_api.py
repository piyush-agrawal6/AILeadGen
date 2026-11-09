import uuid,json
from fastapi.testclient import TestClient
from app.api.server import app
from app.database.connection import db_session
from app.api.routes.workflows import Run


def test_schedule_crud_duplicate_pause_delete_and_history(monkeypatch):
 with TestClient(app) as client:
  body={'name':'Owner weekday plan','configuration':Run(name='Hotels',kind='SCAN').model_dump(),'enabled':False,'timezone':'Europe/London','frequency':'weekdays','start_at':'2027-01-04T06:00:00+00:00'}
  r=client.post('/api/workflow/schedules',json=body);assert r.status_code==201
  sid=r.json()['id']
  assert client.get('/api/workflow/schedules').json()[0]['enabled']==0
  assert client.post(f'/api/workflow/schedules/{sid}/enable').status_code==200
  assert client.post(f'/api/workflow/schedules/{sid}/pause').status_code==200
  assert client.put('/api/workflow/schedules/'+sid,json={**body,'name':'Updated plan'}).status_code==200
  assert client.post(f'/api/workflow/schedules/{sid}/duplicate').status_code==200
  assert len(client.get('/api/workflow/schedules').json())==2
  assert client.get(f'/api/workflow/schedules/{sid}/history').json()==[]
  assert client.request('DELETE','/api/workflow/schedules/'+sid,json={'confirmation':'wrong'}).status_code==422
  assert client.request('DELETE','/api/workflow/schedules/'+sid,json={'confirmation':'DELETE'}).status_code==200
  assert len(client.get('/api/workflow/schedules').json())==1
  with db_session() as c:assert c.execute('SELECT COUNT(*) FROM pipeline_runs').fetchone()[0]==0


def test_manual_scan_pause_resume_and_stop_use_existing_executor(monkeypatch):
 calls=[]
 async def start(*args):calls.append(('start',args))
 async def cancel(rid):calls.append(('cancel',rid));return True
 async def resume(rid):calls.append(('resume',rid));return True
 monkeypatch.setattr('app.api.services.scan_manager.scan_manager.executor.start',start)
 monkeypatch.setattr('app.api.services.scan_manager.scan_manager.cancel_scan',cancel)
 monkeypatch.setattr('app.api.services.scan_manager.scan_manager.resume_scan',resume)
 with TestClient(app) as client:
  assert client.put('/api/automation/controls',json={'scan_paused':False,'email_paused':True}).status_code==200
  config=Run(name='Manual UK hotels',kind='SCAN',target=2).model_dump()
  r=client.post('/api/workflow/runs',json=config);assert r.status_code==201;rid=r.json()['id']
  assert client.post('/api/workflow/runs',json=config).json()['id']==rid
  assert client.post(f'/api/workflow/runs/{rid}/start').status_code==200
  assert client.post(f'/api/workflow/runs/{rid}/start').status_code==200
  assert len([c for c in calls if c[0]=='start'])==1
  assert client.post(f'/api/workflow/runs/{rid}/pause').json()['status']=='PAUSED'
  assert client.post(f'/api/workflow/runs/{rid}/resume').json()['status']=='RUNNING'
  assert client.post(f'/api/workflow/runs/{rid}/stop').json()['status']=='CANCELLED'
  assert [x[0] for x in calls]==['start','cancel','resume','cancel']


def test_email_run_empty_and_disabled_sending_cannot_start(request):
 with TestClient(app) as client:
  from campaign_fixtures import campaign
  with db_session() as c:
   from tests.workspace_fixtures import bind_internal_workspace,workspace_template
   bind_internal_workspace(c,request);cid=campaign(c);template=workspace_template(c)
  body=Run(name='Review before send',kind='OUTREACH',campaign_id=cid,template_id=template).model_dump()
  eligible=client.post('/api/workflow/eligible',json=body);assert eligible.json()['total']==0
  r=client.post('/api/workflow/runs',json=body);rid=r.json()['id']
  prepared=client.post(f'/api/workflow/runs/{rid}/prepare');assert prepared.status_code==200 and prepared.json()['items']==[]
  assert client.post(f'/api/workflow/runs/{rid}/start').status_code in (409,503)
  with db_session() as c:assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
