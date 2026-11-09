ONBOARDING_SETUP_SQL = """
CREATE TABLE organization_setup (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
 default_icp_id TEXT,
 objectives_json TEXT NOT NULL DEFAULT '[]',
 preferences_json TEXT NOT NULL DEFAULT '{}',
 current_step TEXT NOT NULL,
 revision INTEGER NOT NULL,
 completed_revision INTEGER,
 updated_by TEXT NOT NULL REFERENCES users(id),
 updated_at TEXT NOT NULL,
 FOREIGN KEY(default_icp_id,organization_id) REFERENCES ideal_customer_profiles(id,organization_id)
);
"""
