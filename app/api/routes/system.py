from fastapi import APIRouter
from app.api.schemas.system import DiagnosticItem, SystemDoctorResponse
from app.utils.diagnostics import run_system_diagnostics

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/limits")
def safety_limits():
    from app.config.settings import get_settings
    s = get_settings()
    return {"max_active_scans":s.max_active_scans,"max_cities_per_scan":s.max_cities_per_scan,"max_target_leads":s.max_target_leads,"max_raw_businesses":s.max_raw_businesses,"max_lighthouse_audits":s.max_lighthouse_audits,"max_scan_runtime_minutes":s.max_scan_runtime_minutes,"executor":s.scan_executor}


@router.get("/hosted-health")
def hosted_health():
    import httpx
    from app.config.settings import get_settings
    from app.database.connection import db_session
    from app.cloud_doctor import cloud_checks,overpass_health
    from app.audit.lighthouse import find_lighthouse_executable
    s=get_settings()
    if s.app_env=="test":
        return {"environment":"test","checks":[{"name":name,"status":"ready","details":"Deterministic test fixture; external connectivity is not asserted."} for name in ["FastAPI","Application database","PostgreSQL","Cloud Worker Configuration","R2","Overture","OpenStreetMap","Nominatim","Lighthouse"]]}
    checks=[{"name":"FastAPI","status":"ready","details":"Authenticated API request succeeded."}]
    try:
        with db_session() as conn:conn.execute("SELECT 1")
        checks.append({"name":"Application database","status":"ready","details":"PostgreSQL" if s.app_env=="production" else "Configured local database"})
    except Exception:checks.append({"name":"Application database","status":"error","details":"Database query failed."})
    checks.extend(cloud_checks(False))
    try:
        from app.database.phase4_schema import ready
        with db_session() as conn:
            if ready(conn):
                account=conn.execute('SELECT status,smtp_health,imap_health,health_checked_at,last_sync_at FROM email_accounts WHERE id=?',('hostinger-primary',)).fetchone()
                for title,column in [('Email Sending','smtp_health'),('Inbox Sync','imap_health')]:checks.append({'name':title,'status':'ready' if account and account['status']=='CONNECTED' and account[column]=='READY' else 'unverified','details':'Last explicit connection check: '+str(account['health_checked_at']) if account else 'Open Email preferences and test the configured account.'})
                checks.append({'name':'Reply Detection','status':'ready' if account and account['last_sync_at'] else 'unverified','details':'Last bounded tracked-thread sync: '+str(account['last_sync_at']) if account else 'No mailbox sync has completed yet.'})
                from app.mail.config import mail_settings
                from app.mail import tracking
                mail=mail_settings();outbound=mail.sending_enabled and (mail.mode=='test' and not mail.live_approved or mail.mode=='production' and mail.live_approved)
                checks.append({'name':'Outbound email','status':'ready' if outbound else 'warning','details':('ENABLED' if outbound else 'DISABLED')+' · '+('LIVE OUTREACH' if mail.mode=='production' else 'TEST MODE')})
                if tracking.available(conn):
                    checks.append({'name':'Tracking endpoints','status':'ready','details':'Opaque tokens; open/click signals and POST-confirmed unsubscribe. '+mail.tracking_base_url})
                    checks.append({'name':'Bounce monitor','status':'ready' if account and account['last_sync_at'] else 'unverified','details':'Bounded structured DSN monitoring; only authenticated recipient-specific failures can suppress an address.'})
    except Exception:checks.append({'name':'Email provider','status':'unverified','details':'Email readiness could not be checked.'})
    endpoints=[("Overture","https://overturemaps-us-west-2.s3.amazonaws.com/?prefix=release/&delimiter=/"),("Nominatim",s.nominatim_url.rstrip('/')+"/status.php")]
    for name,url in endpoints:
        try:
            response=httpx.get(url,timeout=4,headers={"User-Agent":s.crawler_user_agent})
            checks.append({"name":name,"status":"ready" if response.status_code<400 else "warning","details":f"Endpoint returned HTTP {response.status_code}."})
        except Exception:checks.append({"name":name,"status":"warning","details":"Endpoint did not respond within the health-check timeout."})
    checks.append(overpass_health())
    if s.scan_executor!='gcp':
        checks=[item for item in checks if item['name']!='Lighthouse']
        checks.append({"name":"Lighthouse","status":"ready" if find_lighthouse_executable() else "error","details":"Local executable found." if find_lighthouse_executable() else "Local executable unavailable."})
    return {"environment":s.app_env,"checks":checks}


@router.get("/doctor", response_model=SystemDoctorResponse)
def get_system_doctor():
    """Retrieve system diagnostics, prerequisites, and connectivity health."""
    from app.config.settings import get_settings
    if get_settings().app_env=="production":
        health=hosted_health()
        items=[DiagnosticItem(name=r['name'],status=r['status'],details=r['details'],ready=r['status']=='ready') for r in health['checks']]
        return SystemDoctorResponse(overall_status='ERROR' if any(r.status=='error' for r in items) else 'WARNING' if any(r.status!='ready' for r in items) else 'READY',diagnostics=items,api_version='3.0.0',environment='production')
    results = run_system_diagnostics()
    items = [
        DiagnosticItem(
            name=r.name,
            status=r.status,
            details=r.details,
            ready=r.ready,
        )
        for r in results
    ]

    has_error = any(r.status == "error" for r in results)
    has_warn = any(r.status == "warning" for r in results)
    overall = "ERROR" if has_error else ("WARNING" if has_warn else "READY")

    return SystemDoctorResponse(
        overall_status=overall,
        diagnostics=items,
        api_version="2.0.0",
        environment="local",
    )


@router.post("/doctor", response_model=SystemDoctorResponse)
def rerun_system_doctor():
    """Rerun active diagnostic checks across databases, engines, and connectivity."""
    return get_system_doctor()
