"""Read-only cloud readiness checks; canary execution requires an explicit flag."""
import json
import os
import shutil
import subprocess
import time
import requests
from pathlib import Path
from tempfile import TemporaryDirectory
import uuid
from app.config.settings import get_settings


def authorized_session():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credentials,_=google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        return AuthorizedSession(credentials)
    except Exception:
        # Desktop fallback uses a short-lived CLI token in memory, never an argv secret.
        executable=shutil.which("gcloud")
        if not executable or os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_EXECUTION"):
            raise RuntimeError("Google application credentials unavailable")
        result=subprocess.run([executable,"auth","print-access-token"],capture_output=True,text=True,timeout=20,check=True)
        session=requests.Session();session.headers["Authorization"]="Bearer "+result.stdout.strip()
        return session


def cloud_checks(execute_canary=False):
    s=get_settings();checks=[]
    def record(name,status,detail):checks.append({"name":name,"status":status,"details":detail})
    try:
        from app.database.postgres import PostgresConnection
        conn=PostgresConnection(s.database_url);conn.execute("SELECT 1");conn.close()
        record("PostgreSQL","ready","Configured database is reachable.")
    except Exception:record("PostgreSQL","error","Database connection could not be verified.")
    try:
        from app.storage import R2ArtifactStorage
        storage=R2ArtifactStorage();storage.client.head_bucket(Bucket=storage.bucket)
        record("R2","ready","Bucket is reachable using server credentials; public-access policy is not inferred from this check.")
    except Exception:record("R2","error","Bucket configuration or connectivity could not be verified.")
    job=None;session=None
    try:
        session=authorized_session()
        base=f"https://run.googleapis.com/v2/projects/{s.gcp_project_id}/locations/{s.gcp_region}/jobs/{s.cloud_run_job}"
        response=session.get(base,timeout=15)
        if response.status_code==200:
            job=response.json()
            record("Cloud Worker Configuration","ready","Job exists. Actual execution and image pulling require a canary.")
        else:record("Cloud Worker Configuration","error",f"Job lookup returned HTTP {response.status_code}.")
    except Exception:record("Cloud Worker Configuration","error","Job lookup requires valid GCP configuration and credentials.")
    if execute_canary and job and session:
        response=session.post(base+":run",json={"overrides":{"taskCount":1,"containerOverrides":[{"env":[{"name":"LEADENGINE_CANARY","value":"1"}]}]}},timeout=30)
        operation=response.json() if response.status_code<400 else {}
        name=operation.get("name")
        if not name:record("Canary","error",f"Canary dispatch failed (HTTP {response.status_code}).")
        else:
            deadline=time.monotonic()+180
            execution=None
            while time.monotonic()<deadline:
                operation=session.get("https://run.googleapis.com/v2/"+name,timeout=15).json()
                if operation.get("done"):
                    execution=operation.get("response",{});break
                time.sleep(2)
            execution_name=(execution or {}).get("name") or operation.get("metadata",{}).get("name")
            while execution_name and time.monotonic()<deadline:
                execution=session.get("https://run.googleapis.com/v2/"+execution_name,timeout=15).json()
                if execution.get("completionTime"):break
                time.sleep(2)
            success=bool(execution and execution.get("succeededCount")==1 and execution.get("completionTime"))
            record("Canary","ready" if success else "error","Worker canary completed." if success else "Worker completion could not be verified.")
    else:
        result=completed_canary(job,session) if job and session else None
        record("Canary","ready" if result else "unverified",f"Verified completed worker execution {result['execution']}." if result else "No successful canary recorded for the deployed worker image.")
        record("Lighthouse","ready" if result and result.get('lighthouse') else "unverified","Verified in the completed worker canary." if result else "Requires a successful worker canary for the deployed image.")
    return checks


def source_health(name,url,timeout=6):
    try:
        response=requests.get(url,timeout=timeout,headers={'User-Agent':get_settings().crawler_user_agent})
        return {'name':name,'status':'ready' if response.status_code==200 else 'warning','details':f'Endpoint returned HTTP {response.status_code}.'}
    except requests.RequestException:
        return {'name':name,'status':'warning','details':'Endpoint did not respond within the bounded health-check timeout.'}


def overpass_health():
    from app.discovery.osm import OVERPASS_MIRRORS
    primary=get_settings().overpass_url
    urls=list(dict.fromkeys([primary,*OVERPASS_MIRRORS]))[:2]
    for index,url in enumerate(urls):
        result=source_health('OpenStreetMap',url.rsplit('/',1)[0]+'/status')
        if result['status']=='ready':
            result['details']='Configured endpoint responded.' if index==0 else 'Primary endpoint degraded; fallback mirror responded.'
            return result
    return {'name':'OpenStreetMap','status':'warning','details':'Configured endpoint and one fallback mirror did not respond successfully; discovery retains bounded mirror fallback.'}


def completed_canary(job,session):
    """Require both image-matched evidence and a successfully completed execution."""
    try:
        from app.database.connection import db_session
        from app.storage import R2ArtifactStorage
        with db_session() as conn:
            row=conn.execute("SELECT object_key FROM artifact_objects WHERE kind='worker_canary' ORDER BY created_at DESC LIMIT 1").fetchone()
        if not row:return None
        body=R2ArtifactStorage().get(row[0])
        try:result=json.loads(body.read(65536))
        finally:body.close()
        if result.get('status')!='passed' or result.get('image')!=job['template']['template']['containers'][0]['image']:return None
        execution=result.get('execution','')
        if not execution or '/' in execution:return None
        response=session.get('https://run.googleapis.com/v2/'+job['name']+'/executions/'+execution,timeout=10)
        live=response.json() if response.status_code==200 else {}
        return result if live.get('completionTime') and live.get('succeededCount')==1 else None
    except Exception:return None


def worker_canary():
    from app.database.connection import db_session
    from app.database.repositories import PipelineRunRepository,PipelineRunEventRepository
    from app.database.models import PipelineRun,PipelineRunEvent
    from app.storage import R2ArtifactStorage,publish_artifact
    import duckdb
    import app.worker
    import asyncio
    from app.enrichment.http_probe import probe_website
    get_settings()  # validates the required production environment
    execution=os.environ.get('CLOUD_RUN_EXECUTION','local-'+uuid.uuid4().hex)
    result={'status':'passed','execution':execution,'image':os.environ.get('LEADENGINE_WORKER_IMAGE',''),'imports':True,'environment':True}
    probe=asyncio.run(probe_website('https://example.com',timeout_seconds=10))
    if not probe.reachable or not probe.html_content:raise RuntimeError('Public HTTP transport probe failed')
    result['public_http_fetch']=True
    with db_session() as conn:
        run=PipelineRun(market='Canary temporary event',vertical='dentists',target=5,status='COMPLETED')
        PipelineRunRepository(conn).create(run)
        event=PipelineRunEvent(run_id=run.id,stage='CANARY',event_type='CANARY',message=execution)
        PipelineRunEventRepository(conn).create(event)
        assert PipelineRunEventRepository(conn).get_latest(run.id).message==execution
        conn.execute('DELETE FROM pipeline_runs WHERE id=?',(run.id,))
        result['database_event_write_read_cleanup']=True
    database=duckdb.connect()
    try:
        database.execute("SET extension_directory='/opt/duckdb_extensions'; LOAD httpfs")
        assert database.execute('SELECT 42').fetchone()[0]==42
        result['duckdb']=True
    finally:database.close()
    storage=R2ArtifactStorage()
    with TemporaryDirectory() as directory:
        from app.reports.pdf import fonts
        from reportlab.pdfgen.canvas import Canvas
        from pypdf import PdfReader
        fonts();pdf_path=Path(directory)/'renderer-probe.pdf';pdf=Canvas(str(pdf_path));pdf.setFont('PBRegular',11);pdf.drawString(48,760,'PlaneByte PDF renderer');pdf.save()
        assert 'PlaneByte PDF renderer' in PdfReader(pdf_path).pages[0].extract_text()
        result['pdf_renderer']=True
        source=Path(directory)/'probe.txt';payload=uuid.uuid4().hex.encode();source.write_bytes(payload)
        key=f'audits/canary/{execution}/probe.txt'
        try:
            storage.put(key,source,'text/plain');body=storage.get(key)
            try:assert body.read()==payload
            finally:body.close()
        finally:storage.client.delete_object(Bucket=storage.bucket,Key=key)
        from botocore.exceptions import ClientError
        try:
            storage.client.head_object(Bucket=storage.bucket,Key=key)
            raise AssertionError('Temporary R2 object still exists')
        except ClientError as exc:
            if exc.response['ResponseMetadata']['HTTPStatusCode']!=404:raise
        result['r2_write_read_delete']=True
        for name,command in [('node',["node","--version"]),('chromium',["chromium","--version"]),('lighthouse',["node","node_modules/lighthouse/cli/index.js","--version"])]:
            subprocess.run(command,check=True,capture_output=True,timeout=20);result[name]=True
        result['sources']=[source_health('Overture','https://overturemaps-us-west-2.s3.amazonaws.com/?prefix=release/&delimiter=/'),overpass_health()]
        if result['sources'][0]['status']!='ready':raise RuntimeError('Overture connectivity check failed')
        result_file=Path(directory)/'result.json';result_file.write_text(json.dumps(result))
        with db_session() as conn:publish_artifact(conn,f'audits/canary/{execution}/result.json',result_file,kind='worker_canary')
    print(json.dumps(result))
