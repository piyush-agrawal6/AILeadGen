from app.platform.context import organization
import json
from fastapi.testclient import TestClient
from app.api.server import app
from app.database.connection import db_session
from campaign_fixtures import campaign,lead
from app.automation.service import reconcile

def test_operations_read_models_filters_pages_and_saved_views(request):
 with TestClient(app) as client:
  with db_session() as c:
   from tests.workspace_fixtures import bind_internal_workspace
   bind_internal_workspace(c,request)
   cid=campaign(c,'London Hotels');lead(c,cid,91);lead(c,cid,92,email=False);reconcile(c)
  for path in ['/operations/dashboard','/operations/campaigns','/operations/campaigns/'+cid,'/operations/campaigns/'+cid+'/leads','/operations/runs','/operations/messages','/operations/schedules','/operations/reports']:
   r=client.get('/api'+path);assert r.status_code==200,(path,r.text)
  result=client.get('/api/operations/campaigns?market=London&vertical=hospitality&search=London').json()
  assert result['total']==1 and result['items'][0]['qualified']==2
  assert result['items'][0]['total_accounted']==2
  assert client.get('/api/operations/campaigns?search=Paris').json()['total']==0
  leads=client.get('/api/operations/campaigns/'+cid+'/leads?page=2&page_size=1').json()
  assert leads['total']==2 and len(leads['items'])==1
  masters=client.get('/api/automation/master-leads?campaign_id='+cid+'&minimum_score=80&sort=name').json()
  assert masters['total']==2
  body={'name':'Local hotels','filters':{'campaign_id':cid,'tab':'manual'}}
  saved=client.post('/api/operations/views',json=body);assert saved.status_code==201
  key=saved.json()['id'];assert client.get('/api/operations/views').json()[0]['name']=='Local hotels'
  assert client.put('/api/operations/views/'+key,json={**body,'name':'Manual hotels'}).status_code==200
  assert client.delete('/api/operations/views/'+key).status_code==200
  assert client.get('/api/operations/views').json()==[]
  assert client.get('/api/operations/campaigns?page=0').status_code==422
  assert client.get('/api/operations/campaigns?sort=DROP').status_code==422
  assert client.post('/api/workflow/runs',json={'kind':'OUTREACH'}).status_code==422
  assert client.post('/api/workflow/runs',json={'kind':'OUTREACH','campaign_id':cid,'emails':1}).status_code==422


def test_reply_inherits_campaign_and_actual_pitch_from_existing_thread(request):
 from test_campaign_outreach import message
 from app.api.routes.workflows import Run
 from app.workflows import service
 from app.database.prospects import now
 import uuid
 with TestClient(app) as client:
  with db_session() as c:
   from tests.workspace_fixtures import bind_internal_workspace
   bind_internal_workspace(c,request)
   cid=campaign(c,'Thread campaign');b,pid=lead(c,cid,999)
   r=service.create(c,Run(kind='OUTREACH',template_id=__import__('tests.workspace_fixtures',fromlist=['workspace_template']).workspace_template(c),campaign_id=cid,pitch_types=['WEBSITE','SECURITY']).model_dump(),'owner')
   mid=message(c,pid);outbound=c.execute('SELECT * FROM email_messages WHERE id=?',(mid,)).fetchone()
   c.execute("UPDATE outreach_run_items SET status='SENT',message_id=?,payload_json=? WHERE run_id=?",(mid,json.dumps({'pitch_types':['WEBSITE']}),r['id']))
   reply=str(uuid.uuid4());c.execute("INSERT INTO email_messages(id,prospect_id,account_id,thread_id,provider_message_id,direction,status,from_address,to_address,subject,body_text,created_at,organization_id) VALUES(?,?,?,?,?,'INBOUND','RECEIVED','public@example.com','planebyte@gmail.com','Re: Prior','Owner fixture reply',?,?)",(reply,pid,outbound['account_id'],outbound['thread_id'],'<'+reply+'@example.com>',now(),organization()))
  result=client.get('/api/operations/messages?direction=INBOUND&campaign_id='+cid+'&pitch=WEBSITE').json()
  assert result['total']==1 and result['items'][0]['campaign_id']==cid
  assert result['items'][0]['pitch_types']==['WEBSITE']
  detail=client.get('/api/workflow/messages/'+reply).json()
  assert detail['campaign_name']=='Thread campaign' and detail['pitch_types']==['WEBSITE']
  assert client.get('/api/operations/messages?direction=INBOUND&pitch=SECURITY').json()['total']==0
