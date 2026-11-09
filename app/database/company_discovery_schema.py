COMPANY_DISCOVERY_SQL = """
CREATE TABLE organization_profile_jobs (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL,
 website TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('QUEUED','RUNNING','READY','FAILED','CANCELLED')),
 result_json TEXT,
 error_code TEXT,
 lease_owner TEXT,
 lease_expires_at TEXT,
 execution_name TEXT,
 attempts INTEGER NOT NULL DEFAULT 0,
 confirmed_hash TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id)
);
CREATE INDEX idx_profile_jobs_workspace ON organization_profile_jobs(organization_id,created_at);
"""
