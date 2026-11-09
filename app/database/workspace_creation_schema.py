"""Durable, account-scoped idempotency for deliberate workspace creation."""
WORKSPACE_CREATION_SQL = """
CREATE TABLE workspace_creation_requests (
 user_id TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 requested_name TEXT NOT NULL,
 created_at TEXT NOT NULL,
 PRIMARY KEY(user_id,request_id)
);
"""
