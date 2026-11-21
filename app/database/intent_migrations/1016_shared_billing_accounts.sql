CREATE TABLE workspace_billing_accounts (
 id TEXT PRIMARY KEY REFERENCES organizations(id),
 created_at TEXT NOT NULL
);
CREATE TABLE billing_workspace_links (
 workspace_id TEXT PRIMARY KEY REFERENCES organizations(id),
 account_id TEXT NOT NULL REFERENCES workspace_billing_accounts(id),
 attached_at TEXT NOT NULL
);
CREATE INDEX idx_billing_account_workspaces ON billing_workspace_links(account_id,workspace_id);
CREATE TABLE billing_account_admins (
 account_id TEXT NOT NULL REFERENCES workspace_billing_accounts(id),
 user_id TEXT NOT NULL REFERENCES users(id), PRIMARY KEY(account_id,user_id)
);
-- The immutable account ID is also the historical contract/ledger anchor.
-- Every old workspace starts independent. No inferred grouping and no financial row rewrite.
INSERT INTO workspace_billing_accounts(id,created_at) SELECT id,created_at FROM organizations;
INSERT INTO billing_workspace_links(workspace_id,account_id,attached_at) SELECT id,id,created_at FROM organizations;
INSERT INTO billing_account_admins(account_id,user_id)
 SELECT o.id,o.created_by_user_id FROM organizations o JOIN organization_memberships m
 ON o.id=m.organization_id AND m.user_id=o.created_by_user_id AND m.role='OWNER' AND m.status='ACTIVE'
 WHERE NOT EXISTS(SELECT 1 FROM organization_memberships m2 WHERE m2.organization_id=o.id AND m2.role='OWNER' AND m2.status='ACTIVE' AND m2.user_id<>m.user_id);

-- Clean profile identity
UPDATE intent_schema_metadata SET structure_manifest_sha256='65251a5b8aa0a46953ceb058eb56c2c9aa5190003ba35ee680d6c64506e7cd0e' WHERE singleton=1;
