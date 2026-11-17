# Clean Neon migration — 17 November 2026

Status: production migration complete; controlled owner signup ready for testing.
Verified 17 November 2026 at 04:57 UTC (10:27 IST). The fresh customer journey on
this new production database is deliberately left to the owner, as requested.
The owner explicitly authorized a new empty Intent Radar + Growth Intelligence
database. No customer rows are copied. The existing Neon database and its existing
Secret Manager secret remain the archive/rollback source, with no destructive SQL.

## Schema and verification

The explicit `DATABASE_SCHEMA_PROFILE=intent-radar-v1` lineage contains four
ordered, transactional migrations, versions 1001–1004. These create tables,
keys/indexes, foreign keys, then profile metadata. They do not claim the legacy
1–51 migrations ran on this destination. Startup verifies the exact migration
checksums, profile identity and table inventory. Operator preflight additionally
checks every column, index and constraint against the checked-in manifest and
requires all application tables to be empty. An unrelated existing schema is
rejected before writes. Failed migration batches roll back completely.

The manifest in `app/database/intent_migrations/manifest.json` records 110 required
application tables, their fingerprints, explicit exclusions and dependencies.
Two release-owned metadata tables bring the total to 112. There are no customer
seeds, trial claims, accounts, sessions or purchased entitlements. Approved plans
remain the existing versioned application definitions: Starter $59, Growth $149,
Scale $379; seven-day limited trial; monthly purchases grant 30 days with manual
renewal. Checkout and yearly sales remain disabled.

Five empty legacy compatibility tables are retained solely for foreign keys:

| Table | Structural reason |
|---|---|
| businesses | Referenced by growth company links and artifact ownership |
| prospects | Required parent for the businesses structure |
| pipeline_runs | Referenced by artifact ownership |
| scan_campaigns | Required parent for pipeline_runs |
| email_accounts | Required parent for scan_campaigns |

Ninety-one old tables are excluded or replaced, including the old migration
registry. Lead Engine source and legacy migrations remain preserved. Disabled
legacy job modes reject execution before querying excluded tables. Customer
Gmail and Sheets Lead Engine workers are unavailable on this profile.

Synthetic acceptance data is restricted to disposable local PostgreSQL schemas.
It verifies real service logic for OTP, recovery, Google broker admission, trial
limits, workspace isolation, onboarding, exactly five ICPs, assistant persistence,
discovery, dashboards and fixed-term payment records. Provider responses in these
tests are explicit fixtures, not evidence of real external delivery or payment.
The new Neon destination must contain zero customer records at handover. The
owner's subsequent signup is the final genuine customer-journey acceptance.

## Consumer and cost controls

Existing consumers: Cloud Run API, main worker and acquisition worker. The quota
canary is a provider diagnostic and has no database binding. Frontend and marketing
applications call the API; database credentials must remain server-only.

Use a separate, pinned `leadengine-intent-database-url` secret. Never overwrite
`leadengine-database-url:latest` while old revisions still run. Stage without
production traffic and verify the actual Cloud Run worker before promotion.
Close old admission, drain active work, update workers, promote the verified API,
and remove old revision tags so they cannot expose archive data through old keys.
Preserve old revision specifications and the old secret for deliberate rollback.

The old five-minute inbox and ten-minute recurring dispatch schedulers are paused;
all existing schedulers should remain paused for this empty trial environment.
`DATABASE_BACKGROUND_POLLING_ENABLED=false` stops API two-second mail and
one-minute recurring-monitor database loops. Request-triggered OTP/recovery
dispatch and bounded Cloud Run worker retries remain enabled. Automatic schedules
are disabled; manual authorized checks remain available. API pools retain zero
minimum connections, at most four per process and a 30-second idle release, with
bounded acquisition time and no periodic database health query. Worker connections
are closed after bounded execution. Idle suspend/budget usage must be observed;
this is not a promise that a particular Neon allowance cannot be exceeded.

## Recovery and release evidence

Restricted operator evidence: `data/artifacts/verification/neon-clean-20261117/`.
It includes original consumer specifications, target inspection, archive-only
digests, scheduler snapshots, destination fingerprint checks, tests, schema-only
backup/restoration, build and actual deployment verification. These files and all
credentials stay ignored by Git. The structure-only backup exports no row data;
the local restore reconstructs migration metadata from release source files.

Rollback requires closing new admission and stopping workers first. Before any
owner signup, the archive may be deliberately rebound using its preserved secret
and the legacy schema profile. After new customer writes, stop and reconcile
divergence explicitly; do not silently switch between independent histories.

## Verified production release

| Item | Evidence-backed result |
|---|---|
| Backend source | `b2e27ac709760a4eaa06edf9dc9c7d48e7d72850` |
| Build | `35054183-eb8d-4593-a182-687bbb99b42b`, SUCCESS |
| API | `leadengine-api-00168-his`, 100% traffic; desired template matches active revision |
| API image digest | `sha256:8e2784f4d1dbb086ff13b7842922b7785acfda38ec100fa2000ec30aece4843d` |
| Worker image digest | `sha256:3c58c7f1d656e669ef40eba8fe45383e36f8047cf15dd4f1da1426efd08e0ee4` |
| Database | New supplied Neon, profile `intent-radar-v1`, migration version1004 |
| Actual consumers | API, main worker and acquisition worker all use `leadengine-intent-database-url:1` |
| Diagnostic job | Original provider-only quota diagnostic restored; no database binding |
| Fresh customer directory | 0 users, 0 customer accounts, 0 organizations, 0 sessions, 0 trial claims |
| All application rows | Every application table empty except3 actual short-lived HMAC replay-protection nonces after denial probes |
| Archive | Old schema51 /201tables retained; all10 recorded customer, financial and security table digests unchanged |
| Old endpoints | All old revision tags removed; no archive revision receives customer traffic |
| Signup | Controlled `contact@planebyte.com` admission enabled; global public registration remainsfalse |
| Payments | Public checkout, yearly checkout and unrelated outreach remain disabled |

Actual Cloud Run checks: diagnostic execution `leadengine-quota-canary-rt6tf`
and rebound production worker execution `leadengine-worker-rnvkw` both completed
successfully. Their structured Cloud logs confirm version1004, all110 application
tables empty, full structure verification and successful write/read/rollback.
No dummy accounts or lasting preflight rows were created in Neon.

The structure-only backup is250,816bytes, SHA256
`9bcac89eba4d799b08babded6f5d29baa0035e191f224301b161771482ac9e8b`.
Restoration into a separate local database passed the same structure and empty-data
checks. Metadata was reconstructed from migration files; no customer rows were
exported. Local schema failure and legacy-schema refusal checks also pass.

Final backend suite: **1,197 passed, one intentional real-outreach skip**, eight
existing warnings. The first run lacked the explicit local PostgreSQL tool path;
its restoration test passed when configured, and the final full run includes both
PostgreSQL restoration and the isolated real Chromium security test. No failure
was suppressed. Actual Vertex research of `https://planebyte.com` plus five-ICP
worker generation passed in a disposable local clean PostgreSQL workspace using
three bounded real provider requests; durable worker dispatch claims passed too.
This is explicitly separate from the owner's future production signup.

Production API health200; personal-email password and Google admission403;
unsigned dashboard and old identity without new admission401. Signup, login,
password-recovery and all four legal pages return200. Native forms are visible.
Live signup was visually checked in light/dark mode and at390px. The frontend,
dashboard, settings, navigation, Graph and Discover source was unchanged. Vercel
has no production database environment variable; its API origin is unchanged.

The five existing schedulers are all paused, both database polling loops are off,
and the idle API pool can release every connection after30seconds. Request-driven
transactional mail and bounded AI workers remain configured. No automatic paid
infrastructure change or recurring payment was introduced.

Operational correction: one Cloud Run update response returned stale revision
readiness. Signup was held on the verified closed-admission revision while actual
revision generation, readiness, environment, immutable image digest and worker
logs were re-read. A pristine-destination check still found zero application
records before final promotion. Do not rerun partial private rollout scripts:
read `production-verification.json`, actual cloud state and this release first.

## Remaining acceptance and operational notes

- Owner: sign out of any previous session, open `https://app.planebyte.com/signup`,
  and create the fresh `contact@planebyte.com` account. Enter password/OTP directly
  in the app. Complete the trial, website research, five-ICP approval, assistant
  and dashboard journey. New-database production OTP delivery, password recovery,
  Google callback and the authenticated full journey are not falsely marked as
  tested from fixture or schema checks. No mailbox email was sent during migration.
- The old operator root `.env` `DATABASE_URL` still references the archive; it was
  not edited. Runtime production consumers use the new dedicated secret. Future
  operators must explicitly select `DATABASE_URL_NEW` and the new schema profile
  for current product operations; never run mutating default scripts on the archive.
- Do not restore the archive into the fresh database, re-seed historic users or
  repeat the previous customer reset. Preserve all Lead Engine source and old data.
- Measure normal Neon usage after real activity. Idle controls are verified;
  allowance longevity and load capacity are not guaranteed by this acceptance.
- PayU USD permissions and genuine sandbox checkout remain separate external
  launch dependencies. Checkout stays closed; this migration does not reopen them.
