"""Additive customer mailbox authority; existing Sheets/internal mail remain intact."""
CUSTOMER_GMAIL_SQL = """
CREATE TABLE customer_gmail_connections (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 owner_user_id TEXT NOT NULL REFERENCES users(id),
 provider TEXT NOT NULL CHECK(provider='GMAIL'),
 status TEXT NOT NULL DEFAULT 'NOT_CONNECTED' CHECK(status IN ('NOT_CONNECTED','CONNECTED','REAUTH_REQUIRED','DISCONNECTED')),
 revision INTEGER NOT NULL DEFAULT 1,
 credentials_ciphertext TEXT,
 scopes_json TEXT NOT NULL DEFAULT '[]',
 connected_by TEXT REFERENCES users(id), connected_at TEXT,
 last_success_at TEXT, last_error_code TEXT,
 refresh_lease_id TEXT, refresh_lease_until TEXT,
 account_id TEXT UNIQUE REFERENCES email_accounts(id),
 email_address TEXT, google_subject TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,provider), UNIQUE(id,organization_id)
);
CREATE INDEX idx_customer_gmail_owner ON customer_gmail_connections(organization_id,owner_user_id,status);
CREATE TABLE customer_gmail_oauth_states (
 state_hash TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL,
 connection_id TEXT NOT NULL,
 actor TEXT NOT NULL REFERENCES users(id),
 connection_revision INTEGER NOT NULL,
 verifier_ciphertext TEXT,
 status TEXT NOT NULL CHECK(status IN ('PENDING','CONSUMED','CANCELLED','EXPIRED')),
 expires_at TEXT NOT NULL, created_at TEXT NOT NULL, requested_scope TEXT NOT NULL,
 FOREIGN KEY(connection_id,organization_id) REFERENCES customer_gmail_connections(id,organization_id)
);
CREATE INDEX idx_customer_gmail_states ON customer_gmail_oauth_states(organization_id,created_at);
CREATE TABLE customer_mail_policies (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 revision INTEGER NOT NULL DEFAULT 0,
 sending_approved INTEGER NOT NULL DEFAULT 0,
 approved_by TEXT REFERENCES users(id), approved_at TEXT,
 max_hour INTEGER NOT NULL DEFAULT 5 CHECK(max_hour BETWEEN 1 AND 10),
 max_day INTEGER NOT NULL DEFAULT 50 CHECK(max_day BETWEEN 1 AND 100),
 updated_at TEXT NOT NULL,next_send_at TEXT
);
CREATE TABLE customer_gmail_sync (
 connection_id TEXT PRIMARY KEY REFERENCES customer_gmail_connections(id),
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 lease_id TEXT, lease_until TEXT, cursor_json TEXT NOT NULL DEFAULT '{}',
 last_success_at TEXT, next_attempt_at TEXT, attempts INTEGER NOT NULL DEFAULT 0,
 last_error_code TEXT
);
ALTER TABLE scan_campaigns ADD COLUMN email_account_id TEXT REFERENCES email_accounts(id);
ALTER TABLE email_messages ADD COLUMN mailbox_revision INTEGER;
ALTER TABLE email_messages ADD COLUMN provider_delivery_id TEXT;
ALTER TABLE outreach_run_items ADD COLUMN mail_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE outreach_run_items ADD COLUMN next_mail_attempt_at TEXT;
CREATE TABLE customer_mail_suppressions (
 organization_id TEXT NOT NULL REFERENCES organizations(id), address TEXT NOT NULL,
 source TEXT NOT NULL,soft_bounce_count INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL,
 updated_at TEXT NOT NULL,PRIMARY KEY(organization_id,address)
);
CREATE TABLE customer_mail_tracking_preferences (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 track_opens INTEGER NOT NULL DEFAULT 0,track_clicks INTEGER NOT NULL DEFAULT 0,
 track_replies INTEGER NOT NULL DEFAULT 1,track_bounces INTEGER NOT NULL DEFAULT 1
);
"""
