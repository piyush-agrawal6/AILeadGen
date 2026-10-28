from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GeneralSettings(BaseModel):
    default_target: int = 50
    default_vertical: str = "restaurant"
    exclude_chains: bool = True
    default_min_tier: str = "B"


class DiscoverySettings(BaseModel):
    overture_enabled: bool = True
    osm_enabled: bool = True
    nominatim_endpoint: str = "https://nominatim.openstreetmap.org"
    overpass_endpoint: str = "https://overpass-api.de/api/interpreter"
    candidate_multiplier: int = 4


class CrawlerSettings(BaseModel):
    max_pages: int = Field(default=8, ge=1, le=30)
    page_timeout_seconds: int = Field(default=15, ge=3, le=60)
    max_site_duration_seconds: int = Field(default=60, ge=10, le=300)
    http_concurrency: int = Field(default=20, ge=1, le=100)
    crawl_concurrency: int = Field(default=5, ge=1, le=20)
    max_response_bytes: int = Field(default=3000000, ge=102400, le=5242880)


class AuditingSettings(BaseModel):
    lighthouse_enabled: bool = True
    lighthouse_concurrency: int = Field(default=2, ge=1, le=5)
    lighthouse_timeout_seconds: int = Field(default=60, ge=15, le=180)
    quick_audit_enabled: bool = True
    structured_data_detection: bool = True
    technology_detection: bool = True
    vertical_audit_enabled: bool = True


class ScoringPillarWeight(BaseModel):
    pillar: str
    max_points: float
    description: str


class ScoringSettings(BaseModel):
    minimum_score: float = 35.0
    pillars: List[ScoringPillarWeight] = [
        ScoringPillarWeight(pillar="Website Opportunity", max_points=55.0, description="Missing site, unreachable, missing HTTPS, poor performance"),
        ScoringPillarWeight(pillar="SEO Opportunity", max_points=20.0, description="Missing title, description, schema, viewport, open graph"),
        ScoringPillarWeight(pillar="Vertical Opportunity", max_points=15.0, description="Industry specific features such as menu, booking, listings"),
        ScoringPillarWeight(pillar="Contactability", max_points=10.0, description="Presence of verified email, phone, contact form, socials"),
    ]


class AppSettingsSchema(BaseModel):
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    discovery: DiscoverySettings = Field(default_factory=DiscoverySettings)
    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    auditing: AuditingSettings = Field(default_factory=AuditingSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
