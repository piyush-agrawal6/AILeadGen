"""Source metadata and processing ledgers, not a second permanent lead store."""
ACQUISITION_SQL='''
ALTER TABLE scan_campaigns ADD COLUMN source_type TEXT NOT NULL DEFAULT 'OVERTURE';
ALTER TABLE scan_campaigns ADD COLUMN source_metadata TEXT NOT NULL DEFAULT '{}';
ALTER TABLE scan_campaigns ADD COLUMN original_prompt TEXT;
CREATE INDEX idx_campaign_source_time ON scan_campaigns(source_type,created_at);
CREATE TABLE acquisition_jobs (
 id TEXT PRIMARY KEY,campaign_id TEXT UNIQUE REFERENCES scan_campaigns(id) ON DELETE CASCADE,
 source_type TEXT NOT NULL,status TEXT NOT NULL,owner TEXT NOT NULL,request_key TEXT UNIQUE NOT NULL,
 configuration_json TEXT NOT NULL DEFAULT '{}',origin_json TEXT NOT NULL DEFAULT '{}',mapping_json TEXT,
 upload_key TEXT,manifest_json TEXT NOT NULL DEFAULT '{}',cursor INTEGER NOT NULL DEFAULT 0,
 counts_json TEXT NOT NULL DEFAULT '{}',error_code TEXT,error_message TEXT,execution_name TEXT,lease_owner TEXT,lease_until TEXT,
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL,finished_at TEXT
);
CREATE INDEX idx_acquisition_status ON acquisition_jobs(status,created_at);
CREATE TABLE acquisition_events (
 id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES acquisition_jobs(id) ON DELETE CASCADE,
 stage TEXT NOT NULL,message TEXT NOT NULL,counts_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL
);
CREATE INDEX idx_acquisition_events ON acquisition_events(job_id,created_at);
CREATE TABLE acquisition_batches (
 job_id TEXT NOT NULL REFERENCES acquisition_jobs(id) ON DELETE CASCADE,batch_key TEXT NOT NULL,
 run_id INTEGER NOT NULL UNIQUE REFERENCES pipeline_runs(id) ON DELETE CASCADE,
 PRIMARY KEY(job_id,batch_key)
);
CREATE TABLE acquisition_requests (
 job_id TEXT NOT NULL REFERENCES acquisition_jobs(id) ON DELETE CASCADE,request_key TEXT NOT NULL,
 kind TEXT NOT NULL,status TEXT NOT NULL,response_json TEXT,credits REAL,created_at TEXT NOT NULL,
 PRIMARY KEY(job_id,request_key)
);
CREATE TABLE acquisition_issues (
 id TEXT PRIMARY KEY,job_id TEXT NOT NULL REFERENCES acquisition_jobs(id) ON DELETE CASCADE,
 row_number INTEGER,reason TEXT NOT NULL,values_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL
);
CREATE INDEX idx_acquisition_issues ON acquisition_issues(job_id,row_number);
CREATE TABLE lead_source_evidence (
 id TEXT PRIMARY KEY,prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
 business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 campaign_id TEXT NOT NULL REFERENCES scan_campaigns(id) ON DELETE CASCADE,
 source_type TEXT NOT NULL,source_url TEXT,field_sources_json TEXT NOT NULL,was_existing INTEGER NOT NULL,
 observed_at TEXT NOT NULL,UNIQUE(business_id,source_type)
);
CREATE INDEX idx_lead_source_prospect ON lead_source_evidence(prospect_id,source_type);
CREATE TABLE acquisition_ai_cache (
 fingerprint TEXT PRIMARY KEY,actor TEXT NOT NULL,task TEXT NOT NULL,result_json TEXT NOT NULL,
 expires_at TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE TABLE acquisition_preferences (id INTEGER PRIMARY KEY,configuration_json TEXT NOT NULL,updated_by TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE acquisition_provider_health (
 provider TEXT PRIMARY KEY,status TEXT NOT NULL,checked_at TEXT NOT NULL,error_code TEXT
);
CREATE TABLE acquisition_oauth_states (
 state_hash TEXT PRIMARY KEY,actor TEXT NOT NULL,verifier_ciphertext TEXT NOT NULL,expires_at TEXT NOT NULL
);
CREATE TABLE acquisition_google_connections (
 actor TEXT PRIMARY KEY,tokens_ciphertext TEXT NOT NULL,scopes TEXT NOT NULL,connected_at TEXT NOT NULL
);
'''

def ready(c):return (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=13
