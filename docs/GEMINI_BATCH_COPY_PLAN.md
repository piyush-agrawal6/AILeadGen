# Active batch-copy implementation

Owner steering replaces per-lead Gemini dependency with one currently configured secure key and configurable40-lead batches (10–50). Existing templates, assignment, CTA, signature, tracking, reports and guarded SMTP stay deterministic. Generate only ID-matched subject/opening/finding wording/optional bridge from approved verified evidence. No key rotation, logging or frontend secrets.

Use existing schema14: immutable per-lead generation_json, acquisition_ai_cache for exact input/version/campaign/analysis hashes, experiment_events for durable batch/request/split/partial/fallback metrics, acquisition_preferences for nonsecret circuit state, acquisition_provider_health for status. No new migration is necessary for this change.

Batch validation rejects missing/duplicate/unknown IDs and cross-company/unsupported substitutions; preserves valid siblings. Bound size/tokens, provider retries and wall time; split failed large batches down to5; persist safe deterministic fallback for isolated/provider failures and mark AI_COPY_FAILED. Quota/rate errors open a persisted circuit rather than splitting/hammering the provider. Completed copy is immutable and reused. Flush40 when available, with bounded small-tail delay so discovery remains streaming; provisional batches are leased/CAS claimed.

New-key acceptance progresses1→5→10→40 synthetic leads; the40-lead stage must use exactly one actual provider request with40valid matched/renderable outputs. Mock split40→20+20, partial39+fallback1, quota circuit and restart/cache tests. Then controlled five-strategy email acceptance and progressive10→40pending production preparation, no duplicate of the already-sent AEO owner message.

Production remains unactivated until original experiment gates and new batch acceptance pass. November2start date must not silently move. Root key still matched old exhausted deployed secret at initial comparison; owner asked to replace the existing value securely. Model remainsgemini-3.6-flash. New key values/fragments must never be printed.
