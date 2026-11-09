"""Additive manual runs and owner-created schedules; no existing rows changed."""
WORKFLOW_SQL='''
CREATE TABLE workflow_runs (
 id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'DRAFT',
 configuration_json TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL,
 started_at TEXT,completed_at TEXT,scan_run_id INTEGER REFERENCES pipeline_runs(id),
 requested INTEGER NOT NULL,result_count INTEGER NOT NULL DEFAULT 0,
 error TEXT,next_attempt_at TEXT,schedule_id TEXT,request_key TEXT NOT NULL UNIQUE
);
CREATE INDEX idx_workflow_runs_active ON workflow_runs(status,kind);
CREATE TABLE outreach_run_items (
 id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES workflow_runs(id),prospect_id TEXT NOT NULL REFERENCES prospects(id),
 business_id INTEGER NOT NULL REFERENCES businesses(id),status TEXT NOT NULL DEFAULT 'QUEUED',
 payload_json TEXT,preview_json TEXT,report_id TEXT REFERENCES client_reports(id),
 message_id TEXT REFERENCES email_messages(id),idempotency_key TEXT NOT NULL UNIQUE,
 error TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 UNIQUE(run_id,prospect_id)
);
CREATE INDEX idx_outreach_items_run ON outreach_run_items(run_id,status);
CREATE TABLE automation_schedules (
 id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,
 configuration_json TEXT NOT NULL,timezone TEXT NOT NULL,frequency TEXT NOT NULL,
 cron_expression TEXT,start_at TEXT NOT NULL,next_run_at TEXT,last_run_at TEXT,
 created_by TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,deleted_at TEXT
);
CREATE INDEX idx_schedules_due ON automation_schedules(enabled,next_run_at);
CREATE TABLE automation_schedule_runs (
 id TEXT PRIMARY KEY,schedule_id TEXT NOT NULL REFERENCES automation_schedules(id),
 workflow_run_id TEXT REFERENCES workflow_runs(id),due_at TEXT NOT NULL,status TEXT NOT NULL,
 started_at TEXT NOT NULL,completed_at TEXT,error TEXT,
 UNIQUE(schedule_id,due_at)
);
ALTER TABLE email_messages ADD COLUMN rendered_html TEXT;
ALTER TABLE email_messages ADD COLUMN rendered_text TEXT;
'''
