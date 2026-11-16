# Next PlaneByte agent: start here

Checkpoint 2026-11-16. **Do not restart, redesign the latest UI, reset data, or infer completion from an old report.** Owner requested final safe deployment/handover before usage limit. No new major feature was started during wrap-up.

**Final live checkpoint:** API `leadengine-api-00145-tax` (100% plus retained tags), all three worker images `intent-only-65e9cd3ae9`; Vercel READY `dpl_8njxByesgVJWBbuhnpvssyuTxMcU` actually assigned to `https://app.planebyte.com`. Source65e9cd3. Production health200,15 expected signed smoke results,7 additional setup/context/report reads, public auth/assets/redirect checks passed; zero new API ERROR entries in bounded04:30–04:48UTC window. One actual Vertex report job3f715… completed with10citations, persisted/save/export/replay acceptance. Browser interaction was stopped; fresh authenticated production visual/login acceptance remains pending. Full public paid launch remains closed.

## Exact location and source

Repository `/Users/planebyte/.codex/worktrees/planebyte-public-launch/planebyte-leadgen`, branch `codex/public-launch-20261115`. Released application source `65e9cd3ae998106e268a66f172cb098cd2146410`. Handover documentation is committed afterward; run `git status --short` and `git log -6 --oneline` to identify exact final docs checkpoint. Final API/worker/Vercel revisions and checks are appended in `PLANEBYTE_MASTER_HANDOVER.md`; read that result first.

Owner's independent checkout `/Users/planebyte/Documents/Projects/planebyte-leadgen` was at `15d40b8`, with unrelated untracked marketing directories/scripts/SVGs. Latest owner branding15d/cc/a5 is merged here. Do not overwrite their untracked work or move the launch checkout backward.

## Read before editing

1. Root `AGENTS.md`, `docs/ENGINEERING_STANDARDS_AUDIT.md`, `docs/NEW_MODULE_CHECKLIST.md` and domain standards. Read nearer AGENTS, especially dashboard bundled Next16 documentation before frontend edits.
2. `PLANEBYTE_MASTER_HANDOVER.md`, `PLANEBYTE_COMPLETE_LAUNCH_CHECKLIST.md` and final restricted evidence.
3. `PLANEBYTE_PUBLIC_LAUNCH_DECISIONS_20261115.md`, `PLANEBYTE_LEGAL_OWNER_DECISIONS.md` and the four unpublished legal drafts. Latest owner fixed-term/retention policy overrides older recurring/payment claims.
4. `app/platform/{company_autofill,company_discovery,onboarding_ai,onboarding,company_profiles}.py`, `app/icp/{builder,ai,models}.py`, `app/acquisition/{ai,ai_router,vertex}.py`, `app/platform/provider_usage.py`, `app/intelligence/{jobs,dispatch}.py`.
5. `app/accounts/*`, `app/notifications/*`, `app/billing/{access_periods,fixed_term,payu_v2,trials,ai_accounting,commercial}.py`, migrations48–50, account/fixed-term/privacy tests and shared gateway.
6. `dashboard/auth.ts`, `dashboard/lib/server/{session,env,account-cookies}.ts`, account server actions, auth/Settings/onboarding/Radar components; preserve owner theme/layout.
7. `scripts/{deploy_product_release,build_intent_only_release,deploy_beta_backend,accept_final_product,accept_onboarding_provider,inventory_beta_cleanup}.py`. Some older acceptance scripts hardcode `final-remediation`; do not overwrite previous proof or run old activation scripts blindly.

## Current unfinished work

Real production AI onboarding is **not repaired or accepted**. SyntaxWars website job913bf… READY attempt1; ICP4eb… READY attempt2. Original failure not diagnosed. Exact owner context/jobs in master handover/private metadata; scope all diagnostics to verified owner membership. Never query latest jobs across all tenants.

Confirmed research validation conflict discards AI summaries unless verbatim; modern static crawl/sparse preview quality needs work. Preserve actual source quote/SSRF/robots/content-use defenses. Setup compact conversation/context and3–5 distinct ICPs unfinished; current maximum3. Durable attempt-event migration51 has **not** been written. Broad ICP safe exception mapping and25s provider timeout are hypotheses, not established first-failure causes.

Resend updated key is valid and secret version1 installed. No actual delivered OTP/recovery acceptance, no active transactional runtime. PayU merchant USD/TestMode/legal KYC unverified; checkout closed. No yearly prices/annual allowance cadence. No public signup or native-ledger production activation. Privacy intake exists; no purge performed. Independent AI/source permission/client/performance gates remain.

Handover-only uncommitted work, if any, must be shown by `git status`; do not assume ignored evidence/backups are source changes. Source65e9 app/frontend hashes match completed tests. Docker47→50 and build-evidence mkdir fix are committed; there is no uncommitted AI implementation to recover.

## Tools, setup and safe checks

Use Node24, not systemNode26. `.venv`, `dashboard/node_modules` and runtime are symlinks to existing owner dependencies; writes there need applicable approval. Do not reinstall/upgrade arbitrarily. No root `.env` exists in launch worktree. Read owner ROOT `.env` only into server process memory when authorized; do not copy it into dashboard or print credentials. Never alter `.env`/OAuth/config without current owner authority.

```sh
cd /Users/planebyte/.codex/worktrees/planebyte-public-launch/planebyte-leadgen
git status --short
git log -6 --oneline
git diff --check
.venv/bin/python -c 'from app.database.migrations import MIGRATIONS; print(len(MIGRATIONS))'
```

Current code schema50. PostgreSQL integration tests require a **disposable** database, never production/backup restore. Local test cluster was recreated after temporary files aged out: binaries `data/artifacts/runtime/postgres187-install/bin`, data `/private/tmp/planebyte-launch-review-pgdata`, socket `/private/tmp/planebyte-billing-pg18`, port15433, unix-only. Test database `billing_acceptance_utf8`; restored customer snapshot `launch50_review_20261116` must not be used by mutating test fixtures. Confirm process/resources before reuse; do not drop/reinitialize existing data.

```sh
# Isolated test database only; inherited root production URL must never be used.
APP_ENV=test DATABASE_BACKEND=sqlite RUN_POSTGRES_TESTS=1 \
DATABASE_URL='postgresql://planebyte@/billing_acceptance_utf8?host=/private/tmp/planebyte-billing-pg18&port=15433' \
HEYSOW_PG_TEST_BIN='/Users/planebyte/Documents/Projects/planebyte-leadgen/data/artifacts/runtime/postgres187-install/bin' \
.venv/bin/python -m pytest tests -q

cd dashboard
/Users/planebyte/Documents/Projects/planebyte-leadgen/data/artifacts/runtime/node-v24.22.2-darwin-x64/bin/node node_modules/typescript/bin/tsc --noEmit
/Users/planebyte/Documents/Projects/planebyte-leadgen/data/artifacts/runtime/node-v24.22.2-darwin-x64/bin/node node_modules/vitest/vitest.mjs run
```

For production-style local Next builds, use existing `scripts/local_frontend.cjs build --webpack` under the fixture environment used by acceptance. Turbopack cannot follow the external dependency symlink in this worktree. Required fixture variables/scripts are in `playwright.{accounts,public-launch,public-onboarding}.config.ts` and fixture servers. Generated `next-env.d.ts`/tsconfig build-directory entries can change; restore **only generated changes** from current HEAD after build, never owner source. No overlapping builds sharing a dist directory.

## Deployment/logs/rollback commands

Google CLI `data/artifacts/tooling/google-cloud-sdk/bin/gcloud`593.0.0, official archive hash `108c1a0bb5d273703b61c4dc9cafab9cc0e674797347ab18d5357d228a517131`. Set `CLOUDSDK_PYTHON` to the existing Python3.12 runtime. Gcloud logs write outside worktree, so approval may be required. Preserve existing authenticated account; do not create OAuth keys.

```sh
export CLOUDSDK_PYTHON=/Users/planebyte/Documents/Projects/planebyte-leadgen/.venv/bin/python
export PLANEBYTE_RELEASE_EVIDENCE=public-launch/final
export PLANEBYTE_OPERATOR_ENV_FILE=/Users/planebyte/Documents/Projects/planebyte-leadgen/.env

# Read-only frozen gate and smoke; never enable mail/payments/signup here.
.venv/bin/python -c 'from scripts.deploy_product_release import gate; print(gate())'
.venv/bin/python -m scripts.deploy_product_release smoke

# Only for a new committed, fully tested release under applicable authorization:
# .venv/bin/python -m scripts.build_intent_only_release
# .venv/bin/python -m scripts.deploy_product_release stage
# Perform real bounded staged functional acceptance and inspect private proof.
# .venv/bin/python -m scripts.deploy_product_release promote
```

Frozen gate source hashes intentionally fail after product changes; run genuine checks and write new evidence instead of editing hashes/counts to bypass tests. Existing accepted release test count1144/frontend181, product10/account1/setup2. Docs-only commit differences do not imply a different running application.

Read Cloud Logging with bounded exact revision/job/time filters; print only safe severity/error types/correlation metadata, not raw prompts, tokens, URLs with credentials or SQL rows. Existing command wrapper captures/redacts errors. API GET health unauthenticated; private API uses real server-side signed actor/workspace resolution. Do not add auth bypasses.

Rollback: use `data/backups/product-65e9cd3ae9/*-before.json` and final exact record. Restore previous API traffic and all affected job image references **without altering unrelated env/secrets/schedulers**. Vercel previous source15d40b8 deployment `dpl_2QjNxMpKmHBszB3mshTZyWaUZvXF` can be promoted if the new frontend fails. Verify signed health/read checks after rollback. Production stays schema46 in this wrap-up; after a later50 migration old7eb is not a valid cold-start rollback. Never undo release by wiping/restoring stale production data.

Vercel existing team `team_wYIkjGUus2DtSgRualzW0kge`, project `prj_xT1PDDXHTYsjdHgI776MQtLzFPZb`, scope `piyushagrawal6s-projects`, rootDirectory`dashboard`. CLI `/Users/planebyte/.nvm/versions/node/v26.13.0/bin/vercel` run via Node24. Exact committed frontend archive staged at `data/artifacts/staging/vercel-65e9cd3ae9`; no `.env`/dependencies/build output uploaded. Candidate uses `--prod --skip-domain`, then verified promotion. Never redeploy Netlify marketing as part of SaaS release.

## Infrastructure configuration and secret names

Existing server secrets include `leadengine-database-url`, `leadengine-resend-key:1` and integration/HMAC/Google/AI/PayU secret references recorded privately in runtime snapshots. Confirm actual names from Cloud Run references; do not guess new secret names or rotate working credentials. Vercel/Netlify existing secrets are platform-owned; Netlify write-only values cannot be recovered through normal reads.

Required variable groups, **names only**:

- Core: `APP_ENV`, `DATABASE_BACKEND`, `DATABASE_URL`, `LEADENGINE_API_URL`, `LEADENGINE_API_SIGNING_SECRET`, `AUTH_SECRET`, `AUTH_URL`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `ALLOWED_USER_EMAILS`.
- New account/access: `HEYSOW_ACCOUNTS_ENABLED`, `HEYSOW_ACCESS_PERIODS_ENABLED`, `HEYSOW_CUSTOMER_ACCESS_ENABLED`, `HEYSOW_PUBLIC_REGISTRATION_ENABLED`, `HEYSOW_INVITED_REGISTRATION_ENABLED`, `HEYSOW_GOOGLE_ADMISSION_CLIENT_ID`, `HEYSOW_TERMS_VERSION`.
- Email: `TRANSACTIONAL_MAIL_ENABLED`, `TRANSACTIONAL_MAIL_DAILY_LIMIT`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_WEBHOOK_SECRET`, `HEYSOW_INTEGRATION_ENCRYPTION_KEY`.
- AI/setup: `HEYSOW_COMPANY_DISCOVERY_ENABLED`, `HEYSOW_COMPANY_AI_ENABLED`, `HEYSOW_ICP_AI_ENABLED`, `HEYSOW_LEAD_ASSISTANT_ENABLED`, `AI_PROVIDER`, `AI_PRIMARY_PROVIDER`, `VERTEX_AI_ENABLED`, `VERTEX_AI_PROJECT_ID`, `VERTEX_AI_LOCATION`, `VERTEX_AI_MODEL`, `GEMINI_API_ENABLED`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `AI_FALLBACK_ENABLED`, `AI_MODEL_PRICING_JSON`; exact bound fields in current settings.
- Payments: `FIXED_TERM_BILLING_ENABLED`, `PAYU_ONE_TIME_CHECKOUT_ENABLED`, `PAYU_MODE`, `PAYU_MERCHANT_KEY`, `PAYU_MERCHANT_SALT`, `PAYU_CHARGE_CURRENCY`, `PAYU_MERCHANT_CAPABILITIES_JSON`, `PAYU_CURRENCY_APPROVED`, `PAYU_TAX_POLICY_JSON`, `PAYU_YEARLY_PRICES_JSON`, `BILLING_TERMS_VERSION`, legacy `BILLING_PUBLIC_CHECKOUT_ENABLED`.
- Product/source/API: `INTENT_RADAR_STAGE`, `INTENT_RADAR_GROWTH_ENABLED`, `INTENT_RADAR_AI_ENABLED`, `INTENT_RADAR_SCHEDULES_ENABLED`, `INTENT_RADAR_MIN_SCHEDULE_HOURS`, `INTENT_RADAR_STACKEXCHANGE_ENABLED`, `INTENT_RADAR_STACKEXCHANGE_KEY`, `INTENT_RADAR_STACKEXCHANGE_SITES`, `INTENT_RADAR_APPROVED_FEED_HOSTS`, `HEYSOW_DEVELOPER_API_ENABLED`, `HEYSOW_MCP_ENABLED`, `MCP_ALLOWED_HOSTS`, `MCP_ALLOWED_ORIGINS`, `HEYSOW_WEBHOOKS_ENABLED`.
- Preserve false: `LEAD_ENGINE_AVAILABLE`, `LEAD_ENGINE_PUBLIC_ENABLED`, `AUTO_SCAN_ENABLED`, `AUTO_EMAIL_ENABLED`, `EMAIL_SENDING_ENABLED`, customer mail/live-approval flags and unverified registration/payment flags. Optional values/defaults are not automatically missing credentials.

## Next 10 prioritized tasks and acceptance criteria

1. **Reconcile final actual release first.** Read final source/revisions/checks; compare current owner Git and production metadata. Do not rerun completed jobs or overwrite evidence. All live resources must match intended source or documented safe rollback.
2. **Diagnose first SyntaxWars ICP failure.** Read only exact workspace+verified owner+job attempt/provider logs; preserve profile. Establish stage/type/duration/root cause, not timeout speculation. Add durable safe attempt history only with versioned recovery-tested migration if required.
3. **Fix actual website research quality.** Evidence-grounded summary/interpretation contract, meaningful preview threshold and permitted modern-content fallback; bounded SSRF/robots/claim guards remain. Test representative sites and actual SyntaxWars without hardcoding.
4. **Complete reliable ICP and contextual assistant.** Real1–3 minimum useful distinct candidates first; consistent3–5 expansion if still required; helpful saved/draft conversational context, exact source citations/assumptions, compact mobile UI, safe retries. No synthetic provider success accepted as live proof.
5. **Complete actual Resend transactional acceptance.** Reuse installed key, confirm IAM/runtime/from/Svix; only connected authorized owner mailbox normal OTP→verify and recovery→reset on disposable identity. Record provider acceptance **and inbox receipt**, token/session revocation; never print OTP/key.
6. **Verified legal publication and retention readiness.** Obtain legal contracting identity/address from real KYC/business record; no invented entity. Existing7day refund/30day closure/90day backup policies already owner-approved; do not ask again. Validate operational processes, publish/version approved four pages.
7. **Safe account/schema rollout and genuine new-customer journey.** Fresh backup+restore, schema46→50 preservation, compatible rollback, account/mail/native flags under gates. Two-workspace absent/revoked/foreign denial; verified work-email or real Google→onboarding→assistant→dashboard, exact approved trial. Only then open signup.
8. **PayU merchant evidence and Test Mode.** Existing logged-in dashboard/live key is not USD proof. Verify actual account USD/international/settlement/KYC/TestMode credentials without changing financial products. Do not require GSTIN. Genuine test callback/server verification/idempotent native fulfillment/history/expiry/refund reconciliation; no real charge/refund without separately approved amount/action.
9. **Paid launch business/quality/source approvals.** Monthly approved30days/manual renewal; yearly disabled pending prices/cadence. Validate commercial hosting contract, permitted sources, independent AI evaluation and customer integrations/named MCP where promised. Open only verified paid scope; do not advertise absent adapters.
10. **Final acceptance and operations.** Full isolated tests/build/recovery, mobile/light/dark with genuine providers, bounded latency/error/alert/worker checks, release rollback drill; update both handover/checklist with actual evidence. Preserve all Lead Engine code/tables/data and every newer UI improvement.

Public signup and paid checkout remain separate activation decisions. No real charge/refund/mandate, unsolicited customer email, global product grant, production data reset, destructive migration or deletion is authorized by a continuation alone.

## Actual retained production secret references (names only)

The release retained these existing Cloud Run Secret Manager names. `leadengine-resend-key:1` exists separately and is **not yet bound** to these runtime inventories. No credential values are recorded.

- `leadengine-acquisition-auth-google-secret`
- `leadengine-acquisition-firecrawl-api-key`
- `leadengine-acquisition-gemini-api-key`
- `leadengine-allowed-users`
- `leadengine-api-signing`
- `leadengine-database-url`
- `leadengine-gmail-app-password`
- `leadengine-integration-encryption-key`
- `leadengine-mail-password`
- `leadengine-payu-merchant-key`
- `leadengine-payu-merchant-salt`
- `leadengine-r2-bucket`
- `leadengine-r2-endpoint`
- `leadengine-r2-key`
- `leadengine-r2-secret`
- `leadengine-razorpay-test-key-id`
- `leadengine-razorpay-test-key-secret`
- `leadengine-razorpay-test-webhook-secret`
- `leadengine-upstash-redis-rest-token`
- `leadengine-upstash-redis-rest-url`

Existing API environment names (snapshot, values withheld; worker-specific inventories in `final/staged-runtime-inventory.json`):

`ACQUISITION_CLOUD_RUN_JOB`, `AI_FALLBACK_ENABLED`, `AI_PRIMARY_PROVIDER`, `AI_PROVIDER`, `ALLOWED_USER_EMAILS`, `APP_ENV`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `AUTOMATION_TIMEZONE`, `AUTO_EMAIL_ENABLED`, `AUTO_SCAN_ENABLED`, `BILLING_ENABLED`, `BILLING_PROVIDER`, `BILLING_PUBLIC_CHECKOUT_ENABLED`, `BILLING_TEST_MODE`, `BILLING_TEST_WORKSPACES`, `DAILY_EMAIL_TARGET`, `DAILY_QUALIFIED_LEAD_TARGET`, `DATABASE_URL`, `DEFAULT_FOLLOWUP_DAYS`, `EMAIL_INITIAL_SYNC_DAYS`, `EMAIL_LIVE_APPROVED`, `EMAIL_PROVIDER`, `EMAIL_SENDING_ENABLED`, `EMAIL_SEND_MODE`, `EMAIL_SYNC_ENABLED`, `EMAIL_SYNC_INTERVAL_MINUTES`, `EMAIL_TEST_RECIPIENT`, `EMAIL_TRACKING_BASE_URL`, `EMAIL_TRACKING_ENABLED`, `ENABLE_AI_ACQUISITION`, `ENABLE_FIRECRAWL_ACQUISITION`, `ENABLE_GOOGLE_SHEETS_IMPORT`, `ENABLE_LEAD_IMPORT`, `ENABLE_PRE_OUTREACH_ANALYSIS`, `FIRECRAWL_API_KEY`, `FIRECRAWL_API_URL`, `GCP_PROJECT_ID`, `GCP_REGION`, `GEMINI_API_ENABLED`, `GEMINI_API_KEY`, `GEMINI_COPY_BATCH_SIZE`, `GEMINI_MODEL`, `GMAIL_APP_PASSWORD`, `GMAIL_ENABLED`, `GMAIL_IMAP_HOST`, `GMAIL_IMAP_PORT`, `GMAIL_IMAP_SECURE`, `GMAIL_SMTP_HOST`, `GMAIL_SMTP_PORT`, `GMAIL_SMTP_SECURE`, `GMAIL_USERNAME`, `GOOGLE_SHEETS_REDIRECT_URI`, `HEYSOW_COMPANY_AI_ENABLED`, `HEYSOW_COMPANY_DISCOVERY_ENABLED`, `HEYSOW_CUSTOMER_ACCESS_ENABLED`, `HEYSOW_CUSTOMER_GMAIL_ENABLED`, `HEYSOW_CUSTOMER_GMAIL_REDIRECT_URI`, `HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED`, `HEYSOW_CUSTOMER_MAIL_LIVE_APPROVED`, `HEYSOW_CUSTOMER_MAIL_SENDING_ENABLED`, `HEYSOW_DEVELOPER_API_ENABLED`, `HEYSOW_ICP_AI_ENABLED`, `HEYSOW_INTEGRATION_ENCRYPTION_KEY`, `HEYSOW_INTERNAL_EXPERIMENTS_ENABLED`, `HEYSOW_INVITED_REGISTRATION_ENABLED`, `HEYSOW_LEAD_ASSISTANT_ENABLED`, `HEYSOW_MCP_ENABLED`, `HEYSOW_PUBLIC_REGISTRATION_ENABLED`, `HEYSOW_WEBHOOKS_ENABLED`, `HEYSOW_WORKSPACE_MANAGEMENT_ENABLED`, `INTENT_RADAR_AI_DAILY_CALLS`, `INTENT_RADAR_AI_DAILY_TOKENS`, `INTENT_RADAR_AI_ENABLED`, `INTENT_RADAR_GROWTH_ENABLED`, `INTENT_RADAR_MIN_SCHEDULE_HOURS`, `INTENT_RADAR_SCHEDULES_ENABLED`, `INTENT_RADAR_STACKEXCHANGE_ENABLED`, `INTENT_RADAR_STAGE`, `LEADENGINE_API_SIGNING_SECRET`, `LEADENGINE_CLOUD_RUN_JOB`, `LEADENGINE_ROLE`, `LEAD_ENGINE_AVAILABLE`, `LEAD_ENGINE_PUBLIC_ENABLED`, `LEAD_QUALIFICATION_MODE`, `LIGHTHOUSE_ENABLED`, `MAIL_FROM_ADDRESS`, `MAIL_FROM_NAME`, `MAIL_IMAP_HOST`, `MAIL_IMAP_PORT`, `MAIL_IMAP_SECURE`, `MAIL_PASSWORD`, `MAIL_SIGNATURE_NAME`, `MAIL_SIGNATURE_ROLE`, `MAIL_SMTP_HOST`, `MAIL_SMTP_PORT`, `MAIL_SMTP_SECURE`, `MAIL_USERNAME`, `MAX_ACTIVE_SCANS`, `MAX_CITIES_PER_SCAN`, `MAX_EMAILS_PER_DAY`, `MAX_EMAILS_PER_HOUR`, `MAX_LIGHTHOUSE_AUDITS`, `MAX_RAW_BUSINESSES`, `MAX_SCAN_RUNTIME_MINUTES`, `MAX_TARGET_LEADS`, `MCP_ALLOWED_HOSTS`, `MCP_ALLOWED_ORIGINS`, `OUTREACH_SENDER_NAME`, `OUTREACH_SENDER_ROLE`, `PAYU_BILLING_ENABLED`, `PAYU_MERCHANT_KEY`, `PAYU_MERCHANT_SALT`, `PAYU_MODE`, `PLANEBYTE_COMPANY_NAME`, `PLANEBYTE_CONTACT_EMAIL`, `PLANEBYTE_WEBSITE`, `R2_ACCESS_KEY_ID`, `R2_BUCKET_NAME`, `R2_ENDPOINT`, `R2_SECRET_ACCESS_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_MODE`, `RAZORPAY_WEBHOOK_SECRET`, `SCAN_EXECUTOR`, `UPSTASH_REDIS_REST_TOKEN`, `UPSTASH_REDIS_REST_URL`, `VERTEX_AI_ENABLED`, `VERTEX_AI_LOCATION`, `VERTEX_AI_MODEL`, `VERTEX_AI_PROJECT_ID`.
