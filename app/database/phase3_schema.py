PHASE3_SQL = """
CREATE TABLE users (
    id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
    avatar_url TEXT, role TEXT NOT NULL DEFAULT 'ADMIN', last_login TEXT
);
CREATE TABLE scan_campaigns (
    id TEXT PRIMARY KEY, created_by TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'QUEUED',
    configuration_json TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT,
    target_total INTEGER NOT NULL, cancellation_requested INTEGER NOT NULL DEFAULT 0
);
ALTER TABLE pipeline_runs ADD COLUMN campaign_id TEXT REFERENCES scan_campaigns(id);
ALTER TABLE pipeline_runs ADD COLUMN cancellation_requested INTEGER NOT NULL DEFAULT 0;
ALTER TABLE pipeline_runs ADD COLUMN execution_name TEXT;
ALTER TABLE pipeline_runs ADD COLUMN lease_owner TEXT;
ALTER TABLE pipeline_runs ADD COLUMN lease_expires_at TEXT;
ALTER TABLE pipeline_runs ADD COLUMN failure_class TEXT;
CREATE INDEX idx_runs_campaign ON pipeline_runs(campaign_id, status);
CREATE TABLE prospects (
    id TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
    first_campaign_id TEXT, times_discovered INTEGER NOT NULL DEFAULT 0,
    lead_status TEXT NOT NULL DEFAULT 'NEW' CHECK(lead_status IN ('NEW','SHORTLISTED','CONTACTED','REPLIED','NOT_INTERESTED','DO_NOT_CONTACT','WON')),
    assigned_to TEXT REFERENCES users(id), created_by TEXT, updated_by TEXT, updated_at TEXT NOT NULL,
    business_scale TEXT NOT NULL DEFAULT 'LOCAL', scale_reason TEXT, scale_confidence REAL NOT NULL DEFAULT 0.5
);
CREATE TABLE business_identities (
    identity_key TEXT PRIMARY KEY, prospect_id TEXT NOT NULL REFERENCES prospects(id), evidence_type TEXT NOT NULL
);
ALTER TABLE businesses ADD COLUMN prospect_id TEXT REFERENCES prospects(id);
CREATE INDEX idx_businesses_prospect ON businesses(prospect_id, id);
CREATE INDEX idx_prospects_workflow ON prospects(lead_status, assigned_to);
CREATE INDEX idx_prospects_seen ON prospects(first_seen_at, last_seen_at);
CREATE TABLE prospect_observations (
    prospect_id TEXT NOT NULL REFERENCES prospects(id), run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),
    business_id INTEGER NOT NULL UNIQUE REFERENCES businesses(id), observed_at TEXT NOT NULL,
    PRIMARY KEY(prospect_id,run_id)
);
CREATE TABLE prospect_notes (
    id TEXT PRIMARY KEY, prospect_id TEXT NOT NULL REFERENCES prospects(id), body TEXT NOT NULL,
    created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX idx_notes_prospect ON prospect_notes(prospect_id, created_at);
CREATE TABLE opportunity_scores (
    business_id INTEGER PRIMARY KEY REFERENCES businesses(id), run_id INTEGER REFERENCES pipeline_runs(id),
    website_opportunity_score INTEGER NOT NULL CHECK(website_opportunity_score BETWEEN 0 AND 100),
    seo_opportunity_score INTEGER CHECK(seo_opportunity_score BETWEEN 0 AND 100),
    security_opportunity_score INTEGER CHECK(security_opportunity_score BETWEEN 0 AND 100),
    primary_opportunity TEXT, secondary_opportunity TEXT, contactability_level TEXT NOT NULL,
    scoring_version TEXT NOT NULL, evidence_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX idx_opportunity_website ON opportunity_scores(website_opportunity_score);
CREATE INDEX idx_opportunity_seo ON opportunity_scores(seo_opportunity_score);
CREATE INDEX idx_opportunity_security ON opportunity_scores(security_opportunity_score);
CREATE TABLE internal_request_nonces (nonce TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);
CREATE INDEX idx_nonce_expiry ON internal_request_nonces(expires_at);
CREATE TABLE artifact_objects (
    object_key TEXT PRIMARY KEY, run_id INTEGER REFERENCES pipeline_runs(id), business_id INTEGER REFERENCES businesses(id),
    kind TEXT NOT NULL, content_type TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE shared_settings (id INTEGER PRIMARY KEY CHECK(id=1), configuration_json TEXT NOT NULL, updated_by TEXT NOT NULL, updated_at TEXT NOT NULL);
"""
