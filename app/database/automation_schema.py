"""Additive automation records; prospects remain the canonical lead identity."""
AUTOMATION_SQL = """
CREATE TABLE master_lead_state (
 prospect_id TEXT PRIMARY KEY REFERENCES prospects(id),
 contact_state TEXT NOT NULL DEFAULT 'NOT_CONTACTED',
 sales_state TEXT NOT NULL DEFAULT 'QUALIFIED',
 qualified_at TEXT NOT NULL, updated_at TEXT NOT NULL, manual_reason TEXT
);
CREATE TABLE scan_markets (
 id TEXT PRIMARY KEY,country TEXT NOT NULL,region TEXT,city TEXT NOT NULL,
 vertical TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,
 last_scanned_at TEXT,last_qualified_count INTEGER NOT NULL DEFAULT 0,
 total_scans INTEGER NOT NULL DEFAULT 0,total_candidates INTEGER NOT NULL DEFAULT 0,
 total_qualified INTEGER NOT NULL DEFAULT 0,priority INTEGER NOT NULL DEFAULT 0,
 cooldown_days INTEGER NOT NULL DEFAULT 7,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 UNIQUE(country,city,vertical)
);
CREATE TABLE automation_runs (
 day TEXT PRIMARY KEY,status TEXT NOT NULL,started_at TEXT NOT NULL,completed_at TEXT,
 target INTEGER NOT NULL,new_qualified INTEGER NOT NULL DEFAULT 0,
 updated_leads INTEGER NOT NULL DEFAULT 0,raw_candidates INTEGER NOT NULL DEFAULT 0,
 shortfall INTEGER NOT NULL DEFAULT 0,error_code TEXT
);
CREATE TABLE automation_scans (
 day TEXT NOT NULL REFERENCES automation_runs(day),market_id TEXT NOT NULL REFERENCES scan_markets(id),
 run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),status TEXT NOT NULL,
 PRIMARY KEY(day,market_id),UNIQUE(run_id)
);
CREATE TABLE automation_controls (
 id INTEGER PRIMARY KEY,scan_paused INTEGER NOT NULL DEFAULT 1,
 email_paused INTEGER NOT NULL DEFAULT 1,pause_reason TEXT,
 next_send_at TEXT,updated_at TEXT NOT NULL
);
INSERT INTO automation_controls(id,updated_at) VALUES(1,'1970-01-01T00:00:00+00:00');
CREATE TABLE automation_email_queue (
 prospect_id TEXT PRIMARY KEY REFERENCES prospects(id),
 recipient TEXT NOT NULL,priority INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'QUEUED',
 queued_at TEXT NOT NULL,attempted_at TEXT,message_id TEXT,error_code TEXT,
 idempotency_key TEXT NOT NULL UNIQUE
);
CREATE INDEX idx_automation_queue ON automation_email_queue(status,priority,queued_at);
"""
