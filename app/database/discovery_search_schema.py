"""29: workspace-owned reusable discovery configurations, without starting jobs."""
DISCOVERY_SEARCH_SQL="""
CREATE TABLE discovery_searches (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 name TEXT NOT NULL,
 configuration_json TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1,
 request_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL,
 created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 archived_at TEXT,
 UNIQUE(organization_id,request_id)
);
CREATE INDEX idx_discovery_search_workspace ON discovery_searches(organization_id,archived_at,updated_at);
"""
