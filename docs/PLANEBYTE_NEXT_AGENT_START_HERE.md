# PlaneByte — next agent start here

Current checkpoint:16 November2026. **Resume; do not restart or repeat completed repairs.** Read this, the master handover, complete checklist and launch verification report. Prior versions are retained in `archive/20261116-before-ai-repair/`.

## Current production

- Backend source `dbfe6a6148a3c057770b69fb4971c28a6fd3d519`; API `leadengine-api-00151-tij`,100% customer traffic; all three worker images `intent-only-dbfe6a6148`.
- Frontend `64e9f0bada442c1e2c3bf2c7178601ffccc0c1cc`; `dpl_8wWL8WssS7nfp9s2VcuS1t56DXE6`; actual https://app.planebyte.com alias verified.
- Production PostgreSQL **51**, source migrations51. Five migrations applied; second0; no row loss. Do not rerun recovery/migration as though production were46.
- Transactional Resend and setup diagnostics **on and genuinely verified**. Native accounts/access-period admission, public signup, unverified PayU checkout and unrelated sending remain off.
- Backend1,153passes/one explicit live-mail skip; frontend181passes; local product10/onboarding2/accounts1;12 deployed guest theme/mobile screenshots and real Google handoff. Authenticated fresh callback/new-customer flow remains unverified.
- Restricted current evidence: `data/artifacts/verification/onboarding-repair-20261116/`. Older `public-launch/final/` evidence is historical and must not be overwritten.

## First actions

1. Inspect current Git/owner checkout and actual live resource metadata before touching code. Documentation-only commits after the source SHAs are expected.
2. Read `AGENTS.md`, `docs/ENGINEERING_STANDARDS_AUDIT.md` and domain standards. Read the relevant bundled Next docs before frontend changes.
3. Confirm the current source matrix and recorded real acceptance. Do not claim source65e9/API145/schema46 is still current.
4. Preserve all new UI and every Lead Engine file/API/table/history/suppression record. No production reset, broad deletion, real charge/refund/mandate or unsolicited outreach is authorized.

Owner checkout `/Users/planebyte/Documents/Projects/planebyte-leadgen` remains at15d40b8 with unrelated untracked marketing work. Do not reset it or stage its files. Active release checkout is `/Users/planebyte/.codex/worktrees/planebyte-public-launch/planebyte-leadgen`, branch `codex/public-launch-20261115`.

## Do not repeat completed work

- Company grounded paraphrase/meaningful-preview/static metadata extraction repairs.
- Consistent3–5 distinct ICPs, reviewed save, compact draft/saved/follow-up setup assistant.
- Durable schema51 stage/attempt diagnostics; actual Vertex events recorded.
- Canonical company/offering research context, truthful fallback cache, unique-source report citations, measured7,000 combined output-token budget.
- Existing Resend key/domain/secret installation, runtime binding and real production worker/Svix delivery. Do not ask for a new Resend key.
- Fresh backup/isolated restore and actual46→51 migration.
- Final source builds, controlled real onboarding/worker acceptance, backend/frontend deployment and mobile footer/header fixes.

See the ten-part verification report for exact job/message/deployment IDs, limitations and actual historical failure evidence. The first original SyntaxWars ICP validation criterion is irrecoverable; do not invent it or backfill guessed history.

## Remaining work in order

1. **Legal fact/publication:** verified contracting identity/legal form/official address. Existing Terms/Privacy/Refund/Cancellation drafts are complete and unpublished. Refund/cancellation/30-day ordinary deletion/90-day backup targets are already approved; do not ask again.
2. **Fresh customer acceptance:** after approved legal/versioned consent and controlled admission, complete a real Google callback or work-email production signup/OTP/trial/onboarding/profile/ICPs/assistant/dashboard journey. Keep public signup closed until actual isolation, anti-abuse, trial and mail checks pass. Preserve existing authorized Gmail Google users.
3. **Operator capacity:** owner workspace has95,884/100,000 daily tokens reserved.4,116remaining cannot admit a report with7,000output capacity plus input. Retest final-source report/global semantic answer after ordinary UTC reset. Never raise caps, erase counters or refund unknown attempts to force green acceptance. The corrected report contract already passed a real Vertex request outside production in isolated acceptance.
4. **JS-only rendering:** optional code passed a real isolated Chromium network/security test; production flag remainsfalse. Verify the actual non-root Cloud Run sandbox/network fences before enabling, without adding `--no-sandbox` or weakening SSRF/robots checks.
5. **PayU:** owner personally verifies account-specific USD/international/settlement. Obtain distinct Test Mode credentials/capabilities securely from the merchant account; existing live key/salt are already installed. Run genuine sandbox hosted checkout/callback/independent verification/idempotency/history/expiry. No real transaction without separate exact authorization.
6. **Remaining promised scope:** measured latency work, permitted external sources/customer integrations, independent semantic quality and named MCP client acceptance. Keep absent adapters unavailable. Do not confuse old catalog cards or fixtures with working integrations.
7. **Public opening:** follow separate signup and checkout gates in the report. Owner will review commercial hosting before paid launch; current Vercel is explicitly authorized for continued development/deployment. Annual prices/cadence remain unapproved and annual checkout off. No GST collection without verified registration/treatment.

## Safe tools and verification

- Python `.venv` and dashboard dependencies link to the established owner runtime. Node24: `data/artifacts/runtime/node-v24.22.2-darwin-x64/bin/node` via shared runtime path.
- Existing gcloud: `data/artifacts/tooling/google-cloud-sdk/bin/gcloud`; set `CLOUDSDK_PYTHON=/Users/planebyte/Documents/Projects/planebyte-leadgen/.venv/bin/python`.
- Existing server operator configuration is root project `.env`; read securely in process memory using `PLANEBYTE_OPERATOR_ENV_FILE=/Users/planebyte/Documents/Projects/planebyte-leadgen/.env`. Never print/copy/commit secrets or edit `.env`/OAuth credentials without applicable owner authorization.
- Resend refs: `leadengine-resend-key:1`, `leadengine-resend-webhook-secret:1`; sender `PlaneByte <accounts@planebyte.com>`. API/normal worker identities have required access. Actual webhook is enabled; do not accidentally disable it or duplicate/create keys.
- Existing PostgreSQL local cluster is Unix-only `/private/tmp/planebyte-billing-pg18`,port15433. Test DB `billing_acceptance_utf8`; restored production snapshots `beta_restore_*` are **not disposable test databases**. Never run mutating fixtures against production or restored customer snapshots.
- Full backend uses `RUN_POSTGRES_TESTS=1`, `RUN_RENDER_BROWSER_TESTS=1` and the established PG18 binary path. New tests/builds must correspond to actual changed source; preserve archived proof rather than editing hashes to bypass gates.
- Fresh UI verification logs use `frontend-*-final-ui.log`; the final UI is a separate frontend-only commit after deployed backenddbfe. Existing generic release gate snapshots belong to their named source; do not blindly reuse a stale HEAD/source assertion for another release.
- Current bounded operators/acceptance helpers live privately in the verification directory, including `rollout_schema_mail.py`, `accept_final_setup_worker.py`, `accept_production_mail.py`, `accept_live_diagnostics.py` and `accept_public_browser.cjs`. Inspect state/idempotency before rerunning; some create an authorized test workspace/invitation or spend real provider capacity. Do not repeat completed sends/jobs.

## Rollback and data safety

Fresh snapshot: `data/backups/beta-recovery-20261116T071702Z/production.dump`,SHA256 `31bd74ca2c8626755ea98855ce0e242ca0087416ecbda84054f68f09ce053b13`,118,860,123bytes. Restore and51 migration were tested in isolation. Production migration preserved rows. No cleanup/purge occurred.

API flag-off rollback `leadengine-api-00149-luc` was checked on schema51 through https://schema51-rollback---leadengine-api-befca7xg4a-el.a.run.app without moving customer traffic from151. Same source image, mail/diagnostic flags off. Runtime snapshots: `data/backups/product-dbfe6a6148/` and current verification mail snapshots. Never cold-start old65e9 against51 and never restore a stale DB snapshot to undo a code release.

**After any native managed workspace enrollment, preserve access-period enforcement in rollback.** The current flag-off149 configuration is suitable only while native enrollment is empty. Startup verification deliberately prevents enforcement-disabled rollback after enrollment.

Frontend previous `dpl_8qft5cRk9oGjRJRkCz6uh1fX9Xsa` is retained but has the former footer/mobile-header defects. Netlify marketing stays separate and unchanged.

Future agents must report actual source/revisions/traffic, tests, real external acceptance and remaining business/permission/software limits separately. Do not mark paid launch complete from image deployment, fixture passes or a successful provider call alone.
