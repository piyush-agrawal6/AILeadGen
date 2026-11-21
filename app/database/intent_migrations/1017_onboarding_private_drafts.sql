CREATE TABLE onboarding_private_drafts (
 organization_id TEXT NOT NULL REFERENCES organizations(id), actor TEXT NOT NULL REFERENCES users(id),
 revision INTEGER NOT NULL CHECK(revision>0), profile_version TEXT, draft_json TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(organization_id,actor)
);

-- Clean profile identity
UPDATE intent_schema_metadata SET structure_manifest_sha256='174b8810f13457cd82f814cca0550a8e3e5e3a3dc5ed396073f62e829c3bd55c' WHERE singleton=1;
