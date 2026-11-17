# Production AI onboarding repair — 17 November 2026

## Current result

The actual failed customer website job is recovered and READY. The API, AI worker and focused frontend error handling are deployed. No customer reset, production migration, payment, refund, outreach or browser automation occurred. The current customer account and session remain present. **Do not repeat any historical reset operation.**

| Runtime | Deployed and checked |
|---|---|
| API | `leadengine-api-00183-led`, 100% traffic |
| Backend source | `cf0e43662fa0e447f609c35a94f10ee1deb6ce11` |
| AI worker | `worker:intent-only-cf0e43662f` on existing `leadengine-worker` |
| Backend build | `988878dc-f23c-4583-8d84-f1288440cb5d`, SUCCESS |
| Frontend | `dpl_Dz2kkrNx9rAXwA75M7BvLv6difeV`, source `e02af6c1366ace16baab10968bccf8eb46a489ef` |
| Production onboarding | https://app.planebyte.com/onboarding |
| Database | Existing new Neon, public schema1006; no schema change |
| Preserved gates | Authentication, tenant membership, mandatory Step5, Creem Live checkout |

## Actual root cause and request trace

Original job `7c51336d-cd96-4e7e-9ecf-5d19a8f3d069`, request `3c398f42-7e73-49bc-a0a3-62165e5c202e`, was created at15:05:56.126141UTC and failed at15:06:28.248492UTC in execution `leadengine-worker-w2xb5`. API178 accepted it with202. The worker logged `UndefinedTable`, exposed as `SETUP_REVIEW_FAILED`.

Exact read-only reproduction:

```
psycopg.errors.UndefinedTable: relation "acquisition_preferences" does not exist
LINE 1: SELECT configuration_json FROM acquisition_preferences WHERE...
```

The shared AI router attempted a legacy Lead Engine preferences lookup on the clean Intent Radar schema before provider inference. No provider call/usage row existed for that failed attempt. Earlier clean-schema tests replaced the whole provider and missed this dependency.

The clean-schema router now uses existing shared provider health and namespaced rate-limit records; legacy full-schema behavior remains intact. PostgreSQL REAL cooldown rounding/readback was also fixed so provider cooldowns never expire early. No legacy customer table was recreated.

## Additional real-provider repairs

- A real Copilot response exhausted its former3000-token budget (`MAX_TOKENS`:2323 output and659 thinking tokens), producing incomplete JSON. The bounded6000-token budget, concise answer contract and35-second provider/40-second wrapper now pass. Truncation is reported distinctly rather than relabelled as generic success.
- Valid product descriptions were lost when a model quote omitted the product name. Recovery now binds the proposed description and literal name within the same actual public JSON-LD product/service object, with source-token verification. Cross-product attribution is rejected. No company facts are fabricated.
- Independently malformed field proposals are discarded with warnings while legitimate grounded fields survive. Partial services are validated individually. New schema/cache/request versions avoid reusing invalid old proposals while retaining prior request idempotency.
- Copilot now redacts contact_email consistently from both saved and unsaved context, avoiding a false claim that an unchanged email was added by a draft.
- Correlated failures include safe SQLSTATE/file/function/line diagnostics without SQL parameters, prompts or raw provider text. The existing progress stages stay backend-driven; terminal errors stop polling, preserve the draft and provide the same useful explanation in the form and Copilot. No UI redesign was performed.

## Real provider acceptance

1. **Original customer job:** normal owned retry/dispatch recovered the same job on attempt2. It reached READY through Vertex, reviewed three public pages and persisted seven useful suggestion fields. The original failure history is preserved. The saved customer profile was deliberately not overwritten: these are proposals awaiting the customer's review/save.
2. **Complete deployed-worker pipeline:** execution `leadengine-worker-9cc85`, source `aa774db`, passed website fetch/extraction → real Vertex structured response → validation → reviewed profile save → exactly five generated ICPs → reviewed ICP persistence → contextual Copilot → explicit profile edit/save → refreshed saved context. Four actual Vertex requests succeeded. The test used a guarded isolated schema on the new database; no customer workspace was created in public.
3. **Final follow-up:** execution `leadengine-worker-h8nqs`, final source `cf0e436`, passed one actual Vertex Copilot request (7263ms,2586 input/568 output tokens). It used the previously real-generated isolated profile/ICPs as context, distinguished saved positioning from the unsaved founder-led draft, did not claim a new contact email, and did not save the draft. This check did not regenerate the already-verified website/ICPs or consume customer setup allowance.

Actual profile: “PlaneByte develops Intent Radar and Growth Intelligence software for founders, growth teams, and B2B enterprises.” Both offerings, meaningful buyer-intent/growth positioning and target-market suggestions were present.

Exactly five distinct generated and saved targeting hypotheses:

1. B2B SaaS Growth & Marketing Leaders
2. Early-Stage Tech Founders & Product Strategists
3. B2B Marketing & Lead Gen Agencies
4. Enterprise RevOps & Sales Operations
5. Enterprise Business Intelligence & Strategy Leaders

These are reviewed targeting hypotheses, not verified customer demand. The customer's own five-ICP approval was not performed silently.

## Repaired files and regression evidence

Runtime: `app/acquisition/ai_router.py`, `app/acquisition/ai.py`, `app/platform/company_autofill.py`, `app/platform/company_discovery.py`, `app/platform/onboarding_ai.py`, `app/platform/setup_diagnostics.py`, `dashboard/components/workspaces/onboarding-ai.tsx`. Reusable guarded real-provider harness: `scripts/accept_onboarding_pipeline.py`.

- Full API-only backend run:1222 passed,2 failed,2 skipped. Both failures were reproduced, fixed and rerun: PostgreSQL cooldown decoding and the legacy Razorpay fixture's implicit default provider. That original full run is not represented as all green.
- Subsequent affected suites:36,50,57 and28 passes, zero failures/errors. These overlap; do not add them as unique tests. Includes clean PostgreSQL real-router integration, partial fields, product evidence, bounded provider diagnostics, context and billing guards.
- Frontend:197 unit passes; production Webpack and actual Vercel build passed. Local Turbopack hit the existing outside-workspace node_modules symlink restriction; this was not presented as a successful Turbopack build.
- Production: health200; unauthenticated subscription/context401; unsigned Creem webhook400; guest onboarding redirects to login307; signup200 with72-hour policy. Current customer account/session preserved, original jobREADY, owner profile unchanged, no payment records created.
- Image-only API/worker changes were compared against existing runtime settings. No database bindings, secrets, authentication, OAuth, payment flags, schedules or worker arguments were altered.

Restricted evidence: `data/artifacts/verification/onboarding-p0-20261117/` contains request/worker trace, exact exception, original-job recovery, source-specific Cloud Run/provider results, tests, runtime comparisons and `release-deployed.json`. Keep private payloads and operational scripts uncommitted.

## Verification boundary and recovery

Live backend analysis is working, including the actual recovered customer request. Five-ICP/save/edit/Copilot acceptance passed through deployed workers in isolated tenant schemas. No browser-rendering acceptance is claimed. The customer can reload onboarding, review the recovered profile and continue their own approvals. No additional credential or owner decision blocks this repair.

API181/sourceaa774 and its recorded image remain the previously verified application rollback checkpoint; it contains the full main repair but predates symmetric contact redaction. Preserve current database records and billing/access enforcement on any application rollback. Never restore an old database snapshot to undo this code change, and never rerun historical test-user resets.
