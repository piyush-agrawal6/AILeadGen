"""Workspace configuration service shared by HTTP routes and background jobs."""
import json
from app.api.organization import workspace_settings
from app.config.settings import get_settings
from app.api.schemas.settings import AppSettingsSchema,AuditingSettings,CrawlerSettings,DiscoverySettings,GeneralSettings,ScoringSettings

def load_settings(conn,organization=None):
    """Missing context returns environment defaults, never another tenant's settings."""
    s = get_settings()
    stored = workspace_settings(conn, organization) if organization else {}
    if stored:
        return AppSettingsSchema.model_validate_json(json.dumps(stored))

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

