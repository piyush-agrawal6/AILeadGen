# LeadEngine deployment

## Runtime and local setup

Use Python 3.12 and Node 24. Create `.venv`, install `requirements.lock`, copy `.env.example` to `.env` and set server values. In `dashboard`, run `npm ci`. `python lead_engine.py ui` preserves the desktop launcher; `scripts/dev.ps1` starts development services. SQLite and local artifact storage remain the default outside production. Local authentication bypass requires explicit `AUTH_DISABLED_LOCAL=true`; never use it with production settings.

Run `python -m pytest -q`, then dashboard `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` and `npm run test:e2e`. Opt into a real database test with `RUN_POSTGRES_TESTS=1` and a configured DATABASE_URL; tests create an isolated disposable schema.

## Approved production target

Google project `querryside`, region `asia-south1`; Cloud Run API `leadengine-api`, job `leadengine-worker`, Artifact Registry repository `leadengine`. Database is the configured Neon PostgreSQL instance; private objects use the configured Cloudflare R2 bucket. The dashboard project is `piyushagrawal6s-projects/leadengine` on Vercel. Resource creation can incur charges.

`scripts/deploy-gcp.ps1` prints a plan by default. `-Apply` provisions scoped identities/secrets, builds images, runs additive migrations and verified import/backfill, and deploys the API/job. `-SkipProvision` reuses secret versions; `-SkipBuild` reuses `deploy/images.json`. Source and build logs use separate private GCS buckets. Build logs are in `gs://querryside-leadengine-build-logs`, with public-access prevention and bucket-scoped access for the existing build identity. There is no project-wide build logging grant.

The SQLite source is opened read-only in a snapshot. The importer checks all source primary keys in PostgreSQL and resets sequences. Historical desktop running/queued records become INTERRUPTED so they require explicit resume. Original observations remain intact. Backfill produces canonical identities without inventing historical Phase 3 scores. Reports are in `docs/sqlite-postgres-migration.json` and `docs/prospect-backfill.json`.

`scripts/deploy-vercel.ps1 -Apply` links the existing dashboard project, configures only the required server environment values via secret input, and deploys production. It reads the verified API URL from `deploy/api-url.txt`. Configure the Google OAuth web client callback to `https://<dashboard-domain>/api/auth/callback/google`; the Google consent flow must be checked in a real browser with the allowlisted account. Automated signed-session tests do not establish Google consent success.

## Verification and operations

`python lead_engine.py cloud-doctor --execute-canary` checks PostgreSQL/R2, finds the job and runs the deployed worker image to verify database, object storage, Node, Chromium and Lighthouse. The System page performs read-only checks; an endpoint response is reported separately from an actual job execution.

The worker uses one task, parallelism one, one vCPU, 2 GiB memory, a 180-minute maximum and one platform retry. Application dispatch caps active scans at two. The API scales from zero to two instances. Campaign limits are ten cities, 1,000 qualified leads, 10,000 raw businesses and 500 Lighthouse audits. These are hard limits, not forecast guarantees; source availability and qualifying evidence can yield fewer leads.

For failed scans inspect persisted events and sanitized errors, then Cloud Run execution logs. Resume only FAILED/CANCELLED/INTERRUPTED work after its worker releases the lease. Cancellation is cooperative between bounded units. A dead process releases its advisory lock; leases support recovery. Do not manually start duplicate executions to increase throughput.

Rollback a service to a previous verified image tag. Keep the additive schema and source backup; do not reverse migrations by dropping production tables. Stop new scans before incident repair. Restore database state from the database provider's backup facilities when necessary, then verify artifact references. Never print DATABASE_URL or R2 credentials while diagnosing connectivity.

For a targeted runtime fix, `scripts/deploy-api.ps1 -Apply` or `scripts/deploy-worker.ps1 -Apply` builds and updates only that existing component, preserving identities, secret bindings and limits. A worker update resets canary readiness until an image-matched execution succeeds. For an already-migrated deployment, `deploy-gcp.ps1 -SkipMigrations` avoids repeating import/backfill. See PHASE_3_PRODUCTION_ACCEPTANCE.md for the verified production revisions.
# Phase 3.5 additive release

Use `scripts/deploy-phase35.ps1 -Apply` for the existing project and region. `-BuildOnly` prepares images without changing live resources; `-SkipBuild` releases those prepared images. The script updates the existing job, prepares an API revision without traffic, applies only schema migration 5 and then switches API traffic. Both new binaries accept schema 4 during preparation. Do not use the historical Phase 3 import/backfill steps for this release. Deploy the existing Vercel project after the API, then verify report generation, private downloads, version preservation and the worker canary.

