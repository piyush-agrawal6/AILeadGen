CREATE TABLE radar_actions (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 request_id TEXT NOT NULL, created_by TEXT NOT NULL REFERENCES users(id), opportunity_id TEXT NOT NULL,
 kind TEXT NOT NULL, payload_json TEXT NOT NULL, digest TEXT NOT NULL, opportunity_revision INTEGER NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('NEEDS_REVIEW','SUCCEEDED','CANCELED')),
 approved_by TEXT REFERENCES users(id), approved_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id), UNIQUE(organization_id,id)
);
CREATE INDEX radar_actions_queue ON radar_actions(organization_id,status,created_at);
CREATE TABLE radar_followups (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, owner_id TEXT NOT NULL REFERENCES users(id),
 due_at TEXT NOT NULL, priority TEXT NOT NULL CHECK(priority IN ('low','normal','high')),
 status TEXT NOT NULL CHECK(status IN ('OPEN','DONE')), outcome TEXT, completed_by TEXT REFERENCES users(id), completed_at TEXT,
 FOREIGN KEY(organization_id,id) REFERENCES radar_actions(organization_id,id)
);
CREATE INDEX radar_followups_due ON radar_followups(organization_id,owner_id,status,due_at);

-- Clean profile identity
UPDATE intent_schema_metadata SET structure_manifest_sha256='a977f44ed503b12e25649c131aee3a7b129833ae0f3d5bc636d55a8315ae5305' WHERE singleton=1;
