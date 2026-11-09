ICP_SQL = """
CREATE TABLE ideal_customer_profiles (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 name TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL CHECK(status IN ('ACTIVE','INACTIVE','ARCHIVED','DELETED')),
 criteria_json TEXT NOT NULL,
 revision INTEGER NOT NULL,
 request_id TEXT NOT NULL,
 creation_fingerprint TEXT NOT NULL,
 created_by TEXT NOT NULL REFERENCES users(id),
 updated_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id),
 UNIQUE(id,organization_id)
);
CREATE INDEX idx_icp_workspace ON ideal_customer_profiles(organization_id,status,updated_at);
CREATE TABLE icp_versions (
 icp_id TEXT NOT NULL,
 organization_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 snapshot_json TEXT NOT NULL,
 changed_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 PRIMARY KEY(icp_id,revision),
 FOREIGN KEY(icp_id,organization_id) REFERENCES ideal_customer_profiles(id,organization_id)
);
"""
