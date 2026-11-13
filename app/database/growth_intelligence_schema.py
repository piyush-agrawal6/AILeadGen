"""45: additive Growth Intelligence inside the existing Intent Radar workspace."""
GROWTH_SQL = """
CREATE TABLE growth_research (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id), kind TEXT NOT NULL,
 question TEXT NOT NULL DEFAULT '', title TEXT NOT NULL,
 scope_json TEXT NOT NULL, snapshot_json TEXT NOT NULL DEFAULT '{}',
 output_json TEXT NOT NULL DEFAULT '{}', input_hash TEXT NOT NULL,
 request_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'QUEUED',
 job_id TEXT REFERENCES intelligence_jobs(id), saved_at TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 UNIQUE(organization_id,id), UNIQUE(organization_id,request_id)
);
CREATE INDEX growth_research_page ON growth_research(organization_id,kind,created_at,id);
CREATE TABLE growth_themes (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 research_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL,
 method TEXT NOT NULL, evidence_json TEXT NOT NULL, saved_at TEXT,
 status TEXT NOT NULL DEFAULT 'Active', revision INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,id),
 FOREIGN KEY(organization_id,research_id) REFERENCES growth_research(organization_id,id)
);
CREATE INDEX growth_themes_page ON growth_themes(organization_id,status,created_at,id);
CREATE TABLE growth_theme_signals (
 organization_id TEXT NOT NULL, theme_id TEXT NOT NULL, signal_id TEXT NOT NULL,
 PRIMARY KEY(organization_id,theme_id,signal_id),
 FOREIGN KEY(organization_id,theme_id) REFERENCES growth_themes(organization_id,id),
 FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id)
);
CREATE INDEX growth_theme_signal_lookup ON growth_theme_signals(organization_id,signal_id);
CREATE TABLE growth_competitors (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 name TEXT NOT NULL, aliases_json TEXT NOT NULL DEFAULT '[]', context TEXT NOT NULL DEFAULT '',
 request_id TEXT NOT NULL, archived_at TEXT, revision INTEGER NOT NULL DEFAULT 1,
 created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,id), UNIQUE(organization_id,request_id)
);
CREATE TABLE growth_watchlists (
 organization_id TEXT NOT NULL, monitor_id TEXT NOT NULL,
 kind TEXT NOT NULL, resource_id TEXT, created_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,monitor_id),
 FOREIGN KEY(organization_id,monitor_id) REFERENCES intent_monitors(organization_id,id)
);
CREATE TABLE growth_notes (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 resource_kind TEXT NOT NULL, resource_id TEXT NOT NULL,
 author TEXT NOT NULL REFERENCES users(id), body TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,id)
);
CREATE INDEX growth_notes_resource ON growth_notes(organization_id,resource_kind,resource_id,created_at);
CREATE TABLE growth_company_links (
 organization_id TEXT NOT NULL, opportunity_id TEXT NOT NULL, business_id BIGINT NOT NULL REFERENCES businesses(id),
 created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,opportunity_id,business_id),
 FOREIGN KEY(organization_id,opportunity_id) REFERENCES intent_opportunities(organization_id,id)
);
"""
