"""Versioned, immutable client snapshots; rendering belongs to the bounded worker."""
import json
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from app.database.connection import db_session, get_connection
from app.database.prospects import now
from app.reports.data import client_snapshot

_local_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='client-pdf')


def public_report(row):
    return {key: row[key] for key in ('id','prospect_id','business_id','created_at','created_by','version','status')}


def expire_reports(conn):
    timestamp=datetime.now(timezone.utc)
    conn.execute("UPDATE client_reports SET status='FAILED',error_message='Report worker deadline expired; generate a new version.',updated_at=? WHERE (status='GENERATING' AND lease_expires_at<?) OR (status='QUEUED' AND created_at<?)", (timestamp.isoformat(),timestamp.isoformat(),(timestamp-timedelta(minutes=30)).isoformat()))


def create_report(conn,business_id,prospect_id,actor):
    # Lock the canonical prospect, so concurrent versions cannot collide across
    # API instances. SQLite callers enter BEGIN IMMEDIATE before observing it.
    if getattr(conn,'backend',None)=='postgres':
        conn.execute('SELECT pg_advisory_xact_lock(691944303)')
        conn.execute('SELECT id FROM prospects WHERE id=? FOR UPDATE',(prospect_id,))
    expire_reports(conn)
    pending=conn.execute("SELECT * FROM client_reports WHERE prospect_id=? AND status IN ('QUEUED','GENERATING') ORDER BY version DESC LIMIT 1",(prospect_id,)).fetchone()
    if pending:return public_report(pending)
    if conn.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')").fetchone()[0]>=10:
        from fastapi import HTTPException
        raise HTTPException(429,'The report queue is full. Please try again shortly.')
    version=conn.execute('SELECT COALESCE(MAX(version),0)+1 FROM client_reports WHERE prospect_id=?',(prospect_id,)).fetchone()[0]
    timestamp=now();report_id=str(uuid.uuid4());snapshot=client_snapshot(conn,business_id,timestamp)
    key=f'prospects/{prospect_id}/reports/{timestamp[:10]}/{report_id}.pdf'
    conn.execute("INSERT INTO client_reports(id,prospect_id,business_id,created_at,created_by,version,status,object_key,snapshot_json,updated_at) VALUES(?,?,?,?,?,?,'QUEUED',?,?,?)",(report_id,prospect_id,business_id,timestamp,actor,version,key,json.dumps(snapshot,ensure_ascii=False),timestamp))
    return public_report(conn.execute('SELECT * FROM client_reports WHERE id=?',(report_id,)).fetchone())


def launch_reports():
    from app.config.settings import get_settings
    if get_settings().app_env=='production':
        from app.api.services.cloud_executor import dispatch_queued
        dispatch_queued()
    else:
        with db_session() as conn:
            ids=[r[0] for r in conn.execute("SELECT id FROM client_reports WHERE status='QUEUED'").fetchall()]
        for report_id in ids:_local_pool.submit(execute_report,report_id)


def execute_report(report_id):
    from app.database.migrations import verify_schema
    from app.reports.pdf import render_pdf
    from app.storage import artifact_storage
    owner=str(uuid.uuid4());conn=get_connection(session_bound=True)
    try:
        verify_schema(conn)
        if getattr(conn,'backend',None)=='postgres':
            if not conn.execute('SELECT pg_try_advisory_lock(hashtextextended(?,6919446))',(report_id,)).fetchone()[0]:return
        changed=conn.execute("UPDATE client_reports SET status='GENERATING',lease_owner=?,lease_expires_at=?,updated_at=? WHERE id=? AND status IN ('QUEUED','GENERATING')",(owner,(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),now(),report_id)).rowcount
        conn.commit()
        if changed!=1:return
        row=conn.execute('SELECT * FROM client_reports WHERE id=?',(report_id,)).fetchone()
        snapshot=json.loads(row['snapshot_json'])
        with tempfile.TemporaryDirectory(prefix='leadengine-pdf-') as folder:
            capture=snapshot.get('capture') or {}
            if capture.get('status')=='READY' and capture.get('object_key'):
                try:
                    with artifact_storage().get(capture['object_key']) as image:
                        content=image.read(2_000_001)
                    if len(content)<=2_000_000:
                        image_path=Path(folder)/'homepage.webp';image_path.write_bytes(content)
                        snapshot['_capture_path']=str(image_path)
                except Exception:pass # Missing evidence remains explicitly unavailable.
            path=render_pdf(snapshot,Path(folder)/'report.pdf')
            artifact_storage().put(row['object_key'],path,'application/pdf')
        conn.execute("UPDATE client_reports SET status='READY',error_message=NULL,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND lease_owner=? AND status='GENERATING'",(now(),report_id,owner))
        from app.database.phase4_schema import ready
        if ready(conn):
            from app.sales.service import activity
            activity(conn,row['prospect_id'],row['created_by'],'PDF_GENERATED',{'report_id':report_id,'version':row['version']},'pdf-'+report_id)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        # Internally useful, bounded failure reason; never returned by the API.
        conn.execute("UPDATE client_reports SET status='FAILED',error_message=?,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND status<>'READY'",(type(exc).__name__+': '+str(exc)[:800],now(),report_id));conn.commit()
        raise
    finally:conn.close()
