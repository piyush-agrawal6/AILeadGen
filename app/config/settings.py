import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, model_validator, AliasChoices, SecretStr, field_validator
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
    # Billing is additive and sandbox-only. Public checkout is fail-closed.
    billing_enabled:bool=False
    billing_provider:Literal['creem','razorpay','payu']='creem'
    billing_test_mode:bool=True
    billing_public_checkout_enabled:bool=False
    billing_test_workspaces:str=''
    billing_catalog_json:str=''
    razorpay_mode:Literal['test']='test'
    razorpay_key_id:str=Field('',repr=False)
    razorpay_key_secret:SecretStr=SecretStr('')
    razorpay_webhook_secret:SecretStr=SecretStr('')
    razorpay_test_plan_id_starter:str=''
    razorpay_test_plan_id_growth:str=''
    razorpay_test_plan_id_scale:str=''
    # Hosted PayU credentials remain server-only. Configuring keys does not
    # authorize charges, establish recurring capability, or select a currency.
    payu_billing_enabled:bool=False
    payu_mode:Literal['test','live']='test'
    payu_merchant_key:str=Field('',repr=False)
    payu_merchant_salt:SecretStr=SecretStr('')
    lead_engine_public_enabled:bool=False
    # Reversible product availability, independent of preserved paid/manual grants.
    lead_engine_available:bool=False

    intent_radar_stage:Literal['Disabled','Internal Preview','Beta']=Field('Disabled',alias='INTENT_RADAR_STAGE')
    intent_radar_growth_enabled:bool=Field(False,alias='INTENT_RADAR_GROWTH_ENABLED')
    intent_radar_internal_workspaces:str=Field('',alias='INTENT_RADAR_INTERNAL_WORKSPACES')
    intent_radar_daily_searches:int=Field(20,ge=1,le=50)
    intent_radar_global_daily_searches:int=Field(100,ge=1,le=200)
    intent_radar_monitor_limit:int=Field(50,ge=1,le=100)
    intent_radar_ai_enabled:bool=Field(False,alias='INTENT_RADAR_AI_ENABLED')
    intent_radar_stackexchange_enabled:bool=False
    intent_radar_stackexchange_key:SecretStr=SecretStr('')
    intent_radar_stackexchange_sites:str='stackoverflow;softwareengineering;webmasters'
    intent_radar_approved_feed_hosts:str=''

    @field_validator('intent_radar_stackexchange_sites','intent_radar_approved_feed_hosts',mode='before')
    @classmethod
    def source_configuration_lists(cls,value):
        # The owner-provided site list uses commas; prior deployments use
        # semicolons. Normalize both without losing an existing approved entry.
        import re
        return ';'.join(dict.fromkeys(part.strip().casefold() for part in re.split(r'[;,]',str(value or '')) if part.strip()))

    intent_radar_sources_v2_enabled:bool=False
    github_app_id:str=''
    github_app_slug:str='planebyte-intent-radar'
    github_app_private_key:SecretStr=SecretStr('')
    github_app_private_key_secret:str=''
    github_app_installation_id:str=''
    github_app_client_id:str=''
    github_app_client_secret:SecretStr=SecretStr('')
    github_app_webhook_secret:SecretStr=SecretStr('')
    github_oauth_redirect_uri:str='https://app.planebyte.com/intent-radar/integrations/github/callback'
    github_api_version:str='2026-03-10'
    intent_radar_github_enabled:bool=False
    intent_radar_github_public_search_enabled:bool=False
    intent_radar_github_monitoring_enabled:bool=False
    intent_radar_github_webhooks_enabled:bool=False
    youtube_api_key:SecretStr=SecretStr('')
    youtube_daily_search_limit:int=Field(80,ge=1,le=1000)
    youtube_workspace_daily_search_limit:int=Field(10,ge=1,le=200)
    youtube_daily_unit_limit:int=Field(9000,ge=100,le=100000)
    youtube_workspace_daily_unit_limit:int=Field(500,ge=10,le=20000)
    intent_radar_youtube_enabled:bool=False
    intent_radar_youtube_search_enabled:bool=False
    intent_radar_youtube_comments_enabled:bool=False
    intent_radar_youtube_monitoring_enabled:bool=False
    intent_radar_youtube_ai_analytics_enabled:bool=False
    intent_radar_youtube_cross_source_analytics_enabled:bool=False
    bluesky_api_base_url:str='https://api.bsky.app'
    bluesky_jetstream_url:str='wss://jetstream.us-east.bsky.network/xrpc/network.bsky.jetstream.subscribeEvents'
    bluesky_identifier:str=''
    bluesky_app_password:SecretStr=SecretStr('')
    intent_radar_bluesky_enabled:bool=False
    intent_radar_bluesky_jetstream_enabled:bool=False

    @field_validator('bluesky_jetstream_url',mode='before')
    @classmethod
    def normalize_jetstream_url(cls,value):
        raw=str(value or '').strip().rstrip('/')
        if not raw:return 'wss://jetstream.us-east.bsky.network/xrpc/network.bsky.jetstream.subscribeEvents'
        if '/xrpc/' not in raw:return raw+'/xrpc/network.bsky.jetstream.subscribeEvents'
        return raw
    intent_radar_schedules_enabled:bool=False
    intent_radar_min_schedule_hours:int=Field(12,ge=6,le=24)
    intent_radar_ai_daily_calls:int=Field(10,ge=1,le=50)
    intent_radar_ai_daily_tokens:int=Field(60000,ge=6000,le=300000)
    heysow_webhooks_enabled:bool=Field(False,alias='HEYSOW_WEBHOOKS_ENABLED')
    radar_webhook_events_enabled:bool=Field(False,alias='RADAR_WEBHOOK_EVENTS_ENABLED')
    radar_webhook_workspaces:str=Field('',alias='RADAR_WEBHOOK_WORKSPACES')
    radar_sheets_workspaces:str=Field('',alias='RADAR_SHEETS_WORKSPACES')
    owner_starter_grant_id:str=Field('',alias='OWNER_STARTER_GRANT_ID')
    heysow_mcp_enabled:bool=Field(False,alias='HEYSOW_MCP_ENABLED')
    mcp_allowed_hosts:str=Field('localhost:*,127.0.0.1:*,testserver,leads.planebyte.com',alias='MCP_ALLOWED_HOSTS')
    mcp_allowed_origins:str=Field('http://localhost:*,http://127.0.0.1:*,https://leads.planebyte.com',alias='MCP_ALLOWED_ORIGINS')
    heysow_developer_api_enabled:bool=Field(False,alias='HEYSOW_DEVELOPER_API_ENABLED')
    developer_key_requests_per_minute:int=Field(60,ge=1,le=600)
    developer_workspace_requests_per_minute:int=Field(300,ge=1,le=3000)
    intelligence_active_jobs:int=Field(5,ge=1,le=20)
    intelligence_daily_records:int=Field(1000,ge=1,le=10000)
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
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
    database_schema: str = Field(default='public',alias='DATABASE_SCHEMA',pattern=r'^[a-z][a-z0-9_]{0,62}$')
    database_schema_profile: Literal['legacy','intent-radar-v1'] = Field(default='legacy',alias='DATABASE_SCHEMA_PROFILE')
    database_background_polling_enabled: bool = Field(default=True,alias='DATABASE_BACKGROUND_POLLING_ENABLED')
    upstash_redis_rest_url: str = Field(default='',alias='UPSTASH_REDIS_REST_URL',repr=False)
    upstash_redis_rest_token: str = Field(default='',alias='UPSTASH_REDIS_REST_TOKEN',repr=False)
    api_signing_secret: str = Field(default="", alias="LEADENGINE_API_SIGNING_SECRET", repr=False)
    allowed_user_emails: str = Field(default="", alias="ALLOWED_USER_EMAILS")
    auth_disabled_local: bool = Field(default=False, alias="AUTH_DISABLED_LOCAL")
    heysow_internal_experiments_enabled: bool = Field(False,alias='HEYSOW_INTERNAL_EXPERIMENTS_ENABLED')
    heysow_workspace_creation_limit:int=Field(5,ge=1,le=100,alias='HEYSOW_WORKSPACE_CREATION_LIMIT')
    heysow_pending_invitation_limit:int=Field(100,ge=1,le=10000,alias='HEYSOW_PENDING_INVITATION_LIMIT')
    heysow_icp_limit:int=Field(50,ge=1,le=1000,alias='HEYSOW_ICP_LIMIT')
    heysow_domain_limit:int=Field(20,ge=1,le=100,alias='HEYSOW_DOMAIN_LIMIT')
    heysow_company_discovery_enabled:bool=Field(False,alias='HEYSOW_COMPANY_DISCOVERY_ENABLED')
    heysow_company_ai_enabled:bool=Field(False,alias='HEYSOW_COMPANY_AI_ENABLED')
    heysow_company_js_enabled:bool=Field(False,alias='HEYSOW_COMPANY_JS_ENABLED')
    heysow_setup_diagnostics_enabled:bool=Field(False,alias='HEYSOW_SETUP_DIAGNOSTICS_ENABLED')
    heysow_company_ai_daily_limit:int=Field(10,ge=1,le=100,alias='HEYSOW_COMPANY_AI_DAILY_LIMIT')
    heysow_company_ai_global_daily_limit:int=Field(100,ge=1,le=1000,alias='HEYSOW_COMPANY_AI_GLOBAL_DAILY_LIMIT')
    heysow_company_discovery_hourly_limit:int=Field(5,ge=1,le=100,alias='HEYSOW_COMPANY_DISCOVERY_HOURLY_LIMIT')
    heysow_company_discovery_global_hourly_limit:int=Field(50,ge=1,le=1000,alias='HEYSOW_COMPANY_DISCOVERY_GLOBAL_HOURLY_LIMIT')
    heysow_lead_assistant_enabled:bool=Field(False,alias='HEYSOW_LEAD_ASSISTANT_ENABLED')
    heysow_icp_ai_enabled:bool=Field(False,alias='HEYSOW_ICP_AI_ENABLED')
    heysow_icp_ai_daily_limit:int=Field(10,ge=1,le=1000,alias='HEYSOW_ICP_AI_DAILY_LIMIT')
    heysow_icp_ai_global_daily_limit:int=Field(100,ge=1,le=10000,alias='HEYSOW_ICP_AI_GLOBAL_DAILY_LIMIT')
    heysow_workspace_management_enabled: bool = Field(False,alias='HEYSOW_WORKSPACE_MANAGEMENT_ENABLED')
    heysow_accounts_enabled:bool=Field(False,alias='HEYSOW_ACCOUNTS_ENABLED')
    heysow_work_email_only_enabled:bool=Field(True,alias='HEYSOW_WORK_EMAIL_ONLY_ENABLED')
    heysow_registration_acceptance_emails:str=Field('',max_length=2000,alias='HEYSOW_REGISTRATION_ACCEPTANCE_EMAILS',repr=False,exclude=True)
    heysow_access_periods_enabled:bool=Field(False,alias='HEYSOW_ACCESS_PERIODS_ENABLED')
    transactional_mail_enabled:bool=Field(False,alias='TRANSACTIONAL_MAIL_ENABLED')
    transactional_mail_daily_limit:int=Field(100,ge=1,le=10000,alias='TRANSACTIONAL_MAIL_DAILY_LIMIT')
    resend_api_key:SecretStr=Field(SecretStr(''),alias='RESEND_API_KEY',repr=False,exclude=True)
    resend_from_email:str=Field('',max_length=254,alias='RESEND_FROM_EMAIL')
    resend_webhook_secret:SecretStr=Field(SecretStr(''),alias='RESEND_WEBHOOK_SECRET',repr=False,exclude=True)
    fixed_term_billing_enabled:bool=Field(False,alias='FIXED_TERM_BILLING_ENABLED')
    creem_api_key:SecretStr=Field(SecretStr(''),alias='CREEM_API_KEY',repr=False,exclude=True)
    creem_test_api_key:SecretStr=Field(SecretStr(''),alias='CREEM_TEST_API_KEY',repr=False,exclude=True)
    creem_webhook_secret:SecretStr=Field(SecretStr(''),alias='CREEM_WEBHOOK_SECRET',repr=False,exclude=True)
    creem_test_webhook_secret:SecretStr=Field(SecretStr(''),alias='CREEM_TEST_WEBHOOK_SECRET',repr=False,exclude=True)
    creem_environment:Literal['production','test']=Field('production',alias='CREEM_ENVIRONMENT')
    subscription_onboarding_required:bool=Field(False,alias='SUBSCRIPTION_ONBOARDING_REQUIRED')
    subscription_terms_version:str=Field('',alias='SUBSCRIPTION_TERMS_VERSION')
    subscription_checkout_enabled:bool=Field(False,alias='SUBSCRIPTION_CHECKOUT_ENABLED')
    # Temporary, server-only, auditable internal testing allowance for an explicitly
    # allowlisted owner workspace that already holds a verified Creem contract.
    # Disabled by default; auto-expires at INTERNAL_TESTING_EXPIRES_AT (UTC epoch).
    internal_testing_workspace_id:str=Field('',alias='INTERNAL_TESTING_WORKSPACE_ID')
    internal_testing_owner_email:str=Field('',alias='INTERNAL_TESTING_OWNER_EMAIL',repr=False,exclude=True)
    internal_testing_expires_at:int=Field(0,ge=0,alias='INTERNAL_TESTING_EXPIRES_AT')
    internal_testing_searches_limit:int=Field(100,ge=5,le=200,alias='INTERNAL_TESTING_SEARCHES_LIMIT')
    internal_testing_ai_calls_limit:int=Field(40,ge=3,le=100,alias='INTERNAL_TESTING_AI_CALLS_LIMIT')
    internal_testing_ai_tokens_limit:int=Field(1500000,ge=150000,le=3000000,alias='INTERNAL_TESTING_AI_TOKENS_LIMIT')
    internal_testing_monitors_limit:int=Field(5,ge=1,le=20,alias='INTERNAL_TESTING_MONITORS_LIMIT')
    internal_testing_monitor_executions_limit:int=Field(20,ge=0,le=100,alias='INTERNAL_TESTING_MONITOR_EXECUTIONS_LIMIT')
    internal_testing_reports_limit:int=Field(10,ge=0,le=50,alias='INTERNAL_TESTING_REPORTS_LIMIT')
    internal_testing_api_requests_limit:int=Field(200,ge=0,le=1000,alias='INTERNAL_TESTING_API_REQUESTS_LIMIT')
    payu_one_time_checkout_enabled:bool=Field(False,alias='PAYU_ONE_TIME_CHECKOUT_ENABLED')
    payu_charge_currency:str=Field('',pattern=r'^(|USD|INR)$',alias='PAYU_CHARGE_CURRENCY')
    payu_merchant_capabilities_json:str=Field('{}',alias='PAYU_MERCHANT_CAPABILITIES_JSON')
    payu_currency_approved:bool=Field(False,alias='PAYU_CURRENCY_APPROVED')
    payu_tax_policy_json:str=Field('{}',alias='PAYU_TAX_POLICY_JSON')
    payu_inr_prices_json:str=Field('{}',alias='PAYU_INR_PRICES_JSON')
    payu_yearly_prices_json:str=Field('{}',alias='PAYU_YEARLY_PRICES_JSON')
    billing_terms_version:str=Field('',max_length=100,alias='BILLING_TERMS_VERSION')
    heysow_public_registration_enabled:bool=Field(False,alias='HEYSOW_PUBLIC_REGISTRATION_ENABLED')
    heysow_invited_registration_enabled:bool=Field(False,alias='HEYSOW_INVITED_REGISTRATION_ENABLED')
    heysow_customer_access_enabled:bool=Field(False,alias='HEYSOW_CUSTOMER_ACCESS_ENABLED')
    heysow_google_admission_client_id:str=Field('',alias='HEYSOW_GOOGLE_ADMISSION_CLIENT_ID',repr=False)
    heysow_terms_version:str=Field('',max_length=100,alias='HEYSOW_TERMS_VERSION')
    heysow_customer_integrations_enabled:bool=Field(False,alias='HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED')
    radar_google_sheets_redirect_uri:str=Field('',alias='RADAR_GOOGLE_SHEETS_REDIRECT_URI')
    heysow_customer_gmail_enabled:bool=Field(False,alias='HEYSOW_CUSTOMER_GMAIL_ENABLED')
    heysow_customer_gmail_redirect_uri:str=Field('',alias='HEYSOW_CUSTOMER_GMAIL_REDIRECT_URI')
    heysow_customer_mail_sending_enabled:bool=Field(False,alias='HEYSOW_CUSTOMER_MAIL_SENDING_ENABLED')
    heysow_customer_mail_schedules_enabled:bool=Field(False,alias='HEYSOW_CUSTOMER_MAIL_SCHEDULES_ENABLED')
    heysow_customer_mail_live_approved:bool=Field(False,alias='HEYSOW_CUSTOMER_MAIL_LIVE_APPROVED')
    heysow_customer_mail_mode:Literal['test','production']=Field('test',alias='HEYSOW_CUSTOMER_MAIL_MODE')
    heysow_customer_mail_test_recipient:str=Field('',alias='HEYSOW_CUSTOMER_MAIL_TEST_RECIPIENT',repr=False,exclude=True)
    heysow_integration_encryption_key:str=Field('',alias='HEYSOW_INTEGRATION_ENCRYPTION_KEY',repr=False,exclude=True)
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
    organization_id: str = Field('planebyte',alias='LEADENGINE_ORGANIZATION_ID',pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    lead_qualification_mode: Literal['CONTACTABLE_ONLY','ANALYZED','STRICT'] = Field('CONTACTABLE_ONLY',alias='LEAD_QUALIFICATION_MODE')
    enable_pre_outreach_analysis: bool = Field(False,alias='ENABLE_PRE_OUTREACH_ANALYSIS')
    max_cities_per_scan: int = Field(default=10, ge=1, le=10, alias="MAX_CITIES_PER_SCAN")
    max_target_leads: int = Field(default=1000, ge=5, le=1000, alias="MAX_TARGET_LEADS")
    max_raw_businesses: int = Field(default=10000, ge=20, le=10000, alias="MAX_RAW_BUSINESSES")
    max_lighthouse_audits: int = Field(default=500, ge=0, le=500, alias="MAX_LIGHTHOUSE_AUDITS")
    max_scan_runtime_minutes: int = Field(default=180, ge=1, le=180, alias="MAX_SCAN_RUNTIME_MINUTES")
    seo_crawl_max_pages: int = Field(default=30, ge=1, le=30, alias="SEO_CRAWL_MAX_PAGES")
    r2_endpoint: str = Field(default="", alias="R2_ENDPOINT")
    radar_actions_enabled: bool = Field(False,alias='RADAR_ACTIONS_ENABLED')
    radar_hubspot_enabled: bool = Field(False,alias='RADAR_HUBSPOT_ENABLED')
    radar_hubspot_workspaces: str = Field('',alias='RADAR_HUBSPOT_WORKSPACES')
    radar_hubspot_write_portals: str = Field('',alias='RADAR_HUBSPOT_WRITE_PORTALS')
    radar_hubspot_client_id: str = Field('',alias='RADAR_HUBSPOT_CLIENT_ID')
    radar_hubspot_client_secret: SecretStr = Field(SecretStr(''),alias='RADAR_HUBSPOT_CLIENT_SECRET',repr=False,exclude=True)
    radar_hubspot_redirect_uri: str = Field('',alias='RADAR_HUBSPOT_REDIRECT_URI')
    r2_access_key_id: str = Field(default="", alias="R2_ACCESS_KEY_ID", repr=False)
    r2_secret_access_key: str = Field(default="", alias="R2_SECRET_ACCESS_KEY", repr=False)
    r2_bucket_name: str = Field(default="", alias="R2_BUCKET_NAME")
    reports_r2_bucket:str=Field('',alias='R2_BUCKET')
    reports_r2_access_key_id:SecretStr=Field(SecretStr(''),alias='REPORTS_R2_ACCESS_KEY_ID',repr=False,exclude=True)
    reports_r2_secret_access_key:SecretStr=Field(SecretStr(''),alias='REPORTS_R2_SECRET_ACCESS_KEY',repr=False,exclude=True)
    reports_r2_new_writes:bool=Field(False,alias='REPORTS_R2_NEW_WRITES')
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
            if self.database_schema_profile=='intent-radar-v1' and self.lead_engine_available:
                raise ValueError('The Intent Radar schema cannot enable Lead Engine')
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
