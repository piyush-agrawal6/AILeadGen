-- Composite indexes for scalable Discovery History pagination, filtering, and job hydration.

CREATE INDEX idx_discoveries_org_created ON intent_discoveries(organization_id, created_at DESC, id DESC);
CREATE INDEX idx_job_items_resource ON intelligence_job_items(resource_id, job_id);
CREATE INDEX idx_discovery_meta_mode ON intent_discovery_runs_meta(organization_id, search_mode, deleted_at);

UPDATE intent_schema_metadata SET structure_manifest_sha256='6066e605612adf2262ee7386527f7dcbe6df70cf1dafc01a0fad644303481c20' WHERE singleton=1;
