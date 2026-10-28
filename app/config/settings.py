import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, model_validator, AliasChoices
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    env: str = "development"
    user_agent: str = "LeadEngine/1.0 (+https://planebyte.com)"
    contact_email: str = "leadengine@planebyte.com"


class DatabaseConfig(BaseModel):
    path: str = "data/lead_engine.db"


class CrawlerConfig(BaseModel):
    max_pages_per_site: int = 8
    max_depth: int = 2
    page_timeout_seconds: int = 12
    max_site_duration_seconds: int = 45
    max_response_bytes: int = 3000000
    concurrency: int = 4
    per_domain_concurrency: int = 1


class HttpConfig(BaseModel):
    timeout_seconds: int = 10
    retries: int = 2
    concurrency: int = 15


class DiscoveryConfig(BaseModel):
    raw_multiplier: int = 10
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    overture_s3_region: str = "us-west-2"
    overture_release: str = "2024-04-16.0"


class AuditConfig(BaseModel):
    lighthouse_enabled: bool = True
    lighthouse_timeout_seconds: int = 90
    lighthouse_concurrency: int = 1
    lighthouse_command: str = "lighthouse"
    preliminary_score_threshold: int = 30


class ExportConfig(BaseModel):
    include_rejected: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    crawler_user_agent: str = Field(
        default="LeadEngine/1.0 (+https://planebyte.com)",
        alias="CRAWLER_USER_AGENT",
    )
    crawler_contact_email: str = Field(
        default="leadengine@planebyte.com",
        alias="CRAWLER_CONTACT_EMAIL",
    )
    database_path: str = Field(default="data/lead_engine.db", alias="DATABASE_PATH")
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL", repr=False)
    api_signing_secret: str = Field(default="", alias="LEADENGINE_API_SIGNING_SECRET", repr=False)
    allowed_user_emails: str = Field(default="", alias="ALLOWED_USER_EMAILS")
    auth_disabled_local: bool = Field(default=False, alias="AUTH_DISABLED_LOCAL")
    scan_executor: Literal["local", "gcp"] = Field(default="local", alias="SCAN_EXECUTOR")
    gcp_project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="", alias="GCP_REGION")
    cloud_run_job: str = Field(default="leadengine-worker", validation_alias=AliasChoices("LEADENGINE_CLOUD_RUN_JOB","CLOUD_RUN_JOB"))
    max_active_scans: int = Field(default=2, ge=1, le=8, alias="MAX_ACTIVE_SCANS")
    social_enrichment_enabled: bool = Field(default=True,alias="SOCIAL_ENRICHMENT_ENABLED")
    social_activity_enabled: bool = Field(default=True,alias="SOCIAL_ACTIVITY_ENABLED")
    social_activity_recent_days: int = Field(default=30,ge=1,le=365,alias="SOCIAL_ACTIVITY_RECENT_DAYS")
    social_activity_active_days: int = Field(default=90,ge=31,le=730,alias="SOCIAL_ACTIVITY_ACTIVE_DAYS")
    social_activity_concurrency: int = Field(default=2,ge=1,le=4,alias="SOCIAL_ACTIVITY_CONCURRENCY")
    social_profile_max_requests_per_business: int = Field(default=4,ge=0,le=8,alias="SOCIAL_PROFILE_MAX_REQUESTS_PER_BUSINESS")
    social_profile_timeout_seconds: int = Field(default=8,ge=1,le=15,alias="SOCIAL_PROFILE_TIMEOUT_SECONDS")
    max_cities_per_scan: int = Field(default=10, ge=1, le=10, alias="MAX_CITIES_PER_SCAN")
    max_target_leads: int = Field(default=1000, ge=5, le=1000, alias="MAX_TARGET_LEADS")
    max_raw_businesses: int = Field(default=10000, ge=20, le=10000, alias="MAX_RAW_BUSINESSES")
    max_lighthouse_audits: int = Field(default=500, ge=0, le=500, alias="MAX_LIGHTHOUSE_AUDITS")
    max_scan_runtime_minutes: int = Field(default=180, ge=1, le=180, alias="MAX_SCAN_RUNTIME_MINUTES")
    seo_crawl_max_pages: int = Field(default=30, ge=1, le=30, alias="SEO_CRAWL_MAX_PAGES")
    r2_endpoint: str = Field(default="", alias="R2_ENDPOINT")
    r2_access_key_id: str = Field(default="", alias="R2_ACCESS_KEY_ID", repr=False)
    r2_secret_access_key: str = Field(default="", alias="R2_SECRET_ACCESS_KEY", repr=False)
    r2_bucket_name: str = Field(default="", alias="R2_BUCKET_NAME")
    r2_region: str = Field(default="auto", alias="R2_REGION")

    @property
    def allowed_emails(self) -> list[str]:
        return [email.strip().lower() for email in self.allowed_user_emails.split(",") if email.strip()]

    @model_validator(mode="after")
    def production_configuration(self):
        if self.social_activity_recent_days >= self.social_activity_active_days:
            raise ValueError('The recent activity window must be shorter than the active window')
        if (os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_EXECUTION")) and self.app_env != "production":
            raise ValueError("Cloud runtimes require APP_ENV=production")
        if self.app_env == "production":
            if not self.database_url or not self.database_url.startswith(("postgres://", "postgresql://")):
                raise ValueError("Production requires a PostgreSQL DATABASE_URL")
            if os.environ.get("LEADENGINE_ROLE") != "worker" and (len(self.api_signing_secret) < 32 or not self.allowed_emails or len(self.allowed_emails) > 2):
                raise ValueError("Production requires a strong API signing secret and one or two allowlisted accounts")
            if self.auth_disabled_local:
                raise ValueError("Local authentication bypass is forbidden in production")
            if self.scan_executor != "gcp" or not self.gcp_project_id or not self.gcp_region:
                raise ValueError("Production requires a configured GCP worker")
            if not all([self.r2_endpoint.startswith("https://"), self.r2_access_key_id, self.r2_secret_access_key, self.r2_bucket_name]):
                raise ValueError("Production requires private R2 storage configuration")
        return self
    overture_s3_region: str = Field(default="us-west-2", alias="OVERTURE_S3_REGION")
    overture_release: str = Field(default="", alias="OVERTURE_RELEASE")
    overpass_url: str = Field(
        default="https://overpass-api.de/api/interpreter",
        alias="OVERPASS_URL",
    )
    nominatim_url: str = Field(
        default="https://nominatim.openstreetmap.org",
        alias="NOMINATIM_URL",
    )
    lighthouse_command: str = Field(default="lighthouse", alias="LIGHTHOUSE_COMMAND")
    crawl_max_pages: int = Field(default=8, alias="CRAWL_MAX_PAGES")
    crawl_concurrency: int = Field(default=4, alias="CRAWL_CONCURRENCY")
    http_concurrency: int = Field(default=15, alias="HTTP_CONCURRENCY")
    lighthouse_concurrency: int = Field(default=1, alias="LIGHTHOUSE_CONCURRENCY")

    # Nested sub-configs
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    http: HttpConfig = Field(default_factory=HttpConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    def load_yaml_overrides(self, path: str = "config/settings.yaml") -> None:
        """Merge values from config/settings.yaml if it exists."""
        p = Path(path)
        if not p.exists():
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            if "app" in data:
                self.app = AppConfig(**{**self.app.model_dump(), **data["app"]})
            if "database" in data:
                self.database = DatabaseConfig(**{**self.database.model_dump(), **data["database"]})
            if "crawler" in data:
                self.crawler = CrawlerConfig(**{**self.crawler.model_dump(), **data["crawler"]})
            if "http" in data:
                self.http = HttpConfig(**{**self.http.model_dump(), **data["http"]})
            if "discovery" in data:
                self.discovery = DiscoveryConfig(**{**self.discovery.model_dump(), **data["discovery"]})
            if "audit" in data:
                self.audit = AuditConfig(**{**self.audit.model_dump(), **data["audit"]})
            if "export" in data:
                self.export = ExportConfig(**{**self.export.model_dump(), **data["export"]})

            # Align top-level env aliases with yaml overrides if not overridden by env
            if self.crawler_user_agent == "LeadEngine/1.0 (+https://planebyte.com)" and self.app.user_agent:
                self.crawler_user_agent = self.app.user_agent
            if self.database_path == "data/lead_engine.db" and self.database.path:
                self.database_path = self.database.path
            if self.crawl_max_pages == 8 and self.crawler.max_pages_per_site:
                self.crawl_max_pages = self.crawler.max_pages_per_site
            if self.crawl_concurrency == 4 and self.crawler.concurrency:
                self.crawl_concurrency = self.crawler.concurrency
            if self.http_concurrency == 15 and self.http.concurrency:
                self.http_concurrency = self.http.concurrency
            if self.lighthouse_command == "lighthouse" and self.audit.lighthouse_command:
                self.lighthouse_command = self.audit.lighthouse_command
        except Exception as e:
            import logging
            logging.getLogger("leadengine").warning(f"Error loading yaml overrides from {path}: {e}")


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
        _settings_instance.load_yaml_overrides()
    return _settings_instance
