DOMAIN_SQL = """
CREATE TABLE organization_domains (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 domain TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('PENDING','VERIFIED','REVOKED')),
 challenge_hash TEXT NOT NULL,
 challenge_expires_at TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 verified_at TEXT,
 checked_at TEXT,
 attempts INTEGER NOT NULL DEFAULT 0,
 UNIQUE(organization_id,domain)
);
CREATE INDEX idx_workspace_domains ON organization_domains(organization_id,status);
"""
