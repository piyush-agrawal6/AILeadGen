-- Additive subscriptions and isolated prepayment setup accounting. No customer entitlement seeds.

CREATE TABLE subscription_requirements (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 registered_by TEXT NOT NULL REFERENCES users(id),policy_version TEXT NOT NULL,created_at TEXT NOT NULL
);
CREATE TABLE subscription_products (
 provider TEXT NOT NULL CHECK(provider IN ('creem','payu')),environment TEXT NOT NULL CHECK(environment IN ('production','test')),
 plan_code TEXT NOT NULL CHECK(plan_code IN ('starter','growth','scale')),variant TEXT NOT NULL CHECK(variant IN ('paid','trial')),
 product_id TEXT NOT NULL,price_minor BIGINT NOT NULL CHECK(price_minor>0),currency TEXT NOT NULL,
 interval TEXT NOT NULL,trial_days INTEGER NOT NULL CHECK(trial_days IN (0,3)),
 catalog_hash TEXT NOT NULL,verified_json TEXT NOT NULL,verified_at TEXT NOT NULL,
 PRIMARY KEY(provider,environment,plan_code,variant),UNIQUE(provider,environment,product_id)
);
CREATE TABLE subscription_customers (
 provider TEXT NOT NULL,environment TEXT NOT NULL,organization_id TEXT NOT NULL REFERENCES organizations(id),
 customer_id TEXT NOT NULL,created_at TEXT NOT NULL,
 PRIMARY KEY(provider,environment,organization_id),UNIQUE(provider,environment,customer_id)
);
CREATE TABLE subscription_billing_profiles (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),country TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('PENDING','VERIFIED','REVIEW')),
 verification_source TEXT,verification_reference TEXT,verified_at TEXT,updated_at TEXT NOT NULL
);
CREATE TABLE subscription_provider_readiness (
 provider TEXT NOT NULL,environment TEXT NOT NULL,
 checkout_verified INTEGER NOT NULL DEFAULT 0 CHECK(checkout_verified IN (0,1)),
 recurring_verified INTEGER NOT NULL DEFAULT 0 CHECK(recurring_verified IN (0,1)),
 trial_verified INTEGER NOT NULL DEFAULT 0 CHECK(trial_verified IN (0,1)),
 merchant_verified INTEGER NOT NULL DEFAULT 0 CHECK(merchant_verified IN (0,1)),
 verification_reference TEXT,verified_at TEXT,PRIMARY KEY(provider,environment)
);
CREATE TABLE subscription_checkouts (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),created_by TEXT NOT NULL REFERENCES users(id),
 provider TEXT NOT NULL,environment TEXT NOT NULL,plan_code TEXT NOT NULL,variant TEXT NOT NULL,
 request_id TEXT NOT NULL,request_hash TEXT NOT NULL,customer_id TEXT,product_id TEXT NOT NULL,
 provider_checkout_id TEXT,checkout_url TEXT,
 status TEXT NOT NULL CHECK(status IN ('CREATING','PENDING','COMPLETED','REVIEW','CANCELLED','EXPIRED')),
 country TEXT NOT NULL,currency TEXT NOT NULL,amount_minor BIGINT NOT NULL,trial_days INTEGER NOT NULL,
 terms_version TEXT NOT NULL,accepted_at TEXT NOT NULL,disclosure_json TEXT NOT NULL,
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id),UNIQUE(provider,environment,provider_checkout_id),UNIQUE(organization_id,id)
);
CREATE INDEX subscription_checkout_workspace ON subscription_checkouts(organization_id,created_at,id);
CREATE TABLE subscription_contracts (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),created_by TEXT NOT NULL REFERENCES users(id),
 provider TEXT NOT NULL,environment TEXT NOT NULL,provider_id TEXT NOT NULL,customer_id TEXT NOT NULL,
 checkout_id TEXT NOT NULL,plan_code TEXT NOT NULL,plan_json TEXT NOT NULL,
 status TEXT NOT NULL,recurring_authorized INTEGER NOT NULL DEFAULT 0 CHECK(recurring_authorized IN (0,1)),
 period_start BIGINT,period_end BIGINT,trial_start BIGINT,trial_end BIGINT,
 next_charge_at BIGINT,cancel_at BIGINT,cancel_confirmed_at TEXT,
 provider_updated_at BIGINT,verified_at TEXT,evidence_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 UNIQUE(provider,environment,provider_id),UNIQUE(organization_id,id),
 FOREIGN KEY(organization_id,checkout_id) REFERENCES subscription_checkouts(organization_id,id)
);
CREATE TABLE subscription_workspace_slots (
 organization_id TEXT NOT NULL REFERENCES organizations(id),environment TEXT NOT NULL,
 contract_id TEXT NOT NULL,PRIMARY KEY(organization_id,environment),
 FOREIGN KEY(organization_id,contract_id) REFERENCES subscription_contracts(organization_id,id)
);
CREATE TABLE subscription_trials (
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL UNIQUE REFERENCES users(id),company_domain TEXT NOT NULL UNIQUE,
 organization_id TEXT NOT NULL REFERENCES organizations(id),contract_id TEXT NOT NULL,
 policy_version TEXT NOT NULL,starts_at BIGINT NOT NULL,ends_at BIGINT NOT NULL,
 CHECK(ends_at-starts_at=259200),FOREIGN KEY(organization_id,contract_id) REFERENCES subscription_contracts(organization_id,id)
);
CREATE TABLE subscription_payments (
 provider TEXT NOT NULL,environment TEXT NOT NULL,payment_id TEXT NOT NULL,
 organization_id TEXT NOT NULL,contract_id TEXT NOT NULL,
 amount_minor BIGINT NOT NULL CHECK(amount_minor>=0),currency TEXT NOT NULL,status TEXT NOT NULL,
 period_start BIGINT,period_end BIGINT,receipt_url TEXT,evidence_json TEXT NOT NULL,
 recorded_at TEXT NOT NULL,PRIMARY KEY(provider,environment,payment_id),
 FOREIGN KEY(organization_id,contract_id) REFERENCES subscription_contracts(organization_id,id)
);
CREATE INDEX subscription_payment_history ON subscription_payments(organization_id,recorded_at,payment_id);
CREATE TABLE subscription_adjustments (
 provider TEXT NOT NULL,environment TEXT NOT NULL,adjustment_id TEXT NOT NULL,
 organization_id TEXT NOT NULL,contract_id TEXT NOT NULL,payment_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('refund','dispute')),status TEXT NOT NULL,
 amount_minor BIGINT,currency TEXT,evidence_json TEXT NOT NULL,recorded_at TEXT NOT NULL,
 PRIMARY KEY(provider,environment,adjustment_id),
 FOREIGN KEY(organization_id,contract_id) REFERENCES subscription_contracts(organization_id,id)
);
CREATE TABLE subscription_cancellations (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,contract_id TEXT NOT NULL,
 request_id TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('REQUESTED','REVIEW','CONFIRMED')),
 effective_at BIGINT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 UNIQUE(organization_id,request_id),FOREIGN KEY(organization_id,contract_id) REFERENCES subscription_contracts(organization_id,id)
);
CREATE TABLE subscription_usage (
 organization_id TEXT NOT NULL,contract_id TEXT NOT NULL,period_start BIGINT NOT NULL,period_end BIGINT NOT NULL,
 dimension TEXT NOT NULL,reserved BIGINT NOT NULL DEFAULT 0 CHECK(reserved>=0),used BIGINT NOT NULL DEFAULT 0 CHECK(used>=0),
 PRIMARY KEY(organization_id,contract_id,period_start,dimension),
 FOREIGN KEY(organization_id,contract_id) REFERENCES subscription_contracts(organization_id,id)
);
CREATE TABLE subscription_reservations (
 organization_id TEXT NOT NULL,contract_id TEXT NOT NULL,period_start BIGINT NOT NULL,operation_id TEXT NOT NULL,
 dimension TEXT NOT NULL,amount BIGINT NOT NULL CHECK(amount>0),state TEXT NOT NULL CHECK(state IN ('RESERVED','COMMITTED','RELEASED')),
 actual_amount BIGINT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,operation_id,dimension),
 FOREIGN KEY(organization_id,contract_id) REFERENCES subscription_contracts(organization_id,id)
);
CREATE TABLE subscription_setup_usage (
 organization_id TEXT NOT NULL REFERENCES subscription_requirements(organization_id),contract_id TEXT NOT NULL,
 period_start BIGINT NOT NULL,period_end BIGINT NOT NULL,dimension TEXT NOT NULL,
 reserved BIGINT NOT NULL DEFAULT 0 CHECK(reserved>=0),used BIGINT NOT NULL DEFAULT 0 CHECK(used>=0),
 PRIMARY KEY(organization_id,contract_id,period_start,dimension)
);
CREATE TABLE subscription_setup_reservations (
 organization_id TEXT NOT NULL REFERENCES subscription_requirements(organization_id),contract_id TEXT NOT NULL,
 period_start BIGINT NOT NULL,operation_id TEXT NOT NULL,dimension TEXT NOT NULL,
 amount BIGINT NOT NULL CHECK(amount>0),state TEXT NOT NULL CHECK(state IN ('RESERVED','COMMITTED','RELEASED')),
 actual_amount BIGINT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,operation_id,dimension)
);

UPDATE intent_schema_metadata SET structure_manifest_sha256='e51dae9e45267ba61e55cd32e40e6ba1276a8c5da845ab39a7eb374660579dd8' WHERE singleton=1;
