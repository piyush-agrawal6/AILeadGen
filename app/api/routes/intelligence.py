from typing import Literal
from fastapi import APIRouter, Depends, Query
from app.api.dependencies import get_db

router = APIRouter(prefix="/intelligence", tags=["Lead intelligence"])


def scope_sql(campaign=None, run_id=None):
    conditions, params = [], []
    if campaign:
        conditions.append("b.run_id IN (SELECT id FROM pipeline_runs WHERE campaign_id=?)")
        params.append(campaign)
    if run_id:
        conditions.append("b.run_id=?")
        params.append(run_id)
    scope = "WHERE " + " AND ".join(conditions) if conditions else ""
    cte = f"""WITH scoped AS (SELECT b.* FROM businesses b {scope}),
      latest AS (SELECT MAX(id) AS id FROM scoped GROUP BY COALESCE(prospect_id,CAST(id AS TEXT))) """
    joins = """ FROM scoped b JOIN latest l ON b.id=l.id
      LEFT JOIN prospects p ON p.id=b.prospect_id
      LEFT JOIN opportunity_scores o ON o.business_id=b.id """
    return cte, joins, params


@router.get("/leads")
def leads(search: str = Query("", max_length=200), country: str = Query("", max_length=100), city: str = Query("", max_length=100),
          vertical: str = Query("", max_length=100), opportunity: Literal["", "WEBSITE", "SEO", "SECURITY"] = "",
          primary: Literal["", "WEBSITE", "SEO", "SECURITY"] = "", contactability: Literal["", "HIGH", "MEDIUM", "LOW"] = "",
          business_scale: str = Query("", max_length=120), status: str = Query("", max_length=30), assigned_to: str = Query("", max_length=254),
          min_website: int = Query(0, ge=0, le=100), min_seo: int = Query(0, ge=0, le=100), min_security: int = Query(0, ge=0, le=100),
          campaign: str = Query("", max_length=36), run_id: int | None = Query(None, ge=1), results: Literal["all", "new", "previous"] = "all",
          page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
          commercial_fit: Literal["", "HIGH", "MEDIUM", "LOW", "UNKNOWN"] = "",
          list_id: str = Query('',max_length=36),
          sort_by: Literal["website", "seo", "security", "newest", "name", "commercial_fit"] = "website", sort_dir: Literal["asc", "desc"] = "desc", conn=Depends(get_db)):
    cte, joins, params = scope_sql(campaign, run_id)
    from app.database.phase36_schema import phase36_ready
    enriched = phase36_ready(conn)
    if enriched:joins += ' LEFT JOIN business_intelligence i ON i.business_id=b.id '
    conditions = ["b.is_rejected=0", "b.is_duplicate=0", "b.processing_status='QUALIFIED'"]
    from app.database.phase4_schema import ready as sales_ready
    if sales_ready(conn):
        if not status:conditions.append("p.lead_status<>'DO_NOT_CONTACT' AND NOT EXISTS(SELECT 1 FROM prospect_sales s WHERE s.prospect_id=p.id AND s.suppressed_at IS NOT NULL)")
        if list_id:conditions.append('EXISTS(SELECT 1 FROM lead_list_members m WHERE m.prospect_id=p.id AND m.list_id=?)');params.append(list_id)
    for value, column in [(country,"b.country"),(city,"b.city"),(vertical,"b.vertical"),(primary,"o.primary_opportunity"),(contactability,"o.contactability_level"),(status,"p.lead_status")]:
        if value:
            conditions.append(column+"=?")
            params.append(value)
    if business_scale:
        from fastapi import HTTPException
        scales=list(dict.fromkeys(business_scale.split(',')))
        if any(s not in ('LOCAL','SMALL_GROUP','MID_MARKET','REGIONAL','ENTERPRISE','KNOWN_CHAIN') for s in scales):raise HTTPException(422,'Choose valid business sizes.')
        conditions.append(('COALESCE(i.business_scale,p.business_scale)' if enriched else 'p.business_scale')+' IN ('+','.join('?' for _ in scales)+')')
        params.extend(scales)
    if search:
        conditions.append("(LOWER(b.name) LIKE ? OR LOWER(b.domain) LIKE ?)")
        params.extend(["%"+search.casefold()+"%"]*2)
    if commercial_fit:
        conditions.append("COALESCE(i.commercial_fit,'UNKNOWN')=?" if enriched else "?='UNKNOWN'")
        params.append(commercial_fit)
    for minimum, column in [(min_website,"website"),(min_seo,"seo"),(min_security,"security")]:
        if minimum:
            conditions.append(f"o.{column}_opportunity_score>=?")
            params.append(minimum)
    if opportunity:
        conditions.append(f"o.{opportunity.lower()}_opportunity_score>=40")
    if assigned_to:
        conditions.append("p.assigned_to IS NULL" if assigned_to == "unassigned" else "p.assigned_to=?")
        if assigned_to != "unassigned": params.append(assigned_to)
    if results != "all":
        if campaign:
            conditions.append("p.first_campaign_id=?" if results == "new" else "(p.first_campaign_id IS NULL OR p.first_campaign_id<>?)")
            params.append(campaign)
        else:
            conditions.append("p.times_discovered=1" if results == "new" else "p.times_discovered>1")
    where = " WHERE " + " AND ".join(conditions)
    total = conn.execute(cte + "SELECT COUNT(*)"+joins+where, params).fetchone()[0]
    order = {"website":"o.website_opportunity_score", "seo":"o.seo_opportunity_score", "security":"o.security_opportunity_score", "newest":"b.id", "name":"b.name", "commercial_fit":"CASE i.commercial_fit WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 1 ELSE 0 END" if enriched else 'b.id'}[sort_by]
    order = f"COALESCE({order},0)" if sort_by in ["website","seo","security"] else order
    columns = """b.id,b.name,b.vertical,b.city,b.country,b.country_code,b.domain,b.website,b.phone,b.public_email,b.run_id,b.prospect_id,
      o.website_opportunity_score,o.seo_opportunity_score,o.security_opportunity_score,o.primary_opportunity,o.secondary_opportunity,
      o.contactability_level,p.first_seen_at,p.last_seen_at,p.times_discovered,p.assigned_to,p.business_scale,
      COALESCE(p.lead_status,'NEW') AS lead_status,
      (SELECT r.id FROM client_reports r WHERE r.prospect_id=b.prospect_id ORDER BY version DESC LIMIT 1) AS latest_report_id,
      (SELECT r.status FROM client_reports r WHERE r.prospect_id=b.prospect_id ORDER BY version DESC LIMIT 1) AS latest_report_status,
      (SELECT r.version FROM client_reports r WHERE r.prospect_id=b.prospect_id ORDER BY version DESC LIMIT 1) AS report_version,
      (SELECT r.id FROM client_reports r WHERE r.prospect_id=b.prospect_id AND r.status='READY' ORDER BY version DESC LIMIT 1) AS ready_report_id"""
    if enriched:
        columns=columns.replace('p.business_scale,','COALESCE(i.business_scale,p.business_scale) AS business_scale,')
        columns += ",COALESCE(i.commercial_fit,'UNKNOWN') AS commercial_fit,COALESCE(i.social_presence_status,'UNKNOWN') AS social_presence_status"
    rows = conn.execute(cte+"SELECT "+columns+joins+where+f" ORDER BY {order} {sort_dir.upper()},b.id DESC LIMIT ? OFFSET ?", params+[page_size,(page-1)*page_size]).fetchall()
    items=[dict(row) for row in rows]
    profiles={}
    pids=list({r['prospect_id'] for r in items if r['prospect_id']})
    if enriched and pids:
        for r in conn.execute('SELECT prospect_id,platform,profile_url,activity_status,confidence FROM social_profiles WHERE prospect_id IN ('+','.join('?' for _ in pids)+') ORDER BY platform',pids).fetchall():profiles.setdefault(r['prospect_id'],[]).append(dict(r))
    for item in items:item['social_profiles']=profiles.get(item['prospect_id'],[])
    return {"items":items,"total":total,"page":page,"page_size":page_size,"total_pages":max(1,(total+page_size-1)//page_size)}


@router.get("/overview")
def overview(conn=Depends(get_db)):
    cte, joins, params = scope_sql()
    result = dict(conn.execute(cte+"""SELECT COUNT(*) AS total_leads,
      COALESCE(SUM(CASE WHEN o.business_id IS NOT NULL THEN 1 ELSE 0 END),0) AS assessed_leads,
      COALESCE(SUM(CASE WHEN o.business_id IS NULL THEN 1 ELSE 0 END),0) AS unassessed_leads,
      COALESCE(SUM(CASE WHEN p.times_discovered=1 THEN 1 ELSE 0 END),0) AS new_leads,
      COALESCE(SUM(CASE WHEN o.website_opportunity_score>=65 OR o.seo_opportunity_score>=65 OR o.security_opportunity_score>=65 THEN 1 ELSE 0 END),0) AS high_intent,
      COALESCE(SUM(CASE WHEN o.website_opportunity_score>=40 THEN 1 ELSE 0 END),0) AS website,
      COALESCE(SUM(CASE WHEN o.seo_opportunity_score>=40 THEN 1 ELSE 0 END),0) AS seo,
      COALESCE(SUM(CASE WHEN o.security_opportunity_score>=40 THEN 1 ELSE 0 END),0) AS security,
      COALESCE(SUM(CASE WHEN COALESCE(p.lead_status,'NEW') IN ('NEW','SHORTLISTED') THEN 1 ELSE 0 END),0) AS uncontacted
      """+joins+" WHERE b.processing_status='QUALIFIED' AND b.is_rejected=0",params).fetchone())
    result["statuses"] = [dict(r) for r in conn.execute(cte+"SELECT COALESCE(p.lead_status,'NEW') AS lead_status,COUNT(*) AS count"+joins+" WHERE b.processing_status='QUALIFIED' AND b.is_rejected=0 GROUP BY COALESCE(p.lead_status,'NEW')").fetchall()]
    result["markets"] = [dict(r) for r in conn.execute(cte+"SELECT b.city,b.vertical,COUNT(*) AS count"+joins+" WHERE b.processing_status='QUALIFIED' GROUP BY b.city,b.vertical ORDER BY count DESC LIMIT 5").fetchall()]
    result["running_campaigns"] = conn.execute("SELECT COUNT(*) FROM scan_campaigns c WHERE EXISTS(SELECT 1 FROM pipeline_runs r WHERE r.campaign_id=c.id AND r.status IN ('RUNNING','QUEUED'))").fetchone()[0]
    return result
