# Phase 3 production acceptance — COMPLETE

Production acceptance completed on 26 October 2026 (Asia/Kolkata). The existing application was retained; no new development phase or UI redesign was introduced.

## Acceptance checklist

- [x] Cloud Worker Configuration READY in the actual production System page.
- [x] Real worker canary completed successfully, including a public-page fetch.
- [x] Lighthouse cloud availability verified; actual campaign reports generated.
- [x] Fresh private-window Google login confirmed by the user.
- [x] Clean Austin dentists campaign COMPLETED.
- [x] At least five qualified leads verified with all three opportunity scores.
- [x] Status, assignment and notes persisted after browser refresh.
- [x] CSV, XLSX and HTML generated and authenticated downloads returned 200.
- [x] Actual downloaded files inspected for Phase 3 fields.
- [x] Private R2 object existence verified; public configuration separately user-verified.
- [x] Production security probes passed.
- [x] Complete automated suites, strict types, lint and production build passed.

## Actual deployed configuration

| Item | Verified value |
| --- | --- |
| Dashboard | https://leadengine-livid.vercel.app |
| Project / region | querryside / asia-south1 |
| API service identity | leadengine-api-sa@querryside.iam.gserviceaccount.com |
| Worker identity | leadengine-worker-sa@querryside.iam.gserviceaccount.com |
| API revision | leadengine-api-00005-72b |
| API image | asia-south1-docker.pkg.dev/querryside/leadengine/api:20261026-003801 |
| Worker image | asia-south1-docker.pkg.dev/querryside/leadengine/worker:20261026-000239 |
| Canary execution | leadengine-worker-b25gn |
| Acceptance campaign | 7336e422-0fca-4ef9-bacd-ac6ef0ecfd86 |
| Child run | 29 |
| Worker execution | leadengine-worker-m7pmq |
| Execution result | One successful task; completed 2026-10-25T19:05:25.875931Z |
| Task resources | One task, parallelism one, 1 vCPU, 2 GiB |

The API remains capped at two instances. This acceptance used one active scan. Service identities, secret references and resource limits were preserved during the component-specific updates.

## Exact 403 diagnosis and IAM correction

The actual deployed API identity was inspected before IAM changes. System Health issues GET `https://run.googleapis.com/v2/projects/querryside/locations/asia-south1/jobs/leadengine-worker`; that job lookup returned 403 inside the production API. The existing `roles/run.jobsExecutorWithOverrides` grant contains `run.jobs.run`, `run.jobs.runWithOverrides` and `run.executions.cancel`, but does not contain `run.jobs.get`.

Added `roles/run.viewer` to **leadengine-api-sa** on **leadengine-worker only**. The job lookup immediately became READY without a rebuild. The executor does use runtime overrides, passing only LEADENGINE_RUN_ID, so the existing override execution role was retained. Final job-scoped grants are:

| Principal | Role on leadengine-worker |
| --- | --- |
| API identity | roles/run.viewer |
| API identity | roles/run.jobsExecutorWithOverrides |
| Worker identity | roles/run.jobsExecutorWithOverrides |

No Owner, Editor, Run Admin or project-wide IAM role was added. The deployment script preserves the viewer grant. Evidence: production-job-iam.json and production-health-iam.json.

## Real worker canary

Execution **leadengine-worker-b25gn** checked imports, required production configuration, a real public HTTPS fetch, a temporary PostgreSQL run/event write/read/cleanup, DuckDB/httpfs, temporary R2 object write/read/delete, Node, Chromium, Lighthouse and Overture connectivity. It exited successfully. Overpass was checked against the configured endpoint and one bounded fallback and reported a warning.

The private evidence object is `audits/canary/leadengine-worker-b25gn/result.json`. System Health compares the recorded image to the current job image and checks the recorded execution's successful completion before reporting Canary/Lighthouse READY. Old-image evidence cannot make a new image ready. See production-canary-evidence.json and production-health-final.json.

## Clean campaign outcome

The campaign was created through the authenticated production dashboard with Austin / United States, Dentists, Balanced quality, Local + Small Group, Website + SEO + Basic Security, target five, and Lighthouse enabled. Automation used a short-lived signed session for the approved account; Google login was separately verified by the user.

| Stage | Actual result |
| --- | --- |
| Discovery | 198 public listings |
| Deduplicated / relevant candidates | 166 |
| Probe pool | 40 |
| Reachable websites | 35 |
| Shared crawl | 35 sites enriched |
| Static technical / SEO audits | 40 prospects |
| Lighthouse | Three reports; two have performance/SEO scores, one has partial metrics |
| Qualification | 23 prospects |
| All three scores assessed | 19 prospects, including a valid zero SEO score |
| CSV / XLSX export | Exactly five ranked prospects |
| Final state | COMPLETED |
| Pipeline elapsed time | 1,480.2 seconds |

The UI verification selected five fully assessed prospects. Its positive-score filter returns 18 because it excludes the assessed zero. Null scores remain null for unreachable/unassessed sites; they are not fabricated. Exports preserve the run's ranked snapshot and can include strong website opportunities whose SEO/security could not be assessed.

### Five verified production leads

| ID / Business | Website | SEO | Security | Primary | Contactability | Scale |
| --- | ---: | ---: | ---: | --- | --- | --- |
| 3953 — GK Dental | 62 | 97 | 48 | SEO | HIGH | LOCAL |
| 3924 — Smile Designs | 57 | 73 | 48 | SEO | HIGH | LOCAL |
| 3923 — Oak Canyon Dentistry | 52 | 72 | 42 | SEO | HIGH | LOCAL |
| 3933 — Lake Pointe Dental | 32 | 29 | 40 | SECURITY | HIGH | LOCAL |
| 3931 — Bee Cave Orthodontics | 9 | 9 | 40 | SECURITY | HIGH | LOCAL |

Each was opened in the production UI and checked for score evidence, primary/secondary opportunities where applicable, contacts, website, market, vertical, scale and discovery dates. On GK Dental, Shortlisted → Contacted, assignment to planebyte@gmail.com, and a note persisted after refresh. The note explicitly says this was an acceptance test and no outreach was sent. Browser page errors were empty. Evidence: production-acceptance-scan.json and output/production-acceptance screenshots.

## Reports and private R2

Authenticated browser downloads returned 200 for CSV (2,974 bytes), XLSX (54,461 bytes) and HTML (24,567 bytes). The CSV has exactly five rows. CSV and XLSX include all eleven Phase 3 opportunity/workflow/discovery columns. The workbook's ten sheets are readable. HTML contains the service-opportunity section and no scripts; its download is sandboxed.

Verified object keys:

- `campaigns/7336e422-0fca-4ef9-bacd-ac6ef0ecfd86/runs/29/leads.csv`
- `campaigns/7336e422-0fca-4ef9-bacd-ac6ef0ecfd86/runs/29/leads.xlsx`
- `prospects/3953/reports/report.html`
- `audits/29/3924/lighthouse.json`
- `audits/29/3953/lighthouse.json`
- `audits/29/3923/lighthouse.json`

All six objects were checked with authenticated HeadObject. The user independently confirmed the public r2.dev URL is disabled and no public custom domain is connected. Anonymous S3 endpoint requests did not expose objects/listings; endpoint rejection alone was not used to infer account-level public settings. Downloads require the authenticated dashboard/BFF or signed internal API.

Exports capture the state at pipeline completion. The HTML report was generated after the workflow test and reflects that later state. Evidence: production-artifact-keys.json and production-export-inspection.json.

## Authentication, security and responsiveness

The sole production account is **planebyte@gmail.com**, as explicitly requested. The user confirmed a clean private-window Google login; a fresh callback log returned 302 with informational status. The prior issuer/callback error did not reproduce, and Google provider configuration was not rewritten.

A browser-tool failure printed a temporary acceptance-session cookie. AUTH_SECRET was rotated and the existing dashboard redeployed, invalidating that session on the current production deployment. Test-session lifetime is fifteen minutes and live browser errors now omit request call logs. No token/secret is included in these evidence files. Current sessions may require sign-in again.

The progress check also exposed synchronous database polling on the API event loop. Event-stream reads and nonce claims now run off that loop; stream polling is bounded at two seconds. This was deployed as an API-only update without interrupting the worker. Regression tests cover loop responsiveness and existing replay protection.

Production probes passed signed access, unsigned/bad-signature/unapproved-actor/replay rejection, absence of a CORS grant, disabled API docs, payload limits and cross-origin mutation rejection. See production-security-checks.json and the UI verification record.

## Regression totals

| Check | Result |
| --- | --- |
| Python, including real PostgreSQL | 109 passed |
| Frontend tests | 26 passed |
| Browser acceptance tests | 3 passed |
| TypeScript strict | Passed |
| ESLint | Passed |
| Next.js production build | Passed |

The full suites ran after the runtime fixes. One Starlette/httpx test-client deprecation and transitive ESLint peer warnings remain; actual checks pass.

## Preserved history and remaining warning

Historical leads were not automatically rescanned or assigned invented Phase 3 scores. Overview distinguishes known, assessed and unassessed/legacy leads. Original records remain available.

The previous run 25 was canceled before the clean test. Diagnostic run 27 exposed double decoding of compressed HTTP responses. The fetcher now removes encoding/length headers after bounded decoding and preserves other response evidence; gzip/deflate regressions and real public probes pass. Its 39 invalid qualifications were excluded, with raw observations, original counters and objects retained in diagnostic-invalidation.json. The corrected acceptance is run 29; diagnostic results are not counted as success.

**OpenStreetMap health remains WARNING** because the configured public endpoint and one fallback did not respond successfully within bounded checks. Discovery retains its existing mirror strategy, and the real campaign completed. This warning is not an unresolved worker authorization or execution failure. One Lighthouse report has partial metrics; missing values remain unassessed. Public source attribution and passive security observations still require human review before outreach and are not penetration-test certification.
