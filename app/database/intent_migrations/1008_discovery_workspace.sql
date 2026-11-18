-- Additive Discovery 2.0 workspace tables (immutable run metadata & reusable Saved Searches).

CREATE TABLE intent_discovery_runs_meta (
 organization_id TEXT NOT NULL,
 discovery_id TEXT NOT NULL,
 title TEXT NOT NULL DEFAULT '',
 original_prompt TEXT NOT NULL DEFAULT '',
 search_mode TEXT NOT NULL DEFAULT 'advanced' CHECK(search_mode IN ('ai','advanced','monitor','rerun')),
 parent_discovery_id TEXT,
 strategy_json TEXT NOT NULL DEFAULT '{}',
 deleted_at TEXT,
 updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id, discovery_id),
 FOREIGN KEY(organization_id, discovery_id) REFERENCES intent_discoveries(organization_id, id)
);
CREATE INDEX idx_discovery_meta_active ON intent_discovery_runs_meta(organization_id, deleted_at, updated_at);

CREATE TABLE intent_saved_searches (
 id TEXT PRIMARY KEY,
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id),
 name TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 original_prompt TEXT NOT NULL DEFAULT '',
 configuration_json TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision >= 1),
 last_run_discovery_id TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 UNIQUE(organization_id, id)
);
CREATE INDEX idx_saved_searches_workspace ON intent_saved_searches(organization_id, updated_at);

UPDATE intent_schema_metadata SET structure_manifest_sha256='92fd4b1b3c4338488cf0ad27ee6e87d29ac588d12085ef346af946218a679698' WHERE singleton=1;
