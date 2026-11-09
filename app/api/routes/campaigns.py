import json
from itertools import product
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from app.api.dependencies import get_db
from app.api.schemas.campaigns import CampaignCreate
from app.api.services.scan_manager import scan_manager
from app.config.settings import get_settings
from app.database.models import PipelineRun
from app.database.repositories import PipelineRunRepository
from app.database.prospects import now

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def campaign_detail(conn, campaign_id, persist=False, organization=None):
    if persist and get_settings().scan_executor=='gcp':
        from app.api.services.cloud_executor import reconcile_expired
        reconcile_expired(conn)
    org_sql=(' AND organization_id=?' if organization else '');org_args=(organization,) if organization else ()
    row = conn.execute("SELECT * FROM scan_campaigns WHERE id=?"+org_sql, (campaign_id,)+org_args).fetchone()
    if not row:
        raise HTTPException(404, "Campaign not found.")
    result = dict(row)
    runs = [dict(r) for r in conn.execute("SELECT id,market,vertical,target,status,raw_found,qualified,exported,started_at,finished_at,error_message FROM pipeline_runs WHERE campaign_id=?"+org_sql+" ORDER BY id", (campaign_id,)+org_args).fetchall()]
    statuses = [r["status"] for r in runs]
    if any(s in ["RUNNING", "QUEUED"] for s in statuses):
        status = "RUNNING" if "RUNNING" in statuses else "QUEUED"
    elif statuses and all(s == "COMPLETED" for s in statuses):
        status = "COMPLETED"
    elif "FAILED" in statuses or "INTERRUPTED" in statuses:
        status = "FAILED"
    else:
        status = "CANCELLED"
    completed = now() if status in ["COMPLETED", "FAILED", "CANCELLED"] else None
    if persist:
        conn.execute("UPDATE scan_campaigns SET status=?,completed_at=COALESCE(completed_at,?) WHERE id=?"+org_sql, (status, completed, campaign_id)+org_args)
    result.update(status=status, runs=runs, completed_at=result.get("completed_at") or completed)
    result["configuration"] = json.loads(result.pop("configuration_json"))
    result["counters"] = {key: sum(r[key] for r in runs) for key in ["raw_found", "qualified", "exported"]}
    result["progress"] = {key.lower(): statuses.count(key) for key in ["COMPLETED", "RUNNING", "QUEUED", "FAILED", "CANCELLED"]}
    result["opportunities"] = dict(conn.execute("""SELECT
        COALESCE(SUM(CASE WHEN o.website_opportunity_score>=40 THEN 1 ELSE 0 END),0) AS website,
        COALESCE(SUM(CASE WHEN o.seo_opportunity_score>=40 THEN 1 ELSE 0 END),0) AS seo,
        COALESCE(SUM(CASE WHEN o.security_opportunity_score>=40 THEN 1 ELSE 0 END),0) AS security
        FROM opportunity_scores o JOIN pipeline_runs r ON r.id=o.run_id WHERE r.campaign_id=?"""+org_sql, (campaign_id,)+org_args).fetchone())
    return result


@router.get("")
def list_campaigns(request: Request,page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), conn=Depends(get_db,scope='function')):
    rows = conn.execute("SELECT id FROM scan_campaigns WHERE organization_id=? ORDER BY created_at DESC LIMIT ? OFFSET ?", (request.state.organization_id,page_size, (page-1)*page_size)).fetchall()
    return [campaign_detail(conn, row[0],organization=request.state.organization_id) for row in rows]


@router.get("/{campaign_id}")
def detail(campaign_id: str, request: Request,conn=Depends(get_db,scope='function')):
    return campaign_detail(conn, campaign_id,organization=request.state.organization_id)


@router.post("", status_code=201)
async def create_campaign(config: CampaignCreate, request: Request, conn=Depends(get_db,scope='function')):
    from app.workflows.controls import require_unpaused
    require_unpaused(conn,'scan')
    from app.qualification.configuration import new_scan_settings
    requested_config=new_scan_settings(conn,config.model_dump())
    organization=request.state.organization_id
    existing = conn.execute("SELECT created_by,configuration_json FROM scan_campaigns WHERE id=? AND organization_id=?", (config.request_id,organization)).fetchone()
    if existing:
        if existing[0] != request.state.user_email or json.loads(existing[1]) not in (requested_config,config.model_dump()):
            raise HTTPException(409, "Request ID already belongs to a different campaign.")
        return campaign_detail(conn, config.request_id,organization=organization)
    settings = get_settings()
    if getattr(conn, "backend", None) == "postgres":
        conn.execute("SELECT pg_advisory_xact_lock(691944302)")
    from app.database.acquisition_schema import ready as source_ready
    active = conn.execute("SELECT COUNT(*) FROM scan_campaigns WHERE status IN ('RUNNING','QUEUED') AND organization_id=?"+(" AND source_type='OVERTURE'" if source_ready(conn) else ''), (organization,)).fetchone()[0]
    if active >= settings.max_active_scans:
        raise HTTPException(409, "The workspace is at its active campaign limit. Wait for a campaign to finish.")
    conn.execute("INSERT INTO scan_campaigns(id,created_by,configuration_json,created_at,target_total,organization_id) VALUES(?,?,?,?,?,?)", (config.request_id, request.state.user_email, json.dumps(requested_config), now(), config.target, organization))
    from app.workflows.history import capture_settings
    frozen=capture_settings(conn,config.request_id,requested_config,organization=organization)
    pairs = list(product(config.cities, config.verticals))
    quotient, remainder = divmod(config.target, len(pairs))
    children = []
    for index, (city, vertical) in enumerate(pairs):
        target = quotient + (index < remainder)
        options = {**requested_config, "target": target, "created_by": request.state.user_email, "raw_budget": max(2, settings.max_raw_businesses // len(pairs)), "lighthouse_budget": 0, "exclude_chains": "KNOWN_CHAIN" not in config.business_scales}
        for key in ('crawler','auditing','analysis_mode','social'):options[key]=frozen.get(key)
        from app.qualification.configuration import new_scan_settings
        options=new_scan_settings(conn,options)
        options['deep_audit_budget']=0
        options['max_candidates']=min(options['max_candidates'],max(1,settings.max_raw_businesses//len(pairs)))
        run = PipelineRun(market=city, vertical=vertical, target=target, status="QUEUED", run_configuration=options)
        PipelineRunRepository(conn).create(run,organization=organization)
        conn.execute("UPDATE pipeline_runs SET campaign_id=? WHERE id=? AND organization_id=?", (config.request_id, run.id,organization))
        children.append(run)
    conn.commit()
    for run in children:
        await scan_manager.executor.start(run.id, run.market, run.vertical, run.target, run.run_configuration)
    return campaign_detail(conn, config.request_id,organization=organization)


@router.post("/{campaign_id}/cancel")
async def cancel(campaign_id: str, request: Request,conn=Depends(get_db,scope='function')):
    organization=request.state.organization_id
    campaign = campaign_detail(conn, campaign_id,organization=organization)
    conn.execute("UPDATE scan_campaigns SET cancellation_requested=1 WHERE id=? AND organization_id=?", (campaign_id,organization))
    conn.commit()
    for run in campaign["runs"]:
        if run["status"] in ["QUEUED", "RUNNING"]:
            await scan_manager.cancel_scan(run["id"])
    return campaign_detail(conn, campaign_id,organization=organization)


@router.post("/{campaign_id}/resume")
async def resume(campaign_id: str, request: Request,conn=Depends(get_db,scope='function')):
    from app.database.phase36_schema import phase36_ready
    organization=request.state.organization_id
    if getattr(conn,'backend',None)=='postgres':conn.execute('SELECT pg_advisory_xact_lock(691944307)')
    if phase36_ready(conn) and conn.execute("SELECT 1 FROM deletion_batches WHERE entity_type='campaign' AND entity_id=?",(campaign_id,)).fetchone():raise HTTPException(409,'Finish the pending deletion before resuming this campaign.')
    if phase36_ready(conn) and conn.execute('SELECT 1 FROM deletion_targets d JOIN businesses b ON b.id=d.business_id JOIN pipeline_runs r ON r.id=b.run_id WHERE r.campaign_id=? AND r.organization_id=?',(campaign_id,organization)).fetchone():raise HTTPException(409,'Finish the pending deletion before resuming this campaign.')
    campaign = campaign_detail(conn, campaign_id,organization=organization)
    if campaign.get('source_type','OVERTURE')!='OVERTURE':raise HTTPException(409,'Resume this source from its acquisition checkpoint.')
    if campaign["status"] in ["RUNNING", "QUEUED", "COMPLETED"]:
        raise HTTPException(409, "This campaign cannot be resumed in its current state.")
    conn.execute("UPDATE scan_campaigns SET cancellation_requested=0,completed_at=NULL,status='QUEUED' WHERE id=? AND organization_id=?", (campaign_id,organization))
    conn.commit()
    for run in campaign["runs"]:
        if run["status"] in ["CANCELLED", "FAILED", "INTERRUPTED"]:
            await scan_manager.resume_scan(run["id"])
    return campaign_detail(conn, campaign_id,organization=organization)
