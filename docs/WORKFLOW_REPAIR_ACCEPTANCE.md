# Current owner acceptance request (2 November 2026, Asia/Kolkata)

Prioritize: limits saving, scheduled acquisition, Run Emails, then full offline/browser/isolated PostgreSQL workflow regression. Phase 4.9 remains in progress; do not declare it complete.

After acceptance passes, owner explicitly authorized:

- Configure daily qualified target 500, daily email target 500, hourly maximum 50, daily maximum 500, follow-up 3 days, Asia/Kolkata.
- Create and validate a rollback backup, then clear operational prospect/campaign/run/report/email data and schedule definitions for a fresh start.
- Preserve Gmail/auth/security/configuration/markets/infrastructure and consent/bounce suppression protections.
- Do not start the next real campaign; owner will create it.

## Findings

- Production limits endpoint only accepted 10/hour and 100/day, whereas the screenshot requests 50/hour and 500/day. UI hid structured validation errors.
- Schedule Run Now did not retain `schedule_id`, so it lost scheduled delegation/automatic outreach semantics.
- Combined schedule dispatch unnecessarily required email capability before starting acquisition. Acquisition should respect scan controls and hold the email stage separately.
- Globally paused QA controls were not shown as a blocked schedule reason. Recent production schedules were all soft-deleted by the owner; Run Now produced an unlinked manual combined run.
- The earlier US hospitality campaign has 15 manual-contact and 4 needs-review leads, zero ready emails. This is not a sendable audience; UI must explain that without a generic error.

## Deployment access

Owner reauthenticated this Mac. Cloud Run read access and IAM checks for build, deployment, scheduler access and Secret Manager creation/version upload now pass. No service-account keys created.

## Safety

Production DB controls are scan_paused=1 and email_paused=1. Austin workflow d6261946-c609-4962-a6ea-84a7f33ebd48 was paused; Denver scan 4 received cancellation. No prospect emails sent by these repair actions.

Root Upstash variables are present; synthetic PING/write/read/delete acceptance passed. Credentials never printed. Caching implementation is local until deployed.

## Pending final actions

Complete regression, fix failures, browser acceptance, isolated PostgreSQL checks, Linux exact-lock build, authenticated deployment, signed production smoke. Only then apply requested settings and create/verify backup + authorized operational cleanup. Record exact zero counts and preserved configuration. Invalidate read caches after cleanup. Do not run the stale schema-9 clean-start script unchanged.

## Verified repair release (2 November 2026)

- Linux exact-lock API suite: 345 passed, 10 intentionally skipped (live SMTP and opt-in PostgreSQL). Frontend: 43 unit tests; production build passed; 17 distinct browser checks passed across the full run and corrected-locator rerun. Authentication, shared campaign fixture, pagination, previews, schedule history, bounded preparation, responsive layouts and actual authenticated limits save/reload covered.
- Disposable PostgreSQL: repository/history/delete/target storage/session lock plus campaign migration/accounting/schedule checks passed. The queue-recovery test passed alone (172.59 seconds); concurrent migration tests previously contended on the global migration lock and timed out. No production data was modified by integration fixtures.
- New limits: mocked SMTP proves 50/hour, 500/day and exactly 72-second spacing, including duplicate ticks, failure pause and restart recovery. Lower workspace/run ceilings still apply.
- Schema 11 checkpoint: `data/backups/foundation-schema11-20261102T054954Z.zip`, all 54 table copies restored and count-verified. One additive migration applied; schema 12 and existing data/pause controls verified. Initial preservation checker incorrectly included migration-history count; corrected and verification rerun without another migration.
- Frontend deployed: `dpl_7BpyCx3LwrCVG7HXXQzxM5KcRRiC`, alias `https://leads.planebyte.com`.
- First API revision `leadengine-api-00032-w94` exposed a PostgreSQL wildcard-placeholder error in the new review query. Corrected query was verified read-only against production PostgreSQL; a small image patch is being validated before final acceptance.
- Redis production cache works: dashboard miss 7,609 ms; subsequent authenticated hits 1,694 and 1,463 ms. All requests reauthenticate; no email send/suppression/preview decisions cached. Response cache credentials are server-only Secret Manager references.
- Three automation flags false on API/worker/root. DB scan/email pauses retained. No prospect contacted.
- Full operational rollback snapshot including private R2 artifacts is being restore-verified. Cleanup and final 500/500/50/500 settings are still pending successful final smoke.

## Final controlled acceptance and owner clean start

- Final patch build `ceaf4232-8ccd-42c8-bf1a-df0817ae0735`: **346 passed, 11 skipped** on exact production Linux dependencies. The additional skipped check is opt-in PostgreSQL. The missing new operator file in the first patch image was corrected before this successful build.
- Final API patch `leadengine-api-00033-2c2`: all seven signed review/quality/country/group/settings/health/safety smoke reads returned 200. Later settings-only API revision retains this same image.
- Real deployed Cloud Run dispatch execution `leadengine-worker-jv4wp` succeeded with all flags false and both controls paused; no discovery or email was started.
- Production Redis: MISS → HIT confirmed, and an authenticated save of unchanged targets produced MISS → HIT again. Latest observed dashboard hit 1,380 ms versus 7,534 ms uncached. Only one production allowlisted account exists, so cross-actor isolation is covered by the unit suite rather than fabricating another production identity. Safety decisions are not cached.
- Owner limits applied and read back from API/worker/root/persisted settings: qualified target 500, email target 500, hourly maximum 50, daily maximum 500, follow-up 3 days, Asia/Kolkata. Two preexisting duplicate root limit entries were removed, preserving effective values.
- Full rollback archive `data/backups/owner-final-clean-start-20261102T060818Z.zip`: SHA-256 `a59cba6a789f930227d24ff2a0ad2c008c10b0e77915a74a066ea930c524583d`; all 70 tables restored/count-verified, 11 private artifact bytes hash-verified. Private archive/state are ignored by git and mode 0600.
- Owner-authorized reset completed. Master Leads, qualified/business observations, queues, prospect threads/messages, campaigns and schedules are zero. Old private artifacts removed only after backup verification. Schema 12, migration history, Gmail/auth/settings, market definitions, security, infrastructure, Redis secrets and suppression protections preserved. Market scan statistics reset; configured market priorities/enabled state/cooldowns retained. Sequence identities continue to prevent stale URLs referring to new records.
- Three automation flags remain false; both DB pauses remain set, `next_send_at` cleared. No fresh campaign or schedule created. No real prospect was contacted during QA.
- Broader Phase 4.9 follow-ups remain in `PHASE49_IMPLEMENTATION.md`; this repair/clean-start acceptance does not claim the entire foundation phase complete.

Machine-readable evidence: `workflow-repair-acceptance-20261102.json`; final post-reset production checks: `owner-final-clean-start-20261102.json`.

## Subsequent owner-authorized production activation — 2 November 2026

The owner changed all three root flags to true and explicitly requested production outbound/outreach activation. After GCP access was restored, existing API and worker environment flags were updated to true without rebuilding images, migrations or Gmail changes. API revision `leadengine-api-00035-g7j` receives production traffic. Both database operator pauses were removed; the stale `OWNER_FRESH_START` reason was cleared only when both controls were unpaused. Workspace limits remain 50/hour, 500/day, qualified target 500/day, follow-up 3 days, Asia/Kolkata. Acquisition, outreach and inbox-sync schedulers are enabled; successful last invocation metadata verified. The obsolete duplicate `leadengine-email-sync` scheduler remains paused. No new user campaign or schedule was created by the activation operator, and no test email was sent. The earlier disabled-state clean-start records remain historical checkpoints. Activation evidence: `production-outreach-activation-20261102.json`.
