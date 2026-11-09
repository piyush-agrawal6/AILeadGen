AI_USAGE_SQL = """
CREATE TABLE organization_ai_usage (
 organization_id TEXT NOT NULL REFERENCES organizations(id),
 day TEXT NOT NULL,
 feature TEXT NOT NULL,
 requests INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,day,feature)
);
CREATE INDEX idx_ai_usage_day ON organization_ai_usage(day,feature);
"""
