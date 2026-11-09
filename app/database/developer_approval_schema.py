"""35: MCP requests create reviewable proposals, never implicit writes."""
DEVELOPER_APPROVAL_SQL='''
CREATE TABLE developer_action_approvals (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 key_id TEXT NOT NULL REFERENCES workspace_api_keys(id),
 requested_by TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL,
 kind TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING',
 result_json TEXT NOT NULL DEFAULT '{}',
 expires_at TEXT NOT NULL,
 created_at TEXT NOT NULL,
 decided_at TEXT,
 decided_by TEXT REFERENCES users(id),
 UNIQUE(key_id,request_id)
);
CREATE INDEX idx_developer_approvals ON developer_action_approvals(organization_id,status,created_at);
'''
