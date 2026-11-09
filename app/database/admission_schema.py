"""Additive verified-account and consent ledger; no implicit tenant membership."""
ADMISSION_SQL = """
CREATE TABLE account_admissions (
 user_id TEXT PRIMARY KEY REFERENCES users(id),
 google_subject TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL CHECK(status IN ('ACTIVE','SUSPENDED','CLOSED')),
 terms_version TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE account_terms_acceptances (
 nonce TEXT PRIMARY KEY,
 user_id TEXT NOT NULL REFERENCES users(id),
 terms_version TEXT NOT NULL,
 accepted_at TEXT NOT NULL, recorded_at TEXT NOT NULL
);
CREATE INDEX idx_account_terms_user ON account_terms_acceptances(user_id,recorded_at);
"""
