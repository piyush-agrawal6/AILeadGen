from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DashboardSummaryCards(BaseModel):
    total_businesses: int = 0
    qualified_leads: int = 0
    a_plus_leads: int = 0
    a_leads: int = 0
    no_website_opportunities: int = 0
    completed_scans: int = 0


class TierCount(BaseModel):
    tier: str
    count: int
    percentage: float = 0.0


class ServiceCount(BaseModel):
    service: str
    count: int


class VerticalCount(BaseModel):
    vertical: str
    count: int


class ScoreBucket(BaseModel):
    range: str
    count: int


class RecentScanItem(BaseModel):
    id: int
    market: str
    vertical: str
    status: str
    target: int
    qualified: int
    exported: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    output_file: Optional[str] = None


class DashboardResponse(BaseModel):
    cards: DashboardSummaryCards
    tier_distribution: List[TierCount]
    recommended_services: List[ServiceCount]
    vertical_distribution: List[VerticalCount]
    score_distribution: List[ScoreBucket]
    recent_scans: List[RecentScanItem]
