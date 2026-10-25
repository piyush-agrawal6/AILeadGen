import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
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
