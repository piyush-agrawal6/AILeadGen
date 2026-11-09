# HeySow stabilization report — 2026-11-05

Status: **IN PROGRESS — NOT COMPLETE — PRODUCTION RELEASE BLOCKED**.

## Preservation and checkpoint

Work began on the existing `main` checkout, retaining every prior change. The two
latest commits are `a23b937` and `d009e5f`; no commit, reset, stash or destructive
Git command was used. A restricted local checkpoint was created at
`/private/tmp/heysow-recovery-checkpoint-20261105T112616Z` with 793 source/document
files, hashes, archive-integrity verification and the original Git status.
Environment files and credentials were excluded. This is a source checkpoint,
not a production database backup.

No production data, infrastructure, OAuth, DNS or environment file was modified.
No real email was sent. Public registration remains unavailable. Existing
Vertex-first provider architecture, transport adapters and permanent history
were retained. No new product module, billing integration or paid service was added.

## Baselines and causes

Original report: **347 passed, 70 failed, 70 errors, 15 skipped**.
Recovery reproduced **347 passed, 72 failed, 70 errors, 15 skipped**. All original
140 failing/error test IDs were reproduced; two newer ownership checks exposed
two additional failures. `HEY SOW_REGRESSION_TRIAGE.md` enumerates these cases,
root-cause categories, dependencies, proposed repair and latest status.

Independent causes included missing owner propagation, historical fixture
contracts, a nonexistent users.created_at column, unowned acquisition campaigns,
the shared_settings singleton constraint, global mailbox/registry assumptions,
identity alias collisions, positional SQL after additive migrations, unscoped
reconciliation, an undefined deletion scope variable, separate databases inside
an authentication fixture and historical experiment availability assumptions.
They were not all attributed to missing organization context.

## Implemented repairs

1. Added explicit membership-backed request/job scopes with no tenant default.
   Removed automatic test workspace provisioning from request handling, global
   primary-owner shortcuts and legacy owner-role fallbacks. Revoked membership
   fails authorization, including reads and cache access.
2. Persisted acquisition job/campaign/run ownership and validated existing company,
   run and campaign links. Existing contact-evidence reuse is workspace-scoped.
3. Namespaced newly written identity aliases by workspace while retaining scoped
   historical alias lookup. Independent workspaces can rediscover the same company
   without alias collision or cross-workspace merging.
4. Restricted internal mailbox connection, preview, sync and sending to its owning
   workspace. Customer account status is accurately NOT_CONFIGURED. Worker inbox
   sync validates the persisted account owner. Reply and DSN lookup/contact
   invalidation now include workspace ownership.
5. Scoped permanent contact recording, engagement updates, usage, sales services,
   workflow lookups, report creation and deletion entry points. Public tracking
   uses a verified stored capability that cannot authorize mailbox access.
6. Scoped reconciliation and dispatch to explicit organizations; creator membership
   is rechecked. New Master Lead states and qualification activities retain owners.
7. Added migration 17 for organization-keyed settings, copying the old configuration
   and retaining the legacy table. Updated runtime settings consumers. Fixed user
   creation to use an existing column and report linkage to check persisted data.
8. Updated owned fixtures to pass explicit organization IDs, use real memberships,
   preserve old-schema SQL snapshots and exercise archived behavior only explicitly.
   No tests were removed and no production authorization was relaxed.

## Files and database changes

`HEYSOW_STABILIZATION_CHANGED_FILES.json` inventories recovery changes against the
checkpoint. Principal files are `app/platform/context.py`, acquisition/service and
worker code, canonical prospect repositories, API membership/permissions, mail
service/registry/tracking/bounces, workflow/reconciliation, report/deletion services
and `app/database/workspace_settings_schema.py`. Focused tests are in
`tests/unit/test_heysow_stabilization.py`, with explicit fixture support in
`tests/workspace_fixtures.py`.

Migration 17 is additive and has only run against isolated test databases. Old
rows/tables and migration history are retained. The historical schema-8 tracking
backfill is restricted to its pre-8 migration context so modern runtime membership
services are not called before their schema exists. See `MIGRATIONS.md` for safety
and recovery requirements. No production reset, truncation or migration occurred.

## Security and regression evidence

- Membership, missing-context, revoked-primary-owner, nested cross-tenant scope and
  API mutation/VIEWER-denial tests were added.
- Registry override denial, independent address histories, internal Gmail isolation,
  workspace identity stability and persisted job-owner checks were added.
- Migration preservation checks retain historical DNC, sent counts and opt-out flags.
- The focused security/mail/authentication set passed 80 tests before migration 17;
  the subsequent settings/migration/mail subset passed 68, and the registry/report
  subset passed 16. These overlap and must not be added together as a unique count.
- Frontend unit tests: **49 passed**. Type checking: **PASS**. Production frontend
  build with isolated dummy auth values: **PASS**. Auth browser tests: **3 passed**.
- Browser tests initially could not bind the loopback port under restricted execution;
  an approved local execution passed. No production endpoint was load-tested.

The full current-checkout result is recorded below and in
`HEYSOW_STABILIZATION_TEST_RESULTS.json`.
No focused pass overrides a failing full-suite result.

## Remaining blockers and next stage

The address-keyed suppression table is still a legacy internal-mailbox model, not
an approved general customer-mailbox schema. Current callback/thread, migration-fixture and archived workflow regressions
have been repaired and pass. Remaining ancillary owner persistence still needs
a complete path audit. Query-count regressions must be optimized,
not hidden by raising thresholds. PostgreSQL tests require a dedicated local test
server; no local PostgreSQL/Docker command was available, and production credentials
must not be substituted. The live send acceptance is intentionally excluded.

Do not enable public registration or deploy this checkout. The next stage remains
**stabilization**, not the SaaS roadmap: finish every remaining case in the triage,
complete the scoped data-path audit, validate migration 17 on isolated PostgreSQL,
then rerun backend/frontend/browser/build checks. Public signup, billing, CRM,
MCP and Agent work remain out of scope.


## Frozen backend verification

**499 passed, 0 failed, 0 errors, 15 skipped** in 144.35 seconds. All original
140 failing/error cases and both additional reproduced ownership failures now
pass. The 14 PostgreSQL checks remain unexecuted because no dedicated local
PostgreSQL server is configured. The single live-email acceptance remains
intentionally skipped under the no-send instruction. One existing Starlette/httpx
deprecation warning remains; it is not an authorization or integrity failure.

This replaces intermediate 70/70, 70/15, 41/6 and 30/1 results. The test fixtures
now establish actual memberships and correct owned rows rather than bypassing
security. Queue cap, spacing, restart and simultaneous-dispatch cases pass with
mocked SMTP; a corrected async fixture resets its scope in the same task.

Additional repairs completed during regression work: shared read-only dashboard
service extraction, ownership on incoming reply rows, schedule upsert ownership
protection, scoped historical template seeds, explicit historical migration
fixtures and safe deletion parameter handling. Default-denied archive preparation
is preserved. Migration 16→17 copy/legacy preservation/FK/repeatability also passed
in a separate isolated database check.

Remaining work is verification and residual-path auditing, not failing backend
regressions: validate isolated PostgreSQL, finish the broader browser workflow
check and certify remaining ancillary/integration ownership paths. No production
deployment or public registration approval is implied.


## Broader browser verification — release still blocked

The 26-test workflow browser suite was run locally with disabled acquisition,
SMTP and inbox sync, dummy session secrets and a fresh isolated database. It was
bounded to stop after three failures: **9 passed, 3 failed, 14 not run**. The runner
also reports one non-test shutdown error; its log is retained locally. This is
not a passing end-to-end suite. The separate three authentication browser checks
remain passing.

- `acceptance.spec.ts` unauthenticated protection case still selects “Sign in with
  Google”; the redesigned real button is “Continue with Google”. Update the
  locator while retaining session, API 401 and CSP assertions.
- The shared campaign case exposes a real remaining integration defect:
  `/api/foundation/roles` still writes legacy `account_roles`, while authorization
  now correctly relies on `organization_memberships`. The second user remains
  unauthorized. Repair scoped membership management, preserve owner protections
  and add API regression coverage; do not restore global-role fallback.
- `contactable.spec.ts` expects the archived Outreach Results screen to be enabled
  by default. Replace that outdated contract with default-denial coverage and
  explicit internal archive acceptance. Do not re-enable it for customer use.

The 14 unexecuted browser cases must run after these repairs. Along with dedicated
PostgreSQL validation and residual-path auditing, these findings keep this task
and production release **NOT COMPLETE**. No production change or email was made.


## Subsequent foundation verification — 2026-11-05

The earlier 9-pass/3-fail browser result is historical. Scoped role management was
repaired and outdated UI/archive contracts were updated while retaining access
checks. All **26 existing workflow browser tests now pass**. The separate **3 auth
browser checks** and **6 gated workspace browser checks** also pass. Frontend units
pass **60**, and the production build with fixture settings passes.

The last completed full backend run is **530 passed, zero failures/errors, 15
skipped**. Later focused concurrency/migration/configurable-limit/typed-contract
checks pass; the next full frozen run is recorded separately after completion.
New gated foundations include creation/selection, company/personal profiles and
hashed invitations. Public signup, complete onboarding, PostgreSQL validation and
the remaining SaaS phases still block release. No production configuration, data,
sends, acquisition or infrastructure was changed.
