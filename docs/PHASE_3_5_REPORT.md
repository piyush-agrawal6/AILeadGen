# LeadEngine Phase 3.5

Release date: 26 October 2026. Production acceptance is recorded below after deployment.

## Workspace and filters

The lead table now groups website, phone and email under the business name. Location, vertical, three sortable opportunity scores, primary opportunity, contactability, editable status and PDF report actions remain separate. Assignment stays in lead detail. The duplicate Shortlist action is removed. Server pagination and URL filters are retained.

Filters use a Radix dialog with a visible close button, outside click, Escape, focus restoration and a local draft applied explicitly. Desktop uses a floating two-column panel; narrow screens use a single-column sheet. Missing contact fields add no empty rows. Scores have four semantic tints and an explicit higher-score-means-opportunity legend. All eight statuses, including Lost, have labels, dots and light/dark colors. Status changes update the affected record and roll back on failure.

Lead detail shares the same status and PDF controls, adds contact/social links and business/website information, and retains technical evidence, provenance, assignment and notes. The app uses the geometric P mark approved by the user, with embedded, locally served PlaneByte Sans fonts derived from Inter under its included OFL license. Light is the initial theme; saved dark/system preferences remain supported.

## PDF architecture

`POST /api/leads/{id}/pdf-reports` saves an immutable, allowlisted snapshot of persisted business/profile/findings/Lighthouse/opportunity/contact data. It does not scan the website. A canonical-prospect version lock prevents duplicate versions; a second pending request returns the same pending report. Versions are preserved in `client_reports`, including creator, creation date, private object key and internal error reason.

Production dispatch reuses the existing Cloud Run worker with a report-ID override and a five-minute task deadline. Reports and scans share the existing two-slot dispatcher. No service account, IAM, region, storage-publicity or cloud architecture change is required. Local development uses a single render thread. Queue/generation expiry provides a bounded failure state; errors shown to the UI are generic. Retrying creates a new version.

ReportLab renders A4 documents with embedded fonts, vector branding, page headers/footers, numbered pages and escaped text. Fixed snapshot metadata makes repeat renders deterministic. Each UUID-version PDF is stored privately in R2; authenticated BFF downloads stream the object with PDF MIME type and private/no-store caching. No HTML report remains in the primary UI; the old HTML endpoint remains available for compatibility.

Reachable-site reports contain a cover, executive summary, website experience, search foundations, passive external security review, qualitative business impact, relevant engagement scope and configured PlaneByte contact details. No-website and unreachable-site reports adapt to three pages, explaining new-website foundations or recovery respectively, without empty SEO/security sections. Unassessed values remain unassessed. Reports omit notes, assignment, workflow, internal identifiers and scanner errors. They contain no invented prices, rankings, traffic/revenue estimates, malware/compliance or penetration-test claims. Pricing is disabled by default.

Public contact configuration defaults to the verified `https://planebyte.com` and `contact@planebyte.com`; phone is omitted unless configured. `PLANEBYTE_WEBSITE`, `PLANEBYTE_CONTACT_EMAIL`, `PLANEBYTE_PHONE` and `REPORT_SHOW_PRICING=false` are documented in `.env.example`.

## New Scan and reports library

New Scan retains its working form, curated countries/cities, selection limits, custom locations and sticky campaign summary. Location mode has only Recommended Markets and Custom Location. Selected cities, verticals and options have restrained tints; Website, SEO and Security use blue, teal and purple accents. No new verticals or fabricated market scores were introduced.

Reports & exports separates campaign CSV/XLSX downloads from paginated, versioned client PDFs. Users can see queued/generating/ready/failed states and download previous generated versions.

## Verification

- Baseline: 109 Python tests, 26 frontend tests, three browser tests.
- Final results: **118 Python tests passed** (including two real PostgreSQL tests), **35 frontend tests passed**, and **six browser tests passed**. This improves the accepted baseline; no existing test was removed.
- Strict TypeScript, ESLint and production build: passed; logs in `output/phase35-*.log`.
- Python and dashboard dependency audits: zero known vulnerabilities (`docs/phase35-*-audit.json`).
- Browser coverage includes outside click, Escape, close button, interaction inside, focus restoration, URL persistence, shared workflow, contact placement, absence of Assigned/Shortlist columns/actions, persisted Lost status, protected PDF download, both location modes and theme/responsive behavior.
- Visual captures: `output/qa/phase35/`, including 1366×768, 1440×900, 1920×1080 and 390×844, all eight workflow states, active filters, light/dark lead detail and scan choices.
- PDF samples use actual persisted production observations: GK Dental (reachable), Buda Kids Teeth (unreachable), HMO Estates Ltd (no website). All pages were rasterized with Poppler and visually reviewed. A long-name/long-URL test verifies wrapping, cover containment and deterministic bytes. Adaptive PDFs omit unsupported SEO/security assessments.
- Migration 5 was tested on SQLite while preserving identities/notes/foreign keys and on an isolated real PostgreSQL schema. PostgreSQL report versions, shared workflow and session locks were also checked.
- Existing public production data counts were recorded in `docs/phase35-before-deploy.json` before release.

## Production deployment and acceptance

The production database is at schema **5**, and the data counts immediately after migration exactly matched the pre-release snapshot. API revision **leadengine-api-00006-znl** serves 100% of traffic. API and worker images use tag **phase35-20261026-092619**. Vercel deployed **leadengine-jc4fe7l3g-piyushagrawal6s-projects.vercel.app**, aliased to **https://leadengine-livid.vercel.app**. Worker canary **leadengine-worker-t67ft** passed, including PDF rendering, public HTTP fetching, database event write/read/cleanup, R2 temporary-object write/read/delete, DuckDB, Node, Chromium and Lighthouse. The existing identity, region and resource limits were verified in `docs/phase35-deployment.json`.

A release-script revision-selection issue was corrected using the image digest before dashboard acceptance; the script now verifies the prepared revision against the exact release image. The dashboard deployment uses the explicitly verified existing Vercel account scope.

A final detail-page loading guard prevents generating a duplicate version while existing report metadata is loading. The collaboration/PDF browser scenario was rerun after this polish and passed. New Scan quality selection also uses the correct selected-state tint.

Live report/download acceptance **passed** (`docs/phase35-production.json`): inline Lost persisted and the original Contacted status was restored; live filters closed and restored focus; the duplicate location tab is absent. Four PDFs reached READY: GK Dental versions 1 and 2, Buda Kids Teeth version 1, and HMO Estates Ltd version 1. All downloaded through the authenticated BFF. The first GK Dental version retained the same SHA-256 after regeneration. The live browser reported zero page errors. Final UI checks confirm all four PDF versions in the reports library, the existing-PDF download in lead detail, and selected scan options. Existing run 29 CSV and XLSX downloads returned HTTP 200 with valid opportunity columns/workbook data (`docs/phase35-final-ui.json`). The production acceptance session was short-lived and signed for the sole allowlisted account; the user's earlier fresh Google-login confirmation remains the human OAuth verification.

`docs/phase35-r2-acceptance.json` verifies every object's PDF MIME type, private cache headers, byte count and hash. A signed GET of the same S3 object succeeds; removing its signature returns HTTP 400 (`InvalidArgument`) rather than object content. Unsigned API/BFF metadata/download requests return 401. Public r2.dev and absence of public custom domains were separately confirmed by the user; bucket account settings were not inferred from object credentials.

All three production downloads were rasterized and visually reviewed again: six pages for the reachable case, three for unreachable, three for no website. Samples are in `output/pdf/`; live UI captures are in `output/qa-live/phase35/`.

Final data verification (`docs/phase35-after-acceptance.json`): **5,689 business observations, 2,125 canonical prospects, four campaigns, 31 pipeline runs, one note and 480 opportunity-score rows are unchanged**. The only added artifact catalogue entry is the new worker-canary result; four new versioned client-report records/files are preserved. No existing production leads, campaigns, notes, reports or objects were deleted. Existing campaign results, scoring and exports were covered by regression tests; no additional discovery scan was run for PDF generation.

Hosted health verifies API, database, R2, worker configuration, image-matched completed canary and Lighthouse. The pre-existing public Overpass availability warning remains; bounded fallback is unchanged.

The release procedure is `scripts/deploy-phase35.ps1`: prepare a schema-4/5-compatible worker, prepare the new API without traffic, apply only migration 5, then route traffic. It does not import, backfill or delete production data. The Vercel dashboard is deployed after the API. New worker canary evidence includes the PDF renderer and embedded font check alongside existing database/R2/Lighthouse/discovery checks.

## Practical limits

The report describes the stored assessment, not a real-time rescan. A missing signal is an observation boundary rather than proof of a fault. Passive security observations do not certify security. The selected font supports the existing market languages; no universal non-Latin font coverage is claimed. Tables scroll horizontally on narrower screens. The pre-existing Starlette/httpx test-client deprecation warning remains; production functionality is unaffected.
