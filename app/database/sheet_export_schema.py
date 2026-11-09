"""38: explicit Sheets write grants and reviewed immutable export jobs."""
SHEET_EXPORT_SQL="""
ALTER TABLE integration_oauth_states ADD COLUMN requested_scope TEXT NOT NULL DEFAULT 'https://www.googleapis.com/auth/spreadsheets.readonly';
CREATE TABLE organization_sheet_exports (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),
 connection_id TEXT NOT NULL,connection_revision INTEGER NOT NULL,
 created_by TEXT NOT NULL REFERENCES users(id),list_id TEXT NOT NULL,
 request_id TEXT NOT NULL,fingerprint TEXT NOT NULL,spreadsheet_id TEXT NOT NULL,
 sheet_title TEXT NOT NULL,target_range TEXT NOT NULL,rows_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'DRAFT',attempts INTEGER NOT NULL DEFAULT 0,
 lease_owner TEXT,lease_until TEXT,last_error_code TEXT,created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL,updated_at TEXT NOT NULL,completed_at TEXT,
 UNIQUE(organization_id,request_id),
 FOREIGN KEY(connection_id,organization_id) REFERENCES organization_integrations(id,organization_id),
 FOREIGN KEY(list_id,organization_id) REFERENCES lead_lists(id,organization_id)
);
CREATE INDEX idx_sheet_exports_owner ON organization_sheet_exports(organization_id,created_at);
"""
