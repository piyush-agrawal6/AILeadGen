CREATE TABLE radar_sheet_exports (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 connection_id TEXT NOT NULL, connection_revision INTEGER NOT NULL, created_by TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, selection_json TEXT NOT NULL,
 spreadsheet_id TEXT NOT NULL, sheet_title TEXT NOT NULL, target_range TEXT NOT NULL,
 row_count INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'DRAFT', attempts INTEGER NOT NULL DEFAULT 0,
 lease_owner TEXT, lease_until TEXT, last_error_code TEXT, created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT,
 UNIQUE(organization_id,request_id),
 FOREIGN KEY(connection_id,organization_id) REFERENCES organization_integrations(id,organization_id)
);
CREATE INDEX idx_radar_sheet_history ON radar_sheet_exports(organization_id,connection_id,created_at);
-- Clean profile identity
UPDATE intent_schema_metadata SET structure_manifest_sha256='be10ae5721bbc798836c41f2de61bb79d0156b8d7be3d9f31953c549154948d1' WHERE singleton=1;
