"""Permanent organization-scoped outreach memory and shared company assets."""
CONTACTABLE_SQL = '''
CREATE TABLE contacted_recipients (
 id TEXT PRIMARY KEY,organization_id TEXT NOT NULL,normalized_email TEXT NOT NULL,original_email TEXT NOT NULL,
 canonical_domain TEXT,company_name TEXT,company_domain TEXT,first_sent_at TEXT NOT NULL,last_sent_at TEXT NOT NULL,
 send_count INTEGER NOT NULL DEFAULT 0,first_campaign_id TEXT,last_campaign_id TEXT,first_message_id TEXT,last_message_id TEXT,
 first_acquisition_source TEXT,last_acquisition_source TEXT,last_delivery_status TEXT NOT NULL DEFAULT 'SENT',
 ever_replied INTEGER NOT NULL DEFAULT 0,ever_positive_reply INTEGER NOT NULL DEFAULT 0,hard_bounced INTEGER NOT NULL DEFAULT 0,
 unsubscribed INTEGER NOT NULL DEFAULT 0,do_not_contact INTEGER NOT NULL DEFAULT 0,source TEXT NOT NULL,
 created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(organization_id,normalized_email)
);
CREATE TABLE contacted_recipient_sends (
 organization_id TEXT NOT NULL,message_key TEXT NOT NULL,normalized_email TEXT NOT NULL,message_id TEXT NOT NULL,
 provider_message_id TEXT,sent_at TEXT NOT NULL,campaign_id TEXT,acquisition_source TEXT,created_at TEXT NOT NULL,
 PRIMARY KEY(organization_id,message_key)
);
CREATE INDEX idx_contacted_sends_time ON contacted_recipient_sends(organization_id,sent_at);
CREATE TABLE contacted_unsubscribe_tokens (
 token_hash TEXT PRIMARY KEY,organization_id TEXT NOT NULL,normalized_email TEXT NOT NULL,expires_at TEXT NOT NULL,test_mode INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE company_pdf_assets (
 id TEXT NOT NULL,version TEXT NOT NULL,organization_id TEXT NOT NULL,filename TEXT NOT NULL,object_key TEXT NOT NULL,
 sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,page_count INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL,PRIMARY KEY(organization_id,id,version)
);
ALTER TABLE email_messages ADD COLUMN organization_id TEXT NOT NULL DEFAULT 'planebyte';
ALTER TABLE email_messages ADD COLUMN campaign_id TEXT;
ALTER TABLE email_messages ADD COLUMN template_version TEXT;
ALTER TABLE email_messages ADD COLUMN pdf_asset_id TEXT;
ALTER TABLE email_messages ADD COLUMN pdf_version TEXT;
ALTER TABLE email_messages ADD COLUMN outreach_strategy TEXT;
'''

def ready(c):
    return (c.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0) >= 15
