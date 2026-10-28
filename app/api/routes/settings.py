from fastapi import APIRouter, Depends, Request
from app.api.dependencies import get_db
from app.database.prospects import now
import json
from app.api.schemas.settings import (
    AppSettingsSchema,
    AuditingSettings,
    CrawlerSettings,
    DiscoverySettings,
    GeneralSettings,
    ScoringSettings,
)
from app.config.settings import get_settings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=AppSettingsSchema)
def get_app_settings(conn=Depends(get_db)):
    """Retrieve active system and pipeline configuration."""
    s = get_settings()
    row = conn.execute("SELECT configuration_json FROM shared_settings WHERE id=1").fetchone()
    if row:
        return AppSettingsSchema.model_validate_json(row[0])

    return AppSettingsSchema(
        general=GeneralSettings(
            default_target=50,
            default_vertical="restaurant",
            exclude_chains=True,
            default_min_tier="B",
        ),
        discovery=DiscoverySettings(
            overture_enabled=True,
            osm_enabled=True,
            nominatim_endpoint=s.nominatim_url,
            overpass_endpoint=s.overpass_url,
            candidate_multiplier=s.discovery.raw_multiplier,
        ),
        crawler=CrawlerSettings(
            max_pages=s.crawl_max_pages,
            page_timeout_seconds=s.crawler.page_timeout_seconds,
            max_site_duration_seconds=s.crawler.max_site_duration_seconds,
            http_concurrency=s.http_concurrency,
            crawl_concurrency=s.crawl_concurrency,
            max_response_bytes=s.crawler.max_response_bytes,
        ),
        auditing=AuditingSettings(
            lighthouse_enabled=s.audit.lighthouse_enabled,
            lighthouse_concurrency=s.lighthouse_concurrency,
            lighthouse_timeout_seconds=s.audit.lighthouse_timeout_seconds,
            quick_audit_enabled=True,
            structured_data_detection=True,
            technology_detection=True,
            vertical_audit_enabled=True,
        ),
        scoring=ScoringSettings(),
    )


@router.put("", response_model=AppSettingsSchema)
def update_app_settings(updated: AppSettingsSchema, request: Request, conn=Depends(get_db)):
    """Safely apply updated settings to active pipeline configuration."""
    s = get_settings()

    # Update in-memory configuration safely
    s.crawl_max_pages = updated.crawler.max_pages
    s.crawler.max_pages_per_site = updated.crawler.max_pages
    s.crawler.page_timeout_seconds = updated.crawler.page_timeout_seconds
    s.crawler.max_site_duration_seconds = updated.crawler.max_site_duration_seconds
    s.http_concurrency = updated.crawler.http_concurrency
    s.crawler.concurrency = updated.crawler.crawl_concurrency
    s.crawl_concurrency = updated.crawler.crawl_concurrency
    s.crawler.max_response_bytes = updated.crawler.max_response_bytes

    s.audit.lighthouse_enabled = updated.auditing.lighthouse_enabled
    s.lighthouse_concurrency = updated.auditing.lighthouse_concurrency
    s.audit.lighthouse_concurrency = updated.auditing.lighthouse_concurrency
    s.audit.lighthouse_timeout_seconds = updated.auditing.lighthouse_timeout_seconds

    conn.execute("INSERT INTO shared_settings(id,configuration_json,updated_by,updated_at) VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET configuration_json=excluded.configuration_json,updated_by=excluded.updated_by,updated_at=excluded.updated_at", (updated.model_dump_json(),request.state.user_email,now()))
    return updated
