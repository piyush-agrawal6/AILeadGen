# Vertex AI primary migration

Vertex AI is the production primary provider in project `querryside`, location `global`, model `gemini-3.6-flash`. The existing single Gemini Developer API key remains the secondary provider, with deterministic evidence templates as the final copy fallback. Root `.env` remains the local configuration source; production uses existing environment and Secret Manager references.

The owner explicitly approved `roles/aiplatform.user` for the existing API, worker and acquisition service accounts. Those three identities were preserved and the grants applied once. Cloud Run uses attached service identity through ADC. No service-account key was created, no credentials moved to the frontend, and schema14/data/Gmail configuration were preserved without another migration.

The existing structured AI interface now uses one router for copy, search interpretation and column mapping. Only provider failures trigger provider fallback; programming/schema errors propagate. Bounded transient retries precede same-batch Vertex→Gemini fallback. Independent durable provider cooldowns prevent repeated quota failures. Structured-output problems can split40→20+20→10+10; individual invalid items receive validated deterministic copy. The model remains configurable, with no silent substitution.

Copy defaults to40 leads/request, configurable10–50. Inputs contain concise verified facts only; untrusted website text cannot supply instructions. Outputs match by lead ID, with duplicate/missing/unknown IDs and unsupported claims rejected. Validated content hashes, durable generating leases and recovery handling preserve cache/idempotency. Provider/model/batch/time/mode metadata and separate usage counters are stored without secrets. Unknown monetary cost is shown as unavailable.

Observed acceptance:
- Local ADC:1,5,10,40 leads PASS. One actual40-lead Vertex request returned40 valid matching outputs,0 duplicate/unknown/missing IDs, all renderable. Actual inference38.939seconds; the full stage including cache/database work took112.13seconds.
- Production Cloud Run service-identity inference PASS: Vertex/querryside/global/configured model/structured output; no SMTP.
- Mocked Vertex→Gemini same-batch fallback PASS; both unavailable→deterministic PASS; split,39+1 partial fallback, cooldown and application-error distinction PASS.
- Final exact Linux build:464 passed,15 skipped. Frontend43 passed; browser25 passed; strict TypeScript and production build passed. Real PostgreSQL cache/circuit/idempotency/attribution integration passed.
- First10 existing pending copies validated:9 new Vertex results and1 cache hit. Only1 additional eligible analyzed lead was available. The next real40-lead group waits for inputs; synthetic40 acceptance is separate. Completed copy is reused.
- Five owner-only strategy messages: SMTP accepted, Gmail Sent verified, exact3-page attachments/HTML/text/signature/tracking/opt-out verified. Genuine owner reply matched and classified positive with campaign/source/template/experiment attribution. All15 attachment pages visually reviewed; existing8-page full report preserved. No real prospect was contacted during QA.
- Controlled Overture and Firecrawl source/schedule checks passed. Overture actual6 analyzed/public-email leads after retry (target5) were preserved and reported; no-email deep analysis0.

Production revision: `leadengine-api-00105-cil`; API/core/source images `vertex-20261102-r7`. Frontend deployment `dpl_DXHkvaSF1DfeVrn1zQis5iTDx8q5` Ready. Settings compatibility and actual provider-request resource accounting were repaired and tested. Existing schedulers remain enabled; historical redundant email-sync job remains paused. Runtime environment and service identities are unchanged apart from the approved provider configuration.

Secondary provider limitation: Gemini Developer API currently reports HTTP402 RESOURCE_EXHAUSTED. It remains configured with cooldown; healthy Vertex and deterministic fallback continue. No key rotation or quota bypass was added.

The experiment activation state and actual acquired/sent counts are recorded separately in `EXPERIMENT_ACCEPTANCE_STATUS.md`; successful provider migration is not a claim that500 leads were acquired or emailed.
