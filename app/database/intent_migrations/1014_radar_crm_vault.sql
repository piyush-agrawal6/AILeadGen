CREATE TABLE radar_crm_connections (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), provider TEXT NOT NULL CHECK(provider='HUBSPOT'),
 status TEXT NOT NULL DEFAULT 'NOT_CONNECTED' CHECK(status IN ('NOT_CONNECTED','CONNECTED','REAUTH_REQUIRED','DISCONNECTED')),
 portal_id TEXT, revision INTEGER NOT NULL DEFAULT 1, credentials_ciphertext TEXT, scopes_json TEXT NOT NULL DEFAULT '[]',
 connected_by TEXT, connected_at TEXT, last_success_at TEXT, last_error_code TEXT, refresh_lease_id TEXT, refresh_lease_until TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(organization_id,provider), UNIQUE(organization_id,id)
);
CREATE TABLE radar_crm_oauth_states (
 state_hash TEXT PRIMARY KEY, organization_id TEXT NOT NULL, connection_id TEXT NOT NULL, actor TEXT NOT NULL REFERENCES users(id),
 connection_revision INTEGER NOT NULL, verifier_ciphertext TEXT, status TEXT NOT NULL CHECK(status IN ('PENDING','CONSUMED','CANCELLED','EXPIRED')),
 expires_at TEXT NOT NULL, created_at TEXT NOT NULL, requested_scope TEXT NOT NULL,
 FOREIGN KEY(organization_id,connection_id) REFERENCES radar_crm_connections(organization_id,id)
);
CREATE INDEX radar_crm_state_window ON radar_crm_oauth_states(organization_id,created_at);

-- Clean profile identity
UPDATE intent_schema_metadata SET structure_manifest_sha256='839cb8e3e8f65803e49ccabcf169b5da571cbd6a1c9f160312de626081708343' WHERE singleton=1;
