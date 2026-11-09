"""32: private workspace assistant conversations and explicit action approvals."""
ASSISTANT_SQL='''
CREATE TABLE lead_assistant_conversations (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 title TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(id,organization_id)
);
CREATE INDEX idx_assistant_owner ON lead_assistant_conversations(organization_id,created_by,updated_at);
CREATE TABLE lead_assistant_turns (
 id TEXT PRIMARY KEY,
 conversation_id TEXT NOT NULL,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL,
 prompt TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'QUEUED',
 result_json TEXT NOT NULL DEFAULT '{}',
 job_id TEXT REFERENCES intelligence_jobs(id),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id),
 FOREIGN KEY(conversation_id,organization_id) REFERENCES lead_assistant_conversations(id,organization_id)
);
CREATE TABLE lead_assistant_actions (
 id TEXT PRIMARY KEY,
 turn_id TEXT NOT NULL REFERENCES lead_assistant_turns(id),
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 kind TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING',
 result_json TEXT NOT NULL DEFAULT '{}',
 expires_at TEXT NOT NULL,
 created_at TEXT NOT NULL,
 applied_at TEXT,
 UNIQUE(turn_id,kind,payload_json)
);
CREATE INDEX idx_assistant_turns ON lead_assistant_turns(organization_id,conversation_id,created_at);
'''
