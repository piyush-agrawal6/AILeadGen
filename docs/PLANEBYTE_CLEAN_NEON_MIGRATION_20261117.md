# Clean Neon migration — 17 November 2026

Status: destination created and independently checked; production cutover pending.
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

Pending: full regression completion, Cloud Run staging/preflight, consumer cutover,
production health and empty-customer checks, then owner signup acceptance. Payment
permissions remain a separate external dependency and do not block this migration.
