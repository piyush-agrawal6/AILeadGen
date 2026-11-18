"""Additive Discovery 2.0 tables: immutable run metadata & reusable Saved Searches."""

DISCOVERY_WORKSPACE_SQL = """
CREATE TABLE IF NOT EXISTS intent_discovery_runs_meta (
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
CREATE INDEX IF NOT EXISTS idx_discovery_meta_active ON intent_discovery_runs_meta(organization_id, deleted_at, updated_at);

CREATE TABLE IF NOT EXISTS intent_saved_searches (
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
CREATE INDEX IF NOT EXISTS idx_saved_searches_workspace ON intent_saved_searches(organization_id, updated_at);
"""


def ensure_sqlite_tables(c):
    """Create additive Discovery 2.0 tables lazily on SQLite test databases."""
    if getattr(c, 'backend', None) == 'postgres':
        return
    c.executescript(DISCOVERY_WORKSPACE_SQL)
