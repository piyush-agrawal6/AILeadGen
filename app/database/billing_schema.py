"""46: additive mode-separated billing and durable, bounded provider recovery."""
BILLING_SQL = """
CREATE TABLE billing_subscriptions (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id), mode TEXT NOT NULL CHECK(mode IN ('test','live')),
 request_id TEXT NOT NULL, plan_code TEXT NOT NULL, plan_json TEXT NOT NULL,
 provider_id TEXT, customer_id TEXT, status TEXT NOT NULL DEFAULT 'CREATING',
 current_start BIGINT, current_end BIGINT, paid_start BIGINT, paid_end BIGINT,
 cancel_at_cycle_end INTEGER NOT NULL DEFAULT 0, last_reconciled_at TEXT,
 next_reconcile_at TEXT NOT NULL, failures INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,id), UNIQUE(organization_id,mode,request_id), UNIQUE(mode,provider_id)
);
CREATE INDEX billing_reconcile_due ON billing_subscriptions(mode,next_reconcile_at,id);
CREATE TABLE billing_plan_mappings (
 mode TEXT NOT NULL CHECK(mode IN ('test','live')), code TEXT NOT NULL,
 provider_plan_id TEXT NOT NULL, catalog_hash TEXT NOT NULL, verified_at TEXT NOT NULL,
 PRIMARY KEY(mode,code), UNIQUE(mode,provider_plan_id)
);
CREATE TABLE billing_workspace_slots (
 organization_id TEXT NOT NULL REFERENCES organizations(id), mode TEXT NOT NULL,
 subscription_id TEXT NOT NULL, PRIMARY KEY(organization_id,mode),
 FOREIGN KEY(organization_id,subscription_id) REFERENCES billing_subscriptions(organization_id,id)
);
CREATE TABLE billing_customers (
 organization_id TEXT NOT NULL REFERENCES organizations(id), mode TEXT NOT NULL,
 provider_id TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,mode,provider_id), UNIQUE(mode,provider_id)
);
CREATE TABLE billing_payments (
 mode TEXT NOT NULL, provider_id TEXT NOT NULL, organization_id TEXT NOT NULL,
 subscription_id TEXT NOT NULL, invoice_id TEXT NOT NULL,
 amount BIGINT NOT NULL, currency TEXT NOT NULL, status TEXT NOT NULL,
 period_start BIGINT NOT NULL, period_end BIGINT NOT NULL, recorded_at TEXT NOT NULL,
 PRIMARY KEY(mode,provider_id),
 FOREIGN KEY(organization_id,subscription_id) REFERENCES billing_subscriptions(organization_id,id)
);
CREATE INDEX billing_payments_page ON billing_payments(organization_id,recorded_at,provider_id);
CREATE TABLE billing_webhook_events (
 mode TEXT NOT NULL, event_id TEXT NOT NULL, body_hash TEXT NOT NULL,
 event_type TEXT NOT NULL, provider_subscription_id TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0,
 lease_token TEXT, lease_until TEXT, next_attempt_at TEXT NOT NULL,
 received_at TEXT NOT NULL, processed_at TEXT, error_code TEXT,
 PRIMARY KEY(mode,event_id)
);
CREATE INDEX billing_webhooks_due ON billing_webhook_events(mode,status,next_attempt_at);
CREATE TABLE billing_usage (
 organization_id TEXT NOT NULL, subscription_id TEXT NOT NULL,
 period_start BIGINT NOT NULL, period_end BIGINT NOT NULL,
 dimension TEXT NOT NULL, used BIGINT NOT NULL DEFAULT 0 CHECK(used>=0),
 PRIMARY KEY(organization_id,subscription_id,period_start,dimension),
 FOREIGN KEY(organization_id,subscription_id) REFERENCES billing_subscriptions(organization_id,id)
);
CREATE TABLE billing_reservations (
 organization_id TEXT NOT NULL, dimension TEXT NOT NULL, request_id TEXT NOT NULL,
 subscription_id TEXT NOT NULL, period_start BIGINT NOT NULL,
 amount BIGINT NOT NULL CHECK(amount>0), created_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,dimension,request_id),
 FOREIGN KEY(organization_id,subscription_id) REFERENCES billing_subscriptions(organization_id,id)
);
CREATE TABLE billing_action_windows (
 organization_id TEXT NOT NULL REFERENCES organizations(id), action TEXT NOT NULL,
 window_start BIGINT NOT NULL, requests INTEGER NOT NULL,
 PRIMARY KEY(organization_id,action,window_start)
);
"""
