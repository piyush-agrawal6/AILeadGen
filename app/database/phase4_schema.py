"""Additive private sales workspace; existing identities and observations survive."""
import re

STATUSES=('NEW','SHORTLISTED','READY_TO_CONTACT','CONTACTED','FOLLOW_UP','REPLIED','MEETING','PROPOSAL','WON','LOST','NOT_INTERESTED','DO_NOT_CONTACT')
PHASE4_SQL="""
CREATE TABLE prospect_sales (
 prospect_id TEXT PRIMARY KEY REFERENCES prospects(id) ON DELETE CASCADE,
 suppressed_at TEXT, service_interest TEXT, estimated_value REAL, currency TEXT DEFAULT 'GBP',
 meeting_at TEXT, proposal_value REAL, proposal_at TEXT, close_at TEXT, loss_reason TEXT,
 last_contact_at TEXT, unread_replies INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE activities (
 id TEXT PRIMARY KEY, prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
 actor_user_id TEXT, event_type TEXT NOT NULL, event_at TEXT NOT NULL,
 metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, dedup_key TEXT UNIQUE
);
CREATE INDEX idx_activities_prospect ON activities(prospect_id,event_at);
CREATE TABLE followups (
 id TEXT PRIMARY KEY, prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
 assigned_to TEXT, due_at TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('OPEN','COMPLETED','CANCELED')),
 reason TEXT, note TEXT, created_by TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT
);
CREATE INDEX idx_followups_due ON followups(status,due_at);
CREATE TABLE lead_lists (id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT,created_by TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE lead_list_members (list_id TEXT NOT NULL REFERENCES lead_lists(id) ON DELETE CASCADE,prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,added_by TEXT NOT NULL,added_at TEXT NOT NULL,PRIMARY KEY(list_id,prospect_id));
CREATE TABLE saved_views (id TEXT PRIMARY KEY,name TEXT NOT NULL,filters_json TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE email_accounts (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,provider TEXT NOT NULL,email_address TEXT NOT NULL,display_name TEXT NOT NULL,status TEXT NOT NULL,is_default INTEGER NOT NULL DEFAULT 1,last_sync_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,smtp_health TEXT NOT NULL DEFAULT 'UNKNOWN',imap_health TEXT NOT NULL DEFAULT 'UNKNOWN',health_checked_at TEXT);
CREATE TABLE email_threads (id TEXT PRIMARY KEY,prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,account_id TEXT NOT NULL REFERENCES email_accounts(id),subject TEXT NOT NULL,last_message_at TEXT NOT NULL,last_direction TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX idx_email_threads_prospect ON email_threads(prospect_id,last_message_at);
CREATE TABLE email_messages (
 id TEXT PRIMARY KEY,prospect_id TEXT NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,account_id TEXT NOT NULL REFERENCES email_accounts(id),thread_id TEXT NOT NULL REFERENCES email_threads(id) ON DELETE CASCADE,
 provider_message_id TEXT NOT NULL,direction TEXT NOT NULL,status TEXT NOT NULL,from_address TEXT NOT NULL,to_address TEXT NOT NULL,intended_to TEXT,
 subject TEXT NOT NULL,body_text TEXT NOT NULL,in_reply_to TEXT,references_json TEXT NOT NULL DEFAULT '[]',report_id TEXT,created_at TEXT NOT NULL,sent_at TEXT,received_at TEXT,
 idempotency_key TEXT UNIQUE,content_hash TEXT,test_mode INTEGER NOT NULL DEFAULT 1,error_code TEXT,
 UNIQUE(account_id,provider_message_id)
);
CREATE INDEX idx_email_messages_thread ON email_messages(thread_id,created_at);
CREATE TABLE email_templates (id TEXT PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,vertical TEXT,subject TEXT NOT NULL,body_text TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
CREATE TABLE email_sync_state (account_id TEXT NOT NULL REFERENCES email_accounts(id),folder TEXT NOT NULL,uidvalidity TEXT,last_uid INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(account_id,folder));
CREATE TABLE email_sync_lock (id INTEGER PRIMARY KEY,owner TEXT,expires_at TEXT);
"""

def ready(conn):
    if getattr(conn,'_phase4_ready',False):return True
    available=(conn.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0)>=7
    if available:
        try:conn._phase4_ready=True
        except AttributeError:pass # SQLite has no instance attributes; production PostgreSQL does.
    return available

def apply_phase4(conn,postgres):
    values=','.join("'"+s+"'" for s in STATUSES)
    if postgres:
        conn.execute('ALTER TABLE prospects DROP CONSTRAINT prospects_lead_status_check')
        conn.execute('ALTER TABLE prospects ADD CONSTRAINT prospects_lead_status_check CHECK(lead_status IN ('+values+'))')
    else:
        conn.commit();conn.execute('PRAGMA foreign_keys=OFF')
        try:
            conn.execute('BEGIN IMMEDIATE')
            original=conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='prospects'").fetchone()[0]
            indexes=[r[0] for r in conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='prospects' AND sql IS NOT NULL").fetchall()]
            expanded=re.sub(r'CREATE TABLE\s+(?:"prospects"|prospects)','CREATE TABLE prospects_phase4',original,count=1,flags=re.I)
            expanded=re.sub(r'CHECK\(lead_status IN \([^)]*\)\)','CHECK(lead_status IN ('+values+'))',expanded)
            conn.execute(expanded);conn.execute('INSERT INTO prospects_phase4 SELECT * FROM prospects');conn.execute('DROP TABLE prospects');conn.execute('ALTER TABLE prospects_phase4 RENAME TO prospects')
            for statement in indexes:conn.execute(statement)
            if conn.execute('PRAGMA foreign_key_check').fetchall():raise RuntimeError('Foreign-key verification failed')
            conn.commit()
        except Exception:conn.rollback();raise
        finally:conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript(PHASE4_SQL)
    conn.execute("INSERT INTO prospect_sales(prospect_id,suppressed_at) SELECT id,CASE WHEN lead_status='DO_NOT_CONTACT' THEN updated_at ELSE NULL END FROM prospects")
    # Seed genuine historical events from stored records, without touching them.
    conn.execute("INSERT INTO activities(id,prospect_id,event_type,event_at,created_at,dedup_key) SELECT 'discovery-'||id,id,'LEAD_DISCOVERED',first_seen_at,first_seen_at,'discovery-'||id FROM prospects")
    conn.execute("INSERT INTO activities(id,prospect_id,actor_user_id,event_type,event_at,created_at,dedup_key) SELECT 'note-'||id,prospect_id,created_by,'NOTE_ADDED',created_at,created_at,'note-'||id FROM prospect_notes")
    conn.execute("INSERT INTO activities(id,prospect_id,actor_user_id,event_type,event_at,created_at,dedup_key) SELECT 'pdf-'||id,prospect_id,created_by,'PDF_GENERATED',updated_at,updated_at,'pdf-'||id FROM client_reports WHERE status='READY'")
