PHASE36_SQL="""
CREATE TABLE social_profiles (
 id TEXT PRIMARY KEY, prospect_id TEXT NOT NULL REFERENCES prospects(id), platform TEXT NOT NULL,
 profile_url TEXT NOT NULL, handle TEXT, source_type TEXT NOT NULL, source_url TEXT, confidence TEXT NOT NULL,
 last_activity_at TEXT, activity_status TEXT NOT NULL DEFAULT 'UNKNOWN', activity_source TEXT,
 activity_evidence_url TEXT, activity_checked_at TEXT, activity_reason TEXT,
 metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(prospect_id,profile_url)
);
CREATE INDEX idx_social_prospect ON social_profiles(prospect_id,platform);
CREATE TABLE social_profile_sources (
 profile_id TEXT NOT NULL REFERENCES social_profiles(id) ON DELETE CASCADE,
 business_id INTEGER NOT NULL REFERENCES businesses(id), source_type TEXT NOT NULL,
 source_url TEXT NOT NULL DEFAULT '', confidence TEXT NOT NULL,
 PRIMARY KEY(profile_id,business_id,source_type,source_url)
);
CREATE TABLE business_intelligence (
 business_id INTEGER PRIMARY KEY REFERENCES businesses(id), prospect_id TEXT NOT NULL REFERENCES prospects(id),
 classification_version TEXT NOT NULL, business_scale TEXT NOT NULL, scale_reason TEXT NOT NULL,
 scale_confidence REAL NOT NULL, footprint_json TEXT NOT NULL, commercial_fit TEXT NOT NULL,
 commercial_reason TEXT NOT NULL, social_presence_status TEXT NOT NULL DEFAULT 'UNKNOWN',
 enrichment_metrics_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE TABLE website_captures (
 business_id INTEGER PRIMARY KEY REFERENCES businesses(id), object_key TEXT,
 page_url TEXT, captured_at TEXT NOT NULL, status TEXT NOT NULL, reason TEXT
);
CREATE TABLE deletion_batches (
 id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
 actor TEXT NOT NULL, scope_json TEXT NOT NULL, status TEXT NOT NULL,
 error_message TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(entity_type,entity_id)
);
CREATE TABLE deletion_targets (
 request_id TEXT NOT NULL REFERENCES deletion_batches(id) ON DELETE CASCADE,
 business_id INTEGER NOT NULL, PRIMARY KEY(request_id,business_id)
);
"""


def phase36_ready(conn):
    return (conn.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=6
