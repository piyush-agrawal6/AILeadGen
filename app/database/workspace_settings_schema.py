"""Additive settings storage; retain the legacy singleton and its data."""
WORKSPACE_SETTINGS_SQL = """
CREATE TABLE organization_settings (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 configuration_json TEXT NOT NULL,
 updated_by TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
INSERT INTO organization_settings(organization_id,configuration_json,updated_by,updated_at)
 SELECT organization_id,configuration_json,updated_by,updated_at FROM shared_settings
 WHERE organization_id IS NOT NULL;
"""
