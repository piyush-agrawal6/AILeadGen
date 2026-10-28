# PlaneByte branding and client report correction

26 October 2026.

## Requested changes

The website and PDFs now use the user-supplied `dashboard/public/logo.png`, Signal Orange #FF5A1F, Deep Graphite #0F1110, Charcoal #171A17 / #1D211D, Warm Off-White #EDE9E1, Muted Gray #9D9F98 and technical olive accents. Dark is the new default; Light and System remain available. Logo, login branding, page title and favicon use PlaneByte. Exact public logo/font routes allow image optimization and login typography without exposing workspace or API routes.

Client PDFs contain PlaneByte branding only. LeadEngine has been removed from page headers, footers, cover and PDF metadata. The supplied raster logo is copied unchanged into the renderer; its SHA-256 is recorded in report configuration.

## Current scores and improvement figures

Client measurements are separate from internal sales-opportunity scores:

- Website current score: persisted Lighthouse **mobile performance**.
- SEO current score: persisted **Lighthouse SEO**.
- Security configuration score: equal-weight checklist of HTTPS, HSTS, CSP, content-type protection, frame protection, Referrer Policy and Permissions Policy. All seven must have an explicit result; missing passing-header data is never assumed to pass. Incomplete evidence means Not assessed. This measures external configuration, not overall vulnerability risk or security certification.

Default proposed goals are website 90, SEO 100 and security configuration 100. The PDF labels the arithmetic difference as **Target gain**, and explicitly explains that these are planning goals rather than predictions or guarantees. A score already above a goal is maintained rather than assigned a lower goal. Missing or invalid scores produce neither an invented zero nor a numeric gain. Goals are configurable in `config/report_brand.json`.

GK Dental's stored measurements illustrate the correction: website **13 → proposed 90 (+77 points)**, SEO **75 → proposed 100 (+25 points)**, and the fully evidenced seven-check configuration score **14 → proposed 100 (+86 points)**. The prior internal opportunity values 62/97/48 are not relabeled or displayed as client quality scores. Internal opportunity scoring and the lead workspace's sales-prioritization logic remain unchanged.

No-website and unreachable-site reports omit unsupported score cards and explain that a measured baseline must be established after launch/recovery. No new website scan is performed to generate a PDF.

## Validation and release

PDF/scoring-only tests: 18 passed locally. Full API/PDF regression suite: 134 passed in the Linux image; two opt-in PostgreSQL tests skipped (no schema changes in this release). Windows Application Control blocks the local DuckDB DLL, so the complete suite ran in the existing Cloud Build environment instead of changing machine security policy.

Frontend: **45 unit tests passed**, **three focused brand browser tests passed**, strict TypeScript passed, ESLint passed, and the production build passed. Results are recorded in `output/brand-*.log`. Brand browser tests use explicitly marked offline QA data for desktop/mobile/theme interaction. Live acceptance verifies actual authenticated report generation and storage after deployment.

The reachable, unreachable and no-website samples were rasterized and visually checked: six, three and three pages respectively, with no orphaned summary page. The report includes measured-score provenance, proposed targets and the security checklist methodology.

Production status: **deployed and verified**. The existing website is available at https://leads.planebyte.com (the prior Vercel alias also works). Production deployment: `leadengine-19g2se0dy-piyushagrawal6s-projects.vercel.app`. API revision `leadengine-api-00007-fww` serves 100% of traffic; API and worker images use `brand-20261026-170853`. No schema migration was required.

The live browser verified the logo actually loaded, exact Graphite background and Orange actions, and unauthenticated access denied for private report metadata. Worker canary passed for the new image. GK Dental version 3, Buda Kids Teeth version 2 and HMO Estates Ltd version 2 reached READY and downloaded successfully. Actual downloaded content verifies the 13/75/14 current scores and +77/+25/+86 proposed gains for the reachable case, no LeadEngine text in pages or metadata, and the original GK Dental PDF's unchanged SHA-256. Zero live browser page errors were recorded. Evidence is in `docs/brand-production.json`, `docs/brand-pdf-verification.json`, `docs/brand-worker-canary.json` and `output/qa-brand-live/`.

Older report versions keep their original design and contents. Regenerate creates a new version with the updated branding and score presentation. Existing services, identities, IAM, resource limits, database schema and prior PDF versions are preserved. New reports are generated as new immutable versions.
