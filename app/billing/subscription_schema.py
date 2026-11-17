"""Additive provider-neutral event inbox; no customer or entitlement seeds."""
EVENT_SQL='''
CREATE TABLE subscription_provider_events (
 provider TEXT NOT NULL CHECK(provider IN ('creem','payu')),
 environment TEXT NOT NULL CHECK(environment IN ('production','test')),
 event_id TEXT NOT NULL, event_type TEXT NOT NULL, body_hash TEXT NOT NULL,
 object_id TEXT NOT NULL, payload_encrypted TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','PROCESSING','PROCESSED','IGNORED','REVIEW')),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0),
 lease_token TEXT,lease_until BIGINT,error_code TEXT,
 received_at TEXT NOT NULL,processed_at TEXT,
 PRIMARY KEY(provider,environment,event_id)
);
CREATE INDEX subscription_event_pending ON subscription_provider_events(provider,environment,status,received_at);
'''
