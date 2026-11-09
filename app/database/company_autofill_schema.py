COMPANY_AUTOFILL_SQL="""
ALTER TABLE organization_profiles ADD COLUMN specialties_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE organization_profile_jobs ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'WEBSITE';
ALTER TABLE organization_profile_jobs ADD COLUMN input_text TEXT NOT NULL DEFAULT '';
ALTER TABLE organization_profile_jobs ADD COLUMN use_ai INTEGER NOT NULL DEFAULT 0;
ALTER TABLE organization_profile_jobs ADD COLUMN input_hash TEXT NOT NULL DEFAULT '';
ALTER TABLE organization_profile_jobs ADD COLUMN progress_stage TEXT NOT NULL DEFAULT '';
CREATE INDEX idx_profile_jobs_input ON organization_profile_jobs(organization_id,input_hash,status,updated_at);
"""
