"""HeySow multi-company foundation: organizations, memberships, profiles, onboarding.

Additive only. Existing rows are backfilled to the seeded PlaneByte organization;
no production data is dropped, truncated or recreated.
"""
import json
import uuid

# Deterministic identifier so every environment (dev, test, production) seeds the
# same PlaneByte organization and backfills to one stable tenant id.
PLANEBYTE_ORGANIZATION_ID = "e5ffc3dc-241e-5558-acd4-84f5fe354ca7"

ORGANIZATION_SQL = '''
CREATE TABLE organizations (
 id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 slug TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','SUSPENDED','ARCHIVED')),
 created_by_user_id TEXT REFERENCES users(id),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE organization_memberships (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 user_id TEXT NOT NULL REFERENCES users(id),
 role TEXT NOT NULL DEFAULT 'MEMBER' CHECK(role IN ('OWNER','ADMIN','MEMBER','VIEWER')),
 status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','INVITED','SUSPENDED','REVOKED')),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(organization_id,user_id)
);
CREATE INDEX idx_membership_user ON organization_memberships(user_id,status);
CREATE INDEX idx_membership_organization ON organization_memberships(organization_id,status);
CREATE TABLE user_profiles (
 user_id TEXT PRIMARY KEY REFERENCES users(id),
 display_name TEXT,
 job_title TEXT,
 phone TEXT,
 timezone TEXT,
 locale TEXT,
 avatar_url TEXT,
 onboarding_seen INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE organization_profiles (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 display_name TEXT,
 legal_name TEXT,
 company_type TEXT,
 website_url TEXT,
 primary_domain TEXT,
 tagline TEXT,
 short_description TEXT,
 long_description TEXT,
 industry TEXT,
 sub_industry TEXT,
 company_size TEXT,
 country TEXT,
 city TEXT,
 timezone TEXT,
 contact_email TEXT,
 contact_phone TEXT,
 linkedin_url TEXT,
 x_url TEXT,
 facebook_url TEXT,
 instagram_url TEXT,
 youtube_url TEXT,
 other_socials_json TEXT NOT NULL DEFAULT '{}',
 target_customer_types_json TEXT NOT NULL DEFAULT '[]',
 target_industries_json TEXT NOT NULL DEFAULT '[]',
 target_countries_json TEXT NOT NULL DEFAULT '[]',
 service_regions_json TEXT NOT NULL DEFAULT '[]',
 business_goals_json TEXT NOT NULL DEFAULT '[]',
 brand_logo_url TEXT,
 brand_favicon_url TEXT,
 brand_primary_color TEXT,
 brand_secondary_color TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE organization_services (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 name TEXT NOT NULL,
 slug TEXT NOT NULL,
 category TEXT,
 description TEXT,
 active INTEGER NOT NULL DEFAULT 1,
 source TEXT NOT NULL DEFAULT 'MANUAL' CHECK(source IN ('MANUAL','WEBSITE_DISCOVERY','SYSTEM_SEEDED','USER_CONFIRMED')),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(organization_id,slug)
);
CREATE INDEX idx_services_organization ON organization_services(organization_id,active);
CREATE TABLE organization_onboarding (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 status TEXT NOT NULL DEFAULT 'NOT_STARTED' CHECK(status IN ('NOT_STARTED','IN_PROGRESS','COMPLETED','FAILED')),
 current_step TEXT,
 setup_method TEXT CHECK(setup_method IS NULL OR setup_method IN ('MANUAL','WEBSITE_IMPORT','MANUAL_AND_WEBSITE','SYSTEM_SEEDED')),
 website_import_status TEXT,
 website_import_started_at TEXT,
 website_import_completed_at TEXT,
 website_import_error TEXT,
 website_import_preview_json TEXT,
 profile_completed INTEGER NOT NULL DEFAULT 0,
 services_completed INTEGER NOT NULL DEFAULT 0,
 audience_completed INTEGER NOT NULL DEFAULT 0,
 preferences_completed INTEGER NOT NULL DEFAULT 0,
 completed_at TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE organization_profile_sources (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 source_type TEXT NOT NULL CHECK(source_type IN ('USER_ENTERED','USER_CONFIRMED','WEBSITE_EXTRACTED','AI_INFERRED','SYSTEM_SEEDED')),
 source_url TEXT,
 field_name TEXT NOT NULL,
 extracted_value_json TEXT,
 confidence TEXT,
 detected_at TEXT NOT NULL,
 confirmed_by_user INTEGER NOT NULL DEFAULT 0,
 confirmed_at TEXT
);
CREATE INDEX idx_profile_sources_organization ON organization_profile_sources(organization_id,field_name);
CREATE TABLE organization_products (
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 product TEXT NOT NULL CHECK(product IN ('LEADGEN','INTENT_RADAR','SEARCH_VISIBILITY')),
 enabled INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,product)
);
ALTER TABLE users ADD COLUMN provider TEXT;
ALTER TABLE users ADD COLUMN updated_at TEXT;
ALTER TABLE audit_log ADD COLUMN organization_id TEXT;
ALTER TABLE shared_settings ADD COLUMN organization_id TEXT REFERENCES organizations(id);
'''

# Tenant-owned tables that gain an organization_id column. Every row addressable
# directly by an API route or background worker must be tenant scoped.
TENANT_TABLES = (
    'prospects', 'scan_campaigns', 'pipeline_runs', 'client_reports',
    'workflow_runs', 'automation_schedules', 'automation_scans',
    'email_accounts', 'email_templates', 'email_threads', 'email_drafts',
    'lead_lists', 'saved_views', 'saved_market_groups', 'experiments',
    'acquisition_jobs', 'acquisition_google_connections', 'contact_people',
    'followups', 'activities', 'prospect_sales', 'prospect_notes',
    'review_cases', 'master_lead_state', 'outreach_run_items',
    'campaign_settings_snapshots', 'campaign_business_snapshots',
    'lead_source_evidence', 'email_address_suppressions',
)

# Tenant-owned tables gain organization_id with a foreign key to organizations.id.
# Delete semantics stay restrictive (NO ACTION): removing an organization must be an
# explicit workflow, never a cascade that wipes a company's production data.
TENANT_TABLE_SQL = ''.join(
    f"ALTER TABLE {table} ADD COLUMN organization_id TEXT REFERENCES organizations(id);\n"
    for table in TENANT_TABLES
)

# The full migration: core organization DDL plus tenant columns.
ORGANIZATION_MIGRATION_SQL = ORGANIZATION_SQL + TENANT_TABLE_SQL

# Tables that already carry organization_id='planebyte' literals from migration 15.
LEGACY_LITERAL_TABLES = ('email_messages', 'contacted_recipients', 'contacted_recipient_sends',
                         'contacted_unsubscribe_tokens', 'company_pdf_assets')

PLANE_BYTE_SERVICES = (
    ('Custom Software Development', 'custom-software-development', 'Development', 'Bespoke software engineered around specific business workflows.'),
    ('Web Development', 'web-development', 'Development', 'Marketing sites and web platforms built for speed and conversion.'),
    ('Web Application Development', 'web-application-development', 'Development', 'Interactive web applications from MVP to production scale.'),
    ('Mobile Application Development', 'mobile-application-development', 'Development', 'Native and cross-platform mobile apps for iOS and Android.'),
    ('Desktop / macOS Applications', 'desktop-macos-applications', 'Development', 'Native desktop software for macOS and Windows.'),
    ('Cloud Engineering', 'cloud-engineering', 'Cloud', 'Cloud architecture, infrastructure-as-code and reliability engineering.'),
    ('Cloud Migration', 'cloud-migration', 'Cloud', 'Lift-and-shift and re-architecture migrations to the cloud.'),
    ('DevOps', 'devops', 'Cloud', 'CI/CD pipelines, observability and infrastructure automation.'),
    ('Cybersecurity', 'cybersecurity', 'Security', 'Security hardening, posture reviews and threat protection.'),
    ('Security Audits', 'security-audits', 'Security', 'Structured audits of application and infrastructure security.'),
    ('VAPT / Penetration Testing', 'vapt-penetration-testing', 'Security', 'Vulnerability assessment and penetration testing engagements.'),
    ('SEO', 'seo', 'Growth', 'Technical and content SEO that compounds organic traffic.'),
    ('Local SEO', 'local-seo', 'Growth', 'Local pack visibility, maps optimization and review strategy.'),
    ('AEO / Answer Engine Optimization', 'aeo-answer-engine-optimization', 'Growth', 'Visibility inside answer engines and AI-assisted search.'),
    ('GEO / Generative Engine Optimization', 'geo-generative-engine-optimization', 'Growth', 'Optimization for AI-generated answers and generative search.'),
    ('AI Integrations', 'ai-integrations', 'AI', 'Practical LLM and AI integrations embedded into products and workflows.'),
    ('AI Automation', 'ai-automation', 'AI', 'Agentic automation of repetitive business operations.'),
    ('Data / Analytics', 'data-analytics', 'Data', 'Pipelines, dashboards and decision-ready analytics.'),
    ('Product Development', 'product-development', 'Development', 'End-to-end product discovery, design and delivery.'),
    ('Game Development', 'game-development', 'Development', 'Interactive games and real-time experiences.'),
)

PLANE_BYTE_PROFILE = {
    'display_name': 'PlaneByte',
    'website_url': 'https://planebyte.com',
    'primary_domain': 'planebyte.com',
    'contact_email': 'contact@planebyte.com',
    'company_type': 'Software Studio',
    'short_description': 'Software engineering, cloud, cybersecurity and digital growth studio building custom software and technology solutions for businesses.',
    'industry': 'Software / Technology Services',
    'target_customer_types': ['Startups', 'SMBs', 'Local businesses', 'Agencies', 'SaaS companies'],
    'target_industries': ['Home Services', 'Dentists', 'Auto Repair', 'Real Estate / Property Management',
                          'Legal', 'Hotels / Hospitality', 'Veterinary', 'Startups / SaaS'],
    'target_countries': ['India', 'United States', 'United Kingdom', 'Canada', 'Australia', 'Germany', 'France'],
    'service_regions': ['India', 'United States', 'United Kingdom', 'Canada', 'Australia', 'Germany', 'France'],
}


def _slug(value):
    slug = ''.join(ch if ch.isalnum() else '-' for ch in value.lower()).strip('-')
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug or 'service'


def seed_plane_byte(conn):
    """Seed the PlaneByte organization, profile, services and owner membership."""
    from app.config.settings import get_settings
    settings = get_settings()
    org_id = PLANEBYTE_ORGANIZATION_ID
    owner_email = settings.allowed_emails[0] if settings.allowed_emails else 'planebyte@gmail.com'
    stamp = conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
    stamp = str(stamp)
    # The owner user must exist before the membership FK can reference it.
    conn.execute("INSERT INTO users(id,email,display_name,role) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING",
                 (owner_email, owner_email, owner_email.split('@')[0], 'ADMIN'))
    conn.execute("INSERT INTO organizations(id,name,slug,status,created_by_user_id,created_at,updated_at) "
                 "VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                 (org_id, 'PlaneByte', 'planebyte', 'ACTIVE', owner_email, stamp, stamp))
    profile = PLANE_BYTE_PROFILE
    conn.execute("""INSERT INTO organization_profiles(organization_id,display_name,company_type,website_url,primary_domain,
        contact_email,short_description,industry,target_customer_types_json,target_industries_json,
        target_countries_json,service_regions_json,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id) DO NOTHING""",
                 (org_id, profile['display_name'], profile['company_type'], profile['website_url'], profile['primary_domain'],
                  profile['contact_email'], profile['short_description'], profile['industry'],
                  json.dumps(profile['target_customer_types']), json.dumps(profile['target_industries']),
                  json.dumps(profile['target_countries']), json.dumps(profile['service_regions']), stamp, stamp))
    for name, slug, category, description in PLANE_BYTE_SERVICES:
        conn.execute("""INSERT INTO organization_services(id,organization_id,name,slug,category,description,active,source,created_at,updated_at)
            VALUES(?,?,?,?,?,?,1,'SYSTEM_SEEDED',?,?) ON CONFLICT(organization_id,slug) DO NOTHING""",
                     (str(uuid.uuid4()), org_id, name, slug, category, description, stamp, stamp))
    conn.execute("""INSERT INTO organization_onboarding(organization_id,status,setup_method,profile_completed,
        services_completed,audience_completed,preferences_completed,completed_at,created_at,updated_at)
        VALUES(?,'COMPLETED','SYSTEM_SEEDED',1,1,1,1,?,?,?) ON CONFLICT(organization_id) DO NOTHING""",
                 (org_id, stamp, stamp, stamp))
    conn.execute("""INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at)
        VALUES(?,?,?,?, 'ACTIVE',?,?) ON CONFLICT(organization_id,user_id) DO NOTHING""",
                 (str(uuid.uuid4()), org_id, owner_email, 'OWNER', stamp, stamp))
    for product, enabled in (('LEADGEN', 1), ('INTENT_RADAR', 0), ('SEARCH_VISIBILITY', 0)):
        conn.execute("""INSERT INTO organization_products(organization_id,product,enabled,created_at,updated_at)
            VALUES(?,?,?,?,?) ON CONFLICT(organization_id,product) DO NOTHING""",
                     (org_id, product, enabled, stamp, stamp))
    return org_id, owner_email


def apply(conn):
    """Seed PlaneByte, backfill tenant rows and verify zero orphans.

    Runs inside migration 16 after the DDL. Every existing tenant-owned row belongs
    to PlaneByte; the legacy 'planebyte' literal rows are rewritten to the seeded
    organization UUID so tenant scoping is uniform.
    """
    postgres = getattr(conn, 'backend', None) == 'postgres'
    org_id, owner_email = seed_plane_byte(conn)
    for table in TENANT_TABLES:
        conn.execute(f"UPDATE {table} SET organization_id=? WHERE organization_id IS NULL", (org_id,))
    for table in LEGACY_LITERAL_TABLES:
        conn.execute(f"UPDATE {table} SET organization_id=? WHERE organization_id=?", (org_id, 'planebyte'))
    # Historical audit rows belong to the PlaneByte workspace too.
    conn.execute("UPDATE audit_log SET organization_id=? WHERE organization_id IS NULL", (org_id,))
    conn.execute("UPDATE shared_settings SET organization_id=? WHERE organization_id IS NULL", (org_id,))
    orphans = []
    for table in TENANT_TABLES + LEGACY_LITERAL_TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE organization_id IS NULL").fetchone()[0]
        if count:
            orphans.append((table, count))
    if orphans:
        raise RuntimeError(f"Organization backfill left orphan rows: {orphans}")
    for table in TENANT_TABLES + ('audit_log',):
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_organization ON {table}(organization_id)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_settings_organization ON shared_settings(organization_id)")
    if postgres:
        conn.execute("ANALYZE organizations")
    return {'organization_id': org_id, 'owner': owner_email}


def ready(c):
    return (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0) >= 16
