"""50: retained, authenticated privacy requests; never an automatic purge."""
PRIVACY_REQUEST_SQL = """
CREATE TABLE account_privacy_requests (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
 request_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('EXPORT','CLOSE_AND_DELETE','ERASURE')),
 status TEXT NOT NULL CHECK(status IN ('REQUESTED','REVIEW','AWAITING_INFORMATION','VERIFIED_CLOSURE','COMPLETED','REJECTED')),
 verified_session_id TEXT NOT NULL REFERENCES customer_sessions(id),
 policy_version TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 closure_verified_at BIGINT, ordinary_data_due_at BIGINT, backup_target_at BIGINT,
 completed_at TEXT, resolution_reference TEXT,
 UNIQUE(user_id,request_id),
 CHECK(ordinary_data_due_at IS NULL OR ordinary_data_due_at=closure_verified_at+2592000),
 CHECK(backup_target_at IS NULL OR backup_target_at=closure_verified_at+7776000)
);
CREATE INDEX privacy_request_review ON account_privacy_requests(status,ordinary_data_due_at,created_at);
CREATE INDEX privacy_request_actor ON account_privacy_requests(user_id,created_at);
"""
