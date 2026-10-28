import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.dependencies import get_db
from app.api.schemas.leads import (
    ContactDetail,
    FindingDetail,
    LeadDetailResponse,
    LeadListItem,
    LeadPaginationResponse,
    LeadScoreBreakdown,
    LighthouseMetrics,
    WebsiteProfileDetail,
)
from app.database.repositories import (
    BusinessRepository,
    FindingRepository,
    LeadScoreRepository,
    LighthouseRepository,
    WebsiteProfileRepository,
)
from app.exports.report import generate_html_report

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=LeadPaginationResponse)
def search_leads(
    search: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    vertical: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    website_status: Optional[str] = Query(None),
    has_email: Optional[bool] = Query(None),
    has_phone: Optional[bool] = Query(None),
    has_form: Optional[bool] = Query(None),
    recommended_service: Optional[str] = Query(None),
    min_perf: Optional[float] = Query(None),
    max_perf: Optional[float] = Query(None),
    min_seo: Optional[float] = Query(None),
    max_seo: Optional[float] = Query(None),
    source: Optional[str] = Query(None),
    quality_status: Optional[str] = Query(None),
    run_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: Literal["score", "performance", "seo", "name", "newest", "oldest"] = Query("score"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Search and paginate prospects with multi-dimensional filtering and sorting."""
    repo = BusinessRepository(conn)
    leads_raw, total = repo.search_leads(
        search=search,
        tier=tier,
        min_score=min_score,
        vertical=vertical,
        country=country,
        state=state,
        city=city,
        website_status=website_status,
        has_email=has_email,
        has_phone=has_phone,
        has_form=has_form,
        recommended_service=recommended_service,
        min_perf=min_perf,
        max_perf=max_perf,
        min_seo=min_seo,
        max_seo=max_seo,
        source=source,
        quality_status=quality_status,
        run_id=run_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    items = [
        LeadListItem(
            id=r["id"],
            run_id=r.get("run_id"),
            name=r["name"],
            vertical=r["vertical"],
            city=r["city"],
            state=r["state"],
            country=r["country"],
            website=r["website"],
            domain=r["domain"],
            website_status=r["website_status"],
            phone=r["phone"],
            public_email=r["email"],
            instagram=r["instagram"],
            facebook=r["facebook"],
            linkedin=r["linkedin"],
            total_score=r["score"],
            tier=r["tier"],
            recommended_service=r["recommended_service"],
            performance_score=r["performance"],
            seo_score=r["seo"],
            calculated_at=r["audit_date"],
        )
        for r in leads_raw
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return LeadPaginationResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
def get_lead_detail(lead_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Fetch complete prospect intelligence dossier for a single business."""
    repo = BusinessRepository(conn)
    data = repo.get_lead_detail(lead_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Lead #{lead_id} not found.")

    score_obj = None
    if data.get("score"):
        s = data["score"]
        score_obj = LeadScoreBreakdown(
            total=s["total"],
            tier=s["tier"],
            website_score=s["website_score"],
            seo_score=s["seo_score"],
            vertical_score=s["vertical_score"],
            contactability_score=s["contactability_score"],
            recommended_service=s["recommended_service"],
            recommended_angle=s["recommended_angle"],
            breakdown=s.get("breakdown") or {},
            calculated_at=s.get("calculated_at"),
        )

    profile_obj = None
    if data.get("profile"):
        p = data["profile"]
        profile_obj = WebsiteProfileDetail(
            http_status=p.get("http_status"),
            https_enabled=p.get("https_enabled", False),
            reachable=p.get("reachable", False),
            redirect_count=p.get("redirect_count", 0),
            final_url=p.get("final_url"),
            html_title=p.get("html_title"),
            meta_description=p.get("meta_description"),
            has_contact_page=p.get("has_contact_page", False),
            has_booking=p.get("has_booking", False),
            has_menu=p.get("has_menu", False),
            detected_technologies=p.get("detected_technologies") or p.get("technologies") or [],
            schema_types=p.get("schema_types") or [],
            page_count_crawled=p.get("page_count_crawled", 0),
        )

    lh_obj = None
    if data.get("lighthouse"):
        lh = data["lighthouse"]
        lh_obj = LighthouseMetrics(
            performance_score=lh.get("performance_score",lh.get("performance")),
            seo_score=lh.get("seo_score",lh.get("seo")),
            accessibility_score=lh.get("accessibility_score",lh.get("accessibility")),
            best_practices_score=lh.get("best_practices_score",lh.get("best_practices")),
            lcp_ms=lh.get("lcp_ms"),
            cls=lh.get("cls"),
            tbt_ms=lh.get("tbt_ms"),
            fcp_ms=lh.get("fcp_ms"),
            speed_index_ms=lh.get("speed_index_ms"),
        )

    findings = [
        FindingDetail(
            id=f["id"],
            finding_code=f["finding_code"],
            category=f["category"],
            severity=f["severity"],
            title=f["title"],
            description=f["description"],
            evidence=f.get("evidence"),
            score_points=float(f.get("score_points", 0.0)),
        )
        for f in data.get("findings", [])
    ]

    contacts = [
        ContactDetail(
            id=c["id"],
            type=c["type"],
            value=c["value"],
            source_type=c.get("source_type"),
            confidence=float(c.get("confidence", 1.0)),
        )
        for c in data.get("contacts", [])
    ]

    return LeadDetailResponse(
        business=data["business"],
        website_status=data["website_status"],
        score=score_obj,
        profile=profile_obj,
        lighthouse=lh_obj,
        findings=findings,
        contacts=contacts,
    )


@router.post("/{lead_id}/report")
def generate_lead_report(lead_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Generate a clean standalone HTML audit report for a prospect."""
    biz_repo = BusinessRepository(conn)
    score_repo = LeadScoreRepository(conn)
    profile_repo = WebsiteProfileRepository(conn)
    lh_repo = LighthouseRepository(conn)
    finding_repo = FindingRepository(conn)

    b = biz_repo.get_by_id(lead_id)
    if not b:
        raise HTTPException(status_code=404, detail=f"Lead #{lead_id} not found.")

    score = score_repo.get_by_business_id(lead_id)
    if not score:
        raise HTTPException(status_code=400, detail=f"Lead #{lead_id} has not been scored yet.")

    profile = profile_repo.get_by_business_id(lead_id)
    lh = lh_repo.get_by_business_id(lead_id)
    findings = finding_repo.list_by_business_id(lead_id)

    from app.exports.phase3 import attach_workflow
    attach_workflow(conn,lead_id,score)

    report_path = generate_html_report(
        business=b,
        score=score,
        profile=profile,
        lh=lh,
        findings=findings,
    )
    from app.storage import publish_artifact
    publish_artifact(conn, f"prospects/{b.id}/reports/report.html", report_path, business_id=lead_id, kind="html")

    return {
        "success": True,
        "message": "HTML audit report generated successfully.",
        "report_file": str(report_path.name),
        "download_url": f"/api/leads/{lead_id}/report",
    }


@router.get("/{lead_id}/report")
def download_lead_report(lead_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Download or view the generated HTML audit report for a prospect."""
    from app.storage import download_artifact
    artifact = download_artifact(conn, business_id=lead_id, kind="html")
    if artifact is not None:
        return artifact
    biz_repo = BusinessRepository(conn)
    b = biz_repo.get_by_id(lead_id)
    if not b:
        raise HTTPException(status_code=404, detail=f"Lead #{lead_id} not found.")

    reports_dir = Path("output/reports").resolve()
    # Find matching report file starting with "{lead_id}_"
    matches = list(reports_dir.glob(f"{lead_id}_*.html")) if reports_dir.exists() else []
    if not matches:
        # Generate on-demand if not already generated
        score_repo = LeadScoreRepository(conn)
        score = score_repo.get_by_business_id(lead_id)
        if not score:
            raise HTTPException(status_code=404, detail="Lead has not been scored and has no report.")
        profile = WebsiteProfileRepository(conn).get_by_business_id(lead_id)
        lh = LighthouseRepository(conn).get_by_business_id(lead_id)
        findings = FindingRepository(conn).list_by_business_id(lead_id)
        report_path = generate_html_report(b, score, profile, lh, findings)
        from app.storage import publish_artifact
        publish_artifact(conn,f"prospects/{lead_id}/reports/report.html",report_path,business_id=lead_id,kind="html")
        return download_artifact(conn,business_id=lead_id,kind="html")
    else:
        report_path = matches[0]

    return FileResponse(
        path=report_path,
        media_type="text/html",
        filename=report_path.name,
    )
