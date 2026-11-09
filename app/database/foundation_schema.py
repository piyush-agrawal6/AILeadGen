"""Additive campaign history and reuse metadata; no second lead identity system."""
FOUNDATION_SQL = '''
CREATE TABLE campaign_settings_snapshots (
 campaign_id TEXT PRIMARY KEY REFERENCES scan_campaigns(id),
 signature TEXT NOT NULL, settings_json TEXT NOT NULL, captured_at TEXT NOT NULL,
 provenance TEXT NOT NULL, source_schedule_id TEXT
);
CREATE INDEX idx_campaign_signature ON campaign_settings_snapshots(signature,captured_at);
CREATE TABLE campaign_business_snapshots (
 campaign_id TEXT NOT NULL REFERENCES scan_campaigns(id),
 business_id INTEGER NOT NULL REFERENCES businesses(id),
 prospect_id TEXT NOT NULL REFERENCES prospects(id),
 snapshot_json TEXT NOT NULL,captured_at TEXT NOT NULL,
 PRIMARY KEY(campaign_id,business_id)
);
CREATE INDEX idx_campaign_snapshot_prospect ON campaign_business_snapshots(campaign_id,prospect_id);
CREATE TABLE analysis_cache (
 prospect_id TEXT NOT NULL REFERENCES prospects(id), analyzer TEXT NOT NULL,
 source_business_id INTEGER NOT NULL REFERENCES businesses(id),
 fingerprint TEXT NOT NULL, configuration_hash TEXT NOT NULL,
 payload_json TEXT NOT NULL,analyzed_at TEXT NOT NULL,expires_at TEXT NOT NULL,
 PRIMARY KEY(prospect_id,analyzer)
);
CREATE INDEX idx_analysis_expiry ON analysis_cache(expires_at);
CREATE TABLE worker_attempts (
 id TEXT PRIMARY KEY,run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),
 started_at TEXT NOT NULL,finished_at TEXT,runtime_seconds REAL,status TEXT NOT NULL
);
CREATE TABLE analysis_operations (
 run_id INTEGER NOT NULL REFERENCES pipeline_runs(id), business_id INTEGER NOT NULL REFERENCES businesses(id),
 analyzer TEXT NOT NULL,operation TEXT NOT NULL,recorded_at TEXT NOT NULL,
 PRIMARY KEY(run_id,business_id,analyzer)
);
CREATE TABLE review_cases (
 id TEXT PRIMARY KEY,prospect_id TEXT REFERENCES prospects(id),business_id INTEGER REFERENCES businesses(id),
 campaign_id TEXT REFERENCES scan_campaigns(id),reason TEXT NOT NULL,evidence_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'OPEN',resolution TEXT,created_at TEXT NOT NULL,resolved_at TEXT,resolved_by TEXT
);
CREATE INDEX idx_review_open ON review_cases(status,reason,created_at);
CREATE TABLE contact_evidence (
 contact_id INTEGER PRIMARY KEY REFERENCES contacts(id) ON DELETE CASCADE,
 verification_state TEXT NOT NULL,source_url TEXT NOT NULL,checked_at TEXT NOT NULL,checked_by TEXT NOT NULL
);
CREATE TABLE contact_people (
 id TEXT PRIMARY KEY,prospect_id TEXT NOT NULL REFERENCES prospects(id),name TEXT NOT NULL,
 role TEXT,profile_url TEXT,work_email TEXT,confidence TEXT NOT NULL DEFAULT 'UNKNOWN',
 source_url TEXT NOT NULL,created_at TEXT NOT NULL,created_by TEXT NOT NULL
);
CREATE TABLE identity_resolutions (
 fingerprint TEXT PRIMARY KEY,prospect_id TEXT NOT NULL REFERENCES prospects(id),
 decision TEXT NOT NULL,actor TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE TABLE duplicate_resolutions (
 source_id TEXT PRIMARY KEY,target_id TEXT NOT NULL REFERENCES prospects(id),
 archived_json TEXT NOT NULL,created_at TEXT NOT NULL,actor TEXT NOT NULL
);
CREATE TABLE account_roles (email TEXT PRIMARY KEY,role TEXT NOT NULL,updated_at TEXT NOT NULL,updated_by TEXT NOT NULL);
CREATE TABLE audit_log (
 id TEXT PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,entity TEXT NOT NULL,
 result TEXT NOT NULL,details_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL
);
CREATE INDEX idx_audit_time ON audit_log(created_at);
CREATE TABLE recovery_checkpoints (
 id TEXT PRIMARY KEY,created_at TEXT NOT NULL,schema_version INTEGER NOT NULL,
 reason TEXT NOT NULL,target_version INTEGER,status TEXT NOT NULL,artifact_path TEXT NOT NULL,
 manifest_json TEXT NOT NULL
);
CREATE TABLE saved_market_groups (
 id TEXT PRIMARY KEY,name TEXT NOT NULL,locations_json TEXT NOT NULL,
 created_by TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE TABLE provider_rate_limits (provider TEXT PRIMARY KEY,next_request_at REAL NOT NULL);
CREATE TABLE worker_health (
 name TEXT PRIMARY KEY,status TEXT NOT NULL,started_at TEXT,last_success_at TEXT,
 last_failure_at TEXT,last_error_code TEXT,updated_at TEXT NOT NULL
);
CREATE INDEX idx_business_run_status ON businesses(run_id,processing_status,prospect_id);
CREATE INDEX idx_pipeline_campaign_status ON pipeline_runs(campaign_id,status);
CREATE INDEX idx_messages_prospect_direction ON email_messages(prospect_id,direction,status);
CREATE INDEX idx_findings_business_code ON findings(business_id,finding_code);
'''

def ready(c):
    if getattr(c,'_foundation_ready',None) is not None:return c._foundation_ready
    result=(c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0) >= 12
    if result:
        try:c._foundation_ready=True
        except AttributeError:pass
    return result
