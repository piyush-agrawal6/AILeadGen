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
    return {key: row[key] for key in ('id','prospect_id','business_id','created_at','created_by','version','status')} | {'report_type':json.loads(row['snapshot_json'] or '{}').get('report_type','FULL_AUDIT')}


def expire_reports(conn):
    from app.platform.context import organization
    org=organization()
    timestamp=datetime.now(timezone.utc)
    conn.execute("UPDATE client_reports SET status='FAILED',error_message='Report worker deadline expired; generate a new version.',updated_at=? WHERE organization_id=? AND ((status='GENERATING' AND lease_expires_at<?) OR (status='QUEUED' AND created_at<?))", (timestamp.isoformat(),org,timestamp.isoformat(),(timestamp-timedelta(minutes=30)).isoformat()))


def create_report(conn,business_id,prospect_id,actor,*,pitch_types=None,report_type="FULL_AUDIT",experiment=None,organization=None):
    from app.platform.context import organization as active_organization
    organization=active_organization(organization)
    from app.platform.workspace import business_workspace
    from app.database.repositories import BusinessRepository
    business=BusinessRepository(conn).get_by_id(business_id)
    if not business:
        from fastapi import HTTPException
        raise HTTPException(404,'Company not found.')
    business_workspace(conn,business,organization=organization)
    persisted=conn.execute('SELECT prospect_id FROM businesses WHERE id=?',(business_id,)).fetchone()
    if not persisted or persisted[0]!=prospect_id:
        from fastapi import HTTPException
        raise HTTPException(404,'Report prospect does not match this company.')
    # Lock the canonical prospect, so concurrent versions cannot collide across
    # API instances. SQLite callers enter BEGIN IMMEDIATE before observing it.
    if getattr(conn,'backend',None)=='postgres':
        conn.execute('SELECT pg_advisory_xact_lock(691944303)')
        conn.execute('SELECT id FROM prospects WHERE id=? FOR UPDATE',(prospect_id,))
    org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
    expire_reports(conn)
    pending=conn.execute("SELECT * FROM client_reports WHERE prospect_id=?"+org_sql+" AND status IN ('QUEUED','GENERATING') ORDER BY version DESC LIMIT 1",(prospect_id,)+org_args).fetchone()
    if pending:
        existing_kind=json.loads(pending['snapshot_json']).get('report_type','FULL_AUDIT')
        if existing_kind==report_type:return public_report(pending)
        from fastapi import HTTPException
        raise HTTPException(409,'A different report is still generating; retry this format after it finishes.')
    if conn.execute("SELECT COUNT(*) FROM client_reports WHERE status IN ('QUEUED','GENERATING')"+org_sql,org_args).fetchone()[0]>=10:
        from fastapi import HTTPException
        raise HTTPException(429,'The report queue is full. Please try again shortly.')
    version=conn.execute('SELECT COALESCE(MAX(version),0)+1 FROM client_reports WHERE prospect_id=?'+org_sql,(prospect_id,)+org_args).fetchone()[0]
    timestamp=now();report_id=str(uuid.uuid4());snapshot=client_snapshot(conn,business_id,timestamp)
    snapshot['report_type']=report_type
    if report_type=='OPPORTUNITY_BRIEF_V2':
        snapshot['experiment']=experiment or {}
        from app.experiments.brief import issues
        problems=issues(snapshot)
        if problems:raise ValueError('Needs Review: '+' '.join(problems))
    elif report_type!='FULL_AUDIT':raise ValueError('Unknown report format.')
    if pitch_types is not None and report_type=='FULL_AUDIT':
        snapshot['outreach_pitch_types']=list(pitch_types)
        from app.reports.opportunity import plan,report_issues
        snapshot['sales_review']=plan(snapshot)
        snapshot['content_quality']={'issues':report_issues(snapshot,snapshot['sales_review'])}
    key=f'prospects/{prospect_id}/reports/{timestamp[:10]}/{report_id}.pdf'
    conn.execute("INSERT INTO client_reports(id,prospect_id,business_id,created_at,created_by,version,status,object_key,snapshot_json,updated_at,organization_id) VALUES(?,?,?,?,?,?,'QUEUED',?,?,?,?)",(report_id,prospect_id,business_id,timestamp,actor,version,key,json.dumps(snapshot,ensure_ascii=False),timestamp,organization))
    return public_report(conn.execute('SELECT * FROM client_reports WHERE id=?',(report_id,)).fetchone())


def launch_reports():
    # Assessment rendering is retained for the separate future product and
    # isolated renderer tests, never automatically launched by Lead Engine.
    return []


def execute_report(report_id,organization=None):
    from app.platform.context import job_scope,organization as active_organization
    scope_conn=get_connection()
    try:
        with job_scope(scope_conn,'report',report_id):
            org=active_organization(organization)
            return _execute_owned_report(report_id,org)
    finally:scope_conn.close()

def _execute_owned_report(report_id,organization):
    from app.database.migrations import verify_schema
    from app.reports.pdf import render_pdf
    from app.storage import artifact_storage
    owner=str(uuid.uuid4());conn=get_connection(session_bound=True)
    org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
    try:
        verify_schema(conn)
        if getattr(conn,'backend',None)=='postgres':
            if not conn.execute('SELECT pg_try_advisory_lock(hashtextextended(?,6919446))',(report_id,)).fetchone()[0]:return
        changed=conn.execute("UPDATE client_reports SET status='GENERATING',lease_owner=?,lease_expires_at=?,updated_at=? WHERE id=? AND status IN ('QUEUED','GENERATING')"+org_sql,(owner,(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),now(),report_id)+org_args).rowcount
        conn.commit()
        if changed!=1:return
        row=conn.execute('SELECT * FROM client_reports WHERE id=?',(report_id,)).fetchone()
        snapshot=json.loads(row['snapshot_json'])
        from app.reports.opportunity import report_issues
        brief=snapshot.get('report_type')=='OPPORTUNITY_BRIEF_V2'
        if brief:
            from app.experiments.brief import issues as brief_issues,render_pdf
        problems=brief_issues(snapshot) if brief else report_issues(snapshot)
        if problems:raise ValueError('Needs Review: '+' '.join(problems))
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
            from app.mail.quality import validate_pdf
            validate_pdf(path.read_bytes(),report_type=snapshot.get('report_type','FULL_AUDIT'))
            artifact_storage().put(row['object_key'],path,'application/pdf')
        conn.execute("UPDATE client_reports SET status='READY',error_message=NULL,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND lease_owner=? AND status='GENERATING'"+org_sql,(now(),report_id,owner)+org_args)
        from app.database.phase4_schema import ready
        if ready(conn):
            from app.sales.service import activity
            activity(conn,row['prospect_id'],row['created_by'],'PDF_GENERATED',{'report_id':report_id,'version':row['version']},'pdf-'+report_id,organization=row['organization_id'])
        conn.commit()
    except Exception as exc:
        conn.rollback()
        # Internally useful, bounded failure reason; never returned by the API.
        conn.execute("UPDATE client_reports SET status='FAILED',error_message=?,lease_owner=NULL,lease_expires_at=NULL,updated_at=? WHERE id=? AND status<>'READY'"+org_sql,(type(exc).__name__+': '+str(exc)[:800],now(),report_id)+org_args);conn.commit()
        raise
    finally:conn.close()
