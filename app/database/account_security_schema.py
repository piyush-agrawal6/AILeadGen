"""48: additive customer credentials, verification and notification ledgers.

No existing user, identity, mailbox, admission, payment or research row changes.
"""
ACCOUNT_SECURITY_SQL="""
CREATE TABLE customer_accounts (
 email TEXT PRIMARY KEY, user_id TEXT UNIQUE REFERENCES users(id),
 name TEXT NOT NULL, company_name TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('PENDING','ACTIVE','SUSPENDED','CLOSED')),
 password_hash TEXT, google_subject TEXT UNIQUE,
 verified_at TEXT, terms_version TEXT NOT NULL, terms_accepted_at BIGINT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE account_verifications (
 id TEXT PRIMARY KEY, email TEXT NOT NULL,
 purpose TEXT NOT NULL CHECK(purpose IN ('SIGNUP','SET_PASSWORD')),
 capability_hash TEXT NOT NULL, code_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
 request_id TEXT NOT NULL, request_fingerprint TEXT NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0 AND attempts<=5),
 expires_at BIGINT NOT NULL, consumed_at TEXT, invalidated_at TEXT,
 created_at TEXT NOT NULL, UNIQUE(email,request_id)
);
CREATE INDEX account_verification_expiry ON account_verifications(email,expires_at);
CREATE TABLE customer_sessions (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), token_hash TEXT NOT NULL UNIQUE,
 provider TEXT NOT NULL CHECK(provider IN ('PASSWORD','GOOGLE')),
 created_at TEXT NOT NULL, expires_at BIGINT NOT NULL, revoked_at TEXT
);
CREATE INDEX customer_session_owner ON customer_sessions(user_id,expires_at);
CREATE TABLE account_recovery_requests (
 id TEXT PRIMARY KEY, email TEXT, email_hash TEXT NOT NULL,
 request_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('QUEUED','PROCESSED','EXPIRED')),
 expires_at BIGINT NOT NULL, created_at TEXT NOT NULL, processed_at TEXT,
 UNIQUE(email_hash,request_id)
);
CREATE TABLE account_recovery_tokens (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), token_hash TEXT NOT NULL UNIQUE,
 request_id TEXT NOT NULL, expires_at BIGINT NOT NULL, consumed_at TEXT,
 created_at TEXT NOT NULL, UNIQUE(user_id,request_id)
);
CREATE TABLE account_login_tickets (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), token_hash TEXT NOT NULL UNIQUE,
 expires_at BIGINT NOT NULL, consumed_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE account_link_tickets (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
 session_id TEXT NOT NULL REFERENCES customer_sessions(id), token_hash TEXT NOT NULL UNIQUE,
 expires_at BIGINT NOT NULL, consumed_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE account_rate_limits (
 kind TEXT NOT NULL, bucket_hash TEXT NOT NULL, window_start BIGINT NOT NULL,
 used INTEGER NOT NULL DEFAULT 0 CHECK(used>=0), PRIMARY KEY(kind,bucket_hash,window_start)
);
CREATE TABLE account_security_events (
 id TEXT PRIMARY KEY, account_hash TEXT NOT NULL, action TEXT NOT NULL,
 result TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX account_security_actor ON account_security_events(account_hash,created_at);
CREATE TABLE transactional_notifications (
 id TEXT PRIMARY KEY, account_email TEXT NOT NULL, organization_id TEXT REFERENCES organizations(id),
 purpose TEXT NOT NULL, authority_id TEXT NOT NULL, dedupe_key TEXT NOT NULL UNIQUE,
 payload_encrypted TEXT, status TEXT NOT NULL CHECK(status IN ('QUEUED','SENDING','ACCEPTED','DELIVERED','BOUNCED','COMPLAINED','FAILED','CANCELLED')),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0 AND attempts<=3),
 provider_message_id TEXT UNIQUE, error_code TEXT, execution_name TEXT,
 dispatch_attempts INTEGER NOT NULL DEFAULT 0 CHECK(dispatch_attempts>=0 AND dispatch_attempts<=3),
 lease_token TEXT, lease_until BIGINT, available_at BIGINT NOT NULL,
 expires_at BIGINT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX transactional_delivery_queue ON transactional_notifications(status,available_at);
CREATE TABLE transactional_notification_events (
 provider_event_id TEXT PRIMARY KEY, provider_message_id TEXT NOT NULL, notification_id TEXT REFERENCES transactional_notifications(id),
 event_type TEXT NOT NULL, occurred_at TEXT, received_at TEXT NOT NULL
);
CREATE TABLE transactional_suppressions (
 account_email TEXT PRIMARY KEY, reason TEXT NOT NULL, created_at TEXT NOT NULL
);
"""
