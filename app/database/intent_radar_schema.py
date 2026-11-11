"""Additive Intent Radar records; no changes to company/contact/mail history."""
INTENT_RADAR_SQL = """
CREATE TABLE intent_monitors (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', goal TEXT NOT NULL DEFAULT '',
 configuration_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Active','Paused','Archived')),
 request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 last_checked TEXT, last_job_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,id), UNIQUE(organization_id,request_id)
);
CREATE INDEX intent_monitors_workspace ON intent_monitors(organization_id,status,updated_at);
CREATE TABLE intent_discoveries (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
 created_by TEXT NOT NULL REFERENCES users(id), monitor_id TEXT, configuration_json TEXT NOT NULL,
 created_at TEXT NOT NULL, UNIQUE(organization_id,id),
 FOREIGN KEY(organization_id,monitor_id) REFERENCES intent_monitors(organization_id,id)
);
CREATE TABLE intent_signals (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), source TEXT NOT NULL,
 source_record_id TEXT NOT NULL, source_url TEXT NOT NULL, title TEXT NOT NULL, excerpt TEXT NOT NULL,
 observed_at TEXT NOT NULL, retrieved_at TEXT NOT NULL, category TEXT NOT NULL, score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
 evidence_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'New', notes TEXT NOT NULL DEFAULT '',
 available INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 1,
 UNIQUE(organization_id,id), UNIQUE(organization_id,source,source_record_id)
);
CREATE INDEX intent_signals_workspace ON intent_signals(organization_id,observed_at,score);
CREATE TABLE intent_monitor_signals (
 organization_id TEXT NOT NULL, monitor_id TEXT NOT NULL, signal_id TEXT NOT NULL, matched_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,monitor_id,signal_id),
 FOREIGN KEY(organization_id,monitor_id) REFERENCES intent_monitors(organization_id,id),
 FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id)
);
CREATE TABLE intent_opportunities (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, signal_id TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'New', priority TEXT NOT NULL DEFAULT 'Medium', notes TEXT NOT NULL DEFAULT '',
 next_action TEXT NOT NULL DEFAULT 'Review context', assigned_to TEXT REFERENCES users(id),
 revision INTEGER NOT NULL DEFAULT 1, created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(organization_id,id), UNIQUE(organization_id,signal_id),
 FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id)
);
CREATE TABLE intent_saved_signals (
 organization_id TEXT NOT NULL, signal_id TEXT NOT NULL, collection TEXT NOT NULL DEFAULT 'Inbox',
 tags_json TEXT NOT NULL DEFAULT '[]', notes TEXT NOT NULL DEFAULT '', saved_by TEXT NOT NULL REFERENCES users(id),
 saved_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 PRIMARY KEY(organization_id,signal_id), FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id)
);
CREATE TABLE intent_alerts (
 id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id), monitor_id TEXT,
 signal_id TEXT, event_key TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
 read_at TEXT, created_at TEXT NOT NULL, UNIQUE(organization_id,event_key),
 FOREIGN KEY(organization_id,monitor_id) REFERENCES intent_monitors(organization_id,id),
 FOREIGN KEY(organization_id,signal_id) REFERENCES intent_signals(organization_id,id)
);
CREATE INDEX intent_alerts_workspace ON intent_alerts(organization_id,created_at);
CREATE TABLE intent_preferences (
 organization_id TEXT PRIMARY KEY REFERENCES organizations(id), configuration_json TEXT NOT NULL,
 revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL
);
"""
