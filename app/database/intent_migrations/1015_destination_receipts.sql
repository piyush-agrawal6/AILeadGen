CREATE TABLE radar_destination_receipts (
 organization_id TEXT NOT NULL, action_id TEXT NOT NULL, connection_id TEXT NOT NULL,
 portal_id TEXT NOT NULL, connection_revision INTEGER NOT NULL, target_key TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('REVIEW','EXECUTING','VERIFY','CONFIRMED','REVIEW_AGAIN','UNCERTAIN','CANCELED')),
 attempts INTEGER NOT NULL DEFAULT 0, external_id TEXT, error_code TEXT, updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,action_id),
 FOREIGN KEY(organization_id,action_id) REFERENCES radar_actions(organization_id,id),
 FOREIGN KEY(organization_id,connection_id) REFERENCES radar_crm_connections(organization_id,id)
);
CREATE UNIQUE INDEX radar_destination_target_claim ON radar_destination_receipts(organization_id,connection_id,target_key) WHERE state IN ('EXECUTING','VERIFY','UNCERTAIN');

-- Clean profile identity
UPDATE intent_schema_metadata SET structure_manifest_sha256='e2b0dba350cdcee08530031d44f278699d84ff3f6008413a5ccd691210a06262' WHERE singleton=1;
