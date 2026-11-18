-- Composite indexes for scalable Signals 2.0 pagination, saved views, filtering, and AI hydration.

CREATE INDEX idx_signals_org_avail_observed ON intent_signals(organization_id, available, observed_at DESC, id DESC);
CREATE INDEX idx_signals_org_avail_status_score ON intent_signals(organization_id, available, status, score DESC, id DESC);
CREATE INDEX idx_signals_org_avail_source_obs ON intent_signals(organization_id, available, source, observed_at DESC);
CREATE INDEX idx_signals_org_avail_cat_obs ON intent_signals(organization_id, available, category, observed_at DESC);
CREATE INDEX idx_analyses_org_signal_created ON intent_analyses(organization_id, signal_id, created_at DESC);

UPDATE intent_schema_metadata SET structure_manifest_sha256='e23537137af36613c57a0ddb091458533afb0e1f6d1a832a8e29d4fe1c0797f3' WHERE singleton=1;
