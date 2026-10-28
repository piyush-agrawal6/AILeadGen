"""Additive engagement data; all Phase 4 message history remains intact."""
PHASE41_SQL="""
ALTER TABLE prospect_sales ADD COLUMN suppression_source TEXT;
UPDATE prospect_sales SET suppression_source='MANUAL_DNC' WHERE suppressed_at IS NOT NULL;
ALTER TABLE email_messages ADD COLUMN template_id TEXT;
ALTER TABLE email_messages ADD COLUMN message_type TEXT NOT NULL DEFAULT 'FIRST_CONTACT';
ALTER TABLE email_messages ADD COLUMN track_opens INTEGER NOT NULL DEFAULT 0;
ALTER TABLE email_messages ADD COLUMN track_clicks INTEGER NOT NULL DEFAULT 0;
CREATE TABLE email_tracking_preferences (id INTEGER PRIMARY KEY,track_opens INTEGER NOT NULL DEFAULT 1,track_clicks INTEGER NOT NULL DEFAULT 1,track_replies INTEGER NOT NULL DEFAULT 1,track_bounces INTEGER NOT NULL DEFAULT 1);
INSERT INTO email_tracking_preferences(id) VALUES(1);
CREATE TABLE email_tracking_tokens (
 token_hash TEXT PRIMARY KEY,message_id TEXT NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
 action TEXT NOT NULL CHECK(action IN ('o','c','u')),destination TEXT,created_at TEXT NOT NULL,expires_at TEXT NOT NULL
);
CREATE TABLE email_engagement_events (
 id TEXT PRIMARY KEY,message_id TEXT NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
 thread_id TEXT NOT NULL,prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
 event_type TEXT NOT NULL,occurred_at TEXT NOT NULL,last_at TEXT NOT NULL,token_id TEXT,url_id TEXT,
 user_agent_category TEXT,signal_quality TEXT NOT NULL DEFAULT 'UNKNOWN',suspected_bot INTEGER NOT NULL DEFAULT 0,
 request_count INTEGER NOT NULL DEFAULT 1,metadata_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,dedup_key TEXT UNIQUE NOT NULL
);
CREATE INDEX idx_engagement_prospect ON email_engagement_events(prospect_id,occurred_at);
CREATE INDEX idx_engagement_message ON email_engagement_events(message_id,event_type);
CREATE TABLE email_address_suppressions (
 address TEXT PRIMARY KEY,source TEXT NOT NULL,soft_bounce_count INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL,updated_at TEXT NOT NULL
);
CREATE TABLE email_tracking_rate_limits (bucket TEXT PRIMARY KEY,requests INTEGER NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE email_drafts (id TEXT PRIMARY KEY,prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,actor TEXT NOT NULL,payload_json TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(prospect_id,actor));
"""
