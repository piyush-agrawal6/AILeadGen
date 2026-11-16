"""49: additive fixed-term PayU purchases and explicitly approved trial accounting.

Recurring PayU and historical Razorpay snapshots and ledgers remain unchanged.
"""
ACCESS_PERIOD_SQL="""
CREATE TABLE customer_workspace_access (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 registered_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL
);
CREATE TABLE launch_trial_claims (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL UNIQUE REFERENCES users(id),
 company_domain TEXT NOT NULL UNIQUE, organization_id TEXT NOT NULL UNIQUE REFERENCES organizations(id),
 policy_version TEXT NOT NULL, claimed_at TEXT NOT NULL
);
CREATE TABLE payu_access_orders (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id), provider TEXT NOT NULL DEFAULT 'payu' CHECK(provider='payu'),
 mode TEXT NOT NULL CHECK(mode IN ('test','live')), txn_id TEXT NOT NULL,
 request_id TEXT NOT NULL, request_fingerprint TEXT NOT NULL,
 plan_code TEXT NOT NULL, interval TEXT NOT NULL CHECK(interval IN ('monthly','yearly')),
 plan_json TEXT NOT NULL, catalog_version TEXT NOT NULL, policy_version TEXT NOT NULL,
 terms_version TEXT NOT NULL, terms_accepted_at TEXT NOT NULL,
 currency TEXT NOT NULL, subtotal_minor BIGINT NOT NULL CHECK(subtotal_minor>0),
 tax_minor BIGINT NOT NULL CHECK(tax_minor>=0), total_minor BIGINT NOT NULL CHECK(total_minor>0),
 tax_json TEXT NOT NULL, expected_json TEXT NOT NULL, billing_encrypted TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('CREATING','PENDING','PAID','FAILED','CANCELLED','EXPIRED','REVIEW','REFUNDED')),
 checkout_url TEXT, provider_payment_id TEXT, verified_json TEXT,
 period_start BIGINT, period_end BIGINT, verified_at TEXT,
 creation_started_at TEXT, expires_at BIGINT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id), UNIQUE(mode,txn_id), UNIQUE(mode,provider_payment_id),
 CHECK(total_minor=subtotal_minor+tax_minor)
);
CREATE INDEX payu_access_order_owner ON payu_access_orders(organization_id,created_at);
CREATE TABLE payu_access_callback_events (
 id TEXT PRIMARY KEY, order_id TEXT NOT NULL REFERENCES payu_access_orders(id),
 body_sha256 TEXT NOT NULL, event_type TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(order_id,body_sha256)
);
CREATE TABLE payu_access_refunds (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 order_id TEXT NOT NULL REFERENCES payu_access_orders(id), requested_by TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL, amount_minor BIGINT NOT NULL CHECK(amount_minor>0), currency TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('REQUESTED','REVIEW','PENDING','SUCCEEDED','REJECTED')),
 provider_refund_id TEXT, verified_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id), UNIQUE(provider_refund_id)
);
CREATE TABLE access_periods (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 source_kind TEXT NOT NULL CHECK(source_kind IN ('TRIAL','PAYMENT')),
 source_id TEXT NOT NULL, plan_code TEXT NOT NULL, plan_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('ACTIVE','EXPIRED','REVOKED','REPLACED')),
 paid_start BIGINT NOT NULL, paid_end BIGINT NOT NULL, verified_at TEXT NOT NULL,
 mode TEXT NOT NULL CHECK(mode IN ('trial','test','live')),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(source_kind,source_id), UNIQUE(organization_id,id), CHECK(paid_end>paid_start)
);
CREATE INDEX access_period_current ON access_periods(organization_id,status,paid_start,paid_end);
CREATE INDEX access_period_expiry ON access_periods(status,paid_end);
CREATE TABLE payu_refund_observations (
 mode TEXT NOT NULL CHECK(mode IN ('test','live')),
 provider_refund_id TEXT NOT NULL, order_id TEXT NOT NULL REFERENCES payu_access_orders(id),
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 provider_payment_id TEXT NOT NULL, amount_minor BIGINT NOT NULL CHECK(amount_minor>0),
 currency TEXT, status TEXT NOT NULL CHECK(status IN ('PENDING','SUCCEEDED','FAILED','REVIEW')),
 verified_json TEXT NOT NULL, first_seen_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(mode,provider_refund_id)
);
CREATE INDEX payu_refund_order ON payu_refund_observations(organization_id,order_id);
CREATE TABLE access_period_usage (
 organization_id TEXT NOT NULL, contract_id TEXT NOT NULL,
 period_start BIGINT NOT NULL, period_end BIGINT NOT NULL,
 dimension TEXT NOT NULL, reserved BIGINT NOT NULL DEFAULT 0 CHECK(reserved>=0),
 used BIGINT NOT NULL DEFAULT 0 CHECK(used>=0),
 PRIMARY KEY(organization_id,contract_id,period_start,dimension),
 FOREIGN KEY(organization_id,contract_id) REFERENCES access_periods(organization_id,id)
);
CREATE TABLE access_period_reservations (
 organization_id TEXT NOT NULL, contract_id TEXT NOT NULL, period_start BIGINT NOT NULL,
 operation_id TEXT NOT NULL, dimension TEXT NOT NULL, amount BIGINT NOT NULL CHECK(amount>0),
 state TEXT NOT NULL CHECK(state IN ('RESERVED','COMMITTED','RELEASED')),
 actual_amount BIGINT CHECK(actual_amount>=0 AND actual_amount<=amount),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,operation_id,dimension),
 FOREIGN KEY(organization_id,contract_id) REFERENCES access_periods(organization_id,id)
);
"""
