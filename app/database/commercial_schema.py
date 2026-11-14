"""47: additive commercial contract snapshots and idempotent cycle accounting.

Historical Razorpay tables remain unchanged. No access is granted by migration.
"""
COMMERCIAL_SQL = """
CREATE TABLE commercial_contracts (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 provider TEXT NOT NULL CHECK(provider='payu'), mode TEXT NOT NULL CHECK(mode IN ('test','live')),
 provider_subscription_id TEXT NOT NULL, plan_code TEXT NOT NULL,
 catalog_version TEXT NOT NULL, plan_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('PENDING','ACTIVE','PAST_DUE','CANCELLED','COMPLETED','REVIEW')),
 mandate_verified INTEGER NOT NULL DEFAULT 0 CHECK(mandate_verified IN (0,1)),
 paid_start BIGINT, paid_end BIGINT, verified_at TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,id), UNIQUE(provider,mode,provider_subscription_id),
 CHECK((paid_start IS NULL AND paid_end IS NULL) OR (paid_start IS NOT NULL AND paid_end IS NOT NULL AND paid_end>paid_start))
);
CREATE TABLE commercial_workspace_slots (
 organization_id TEXT NOT NULL REFERENCES organizations(id), mode TEXT NOT NULL,
 contract_id TEXT NOT NULL, PRIMARY KEY(organization_id,mode),
 FOREIGN KEY(organization_id,contract_id) REFERENCES commercial_contracts(organization_id,id)
);
CREATE TABLE commercial_usage (
 organization_id TEXT NOT NULL, contract_id TEXT NOT NULL,
 period_start BIGINT NOT NULL, period_end BIGINT NOT NULL,
 dimension TEXT NOT NULL, reserved BIGINT NOT NULL DEFAULT 0 CHECK(reserved>=0),
 used BIGINT NOT NULL DEFAULT 0 CHECK(used>=0),
 PRIMARY KEY(organization_id,contract_id,period_start,dimension),
 FOREIGN KEY(organization_id,contract_id) REFERENCES commercial_contracts(organization_id,id)
);
CREATE TABLE commercial_reservations (
 organization_id TEXT NOT NULL, contract_id TEXT NOT NULL, period_start BIGINT NOT NULL,
 operation_id TEXT NOT NULL, dimension TEXT NOT NULL, amount BIGINT NOT NULL CHECK(amount>0),
 state TEXT NOT NULL CHECK(state IN ('RESERVED','COMMITTED','RELEASED')),
 actual_amount BIGINT CHECK(actual_amount>=0 AND actual_amount<=amount),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,operation_id,dimension),
 FOREIGN KEY(organization_id,contract_id) REFERENCES commercial_contracts(organization_id,id)
);
CREATE INDEX commercial_usage_period ON commercial_usage(organization_id,contract_id,period_start);
"""
