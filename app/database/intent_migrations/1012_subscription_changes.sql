CREATE TABLE subscription_plan_changes (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 environment TEXT NOT NULL, contract_id TEXT NOT NULL, actor TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL, product_id TEXT NOT NULL, plan_code TEXT NOT NULL,
 terms_version TEXT NOT NULL, effective_at BIGINT NOT NULL, created_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('REQUESTED','CONFIRMED','APPLIED','REVIEW')),
 UNIQUE(organization_id,request_id)
);
CREATE UNIQUE INDEX subscription_change_inflight ON subscription_plan_changes(contract_id,environment) WHERE status IN ('REQUESTED','CONFIRMED','REVIEW');

-- Clean profile identity
UPDATE intent_schema_metadata SET structure_manifest_sha256='439ce075cfd6c3e8c2b540e52f1b8c074dc4f3849f209367694a7b6b9a0282af' WHERE singleton=1;
