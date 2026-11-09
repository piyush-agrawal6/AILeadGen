INTEGRATION_SQL="""
CREATE TABLE organization_integrations (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 provider TEXT NOT NULL CHECK(provider IN ('GOOGLE_SHEETS')),
 status TEXT NOT NULL DEFAULT 'NOT_CONNECTED' CHECK(status IN ('NOT_CONNECTED','CONNECTED','REAUTH_REQUIRED','DISCONNECTED')),
 revision INTEGER NOT NULL DEFAULT 1,
 credentials_ciphertext TEXT,
 scopes_json TEXT NOT NULL DEFAULT '[]',
 connected_by TEXT REFERENCES users(id),
 connected_at TEXT,
 last_success_at TEXT,
 last_error_code TEXT,
 refresh_lease_id TEXT,
 refresh_lease_until TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(organization_id,provider),
 UNIQUE(id,organization_id)
);
CREATE INDEX idx_integrations_workspace ON organization_integrations(organization_id,status);
CREATE TABLE integration_oauth_states (
 state_hash TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL,
 connection_id TEXT NOT NULL,
 actor TEXT NOT NULL REFERENCES users(id),
 connection_revision INTEGER NOT NULL,
 verifier_ciphertext TEXT,
 status TEXT NOT NULL CHECK(status IN ('PENDING','CONSUMED','CANCELLED','EXPIRED')),
 expires_at TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(connection_id,organization_id) REFERENCES organization_integrations(id,organization_id)
);
CREATE INDEX idx_integration_states_owner ON integration_oauth_states(organization_id,created_at);
"""
