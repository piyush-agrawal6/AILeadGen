# Acquisition Phase 1

Scope: Gemini-guided Firecrawl acquisition and reviewed CSV/XLSX/read-only Google Sheets imports, feeding existing canonical prospects, observations, analysis, qualification, reports and campaign-scoped outreach. No Phase 5.

## Production safety

Production scanning/outreach are owner-enabled. Keep current flags, controls, schedules, running workflow records, existing worker image, SMTP and eligibility unchanged. New features start disabled. Deploy a separate acquisition job. No prospect email during QA. Add schema 13 with short lock timeout and retry rather than stopping workers. No reset/truncation.

## Audit / design

- `scan_campaigns` is canonical; per-run `businesses` plus `prospect_observations` are existing campaign membership. `ProspectRepository.observe` owns identity and history.
- `PipelineRunner` already shares crawl/probe/security/SEO/Lighthouse, Phase 4.9 freshness reuse, deterministic qualification, reports and reconciliation. Add a default-preserving optional discovery dependency; use it only in the separate acquisition job. Existing Overture worker deployment stays pinned.
- Existing Cloud Run dispatcher selects QUEUED scans. Acquisition-owned scan batches use a separate job lease in `acquisition_jobs`; their scan rows have no Maps execution reservation/lease and are never QUEUED, so they do not consume Maps dispatcher or worker capacity. They must never enter that dispatcher. Resume source acquisitions through their own job route.
- Imports are parsed server-side in bounded batches, staged privately, reviewed before canonical writes. Imported emails remain unverified until existing public-source/domain checks support them.
- Google Sheets uses opt-in read-only scope and existing Google OAuth client, encrypted server-side refresh token and actor-bound state. No change to normal sign-in scopes. Spreadsheet URL + tab selection avoids requesting broad Drive access.
- AI receives bounded intent or headers and three sanitized sample rows; never a full file or one call per row. Validated structured plans only; owner reviews before acquisition/import.
- Credentials requested: `GEMINI_API_KEY`, `FIRECRAWL_API_KEY` in root `.env`, no duplicate or public secret names. Official model documentation confirms `gemini-3.8-flash`.

## Delivery order

1. Audit complete; remaining steps in progress.
2. Add campaign source metadata and additive processing/event/provenance tables.
3–8. Provider interface, Gemini strict planner, Firecrawl adapter/review UI, shared pipeline integration.
9. Overture regression.
10–14. Bounded CSV/XLSX parsing, AI mapping, manual review, shared ingestion, read-only Sheets.
15–18. Unified selectors/source UI and source-agnostic PDF/email-preview tests with fake SMTP.
19. Active-work preservation checks, backup, additive migration, new acquisition job/API/frontend deployment.
20. Production verification then enable new features individually. Never send QA to discovered prospects.

Status: IN PROGRESS. Frontend deployed as `dpl_E8SGknpX4rv3CL6apGUsNBdyepfH`; gated API revision `leadengine-api-00037-pl9` is serving. Schema 13 is live. New source flags remain disabled until verification. Existing production worker and global automation flags are preserved.

## Verification, 2 November 2026

- Backend: 366 passed, 11 opt-in tests skipped. Frontend unit: 43 passed. Acquisition browser: 4 passed; the earlier full browser run passed the other 17 cases. TypeScript, ESLint (one pre-existing warning) and production webpack build passed.
- Schema 13 and existing repository/report behavior passed against a disposable PostgreSQL schema. Linux image build and exact-lock suite passed (`a7d961f6-6b36-46fd-b66a-d07c7b14bdae`).
- All four source labels use existing reports/email preparation; test PDFs have 8 pages. SMTP is mocked in these checks. Cross-source identity reuse, DNC precedence, checkpoint idempotency, read-only OAuth state/token handling and resource caps are covered.
- Online schema-12 rollback snapshot was restored into a disposable schema and verified. Initial live migration attempts rolled back on the 750 ms lock timeout. A bounded retry subsequently applied schema 13 without changing automation controls, resetting data or interrupting the running scan.
- Gemini model/key metadata and Firecrawl credits were verified. Actual local Gemini generation returned timeouts/503, so AI is not yet accepted. The production Cloud Run check also timed out at 35 seconds. An isolated 90-second diagnostic also returned ReadTimeout at 90.6 seconds. Production timeouts/model are unchanged; AI remains NOT READY.
- Existing production API and Gmail SMTP/IMAP passed post-deployment checks. The acquisition job uses a dedicated source service account and has no Gmail configuration. The existing worker specification is unchanged.
- Live Firecrawl adapter check: one query, five results, two public website scrapes, two evidence-confirmed candidates. No canonical lead writes or emails. Full acquisition/qualification acceptance is still pending. Existing scheduler metadata remains intact.
- Owner completed read-only Sheets OAuth. Live metadata/sample read and private immutable snapshot succeeded for the controlled “Acceptance Leads” tab (10 rows). Reviewed deterministic mapping is stored; AI mapping is explicitly unavailable. The no-mail import completed: 10 canonical leads, observations, source evidence and review cases; zero qualified leads, queue entries, messages or outreach runs. All sample websites were empty, so no website or qualification was invented. Duplicate execution left all counts unchanged. The deployed progress API now reports review_cases=10 separately from email eligibility.

Remaining: successful live Gemini structured generation, full live acquisition/qualification/import acceptance, feature-by-feature enablement. Do not mark this phase complete while these remain outstanding.

Source worker follow-up: mixed-industry groups share a single deadline; the complete source operation is bounded by its configured runtime. Both regression tests passed and fixes were deployed only to the isolated acquisition job.

Gemini diagnosis follow-up: the official REST structured-output example matches the implemented responseFormat.text.schema shape. Minimal plain and JSON calls on 3.8 also timed out. A diagnostic 3.6 Flash call returned in 2.6 seconds, and actual strict intent plus sanitized import mapping both passed in 10 seconds. Owner approval to change GEMINI_MODEL is pending; production configuration remains 3.8.

## Controlled source acceptance follow-up

- CSV and XLSX each processed three controlled rows: two valid, one duplicate, one invalid-row issue, one existing canonical business and zero new canonical businesses. Authenticated issue CSV downloads passed. Neither created queue entries, messages or outreach runs.
- Real Bristol Firecrawl run used one query and five scrapes: five results, four normalized businesses, three website analyses, one chain rejected. Actual website/SEO scores did not meet the unchanged qualification threshold, so it recorded qualified=0 and shortfall=5, preserving the partial campaign. No outreach or messages. This does not establish five-qualified-lead acquisition acceptance.
- Owner approved Gemini 3.6 Flash; root .env and API/acquisition job now use it. Production key equality was verified without exposing it. Cloud Run initially returned explicit HTTP 503; the same strict request succeeded on a second, backed-off attempt. Added at most three explicit 502/503/504 attempts within one 35-second total deadline; quota/auth errors, uncertain read timeouts and invalid output are not retried. Targeted source tests passed; exact-lock build and production recheck are pending. No source feature was activated while the production check was failing.

The reviewed-intent production check caught a schema-valid semantic mismatch: 555 requested leads returned for an explicit target of 5. No acquisition started and Firecrawl was still disabled. AI preview was temporarily disabled again. The fix constrains explicit numeric targets in the provider schema, independently validates the result before returning/caching, revalidates cache hits, and increments the cache format version so older invalid plans cannot reappear. Cached import mappings also revalidate column membership. Targeted tests: 24 passed; exact-lock build is pending. Existing scanning/outreach remains untouched.
