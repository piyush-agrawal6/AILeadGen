import asyncio,json,uuid,sqlite3
from urllib.parse import urlsplit,parse_qs,unquote
from unittest.mock import AsyncMock
import httpx,pytest
from fastapi import HTTPException
from test_customer_integrations import workspace,OWNER,TOKENS,start
from test_people import seed
from app.integrations import service,sheet_exports as exports
from app.acquisition import sheets
from app.platform.context import workspace_scope
from app.sales import collections
from app.database import migrations

def prepare(c,org,monkeypatch,write=True):
    response=service.authorize(c,write=write);state=parse_qs(urlsplit(response['authorization_url']).query)['state'][0]
    monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value={**TOKENS,'scope':service.WRITE_SCOPE if write else sheets.SCOPE}))
    connected=asyncio.run(service.connect(c,state,'controlled-code'));c.commit()
    company=seed(c,org);c.execute('UPDATE businesses SET name=?,public_email=? WHERE id=?',('=IMPORTXML("untrusted")','public@controlled.example',company.id))
    group=collections.save(c,collections.Named(name='Reviewed export list'));collections.change_members(c,group['id'],[company.id]);c.commit()
    body=exports.Export(list_id=group['id'],spreadsheet='controlled-sheet-id',sheet="Owner's tab",start_row=3,request_id=uuid.uuid4())
    return connected,body,company

def test_explicit_write_grant_snapshot_raw_mapping_and_idempotent_worker(workspace,monkeypatch):
    c,org,other,path=workspace
    with workspace_scope(c,OWNER,org):
        connection,body,company=prepare(c,org,monkeypatch);job=exports.stage(c,connection['id'],body);c.commit()
        assert job['status']=='DRAFT' and job['row_count']==1 and job['target_range']=="'Owner''s tab'!A3:H4"
        assert job['preview'][0][0].startswith('=IMPORTXML') and job['preview'][0][2]=='public@controlled.example'
        assert exports.stage(c,connection['id'],body)['id']==job['id']
        with pytest.raises(HTTPException):exports.stage(c,connection['id'],body.model_copy(update={'start_row':4}))
        with pytest.raises(HTTPException):exports.approve(c,job['id'],'0'*64,'OVERWRITE_REVIEWED_RANGE')
        exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
        c.execute('UPDATE businesses SET name=? WHERE id=?',('Changed after review',company.id));c.commit()
    calls=[]
    def receive(request):
        calls.append(request);payload=json.loads(request.content)
        assert request.method=='PUT' and request.url.host=='sheets.googleapis.com'
        assert request.url.params['valueInputOption']=='RAW'
        assert payload['values'][1][0].startswith('=IMPORTXML')
        assert unquote(request.url.path).endswith("'Owner''s tab'!A3:H4")
        return httpx.Response(200,json={'updatedCells':16})
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(receive)))
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(receive)))
    with workspace_scope(c,OWNER,org):
        result=exports.view(exports.owned(c,job['id']));assert result['status']=='COMPLETED' and result['attempts']==1 and len(calls)==1
        assert exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE')['status']=='COMPLETED'
        assert c.execute('SELECT COUNT(*) FROM email_messages').fetchone()[0]==0
    with workspace_scope(c,OWNER,other):
        with pytest.raises(HTTPException) as foreign:exports.owned(c,job['id'])
        assert foreign.value.status_code==404
        with pytest.raises(HTTPException):exports.stage(c,connection['id'],body)
    with pytest.raises(HTTPException):exports.owned(c,job['id'])

def test_readonly_connection_never_silently_upgrades_and_disconnect_stops_job(workspace,monkeypatch):
    c,org,_,path=workspace
    with workspace_scope(c,OWNER,org):
        connection,body,_=prepare(c,org,monkeypatch,write=False)
        with pytest.raises(HTTPException) as denied:exports.stage(c,connection['id'],body)
        assert denied.value.status_code==409
        response=service.authorize(c,write=True);state=parse_qs(urlsplit(response['authorization_url']).query)['state'][0]
        # A write request cannot accept a read-only token or an unrelated broad grant.
        with pytest.raises(HTTPException):asyncio.run(service.connect(c,state,'controlled-code'))
        response=service.authorize(c,write=True);state=parse_qs(urlsplit(response['authorization_url']).query)['state'][0]
        monkeypatch.setattr(sheets,'token_request',AsyncMock(return_value={**TOKENS,'scope':service.WRITE_SCOPE}));asyncio.run(service.connect(c,state,'controlled-code'))
        job=exports.stage(c,connection['id'],body);exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');service.disconnect(c,connection['id']);c.commit()
    calls=[]
    with pytest.raises(HTTPException):asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(lambda request:calls.append(1) or httpx.Response(200))))
    assert calls==[]

def test_uncertain_write_has_no_automatic_retry_and_explicit_retry_overwrites_same_range(workspace,monkeypatch):
    c,org,_,path=workspace
    with workspace_scope(c,OWNER,org):
        connection,body,_=prepare(c,org,monkeypatch);job=exports.stage(c,connection['id'],body);exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    calls=[]
    def timeout(request):calls.append(str(request.url));raise httpx.ReadTimeout('synthetic')
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(timeout)))
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(timeout)))
    with workspace_scope(c,OWNER,org):
        assert exports.owned(c,job['id'])['status']=='UNCERTAIN' and len(calls)==1
        with pytest.raises(HTTPException):exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE')
        exports.retry(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(lambda request:calls.append(str(request.url)) or httpx.Response(200,json={'updatedCells':16}))))
    assert len(calls)==2 and calls[0]==calls[1]
    with workspace_scope(c,OWNER,org):assert exports.owned(c,job['id'])['status']=='COMPLETED'

def test_export_cancel_and_revoked_manager_never_write(workspace,monkeypatch):
    c,org,_,path=workspace
    with workspace_scope(c,OWNER,org):
        connection,body,_=prepare(c,org,monkeypatch);job=exports.stage(c,connection['id'],body);exports.cancel(c,job['id']);c.commit()
        with pytest.raises(HTTPException):exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE')
        job=exports.stage(c,connection['id'],body.model_copy(update={'request_id':uuid.uuid4()}));exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    c.execute("UPDATE organization_memberships SET role='VIEWER' WHERE organization_id=? AND user_id=?",(org,OWNER));c.commit();calls=[]
    with pytest.raises(HTTPException):asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(lambda request:calls.append(1) or httpx.Response(200))))
    assert calls==[]

def test_export_migration_preserves_history_and_restore(tmp_path,monkeypatch):
    latest=migrations.MIGRATIONS;c=sqlite3.connect(tmp_path/'before.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:37]);migrations.run_migrations(c)
    before=c.execute('SELECT COUNT(*) FROM organizations').fetchone()[0];backup=sqlite3.connect(tmp_path/'backup.db');c.backup(backup)
    monkeypatch.setattr(migrations,'MIGRATIONS',latest[:38]);assert migrations.run_migrations(c)==1;assert migrations.run_migrations(c)==0
    assert c.execute('SELECT COUNT(*) FROM organizations').fetchone()[0]==before and c.execute('PRAGMA foreign_key_check').fetchall()==[]
    restored=sqlite3.connect(tmp_path/'restored.db');backup.backup(restored);assert restored.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]==37
    assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok';c.close();backup.close();restored.close()

def test_http_export_review_launch_and_foreign_access(workspace,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api.server import app
    from app.platform.workspaces import select_workspace
    from app.api.organization import complete_onboarding
    c,org,other,path=workspace
    with workspace_scope(c,OWNER,org):connection,body,_=prepare(c,org,monkeypatch)
    complete_onboarding(c,org);complete_onboarding(c,other);select_workspace(c,OWNER,org);c.commit()
    launcher=AsyncMock();monkeypatch.setattr(exports,'launch',launcher)
    with TestClient(app) as http:
        created=http.post('/api/organization/integrations/'+connection['id']+'/sheets/exports',json=body.model_dump(mode='json'));assert created.status_code==201,created.text
        job=created.json();assert job['status']=='DRAFT' and launcher.await_count==0
        approval={'review_digest':job['review_digest'],'confirmation':'OVERWRITE_REVIEWED_RANGE'}
        accepted=http.post('/api/organization/integrations/sheets/exports/'+job['id']+'/approve',json=approval);assert accepted.status_code==200,accepted.text
        assert launcher.await_count==1
        asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(lambda request:httpx.Response(200,json={'updatedCells':16}))))
        assert http.get('/api/organization/integrations/'+connection['id']+'/sheets/exports').json()['items'][0]['status']=='COMPLETED'
        assert http.put('/api/organization/active',json={'organization_id':other}).status_code==200
        assert http.post('/api/organization/integrations/sheets/exports/'+job['id']+'/approve',json=approval).status_code==404
        assert http.get('/api/organization/integrations/'+connection['id']+'/sheets/exports').status_code==404
        assert launcher.await_count==1

def test_cloud_worker_export_clears_other_modes_and_checks_gate_first(monkeypatch):
    from unittest.mock import Mock
    from app.api.services.cloud_executor import run_job
    from app.config.settings import get_settings
    config=get_settings();monkeypatch.setattr(config,'heysow_workspace_management_enabled',True);monkeypatch.setattr(config,'heysow_customer_integrations_enabled',False)
    session=Mock()
    with pytest.raises(HTTPException):run_job(None,session,sheet_export_id='controlled-job')
    session.post.assert_not_called()
    monkeypatch.setattr(config,'heysow_customer_integrations_enabled',True);session.post.return_value.status_code=200;session.post.return_value.json.return_value={'name':'controlled-dispatch'}
    assert run_job(None,session,sheet_export_id='controlled-job')=='controlled-dispatch'
    override=session.post.call_args.kwargs['json']['overrides'];values={item['name']:item['value'] for item in override['containerOverrides'][0]['env']}
    assert values['LEADENGINE_SHEET_EXPORT_ID']=='controlled-job' and values['LEADENGINE_RUN_ID']=='' and values['LEADENGINE_EMAIL_SYNC']=='0' and values['LEADENGINE_WEBHOOK_ENDPOINT_ID']==''
    assert override['timeout']=='90s'

def test_duplicate_export_workers_make_one_provider_request(workspace,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    c,org,_,path=workspace
    with workspace_scope(c,OWNER,org):
        connection,body,_=prepare(c,org,monkeypatch);job=exports.stage(c,connection['id'],body);exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    started=threading.Event();release=threading.Event();calls=[]
    def receive(request):
        calls.append(1);started.set();assert release.wait(4);return httpx.Response(200,json={'updatedCells':16})
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(lambda:asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(receive))))
        try:
            assert started.wait(4);asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(receive)))
        finally:release.set()
        pending.result(timeout=5)
    assert len(calls)==1

def test_unverified_success_redirect_and_retry_budget_are_not_hidden(workspace,monkeypatch):
    c,org,_,path=workspace
    with workspace_scope(c,OWNER,org):
        connection,body,_=prepare(c,org,monkeypatch);job=exports.stage(c,connection['id'],body);exports.approve(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(lambda request:httpx.Response(200,json={'updatedCells':0}))))
    with workspace_scope(c,OWNER,org):
        assert exports.owned(c,job['id'])['status']=='UNCERTAIN'
        exports.retry(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    calls=[]
    def redirect(request):calls.append(1);return httpx.Response(302,headers={'Location':'http://127.0.0.1/private'})
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(redirect)))
    with workspace_scope(c,OWNER,org):
        assert exports.owned(c,job['id'])['last_error_code']=='SHEETS_HTTP_302' and calls==[1]
        exports.retry(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE');c.commit()
    asyncio.run(exports.execute(job['id'],path,httpx.MockTransport(redirect)))
    with workspace_scope(c,OWNER,org):
        assert exports.owned(c,job['id'])['attempts']==3
        with pytest.raises(HTTPException):exports.retry(c,job['id'],job['review_digest'],'OVERWRITE_REVIEWED_RANGE')
