"""31: durable bounded enrichment work over existing companies and people."""
INTELLIGENCE_JOB_SQL="""
CREATE TABLE intelligence_jobs (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 kind TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'QUEUED',
 request_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL,
 configuration_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 completed_at TEXT,
 lease_owner TEXT,
 lease_until TEXT,
 attempts INTEGER NOT NULL DEFAULT 0,
 dispatch_attempts INTEGER NOT NULL DEFAULT 0,
 error_code TEXT,
 execution_name TEXT,
 UNIQUE(organization_id,request_id)
);
CREATE INDEX idx_intelligence_jobs_queue ON intelligence_jobs(status,organization_id,created_at);
CREATE TABLE intelligence_job_items (
 id TEXT PRIMARY KEY,
 job_id TEXT NOT NULL REFERENCES intelligence_jobs(id),
 resource_id TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'QUEUED',
 result_json TEXT NOT NULL DEFAULT '{}',
 error_code TEXT,
 updated_at TEXT NOT NULL,
 UNIQUE(job_id,resource_id)
);
"""
