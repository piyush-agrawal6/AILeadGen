import asyncio,json,sqlite3
import httpx,pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import ValidationError
from test_people import owned,seed
from app.config.settings import get_settings
from app.platform.context import workspace_scope
from app.webhooks import service,worker
from app.people import service as people
from app.sales import tasks
from app.database import migrations


@pytest.fixture
def hooks(owned,monkeypatch):
    c,path,org,other=owned;config=get_settings()
    monkeypatch.setattr(config,'heysow_webhooks_enabled',True)
    monkeypatch.setattr(config,'heysow_integration_encryption_key',Fernet.generate_key().decode())
    return c,path,org,other


def endpoint(c,topics=None):
    return service.save(c,service.Endpoint(name='Controlled receiver',url='https://receiver.example.com/events',topics=topics or list(service.TOPICS)))


def test_scoped_encrypted_endpoint_events_and_real_signature(hooks):
    c,_,org,other=hooks
    with workspace_scope(c,'controlled@example.test',org):
        created=endpoint(c);key=created['endpoint']['id'];secret=created['signing_secret'];assert len(secret)>=40
        assert secret not in json.dumps(service.listing(c))
        assert secret not in c.execute('SELECT signing_secret_ciphertext FROM webhook_endpoints WHERE id=?',(key,)).fetchone()[0]
        company=seed(c,org);person=people.save(c,company.id,people.Person(name='Avery Example'))
        tasks.create(c,tasks.Task(business_id=company.id,title='Review company evidence',task_type='REVIEW',due_at='2026-12-01T09:00:00Z'));c.commit()
        history=service.history(c,key);assert history['total']==3
        assert {row['topic'] for row in history['items']}=={'company.created','contact.created','task.created'}
        delivery=next(item for item in history['items'] if item['topic']=='contact.created');calls=[]
        def receive(request):
            body=request.content;payload=json.loads(body);calls.append(payload)
            assert request.headers['X-PlaneByte-Signature']==service.signature(secret,request.headers['X-PlaneByte-Timestamp'],body)
            assert payload['data']['contact_id']==person['id'] and 'work_email' not in payload['data']
            assert request.headers['Idempotency-Key']==delivery['id']
            return httpx.Response(204)
        transport=httpx.MockTransport(receive)
        assert asyncio.run(worker.deliver(c,key,delivery['id'],transport))=='DELIVERED'
        assert asyncio.run(worker.deliver(c,key,delivery['id'],transport))=='NOT_DUE' and len(calls)==1
    with workspace_scope(c,'foreign@example.test',other):
        with pytest.raises(HTTPException) as denied:service.owned(c,key)
        assert denied.value.status_code==404 and service.listing(c)['items']==[]
    with pytest.raises(HTTPException):service.listing(c)


def test_retries_are_bounded_redirects_pause_and_receiver_body_is_never_stored(hooks):
    c,_,org,_=hooks
    with workspace_scope(c,'controlled@example.test',org):
        created=endpoint(c,['company.created']);key=created['endpoint']['id'];seed(c,org);c.commit();delivery=service.history(c,key)['items'][0]
        failures=httpx.MockTransport(lambda request:httpx.Response(503,text='private receiver diagnostics'))
        assert asyncio.run(worker.deliver(c,key,delivery['id'],failures))=='RETRY'
        result=service.history(c,key)['items'][0];assert result['attempts']==1 and result['next_attempt_at']>result['created_at']
        assert asyncio.run(worker.deliver(c,key,delivery['id'],failures))=='NOT_DUE'
        for attempt in range(2,6):
            c.execute("UPDATE webhook_deliveries SET next_attempt_at='2000-01-01T00:00:00+00:00' WHERE id=?",(delivery['id'],));c.commit()
            result=asyncio.run(worker.deliver(c,key,delivery['id'],failures))
        assert result=='FAILED' and service.history(c,key)['items'][0]['attempts']==5
        with pytest.raises(HTTPException):service.retry(c,key,delivery['id'])
        assert 'private receiver diagnostics' not in json.dumps(service.history(c,key))
        service.emit(c,'company.created','new-controlled-event',{'business_id':999});c.commit()
        fresh=service.history(c,key)['items'][0];calls=[]
        redirect=httpx.MockTransport(lambda request:(calls.append(str(request.url)) or httpx.Response(302,headers={'Location':'http://127.0.0.1/private'})))
        assert asyncio.run(worker.deliver(c,key,fresh['id'],redirect))=='FAILED'
        assert len(calls)==1 and service.owned(c,key)['status']=='PAUSED'


def test_disable_worker_revocation_recovery_and_idempotent_events(hooks,monkeypatch):
    c,path,org,_=hooks
    with workspace_scope(c,'controlled@example.test',org):
        key=endpoint(c,['company.created'])['endpoint']['id'];seed(c,org);c.commit();item=service.history(c,key)['items'][0]
        transport=httpx.MockTransport(lambda request:httpx.Response(200))
        c.execute("UPDATE webhook_deliveries SET status='DELIVERING',lease_owner='old-process',lease_until='2000-01-01T00:00:00+00:00',attempts=1 WHERE id=?",(item['id'],));c.commit()
        assert asyncio.run(worker.deliver(c,key,item['id'],transport))=='DELIVERED'
        service.emit(c,'company.created','stable-event',{'business_id':1});service.emit(c,'company.created','stable-event',{'business_id':1});c.commit()
        assert service.history(c,key)['total']==2
        monkeypatch.setattr(get_settings(),'heysow_webhooks_enabled',False)
        with pytest.raises(HTTPException):worker.execute(key,path)
        monkeypatch.setattr(get_settings(),'heysow_webhooks_enabled',True)
        c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=? AND user_id='controlled@example.test'",(org,));c.commit()
        with pytest.raises(HTTPException):worker.execute(key,path)


@pytest.mark.parametrize('url',['http://receiver.example.com','https://127.0.0.1/','https://169.254.169.254/','https://receiver.local/','https://user:secret@receiver.example.com/','https://receiver.example.com/?token=secret','https://receiver.example.com:444/'])
def test_ssrf_and_url_secrets_are_rejected(url):
    with pytest.raises(ValidationError):service.Endpoint(name='Unsafe endpoint',url=url,topics=['company.created'])


def test_creation_retry_reuses_endpoint_without_revealing_secret_again(hooks):
    c,_,org,_=hooks
    body=service.Endpoint(name='Idempotent receiver',url='https://receiver.example.com/events',topics=['company.created'])
    with workspace_scope(c,'controlled@example.test',org):
        first=service.save(c,body);replay=service.save(c,body)
        assert first['endpoint']['id']==replay['endpoint']['id']
        assert replay['already_created'] is True and 'signing_secret' not in replay
        assert c.execute('SELECT COUNT(*) FROM webhook_endpoints WHERE organization_id=?',(org,)).fetchone()[0]==1
        with pytest.raises(HTTPException) as conflict:service.save(c,body.model_copy(update={'name':'Different content'}))
        assert conflict.value.status_code==409


def test_crash_during_final_attempt_is_terminal_without_sixth_send(hooks):
    c,path,org,_=hooks
    with workspace_scope(c,'controlled@example.test',org):
        key=endpoint(c,['company.created'])['endpoint']['id'];seed(c,org);c.commit()
        delivery=service.history(c,key)['items'][0]['id']
        c.execute("UPDATE webhook_deliveries SET status='DELIVERING',attempts=5,lease_owner='lost-process',lease_until='2000-01-01T00:00:00+00:00' WHERE id=?",(delivery,));c.commit()
    calls=[]
    asyncio.run(worker.execute_async(key,path,httpx.MockTransport(lambda request:calls.append(request) or httpx.Response(200))))
    with workspace_scope(c,'controlled@example.test',org):
        result=service.history(c,key)['items'][0]
        assert result['status']=='FAILED' and result['last_error_code']=='DELIVERY_OUTCOME_UNKNOWN'
        assert result['attempts']==5 and calls==[]


def test_webhook_upgrade_preserves_rows_and_restore(tmp_path,monkeypatch):
    latest=migrations.MIGRATIONS;c=sqlite3.connect(tmp_path/'before.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:36]);migrations.run_migrations(c)
    tables=('organizations','organization_profiles','ideal_customer_profiles','contacted_recipients','email_messages')
    before={table:[tuple(row) for row in c.execute('SELECT * FROM '+table)] for table in tables}
    snapshot=sqlite3.connect(tmp_path/'snapshot.db');c.backup(snapshot)
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:37]);assert migrations.run_migrations(c)==1;assert migrations.run_migrations(c)==0
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    for table,rows in before.items():assert [tuple(row) for row in c.execute('SELECT * FROM '+table)]==rows
    restored=sqlite3.connect(tmp_path/'restored.db');snapshot.backup(restored);assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==36
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    c.close();snapshot.close();restored.close()


def test_concurrent_delivery_reservation_performs_one_request(hooks):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from app.database.connection import db_session
    c,path,org,_=hooks
    with workspace_scope(c,'controlled@example.test',org):
        key=endpoint(c,['company.created'])['endpoint']['id'];seed(c,org);c.commit();delivery=service.history(c,key)['items'][0]['id']
    started=threading.Event();release=threading.Event();calls=[]
    def receive(request):
        calls.append(1);started.set();assert release.wait(4);return httpx.Response(200)
    def first():
        with db_session(path) as connection:
            with workspace_scope(connection,'controlled@example.test',org):return asyncio.run(worker.deliver(connection,key,delivery,httpx.MockTransport(receive)))
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(first)
        try:
            assert started.wait(4)
            with db_session(path) as connection:
                with workspace_scope(connection,'controlled@example.test',org):assert asyncio.run(worker.deliver(connection,key,delivery,httpx.MockTransport(receive)))=='NOT_DUE'
        finally:release.set()
        assert pending.result(timeout=5)=='DELIVERED'
    assert len(calls)==1


def test_owner_http_endpoints_and_missing_or_cross_workspace_access(hooks,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.platform.workspaces import select_workspace
    from app.api.organization import complete_onboarding
    c,path,org,other=hooks;config=get_settings()
    monkeypatch.setattr(config,'database_path',str(path));monkeypatch.setattr(config,'allowed_user_emails','controlled@example.test')
    monkeypatch.setattr(config,'heysow_workspace_management_enabled',True)
    complete_onboarding(c,org);complete_onboarding(c,other);select_workspace(c,'controlled@example.test',org);c.commit()
    with TestClient(app) as http:
        created=http.post('/api/organization/webhooks',json={'name':'Owned HTTP receiver','url':'https://receiver.example.com/events','topics':['task.created']})
        assert created.status_code==201,created.text;key=created.json()['endpoint']['id'];secret=created.json()['signing_secret']
        assert created.headers['cache-control']=='no-store'
        listed=http.get('/api/organization/webhooks');assert listed.status_code==200 and secret not in listed.text
        foreign=str(__import__('uuid').uuid4())
        assert http.get('/api/organization/webhooks/'+foreign+'/deliveries').status_code==404
        assert http.post('/api/organization/webhooks/'+key+'/control',json={'revision':1,'action':'pause'}).status_code==200
        assert http.post('/api/organization/webhooks/'+key+'/control',json={'revision':1,'action':'resume'}).status_code==409
        assert http.post('/api/organization/webhooks/'+key+'/control',json={'revision':2,'action':'archive'}).status_code==200
        assert http.get('/api/organization/webhooks/'+key+'/deliveries').status_code==200
        c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=? AND user_id='controlled@example.test'",(org,));c.commit()
        assert http.get('/api/organization/webhooks').status_code==403
        assert http.post('/api/organization/webhooks',json={'name':'Denied receiver','url':'https://receiver.example.com/events','topics':['task.created']}).status_code==403
