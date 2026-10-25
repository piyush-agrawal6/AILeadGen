from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    NORMALIZED = "NORMALIZED"
    DEDUPED = "DEDUPED"
    HTTP_PROBED = "HTTP_PROBED"
    CRAWLED = "CRAWLED"
    AUDITED = "AUDITED"
    SCORED = "SCORED"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"


class ContactType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    CONTACT_FORM = "contact_form"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    X_URL = "x_url"
    BOOKING = "booking"


class Business(BaseModel):
    id: Optional[int] = None
    external_overture_id: Optional[str] = None
    external_osm_id: Optional[str] = None

    name: str
    normalized_name: str

    vertical: str
    subcategory: Optional[str] = None

    country: Optional[str] = None
    country_code: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    address: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    phone: Optional[str] = None
    normalized_phone: Optional[str] = None

    website: Optional[str] = None
    domain: Optional[str] = None

    public_email: Optional[str] = None

    instagram: Optional[str] = None
    facebook: Optional[str] = None
    linkedin: Optional[str] = None
    x_url: Optional[str] = None

    source_overture: bool = False
    source_osm: bool = False
    source_confidence: float = 0.5
    operating_status: Optional[str] = "active"

    is_chain: bool = False
    is_duplicate: bool = False
    is_rejected: bool = False
    rejection_reason: Optional[str] = None
    processing_status: str = ProcessingStatus.DISCOVERED.value

    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WebsiteProfile(BaseModel):
    id: Optional[int] = None
    business_id: int

    requested_url: str
    final_url: Optional[str] = None
    domain: Optional[str] = None

    http_status: Optional[int] = None
    https_enabled: bool = False
    reachable: bool = False
    redirect_count: int = 0

    html_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None

    has_viewport: bool = False
    has_h1: bool = False
    h1_count: int = 0

    has_robots_txt: bool = False
    has_sitemap: bool = False

    has_schema: bool = False
    schema_types: List[str] = Field(default_factory=list)

    has_open_graph: bool = False

    has_analytics: bool = False
    analytics_providers: List[str] = Field(default_factory=list)

    has_contact_page: bool = False
    contact_page_url: Optional[str] = None

    has_booking: bool = False
    booking_url: Optional[str] = None

    has_menu: bool = False
    menu_url: Optional[str] = None
    menu_is_pdf: bool = False

    has_phone_on_site: bool = False
    has_email_on_site: bool = False

    detected_technologies: List[str] = Field(default_factory=list)

    page_count_crawled: int = 0
    crawl_duration_ms: int = 0

    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Contact(BaseModel):
    id: Optional[int] = None
    business_id: int

    contact_type: str
    contact_value: str

    source_url: Optional[str] = None
    source_type: str = "WEBSITE"  # WEBSITE, OVERTURE, OSM, DNS

    confidence: float = 1.0
    is_public_business_contact: bool = True
    is_valid: bool = True

    created_at: Optional[str] = None


class LighthouseResult(BaseModel):
    id: Optional[int] = None
    business_id: int

    performance_score: Optional[float] = None
    seo_score: Optional[float] = None
    accessibility_score: Optional[float] = None
    best_practices_score: Optional[float] = None

    lcp_ms: Optional[float] = None
    cls: Optional[float] = None
    tbt_ms: Optional[float] = None
    fcp_ms: Optional[float] = None
    speed_index_ms: Optional[float] = None

    raw_report_path: Optional[str] = None
    created_at: Optional[str] = None


class Finding(BaseModel):
    id: Optional[int] = None
    business_id: int

    finding_code: str
    category: str
    severity: str  # HIGH, MEDIUM, LOW, INFO

    title: str
    description: str = ""

    evidence: Optional[str] = None
    source_url: Optional[str] = None

    score_points: int = 0
    created_at: Optional[str] = None


class LeadScore(BaseModel):
    business_id: int

    total_score: float = 0.0
    tier: str = "D"

    website_score: float = 0.0
    seo_opportunity_score: float = 0.0
    vertical_opportunity_score: float = 0.0
    contactability_score: float = 0.0

    recommended_service: str = "NONE"
    recommended_angle: str = ""

    score_breakdown: Dict[str, Any] = Field(default_factory=dict)
    calculated_at: Optional[str] = None


class PipelineRun(BaseModel):
    id: Optional[int] = None

    market: str
    vertical: str
    target: int = 250

    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    status: str = "RUNNING"  # RUNNING, COMPLETED, FAILED, INTERRUPTED

    raw_found: int = 0
    deduped: int = 0
    filtered: int = 0
    websites_processed: int = 0
    qualified: int = 0
    exported: int = 0

    output_file: Optional[str] = None
    error_message: Optional[str] = None
