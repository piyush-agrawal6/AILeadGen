"""34: hash-only scoped API keys and bounded request windows."""
DEVELOPER_SQL='''
CREATE TABLE workspace_api_keys (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 name TEXT NOT NULL,
 token_hash TEXT NOT NULL,
 scopes_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL,
 revoked_at TEXT,
 last_used_at TEXT,
 rotated_from TEXT REFERENCES workspace_api_keys(id),
 UNIQUE(id,organization_id)
);
CREATE INDEX idx_api_keys_workspace ON workspace_api_keys(organization_id,revoked_at,created_at);
CREATE TABLE developer_request_windows (
 owner_key TEXT NOT NULL,
 window_start INTEGER NOT NULL,
 requests INTEGER NOT NULL,
 PRIMARY KEY(owner_key,window_start)
);
CREATE INDEX idx_developer_window_cleanup ON developer_request_windows(window_start);
'''
