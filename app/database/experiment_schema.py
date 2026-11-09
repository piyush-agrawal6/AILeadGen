"""Additive experiment attribution; no existing prospect or email history rewrite."""
EXPERIMENT_SQL='''
CREATE TABLE experiments (
 id TEXT PRIMARY KEY,name TEXT NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,
 daily_target INTEGER NOT NULL,total_target INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'SETUP',
 configuration_json TEXT NOT NULL DEFAULT '{}',acceptance_json TEXT NOT NULL DEFAULT '{}',
 send_approved INTEGER NOT NULL DEFAULT 0,created_by TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL
);
CREATE TABLE experiment_segments (
 id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL REFERENCES experiments(id),day INTEGER NOT NULL,acquisition_date TEXT NOT NULL,
 country TEXT NOT NULL,city TEXT NOT NULL,vertical TEXT NOT NULL,recipient_timezone TEXT NOT NULL,target INTEGER NOT NULL,
 planned_source_mix TEXT NOT NULL,actual_source_mix TEXT NOT NULL DEFAULT '{}',shortfall_reason TEXT,
 status TEXT NOT NULL DEFAULT 'PLANNED',UNIQUE(experiment_id,day,city)
);
CREATE TABLE experiment_sources (
 id TEXT PRIMARY KEY,segment_id TEXT NOT NULL REFERENCES experiment_segments(id),source_type TEXT NOT NULL,
 target INTEGER NOT NULL,allocation_round INTEGER NOT NULL DEFAULT 0,schedule_id TEXT REFERENCES automation_schedules(id),workflow_id TEXT REFERENCES workflow_runs(id),campaign_id TEXT REFERENCES scan_campaigns(id),
 acquisition_job_id TEXT REFERENCES acquisition_jobs(id),status TEXT NOT NULL DEFAULT 'PLANNED',error TEXT,
 UNIQUE(segment_id,source_type,allocation_round)
);
CREATE TABLE experiment_members (
 id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL REFERENCES experiments(id),segment_id TEXT REFERENCES experiment_segments(id),
 experiment_day INTEGER NOT NULL,prospect_id TEXT NOT NULL REFERENCES prospects(id),business_id INTEGER NOT NULL REFERENCES businesses(id),
 campaign_id TEXT NOT NULL REFERENCES scan_campaigns(id),acquisition_source TEXT NOT NULL,country TEXT NOT NULL,city TEXT NOT NULL,vertical TEXT NOT NULL,
 normalized_domain TEXT,recipient TEXT NOT NULL,recipient_timezone TEXT NOT NULL,
 template_id TEXT NOT NULL,template_version INTEGER NOT NULL,subject_variant INTEGER NOT NULL,primary_pitch TEXT NOT NULL,secondary_pitch TEXT,
 brief_version INTEGER NOT NULL DEFAULT 2,catalog_attached INTEGER NOT NULL DEFAULT 0,catalog_snapshot_json TEXT NOT NULL DEFAULT '{}',
 report_id TEXT REFERENCES client_reports(id),outreach_run_id TEXT REFERENCES workflow_runs(id),item_id TEXT REFERENCES outreach_run_items(id),message_id TEXT REFERENCES email_messages(id),
 state TEXT NOT NULL DEFAULT 'ACQUIRED',copy_started_at TEXT,copy_attempts INTEGER NOT NULL DEFAULT 0,generation_json TEXT NOT NULL DEFAULT '{}',prepared_at TEXT,queued_at TEXT,sent_at TEXT,
 reply_disposition TEXT NOT NULL DEFAULT 'UNKNOWN',conversion_status TEXT NOT NULL DEFAULT 'NO_REPLY',
 controlled_acceptance INTEGER NOT NULL DEFAULT 0,error TEXT,created_at TEXT NOT NULL,
 UNIQUE(experiment_id,prospect_id),UNIQUE(experiment_id,recipient),UNIQUE(experiment_id,normalized_domain)
);
CREATE INDEX idx_experiment_members_stage ON experiment_members(experiment_id,state,experiment_day);
CREATE TABLE experiment_replies (
 inbound_message_id TEXT PRIMARY KEY REFERENCES email_messages(id),member_id TEXT NOT NULL REFERENCES experiment_members(id),
 disposition TEXT NOT NULL,confidence TEXT NOT NULL,method TEXT NOT NULL,manually_corrected INTEGER NOT NULL DEFAULT 0,
 classified_at TEXT NOT NULL,corrected_by TEXT
);
CREATE TABLE experiment_events (
 id TEXT PRIMARY KEY,experiment_id TEXT NOT NULL REFERENCES experiments(id),event_type TEXT NOT NULL,
 metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,dedup_key TEXT UNIQUE
);
CREATE TABLE experiment_catalog (
 id INTEGER PRIMARY KEY,version INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'NOT_CONFIGURED',
 object_key TEXT,filename TEXT,sha256 TEXT,size_bytes INTEGER NOT NULL DEFAULT 0,
 attach_enabled INTEGER NOT NULL DEFAULT 0,mode TEXT NOT NULL DEFAULT 'BRIEF_ONLY',public_url TEXT,
 updated_at TEXT NOT NULL,updated_by TEXT NOT NULL
);
'''
def ready(c):return (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=14
