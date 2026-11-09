"""33: archive/version existing lists and extend existing follow-ups into sales tasks."""
SALES_OPERATIONS_SQL='''
ALTER TABLE lead_lists ADD COLUMN archived_at TEXT;
ALTER TABLE lead_lists ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE lead_lists ADD COLUMN request_id TEXT;
ALTER TABLE lead_lists ADD COLUMN creation_fingerprint TEXT;
CREATE UNIQUE INDEX idx_list_request ON lead_lists(organization_id,request_id);
CREATE INDEX idx_list_archive ON lead_lists(organization_id,archived_at,updated_at);
ALTER TABLE followups ADD COLUMN title TEXT NOT NULL DEFAULT 'Follow-up';
ALTER TABLE followups ADD COLUMN task_type TEXT NOT NULL DEFAULT 'FOLLOW_UP';
ALTER TABLE followups ADD COLUMN priority TEXT NOT NULL DEFAULT 'NORMAL';
ALTER TABLE followups ADD COLUMN contact_id TEXT REFERENCES contact_people(id);
ALTER TABLE followups ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE followups ADD COLUMN request_id TEXT;
ALTER TABLE followups ADD COLUMN creation_fingerprint TEXT;
CREATE UNIQUE INDEX idx_task_request ON followups(organization_id,request_id);
CREATE INDEX idx_tasks_workspace ON followups(organization_id,status,due_at,id);
'''
