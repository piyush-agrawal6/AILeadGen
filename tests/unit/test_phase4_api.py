from datetime import datetime,timezone,timedelta
import uuid
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.api.server import app
from app.database.connection import db_session
from app.database.models import Business,PipelineRun
from app.database.repositories import BusinessRepository,PipelineRunRepository
from app.database.prospects import ProspectRepository
from app.mail.config import MailSettings

@pytest.fixture
def client4(monkeypatch):
    monkeypatch.setattr('app.reports.service.launch_reports',lambda:None)
    with TestClient(app) as client:
        ids=[]
        with db_session() as c:
            for city in ('London','Manchester'):
                run=PipelineRun(market=city,vertical='hospitality',target=5);PipelineRunRepository(c).create(run)
                b=Business(name=city+' Hotel',normalized_name=city.lower()+' hotel',vertical='hospitality',city=city,run_id=run.id,website='https://'+city.lower()+'.example',domain=city.lower()+'.example',public_email='hello@'+city.lower()+'.example',processing_status='QUALIFIED');BusinessRepository(c).insert(b);ProspectRepository(c).observe(b);ids.append(b.id)
        yield client,ids

def test_sales_routes_followups_lists_views_bulk_and_suppression(client4):
    client,ids=client4
    created=client.post('/api/sales/lists',json={'name':'Acceptance priority'});assert created.status_code==201;lid=created.json()['id']
    assert client.post('/api/sales/bulk',json={'lead_ids':ids,'action':'list','list_id':lid}).json()['updated']==2
    assert client.get('/api/sales/lists').json()[0]['member_count']==2
    assert client.post('/api/sales/bulk',json={'lead_ids':ids,'action':'status','status':'READY_TO_CONTACT'}).status_code==200
    assert client.get('/api/sales/outreach').json()['counts']['ready']==2
    due=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    fid=client.post(f'/api/sales/leads/{ids[0]}/followups',json={'due_at':due}).json()['id']
    assert client.get('/api/sales/outreach?queue=overdue').json()['total']==1
    assert client.patch(f'/api/sales/leads/{ids[0]}/followups/{fid}',json={'status':'COMPLETED'}).status_code==200
    assert client.get('/api/sales/outreach?queue=overdue').json()['total']==0
    assert client.patch(f'/api/sales/leads/{ids[1]}/followups/{fid}',json={'status':'CANCELED'}).status_code==404
    assert client.post('/api/sales/views',json={'name':'High fit','filters':{'commercial_fit':'HIGH','sort_by':'commercial_fit'}}).status_code==201
    assert client.post('/api/sales/views',json={'name':'Unsafe','filters':{'sql':'DELETE FROM prospects'}}).status_code==422
    assert client.post('/api/sales/bulk',json={'lead_ids':ids,'action':'followup','due_at':(datetime.now(timezone.utc)+timedelta(days=3)).isoformat()}).status_code==200
    assert client.patch(f'/api/leads/{ids[0]}/workflow',json={'lead_status':'DO_NOT_CONTACT'}).status_code==200
    assert client.get('/api/sales/outreach').json()['total']==1
    assert client.get('/api/sales/outreach?queue=do_not_contact').json()['total']==1
    assert client.post(f'/api/sales/leads/{ids[0]}/followups',json={'due_at':due}).status_code==409
    assert client.patch(f'/api/sales/leads/{ids[1]}',json={'service_interest':'COMBINED','proposal_value':5000,'currency':'GBP','meeting_at':(datetime.now(timezone.utc)+timedelta(days=4)).isoformat()}).status_code==200

def test_email_api_account_never_exposes_secret_and_requires_review(client4,monkeypatch):
    client,ids=client4
    settings=MailSettings(_env_file=None,MAIL_PASSWORD='UNIT_ONLY_NEVER_EXPOSE',EMAIL_TEST_RECIPIENT='controlled@example.com',EMAIL_SEND_MODE='test')
    monkeypatch.setattr('app.mail.service.mail_settings',lambda:settings);monkeypatch.setattr('app.api.routes.mail.mail_settings',lambda:settings)
    mock=Mock();mock.send_message.return_value='ok';monkeypatch.setattr('app.mail.service.provider',lambda:mock)
    account=client.get('/api/email/account');assert account.status_code==200 and 'UNIT_ONLY_NEVER_EXPOSE' not in account.text
    setup=client.get(f'/api/email/leads/{ids[0]}/compose');assert setup.status_code==200 and setup.json()['recipients']==['hello@london.example']
    body={'to_address':'hello@london.example','subject':'Controlled acceptance','body_text':'A reviewed test message.'}
    preview=client.post(f'/api/email/leads/{ids[0]}/preview',json=body);assert preview.status_code==200 and preview.json()['to_address']=='controlled@example.com'
    assert client.post(f'/api/email/leads/{ids[0]}/send',json=body).status_code==422
    send={**body,'confirmation':'SEND','preview_token':preview.json()['preview_token'],'idempotency_key':str(uuid.uuid4())}
    result=client.post(f'/api/email/leads/{ids[0]}/send',json=send);assert result.status_code==200 and result.json()['status']=='SENT'
    assert client.post(f'/api/email/leads/{ids[0]}/send',json=send).json()['duplicate_prevented'];assert mock.send_message.call_count==1
    thread=result.json()['thread_id'];assert client.get(f'/api/email/leads/{ids[1]}/threads/{thread}').status_code==404
    assert client.get(f'/api/email/leads/{ids[0]}/threads/{thread}').json()[0]['test_mode']==1
    assert client.patch(f'/api/leads/{ids[0]}/workflow',json={'lead_status':'DO_NOT_CONTACT'}).status_code==200
    assert client.post(f'/api/email/leads/{ids[0]}/preview',json=body).status_code==409
