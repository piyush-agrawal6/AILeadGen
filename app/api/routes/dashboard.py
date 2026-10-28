import sqlite3
from typing import Any, Dict
from fastapi import APIRouter, Depends

from app.api.dependencies import get_db
from app.api.schemas.dashboard import (
    DashboardResponse,
    DashboardSummaryCards,
    RecentScanItem,
    ScoreBucket,
    ServiceCount,
    TierCount,
    VerticalCount,
)
from app.database.repositories import BusinessRepository

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(conn: sqlite3.Connection = Depends(get_db)):
    """Fetch aggregated business, scoring, and pipeline run metrics for the dashboard."""
    repo = BusinessRepository(conn)
    raw = repo.get_dashboard_stats()

    total_scored = sum(raw["tiers"].values())
    tier_distribution = []
    for tier, count in raw["tiers"].items():
        pct = (count / total_scored * 100.0) if total_scored > 0 else 0.0
        tier_distribution.append(TierCount(tier=tier, count=count, percentage=round(pct, 1)))

    services = [ServiceCount(service=s["name"], count=s["count"]) for s in raw["services"]]
    verticals = [VerticalCount(vertical=v["name"], count=v["count"]) for v in raw["verticals"]]
    score_dist = [ScoreBucket(range=b["range"], count=b["count"]) for b in raw["score_distribution"]]

    recent_scans = []
    for s in raw["recent_scans"]:
        duration = None
        if s.get("started_at") and s.get("finished_at"):
            try:
                from datetime import datetime
                t0 = datetime.fromisoformat(s["started_at"])
                t1 = datetime.fromisoformat(s["finished_at"])
                duration = round((t1 - t0).total_seconds(), 1)
            except Exception:
                duration = None

        recent_scans.append(
            RecentScanItem(
                id=s["id"],
                market=s["market"],
                vertical=s["vertical"],
                status=s["status"],
                target=s["target"],
                qualified=s["qualified"],
                exported=s["exported"],
                started_at=s["started_at"],
                finished_at=s["finished_at"],
                duration_seconds=duration,
            )
        )

    cards = DashboardSummaryCards(
        total_businesses=raw["total_businesses"],
        qualified_leads=raw["qualified_leads"],
        a_plus_leads=raw["a_plus_leads"],
        a_leads=raw["a_leads"],
        no_website_opportunities=raw["no_website_leads"],
        completed_scans=raw["completed_scans"],
    )

    return DashboardResponse(
        cards=cards,
        tier_distribution=tier_distribution,
        recommended_services=services,
        vertical_distribution=verticals,
        score_distribution=score_dist,
        recent_scans=recent_scans,
    )
