-- Additive source integration tables (budgets, cache, requests, GitHub OAuth/webhooks, Bluesky Jetstream).

CREATE TABLE intent_source_registry (
 id TEXT PRIMARY KEY, family TEXT NOT NULL, name TEXT NOT NULL, endpoint TEXT NOT NULL,
 configuration_json TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE intent_provider_budgets (
 provider TEXT NOT NULL, scope TEXT NOT NULL, bucket TEXT NOT NULL, period TEXT NOT NULL,
 used INTEGER NOT NULL DEFAULT 0 CHECK(used>=0), capacity INTEGER NOT NULL CHECK(capacity>=0),
 reset_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(provider,scope,bucket,period)
);
CREATE TABLE intent_provider_cache (
 provider TEXT NOT NULL, scope TEXT NOT NULL, fingerprint TEXT NOT NULL,
 result_json TEXT NOT NULL DEFAULT '{}', ciphertext TEXT,
 etag TEXT, last_modified TEXT, expires_at TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('FETCHING','READY','FAILED')),
 lease_owner TEXT, lease_until TEXT, updated_at TEXT NOT NULL,
 PRIMARY KEY(provider,scope,fingerprint)
);
CREATE INDEX idx_provider_cache_expiry ON intent_provider_cache(expires_at,provider,scope);
CREATE TABLE intent_provider_requests (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 actor TEXT NOT NULL REFERENCES users(id), provider TEXT NOT NULL,
 discovery_id TEXT REFERENCES intent_discoveries(id), monitor_id TEXT REFERENCES intent_monitors(id),
 fingerprint TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('QUEUED','RUNNING','COMPLETE','FAILED','CANCELLED')),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0), retry_at TEXT,
 lease_owner TEXT, lease_until TEXT, detail_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,provider,discovery_id,fingerprint)
);
CREATE INDEX idx_provider_requests_due ON intent_provider_requests(state,retry_at,organization_id,created_at);
CREATE TABLE intent_github_connections (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 owner_user_id TEXT NOT NULL REFERENCES users(id), installation_id TEXT,
 github_user_id TEXT, account_login TEXT, account_type TEXT,
 status TEXT NOT NULL CHECK(status IN ('NOT_CONNECTED','PENDING','CONNECTED','REAUTH_REQUIRED','DISCONNECTED','REVOKED')),
 permissions_json TEXT NOT NULL DEFAULT '{}', repositories_json TEXT NOT NULL DEFAULT '[]',
 credentials_ciphertext TEXT, revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1),
 last_verified_at TEXT, last_error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id), UNIQUE(id,organization_id)
);
CREATE INDEX idx_github_installations ON intent_github_connections(installation_id,status);
CREATE TABLE intent_github_oauth_states (
 state_hash TEXT PRIMARY KEY, organization_id TEXT NOT NULL, connection_id TEXT NOT NULL,
 actor TEXT NOT NULL REFERENCES users(id), connection_revision INTEGER NOT NULL,
 verifier_ciphertext TEXT NOT NULL, lease_owner TEXT, lease_until TEXT,
 status TEXT NOT NULL CHECK(status IN ('PENDING','PROCESSING','CONSUMED','CANCELLED','EXPIRED')),
 expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(connection_id,organization_id) REFERENCES intent_github_connections(id,organization_id)
);
CREATE INDEX idx_github_oauth_owner ON intent_github_oauth_states(organization_id,status,expires_at);
CREATE TABLE intent_provider_events (
 id TEXT PRIMARY KEY, provider TEXT NOT NULL, delivery_id TEXT NOT NULL,
 organization_id TEXT REFERENCES organizations(id), connection_id TEXT,
 installation_id TEXT, event_type TEXT NOT NULL, payload_hash TEXT NOT NULL,
 payload_ciphertext TEXT, status TEXT NOT NULL CHECK(status IN ('QUEUED','RUNNING','COMPLETE','IGNORED','FAILED')),
 attempts INTEGER NOT NULL DEFAULT 0, lease_owner TEXT, lease_until TEXT,
 error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(provider,delivery_id), UNIQUE(provider,payload_hash)
);
CREATE INDEX idx_provider_events_due ON intent_provider_events(status,created_at);
CREATE TABLE intent_stream_checkpoints (
 stream_id TEXT PRIMARY KEY, sequence BIGINT NOT NULL DEFAULT 0 CHECK(sequence>=0),
 filter_hash TEXT NOT NULL, lease_owner TEXT, lease_until TEXT,
 state TEXT NOT NULL, detail_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL
);
CREATE TABLE intent_stream_matches (
 organization_id TEXT NOT NULL REFERENCES organizations(id), monitor_id TEXT NOT NULL,
 native_id TEXT NOT NULL, sequence BIGINT NOT NULL CHECK(sequence>=0), operation TEXT NOT NULL,
 record_json TEXT NOT NULL DEFAULT '{}', expires_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,monitor_id,native_id),
 FOREIGN KEY(organization_id,monitor_id) REFERENCES intent_monitors(organization_id,id)
);
CREATE INDEX idx_stream_match_expiry ON intent_stream_matches(expires_at,organization_id,monitor_id);

UPDATE intent_schema_metadata SET structure_manifest_sha256='eafc7d9c9e3cd8400e03a56c050d37c9a38c228ae9a3075e6e1215f0666a1020' WHERE singleton=1;
