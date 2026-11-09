"""Reviewed AI provenance, additive to the existing ICP entity and history."""
ICP_PROPOSAL_SQL = """
ALTER TABLE ideal_customer_profiles ADD COLUMN generation_source TEXT NOT NULL DEFAULT 'MANUAL';
ALTER TABLE ideal_customer_profiles ADD COLUMN generation_metadata_json TEXT NOT NULL DEFAULT '{}';
CREATE TABLE icp_ai_proposals (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 source TEXT NOT NULL CHECK(source IN ('BUSINESS_PROFILE','AI_ASSISTED','AI_REFINED')),
 input_hash TEXT NOT NULL,
 result_json TEXT NOT NULL,
 profile_version TEXT,
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL,
 UNIQUE(organization_id,created_by,input_hash)
);
CREATE INDEX idx_icp_proposal_owner ON icp_ai_proposals(organization_id,created_by,expires_at);
"""
