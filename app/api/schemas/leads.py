from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class LeadListItem(BaseModel):
    id: int
    run_id: Optional[int] = None
    name: str
    vertical: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    domain: Optional[str] = None
    website_status: str
    phone: Optional[str] = None
    public_email: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    total_score: float = 0.0
    tier: str = "D"
    recommended_service: Optional[str] = None
    performance_score: Optional[float] = None
    seo_score: Optional[float] = None
    calculated_at: Optional[str] = None


class LeadPaginationResponse(BaseModel):
    items: List[LeadListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class FindingDetail(BaseModel):
    id: int
    finding_code: str
    category: str
    severity: str
    title: str
    description: str
    evidence: Optional[str] = None
    score_points: float = 0.0


class ContactDetail(BaseModel):
    id: int
    type: str
    value: str
    source_type: Optional[str] = None
    confidence: float = 1.0


class LighthouseMetrics(BaseModel):
    performance_score: Optional[float] = None
    seo_score: Optional[float] = None
    accessibility_score: Optional[float] = None
    best_practices_score: Optional[float] = None
    lcp_ms: Optional[float] = None
    cls: Optional[float] = None
    tbt_ms: Optional[float] = None
    fcp_ms: Optional[float] = None
    speed_index_ms: Optional[float] = None


class WebsiteProfileDetail(BaseModel):
    http_status: Optional[int] = None
    https_enabled: bool = False
    reachable: bool = False
    redirect_count: int = 0
    final_url: Optional[str] = None
    html_title: Optional[str] = None
    meta_description: Optional[str] = None
    has_contact_page: bool = False
    has_booking: bool = False
    has_menu: bool = False
    detected_technologies: List[str] = []
    schema_types: List[str] = []
    page_count_crawled: int = 0


class LeadScoreBreakdown(BaseModel):
    total: float = 0.0
    tier: str = "D"
    website_score: float = 0.0
    seo_score: float = 0.0
    vertical_score: float = 0.0
    contactability_score: float = 0.0
    recommended_service: str = "NONE"
    recommended_angle: str = ""
    breakdown: Dict[str, Any] = {}
    calculated_at: Optional[str] = None


class LeadDetailResponse(BaseModel):
    business: Dict[str, Any]
    website_status: str
    score: Optional[LeadScoreBreakdown] = None
    profile: Optional[WebsiteProfileDetail] = None
    lighthouse: Optional[LighthouseMetrics] = None
    findings: List[FindingDetail] = []
    contacts: List[ContactDetail] = []
