import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from app.api.server import app
from app.database.connection import db_session
from app.database.models import Business,WebsiteProfile,PipelineRun,LighthouseResult
from app.database.repositories import BusinessRepository,WebsiteProfileRepository,PipelineRunRepository,LighthouseRepository
from app.database.prospects import ProspectRepository
from app.reports.data import client_snapshot
from app.reports.pdf import render_pdf
from app.reports.service import execute_report


@pytest.fixture
def ready_client(monkeypatch):
    monkeypatch.setattr('app.api.routes.client_reports.launch_reports',lambda:None)
    with TestClient(app) as client:
        with db_session() as conn:
            run=PipelineRun(market='Leeds, UK',vertical='dentists',target=5);PipelineRunRepository(conn).create(run)
            business=Business(name='Dental & Care <North>',normalized_name='dental care north',vertical='dentists',city='Leeds',country='United Kingdom',website='https://dental.example',run_id=run.id)
            BusinessRepository(conn).insert(business);pid=ProspectRepository(conn).observe(business)
            ProspectRepository(conn).add_note(pid,'founder@example.com','INTERNAL SECRET NOTE')
            ProspectRepository(conn).user("private@example.com")
            conn.execute("UPDATE prospects SET lead_status='CONTACTED',assigned_to='private@example.com' WHERE id=?",(pid,))
            WebsiteProfileRepository(conn).upsert(WebsiteProfile(business_id=business.id,requested_url=business.website,reachable=True,https_enabled=True,has_viewport=True))
            LighthouseRepository(conn).upsert(LighthouseResult(business_id=business.id,performance_score=23,seo_score=68))
            evidence={'WEBSITE':[{'code':'NO_BOOKING','detail':'No booking action observed in sampled pages.','points':20}],'SEO':[{'code':'NO_CSP','detail':'Search metadata requires review.','points':20}],'SECURITY':[{'code':'NO_HSTS','detail':'HSTS header not observed.','points':10}]}
            conn.execute("INSERT INTO opportunity_scores(business_id,website_opportunity_score,seo_opportunity_score,security_opportunity_score,primary_opportunity,contactability_level,scoring_version,evidence_json,created_at) VALUES(?,76,42,80,'WEBSITE','HIGH','test',?,'2026-10-26')",(business.id,json.dumps(evidence)))
        yield client,business.id,pid


def test_pdf_generation_storage_versioning_and_protected_api(ready_client):
    client,bid,pid=ready_client
    first=client.post(f'/api/leads/{bid}/pdf-reports');assert first.status_code==202
    row=first.json();assert row['status']=='QUEUED'
    assert client.post(f'/api/leads/{bid}/pdf-reports').json()['id']==row['id']
    assert client.get('/api/client-reports/'+row['id']+'/download').status_code==409
    execute_report(row['id'])
    result=client.get('/api/client-reports/'+row['id']);assert result.json()['status']=='READY'
    response=client.get('/api/client-reports/'+row['id']+'/download')
    assert response.status_code==200 and response.content.startswith(b'%PDF-') and len(response.content)>10000
    assert response.headers['content-type']=='application/pdf' and 'no-store' in response.headers['cache-control']
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
    for term in ('PlaneByte','Dental & Care <North>','23','68','Proposed target: 90/100','Target gain: +67 points','Search foundations','Basic external security review','HSTS header not observed'):
        assert term in text
    for term in ('INTERNAL SECRET NOTE','private@example.com','CONTACTED',pid,'Traceback','scoring_version','LeadEngine','Website opportunity','Higher opportunity score'):
        assert term not in text
    second=client.post(f'/api/leads/{bid}/pdf-reports').json();assert second['version']==2 and second['id']!=row['id']
    with db_session() as conn:
        stored=conn.execute('SELECT * FROM client_reports WHERE id=?',(row['id'],)).fetchone()
        assert stored['object_key'].endswith(row['id']+'.pdf')
        snapshot=json.loads(stored['snapshot_json']);assert 'notes' not in snapshot
        from app.storage import artifact_storage
        with artifact_storage().get(stored['object_key']) as file:assert file.read()==response.content
    execute_report(row['id']) # Ready reports are immutable even after a retry.
    assert client.get('/api/client-reports/'+row['id']+'/download').content==response.content
    assert client.get('/api/client-reports?lead_id='+str(bid)).json()['total']==2


def test_failure_is_internal_and_retry_preserves_old_version(ready_client,monkeypatch):
    client,bid,_=ready_client
    row=client.post(f'/api/leads/{bid}/pdf-reports').json()
    def fail(*args):raise RuntimeError('INTERNAL RENDER DETAIL')
    monkeypatch.setattr('app.reports.pdf.render_pdf',fail)
    with pytest.raises(RuntimeError):execute_report(row['id'])
    result=client.get('/api/client-reports/'+row['id']);assert result.json()['status']=='FAILED'
    assert 'INTERNAL RENDER DETAIL' not in result.text
    with db_session() as conn:assert 'INTERNAL RENDER DETAIL' in conn.execute('SELECT error_message FROM client_reports WHERE id=?',(row['id'],)).fetchone()[0]
    retry=client.post(f'/api/leads/{bid}/pdf-reports').json();assert retry['version']==2


@pytest.mark.parametrize('mode',['NO_WEBSITE','UNREACHABLE'])
def test_adaptive_pdf_does_not_invent_assessment(ready_client,tmp_path,mode):
    _,bid,_=ready_client
    with db_session() as conn:
        if mode=='NO_WEBSITE':conn.execute('UPDATE businesses SET website=NULL WHERE id=?',(bid,))
        else:conn.execute('UPDATE website_profiles SET reachable=0 WHERE business_id=?',(bid,))
        data=client_snapshot(conn,bid,'2026-10-26T04:00:00+00:00')
    assert data['mode']==mode
    path=render_pdf(data,tmp_path/'adaptive.pdf');text='\n'.join(p.extract_text() for p in PdfReader(path).pages)
    assert ('New website' if mode=='NO_WEBSITE' else 'Website recovery / redesign') in text
    assert 'Search foundations\n' not in text and 'Basic external security review\n' not in text


def test_render_is_deterministic_and_long_text_wraps(ready_client,tmp_path):
    _,bid,_=ready_client
    with db_session() as conn:data=client_snapshot(conn,bid,'2026-10-26T04:00:00+00:00')
    data['business']['name']='A long business name with & symbols and <literal> text '*3
    data['website']['canonical_url']='https://example.com/'+'long-url-segment/'*20
    a=render_pdf(data,tmp_path/'one.pdf');b=render_pdf(data,tmp_path/'two.pdf')
    assert a.read_bytes()==b.read_bytes()
    pages=PdfReader(a).pages
    assert '<literal>' in ''.join(p.extract_text() for p in pages)
    assert 'Executive summary' in pages[1].extract_text()
    assert 'Clear evidence. Practical next steps.' in pages[0].extract_text()


def test_cloud_pdf_override_is_bounded():
    from app.api.services.cloud_executor import run_job
    session=Mock();session.post.return_value.status_code=200;session.post.return_value.json.return_value={'name':'accepted'}
    run_job(None,session,report_id='report-id')
    body=session.post.call_args.kwargs['json']['overrides']
    assert body['timeout']=='300s' and body['taskCount']==1
    assert {'name':'LEADENGINE_REPORT_ID','value':'report-id'} in body['containerOverrides'][0]['env']


def test_pdf_r2_upload_is_private_and_mime_typed(tmp_path,monkeypatch):
    from app.storage import R2ArtifactStorage
    client=Mock();storage=R2ArtifactStorage(client=client)
    source=tmp_path/'report.pdf';source.write_bytes(b'%PDF-test')
    key='prospects/example/reports/version-one.pdf'
    storage.put(key,source,'application/pdf')
    assert client.upload_file.call_args.args==(str(source),storage.bucket,key)
    assert client.upload_file.call_args.kwargs['ExtraArgs']=={'ContentType':'application/pdf','CacheControl':'private, no-store'}


def test_reports_and_scans_share_existing_dispatch_capacity(ready_client,monkeypatch):
    from app.api.services.cloud_executor import dispatch_queued
    from app.config.settings import get_settings
    client,bid,_=ready_client
    report=client.post(f'/api/leads/{bid}/pdf-reports').json()
    monkeypatch.setattr(get_settings(),'max_active_scans',2)
    with db_session() as conn:
        active=PipelineRun(market='Active scan',vertical='dentists',target=5,status='RUNNING');PipelineRunRepository(conn).create(active)
        conn.execute("UPDATE pipeline_runs SET execution_name='existing' WHERE id=?",(active.id,))
        queued=PipelineRun(market='Queued scan',vertical='dentists',target=5,status='QUEUED');PipelineRunRepository(conn).create(queued)
    dispatch=Mock(return_value='operation/pdf')
    monkeypatch.setattr('app.api.services.cloud_executor.run_job',dispatch)
    assert dispatch_queued()==[]
    dispatch.assert_called_once_with(None,report_id=report['id'])
    dispatch_queued()
    assert dispatch.call_count==1

