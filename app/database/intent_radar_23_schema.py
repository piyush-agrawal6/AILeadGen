"""Phase 2/3 additive storage; all customer-derived records retain workspace ownership."""
INTENT_RADAR_23_SQL = """
ALTER TABLE intent_monitors ADD COLUMN schedule_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE intent_monitors ADD COLUMN next_run_at TEXT;
CREATE INDEX intent_monitors_due ON intent_monitors(status,next_run_at);
CREATE TABLE intent_source_runs (
 organization_id TEXT NOT NULL, discovery_id TEXT NOT NULL, provider TEXT NOT NULL,
 status TEXT NOT NULL, result_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,discovery_id,provider),
 FOREIGN KEY(organization_id,discovery_id) REFERENCES intent_discoveries(organization_id,id)
);
CREATE TABLE intent_source_configs (
 organization_id TEXT NOT NULL REFERENCES organizations(id), id TEXT NOT NULL, configuration_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(organization_id,id)
);
CREATE TABLE intent_provider_limits (
 id TEXT PRIMARY KEY, next_request_at TEXT NOT NULL, state_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE intent_source_cache (
 organization_id TEXT NOT NULL REFERENCES organizations(id), fingerprint TEXT NOT NULL,
 result_json TEXT NOT NULL, expires_at TEXT NOT NULL, PRIMARY KEY(organization_id,fingerprint)
);
CREATE TABLE intent_analyses (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, signal_id TEXT NOT NULL, input_hash TEXT NOT NULL,
 icp_id TEXT, icp_revision INTEGER, analysis_json TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(organization_id,signal_id,input_hash),
 FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id),
 FOREIGN KEY(organization_id,icp_id) REFERENCES ideal_customer_profiles(organization_id,id)
);
CREATE TABLE intent_feedback (
 organization_id TEXT NOT NULL, signal_id TEXT NOT NULL, actor TEXT NOT NULL REFERENCES users(id),
 label TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
 updated_at TEXT NOT NULL, PRIMARY KEY(organization_id,signal_id,actor),
 FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id)
);
CREATE TABLE intent_analysis_usage (
 organization_id TEXT NOT NULL REFERENCES organizations(id), day TEXT NOT NULL,
 reserved_tokens INTEGER NOT NULL DEFAULT 0, calls INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(organization_id,day)
);
"""
