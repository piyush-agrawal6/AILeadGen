"""Hashed invitation capabilities; no stored raw tokens or email dispatch."""
INVITATION_SQL = """
CREATE TABLE workspace_invitations (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 email TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('ADMIN','MEMBER','VIEWER')),
 token_hash TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL CHECK(status IN ('PENDING','ACCEPTED','REJECTED','REVOKED','EXPIRED')),
 invited_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL,
 responded_at TEXT
);
CREATE UNIQUE INDEX idx_workspace_invitation_pending ON workspace_invitations(organization_id,email) WHERE status='PENDING';
CREATE INDEX idx_workspace_invitation_list ON workspace_invitations(organization_id,created_at);
CREATE TABLE workspace_notifications (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 user_id TEXT NOT NULL REFERENCES users(id),
 kind TEXT NOT NULL,
 entity_id TEXT NOT NULL,
 created_at TEXT NOT NULL,
 read_at TEXT
);
CREATE INDEX idx_workspace_notification_user ON workspace_notifications(organization_id,user_id,created_at);
"""
