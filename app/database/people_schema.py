"""30: extend existing professional contacts, retaining all import/history rows."""
PEOPLE_SQL="""
ALTER TABLE contact_people ADD COLUMN request_id TEXT;
ALTER TABLE contact_people ADD COLUMN creation_fingerprint TEXT;
CREATE UNIQUE INDEX idx_person_request ON contact_people(organization_id,request_id);
ALTER TABLE contact_people ADD COLUMN department TEXT NOT NULL DEFAULT '';
ALTER TABLE contact_people ADD COLUMN seniority TEXT NOT NULL DEFAULT '';
ALTER TABLE contact_people ADD COLUMN job_function TEXT NOT NULL DEFAULT '';
ALTER TABLE contact_people ADD COLUMN phone TEXT NOT NULL DEFAULT '';
ALTER TABLE contact_people ADD COLUMN discovery_state TEXT NOT NULL DEFAULT 'FOUND';
ALTER TABLE contact_people ADD COLUMN verification_state TEXT NOT NULL DEFAULT 'UNKNOWN';
ALTER TABLE contact_people ADD COLUMN evidence_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE contact_people ADD COLUMN updated_at TEXT;
ALTER TABLE contact_people ADD COLUMN checked_at TEXT;
ALTER TABLE contact_people ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE contact_people ADD COLUMN archived_at TEXT;
CREATE UNIQUE INDEX idx_person_workspace_identity ON contact_people(id,organization_id);
CREATE INDEX idx_people_workspace_company ON contact_people(organization_id,prospect_id,archived_at);
CREATE TABLE contact_person_notes (
 id TEXT PRIMARY KEY,
 contact_id TEXT NOT NULL,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 body TEXT NOT NULL,
 created_by TEXT NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL,
 FOREIGN KEY(contact_id,organization_id) REFERENCES contact_people(id,organization_id)
);
CREATE UNIQUE INDEX idx_list_workspace_identity ON lead_lists(id,organization_id);
CREATE TABLE contact_list_members (
 list_id TEXT NOT NULL,
 contact_id TEXT NOT NULL,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 added_at TEXT NOT NULL,
 PRIMARY KEY(list_id,contact_id),
 FOREIGN KEY(list_id,organization_id) REFERENCES lead_lists(id,organization_id),
 FOREIGN KEY(contact_id,organization_id) REFERENCES contact_people(id,organization_id)
);
"""
