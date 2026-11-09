"""Separate customer acquisition settings from platform provider state."""
ACQUISITION_PREFERENCES_SQL = """
CREATE TABLE organization_acquisition_preferences (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 configuration_json TEXT NOT NULL,
 updated_by TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
INSERT INTO organization_acquisition_preferences(organization_id,configuration_json,updated_by,updated_at)
SELECT o.id,p.configuration_json,p.updated_by,p.updated_at
FROM acquisition_preferences p JOIN organizations o ON o.id='e5ffc3dc-241e-5558-acd4-84f5fe354ca7'
WHERE p.id=1;
ALTER TABLE acquisition_ai_cache ADD COLUMN organization_id TEXT REFERENCES organizations(id);
CREATE INDEX idx_acquisition_cache_expiry ON acquisition_ai_cache(organization_id,expires_at);
"""
