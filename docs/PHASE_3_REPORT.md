# LeadEngine Phase 3 report

Phase 3 production acceptance is COMPLETE. The detailed checklist, deployment identities, exact resource revisions and evidence are in [PHASE_3_PRODUCTION_ACCEPTANCE.md](PHASE_3_PRODUCTION_ACCEPTANCE.md). The live Austin campaign completed and its real UI, workflow, private objects and downloaded files were verified.

## Delivered in the existing application

The original Python pipeline and Next.js dashboard were extended in place. Before feature work, the original 31 Python tests and dashboard checks passed. Modernization moved the dashboard to Next.js 16.4.3, React 19.3.1, TypeScript 6.0.3, Tailwind 4.3.3 and Node 24. Auth.js 5.0.0-beta.32 is a pinned, documented integration exception. Dependency audit outputs reported zero known findings. Python remains 3.12.

Implemented areas include multi-city/vertical campaigns, the seven recommended vertical families plus the legacy restaurant vertical, curated country/city presets and custom locations, three independent evidence-based opportunity scores, scale and quality filters, canonical rediscovery, shared workflow/assignment/notes/settings, persisted progress, private reports/exports, local SQLite development and cloud PostgreSQL/Cloud Run execution. Existing engine functionality remains available.

Security includes verified Google email allowlisting, per-request authorization, server-only credentials, HMAC internal requests with persisted replay protection, origin checks, bounded input, nonce CSP, safe errors, public-IP-pinned HTTP fetching, verified TLS, guarded Lighthouse subresources, escaped HTML and spreadsheet-safe exports. Secrets are scoped to the API/worker identities. Detailed controls and limits are in [SECURITY.md](SECURITY.md).

## Data preservation

Four additive migrations applied to the configured PostgreSQL database. A read-only SQLite snapshot import verified all source primary keys. The snapshot contained 3,520 businesses, 24 historical runs, 374 contacts, 512 findings, 181 legacy scores and nine Lighthouse records. Backfill linked 2,237 non-rejected observations to 1,514 canonical prospects. A repeat produced zero new prospects. Historical scores were not fabricated, and no automatic rescan of the roughly 98 historically qualified leads was started.

Shared corporate domains require location evidence to avoid combining separate venues. A historical bridge joined only groups created inside the backfill transaction; conflicting persisted workflow is never merged automatically. The source database and source artifacts were retained. Thirty-five available historical artifacts were copied to R2; five imported test-era references had no available source file and are not claimed to be downloadable.

## Production verification achieved

The dashboard is live at https://leadengine-livid.vercel.app. The API is https://leadengine-api-befca7xg4a-el.a.run.app. The user confirmed a fresh private-window Google login as the sole approved account, planebyte@gmail.com. The fresh callback returned 302 with informational logs; the old issuer error did not reproduce and authentication was unchanged.

The worker lookup 403 was traced to missing `run.jobs.get` on the actual API service identity. Adding Viewer on the worker job only resolved it. The override execution role remains because the executor passes LEADENGINE_RUN_ID. No broad administrative grant was made.

The corrected worker image completed the expanded canary, including a real public HTTP fetch: imports/environment, temporary database event write/read/cleanup, DuckDB/httpfs, temporary R2 write/read/delete, Chromium, Lighthouse, Node and Overture connectivity. System Health verifies both image match and successful execution completion before showing Canary/Lighthouse READY. Public Overpass remains a bounded warning, with one health-check fallback and the existing discovery mirror strategy retained.

The real PostgreSQL tests and initial live scan exposed transaction-pool session leakage. Every transaction now applies schema/UTC/timeout with SET LOCAL. The worker lock uses a direct Neon connection. Real tests verify lock exclusion across commit and release on close. Expired worker heartbeats make interrupted work resumable. Identity persistence uses batched lookups and visible checkpoints.

The user independently confirmed that R2's public r2.dev URL is disabled and no public custom domain is connected. Signed storage operations and authenticated downloads are tested separately. S3 endpoint rejection alone is not treated as public-policy evidence.

The live test also reproduced a double-decoding bug in compressed HTTP responses. The bounded fetcher now removes encoding/length headers after decoding, preserves other evidence headers and enforces its decoded byte limit. Gzip/deflate regressions and actual public probes pass. Only the worker was rebuilt for this fix. Its canary now performs a real public fetch. The 39 false qualifications from diagnostic run 27 were excluded, with raw observations, original counters and objects retained in diagnostic-invalidation.json. Historical leads were untouched.

## Validation

109 Python tests pass, including real PostgreSQL and canary evidence tests. The dashboard passes strict TypeScript, ESLint, 26 frontend tests, production build and all three browser acceptance tests. Production security checks pass for unsigned/bad-signature/unapproved/replayed request rejection, no CORS grant, disabled API docs and payload limits. A Starlette/httpx test-client deprecation and transitive ESLint peer warnings remain; neither prevents the actual checks from passing.

Visual QA covers all major pages, the lower scan options and workflow sections, the individual scan monitor, dark/light themes and laptop/desktop/tablet widths. The acceptance screenshots and browser-error records are in output/qa and output/production-acceptance. The legacy terminology correction retains the working layout.

## Completed live acceptance

Campaign **7336e422-0fca-4ef9-bacd-ac6ef0ecfd86**, child run **29**, completed with **23 qualified prospects and five exports**. Nineteen prospects have all three scores assessed. Five fully assessed leads were opened and verified in the production UI. Status, assignment and notes persisted after refresh. CSV, XLSX and HTML downloads returned 200; their actual bytes and Phase 3 fields were inspected. All six associated R2 export/audit/report objects were verified.

The worker execution was **leadengine-worker-m7pmq**. Current API revision is **leadengine-api-00005-72b**, API image **20261026-003801** and worker image **20261026-000239**. The real-fetch canary is **leadengine-worker-b25gn**. Cloud Worker Configuration, Canary and Lighthouse are READY in the production System screen. Two Lighthouse reports have performance/SEO scores and a third has partial metrics; absent metrics were not fabricated.

An API-only fix moved synchronous event polling and nonce IO off the request loop and bounded stream polling to two seconds. A temporary test session printed by a browser-tool error was invalidated by rotating the session key and redeploying the dashboard; live test errors are now redacted. Production Google provider configuration was unchanged. Users may need to sign in again.

The only remaining live service warning is bounded public Overpass degradation; the real campaign completed using available discovery sources. The source and scoring limits below remain applicable.

Passive security observations are not an active security assessment; source coverage and reachability can reduce usable results. Cloud hosting/storage can incur charges even though public discovery does not use paid lead-data APIs.
