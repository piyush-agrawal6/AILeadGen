"""37: encrypted workspace endpoints and a durable, bounded delivery outbox."""
WEBHOOK_SQL = """
CREATE TABLE webhook_endpoints (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 name TEXT NOT NULL, url TEXT NOT NULL, topics_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'ACTIVE', revision INTEGER NOT NULL DEFAULT 1,
 signing_secret_ciphertext TEXT NOT NULL, created_by TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL, creation_fingerprint TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_error_code TEXT,
 dispatch_token TEXT, dispatch_until TEXT, last_dispatch_at TEXT, UNIQUE(id,organization_id),UNIQUE(organization_id,request_id)
);
CREATE INDEX idx_webhooks_owner ON webhook_endpoints(organization_id,status);
CREATE TABLE webhook_deliveries (
 id TEXT PRIMARY KEY, endpoint_id TEXT NOT NULL, organization_id TEXT NOT NULL,
 event_id TEXT NOT NULL, topic TEXT NOT NULL, body_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'QUEUED', attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt_at TEXT NOT NULL, lease_owner TEXT, lease_until TEXT,
 last_http_status INTEGER, last_error_code TEXT, created_at TEXT NOT NULL, delivered_at TEXT,
 UNIQUE(endpoint_id,event_id), UNIQUE(id,organization_id),
 FOREIGN KEY(endpoint_id,organization_id) REFERENCES webhook_endpoints(id,organization_id)
);
CREATE INDEX idx_webhook_delivery_due ON webhook_deliveries(status,next_attempt_at,endpoint_id);
CREATE INDEX idx_webhook_delivery_workspace ON webhook_deliveries(organization_id,status);
CREATE TABLE webhook_delivery_attempts (
 delivery_id TEXT NOT NULL, organization_id TEXT NOT NULL, attempt INTEGER NOT NULL,
 started_at TEXT NOT NULL, finished_at TEXT, http_status INTEGER, error_code TEXT,
 PRIMARY KEY(delivery_id,attempt),
 FOREIGN KEY(delivery_id,organization_id) REFERENCES webhook_deliveries(id,organization_id)
);
"""
