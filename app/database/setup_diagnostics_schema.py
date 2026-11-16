"""Additive, workspace-owned setup attempt history; no prompts or raw output."""
SETUP_DIAGNOSTICS_SQL="""
CREATE UNIQUE INDEX idx_profile_job_scope ON organization_profile_jobs(organization_id,id);
CREATE TABLE organization_profile_job_events (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL,
 job_id TEXT NOT NULL,
 attempt INTEGER NOT NULL CHECK(attempt BETWEEN 1 AND 3),
 stage TEXT NOT NULL,
 outcome TEXT NOT NULL CHECK(outcome IN ('STARTED','PROGRESS','READY','FAILED','CANCELLED','SUPERSEDED')),
 error_code TEXT,
 provider TEXT,
 model TEXT,
 duration_ms INTEGER NOT NULL CHECK(duration_ms>=0),
 created_at TEXT NOT NULL,
 FOREIGN KEY(organization_id,job_id) REFERENCES organization_profile_jobs(organization_id,id)
);
CREATE INDEX idx_profile_job_events_owned ON organization_profile_job_events(organization_id,job_id,attempt,created_at);
"""
