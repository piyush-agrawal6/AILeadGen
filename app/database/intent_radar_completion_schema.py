"""Additive Phase 2/3 completion storage. No historical rows are deleted."""
INTENT_RADAR_COMPLETION_SQL = """
CREATE TABLE ai_request_usage (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), actor TEXT NOT NULL,
 operation TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL,
 input_tokens INTEGER, output_tokens INTEGER, cached_tokens INTEGER, thinking_tokens INTEGER,
 usage_basis TEXT NOT NULL, estimated_cost_usd TEXT, pricing_reference TEXT,
 fallback INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX ai_request_usage_workspace_time ON ai_request_usage(organization_id,created_at);
CREATE TABLE intent_rankings (
 organization_id TEXT NOT NULL, signal_id TEXT NOT NULL, score INTEGER NOT NULL,
 input_hash TEXT NOT NULL, icp_id TEXT, icp_revision INTEGER, explanation_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(organization_id,signal_id),
 FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id),
 FOREIGN KEY(organization_id,icp_id) REFERENCES ideal_customer_profiles(organization_id,id)
);
CREATE TABLE intent_collection_cursors (
 organization_id TEXT NOT NULL, monitor_id TEXT NOT NULL, provider TEXT NOT NULL,
 configuration_hash TEXT NOT NULL, cursor_json TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,monitor_id,provider),
 FOREIGN KEY(organization_id,monitor_id) REFERENCES intent_monitors(organization_id,id)
);
CREATE TABLE intent_source_usage (
 organization_id TEXT NOT NULL REFERENCES organizations(id), provider TEXT NOT NULL, day TEXT NOT NULL,
 reserved_requests INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(organization_id,provider,day)
);
CREATE TABLE intent_worker_health (
 worker_id TEXT PRIMARY KEY, last_tick_at TEXT NOT NULL, state TEXT NOT NULL, detail_json TEXT NOT NULL
);
CREATE TABLE intent_retention_cursors (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 signal_after TEXT NOT NULL DEFAULT '', cache_after TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL
);
CREATE INDEX intent_signal_rank_page ON intent_signals(organization_id,available,score,id);
CREATE INDEX intent_saved_page ON intent_saved_signals(organization_id,collection,saved_at,signal_id);
CREATE INDEX intent_source_run_health ON intent_source_runs(organization_id,provider,updated_at);
CREATE INDEX intent_due_monitor_page ON intent_monitors(status,next_run_at);
"""
