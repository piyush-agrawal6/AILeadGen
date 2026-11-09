# PlaneByte Lead Engine — Phase 1–6 implementation status report

Assessment date: **2026-11-08 (UTC)**. Reporting and verification only. Application source was not repaired or rewritten in this assessment. Production databases/infrastructure, real mail and live customer integrations were not modified or used.

**Continuation update — 2026-11-09:** this assessment's executive counts are historical. The saved post-assessment B01/F12 and B02 summary repairs survived and pass fresh focused local checks. F02/B03 now includes gated account admission, consent renewal and invitation-only new-account access without implicit membership. PostgreSQL and real external-account acceptance remain pending. Current continuation evidence and exact next steps are maintained in `LEAD_ENGINE_PHASE_1_TO_6_COMPLETION.md`; no completed audit was restarted or progress reset.

## Executive summary

The application has substantial working **local** company discovery/intelligence, ICPs, lists/tasks, internal outreach safeguards, reviewed Sheets workflows, scoped REST keys, genuine MCP and signed-webhook foundations. It is **not ready for public SaaS launch**. Existing test suites pass, but two additional assessment probes expose PostgreSQL onboarding failure and internal automation metadata visible to a customer workspace. Customer admission/mail routing, CRM/enrichment providers, supported dependency fidelity, approved policies and staged external acceptance remain incomplete.

**Functional estimate: 75.1%; fully verified requirement closure: 56.7%. Seven P0 workstreams remain open. No phase is marked entirely complete.** The model includes all 174 listed audit rows (173 in scope; unspecified-other-CRM is not applicable). It measures demonstrated engineering scope, not deliverability, legal approval or complete customer journey success.

Requirement inventory: **97 complete and verified; 24 implemented but not fully verified; 31 partial; 16 not implemented; 2 broken; 3 externally blocked; 1 not applicable**. All 76 incomplete requirements map to the pending backlog.

Reports are complementary: this file contains requirement matrices/source/UI/test evidence; `PLANEBYTE_LEAD_ENGINE_PENDING_FEATURES.md` maps every incomplete row to prioritized work and acceptance; `PLANEBYTE_LEAD_ENGINE_RELEASE_READINESS.md` records launch gates and all 24 customer questions.

## Percentage methodology

- Weight **3**: trust/isolation/access or essential discovery/contact/sales/integration execution; **2**: primary supporting product workflow; **1**: supplementary UI/history/documentation. Each row shows its weight; no equal-phase averaging is used.
- Credit: COMPLETE AND VERIFIED = **1**; IMPLEMENTED, NOT FULLY VERIFIED = **0.75** (working code plus relevant local tests, missing broader/end-to-end/external acceptance); PARTIAL = **0.25/0.50/0.75** for foundation-only/a stable demonstrated subset/most behavior with a material remaining gap. Each row states the supported subset and limitation.
- NOT IMPLEMENTED, BROKEN and BLOCKED = **0**. NOT APPLICABLE = weight **0**, excluded. Implemented code with unaccepted external behavior is I, while its separate live-acceptance requirement is BLOCKED; external approval never counts as complete.
- Functional estimate = sum(weight × credit) / sum(weight). Verified closure = sum(weight of COMPLETE AND VERIFIED rows) / sum(weight). This is **requirement closure**, not statement coverage, test-pass percentage or proof of all UI states.
- A verified internal mail transport does not satisfy the separate customer-mail connection requirement. API/MCP foundations cannot count as CRM completion. Feature-density scores can coexist with a blocked customer journey; production readiness is a separate critical-gate decision.
- Partial credits are documented engineering estimates. Recalculate directly from the tables. No production-readiness percentage is inferred.

## Current Git and evidence provenance

Branch: `main` tracking `origin/main`; no ahead/behind divergence was reported. Assessment-start status: **117 modified tracked files, 511 untracked status entries, 0 staged changes**. Entries are not a recursive file count. Existing work spans backend, dashboard, schemas/jobs/tests/docs; it was preserved. No commit, push, deploy or cleanup was performed.

Recent commits (existing):

```text
a23b937 first commit
d009e5f feat: initial release of LeadEngine V1 zero-cost lead engine
```

Guidance reviewed: root/dashboard AGENTS, README, engineering audit/checklist, migrations, tenancy/security, AI/job standards, stabilization/regression reports, recovery tracker and source files. Historical 624/708-pass reports were checkpoints, not proof of this checkout. Current verification used an isolated source copy under `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108`; 1,052 source/assets matched original SHA-256 values before reporting. Root .env files and production data were excluded. Raw logs remain private there; durable compact results follow.

## Completion calculation

| Area | Earned / weight | Functional estimate | Verified closure | Production readiness |
|---|---:|---:|---:|---|
| SaaS foundation | 29.5 / 51 | 57.8% | 37.3% | NOT READY; required gaps remain |
| Phase 1 — Discovery | 32.25 / 43 | 75.0% | 41.9% | NOT READY; required gaps remain |
| Phase 2 — Company/contact intelligence | 35.75 / 42 | 85.1% | 61.9% | NOT READY; required gaps remain |
| Phase 3 — Enrichment/verification | 32.5 / 48 | 67.7% | 54.2% | NOT READY; required gaps remain |
| Phase 4 — AI/ICP qualification | 44 / 53 | 83.0% | 47.2% | NOT READY; required gaps remain |
| Phase 5 — Sales workspace/outreach | 57.75 / 70 | 82.5% | 71.4% | NOT READY; required gaps remain |
| Phase 6 — Integrations/API/webhooks/MCP | 88.75 / 120 | 74.0% | 65.0% | NOT READY; required gaps remain |
| Overall including foundation | 320.5 / 427 | 75.1% | 56.7% | BLOCKED: seven P0 workstreams |

## SaaS foundation — requirement matrix

| ID | Requirement | Status | Weight | Credit | Demonstrated behavior / remaining limitation | Source/test key; backlog |
|---|---|---|---:|---:|---|---|
| F01 | Google OAuth | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Real Auth.js provider and protected handoff; no fresh live customer login acceptance | AUTH; B07 |
| F02 | Public registration | NOT IMPLEMENTED | 3 | 0.00 | Signup blocked; Google admission and backend production validation remain restricted to one or two allowlisted accounts | AUTH; B03 |
| F03 | Account profile | COMPLETE AND VERIFIED | 1 | 1.00 | Actor-owned profile read/update and browser controls tested | ORG; - |
| F04 | Organization creation | COMPLETE AND VERIFIED | 3 | 1.00 | Verified actor creates independent organization; local lifecycle tests pass; admission remains separately gated | ORG; - |
| F05 | Workspace switching | COMPLETE AND VERIFIED | 3 | 1.00 | Server-verified membership and persisted selection; two-workspace browser tests pass | ORG; - |
| F06 | Organization memberships | COMPLETE AND VERIFIED | 3 | 1.00 | Active membership checked on requests and workers; removal/revocation tests pass | ORG; - |
| F07 | Roles and permissions | COMPLETE AND VERIFIED | 3 | 1.00 | Owner/admin/member/viewer permissions and denial cases tested | ORG; - |
| F08 | Team invitations | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Scoped tokens, acceptance, rejection and expiry tested; external invited-account admission not accepted | ORG; B03 |
| F09 | Organization profile | COMPLETE AND VERIFIED | 2 | 1.00 | Revisioned profile/services and manual edits tested; changes do not start scans | COMPANY; - |
| F10 | AI website-to-company-profile extraction | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Bounded website discovery, cited editable proposals and AI validation tested synthetically; live website/model acceptance pending | COMPANY; B07 |
| F11 | Domain verification | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | DNS challenge and role/isolation controls tested with synthetic resolver; external DNS ownership acceptance pending | ORG; B07 |
| F12 | Onboarding workflow | COMPLETE AND VERIFIED | 3 | 1.00 | Adapter-compatible read/save/resume/complete and saved profile/service history pass real isolated PostgreSQL; owner/admin/member/viewer and revocation covered; no implicit jobs/sends | ORG; B01 closed, milestone1-sqlite-final.xml and milestone1-postgres-final.xml |
| F13 | Personal settings | COMPLETE AND VERIFIED | 1 | 1.00 | Profile/preferences/appearance controls and persistence tested | ORG; - |
| F14 | Organization settings | COMPLETE AND VERIFIED | 2 | 1.00 | Scoped workspace settings and setup gates tested; operational deployment secrets remain server-only | ORG; - |
| F15 | Workspace isolation | PARTIAL | 3 | 0.75 | Confirmed summary exposure repaired with owned aggregates, strict nested allowlist and no cache; broader new-customer/mailbox/CRM isolation acceptance remains open | ORG; B02 defect closed; B04/B07 |
| F16 | Notifications | PARTIAL | 1 | 0.50 | Invitation activity menu works; broader job/campaign notifications and read-state lifecycle absent | ORG; B19 |
| F17 | Usage tracking | PARTIAL | 2 | 0.50 | AI request and source counters exist; unified customer metering/cost ledger and dashboard incomplete | USAGE; B18 |
| F18 | Plans and entitlements | NOT IMPLEMENTED | 2 | 0.00 | Feature switches are availability controls, not purchased plans; no plan entitlement service found | USAGE; B18 |
| F19 | Billing readiness | NOT IMPLEMENTED | 2 | 0.00 | No payment adapter, checkout, subscription lifecycle or billing webhook implementation found | USAGE; B18 |
| F20 | Support/help | COMPLETE AND VERIFIED | 1 | 1.00 | Searchable maintained help and support mailto link tested; no claim of live chat or ticket backend | HELP; - |
| F21 | Approved Privacy Policy and Terms | BLOCKED | 3 | 0.00 | Responsive development-review text exists; owner/legal approval not evidenced | HELP; B06 |
| F22 | Security and audit logging | PARTIAL | 3 | 0.50 | Signed requests, nonce/RBAC and audit records exist; metadata defect repaired; full request audit and staged release certification remain | ORG; B20/B07 |

## Phase 1 — Discovery — requirement matrix

| ID | Requirement | Status | Weight | Credit | Demonstrated behavior / remaining limitation | Source/test key; backlog |
|---|---|---|---:|---:|---|---|
| D01 | Global company discovery | PARTIAL | 3 | 0.50 | Country-aware Maps and reviewed acquisition work locally; global geographic/provider coverage not accepted | DISC; B08 |
| D02 | Overture and existing maps discovery | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Real Overture DuckDB/public S3 and OSM Overpass adapters with bounded queries; fresh live source yield not run | DISC; B07 |
| D03 | Other configured discovery providers | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Firecrawl search/scrape adapter exists behind explicit feature/configuration gates; synthetic tests pass, live acceptance pending | DISC; B07 |
| D04 | AI/natural-language search | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Real structured interpretation and reviewed search plan endpoints; gateway mocked in fresh checks | AI; B12 |
| D05 | Country, region and city selection | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | ISO country validation and bounded Nominatim selection/cache work; live global city lookup not validated | DISC; B08 |
| D06 | Multiple-country searches | COMPLETE AND VERIFIED | 2 | 1.00 | Bounded list of explicit markets/countries expands into stored runs; configuration and routing tested | DISC; - |
| D07 | Industry and category filters | PARTIAL | 2 | 0.50 | Configured vertical/category mappings work; arbitrary industry taxonomy/provider coverage incomplete | DISC; B08 |
| D08 | ICP-based discovery | PARTIAL | 2 | 0.50 | Approved ICP prefills industries/geography and displays unsupported evidence criteria; not all ICP criteria are executable discovery filters | ICP; B08 |
| D09 | Company size and other supported filters | PARTIAL | 2 | 0.25 | Typed targeting fields exist; size evidence mainly website employee count, not a reliable discovery-provider filter | DISC; B08 |
| D10 | Progressive search results | COMPLETE AND VERIFIED | 2 | 1.00 | Persisted batch progress and partial qualified results tested; progress is batch-level, not instantaneous provider streaming | DISC; - |
| D11 | Background discovery jobs | COMPLETE AND VERIFIED | 3 | 1.00 | Persisted jobs, scoped dispatch and bounded execution tested; no reliance on UI-only execution | DISC; - |
| D12 | Search progress and cancellation | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Progress, pause/cancel/resume and leases tested locally; blocking provider calls cannot guarantee immediate cancellation | DISC; B08 |
| D13 | Saved searches | COMPLETE AND VERIFIED | 1 | 1.00 | Scoped revisioned search drafts, approval and reuse tested; saving starts no scan | DISC; - |
| D14 | Search history | COMPLETE AND VERIFIED | 1 | 1.00 | Persisted run/job/event history and scoped API pagination tested | DISC; - |
| D15 | Company deduplication | COMPLETE AND VERIFIED | 3 | 1.00 | Canonical workspace identity, domains/phones/names and legacy alias preservation tested | DISC; - |
| D16 | Source provenance | COMPLETE AND VERIFIED | 3 | 1.00 | Observed source records and policy distinctions retained; owner imports are not labelled public evidence | DISC; - |
| D17 | Geographic coverage | PARTIAL | 2 | 0.25 | ISO/global inputs supported; no country-by-country source coverage, contact yield or unsupported-region acceptance matrix | DISC; B08 |
| D18 | Search quotas and cost controls | PARTIAL | 3 | 0.50 | Raw/result/query/scrape caps and reservations exist; customer-plan spending ceilings and complete cost metering absent | DISC; B18 |
| D19 | Workspace isolation | COMPLETE AND VERIFIED | 3 | 1.00 | Discovery jobs, prospects, source evidence and resource access scoped and regression-tested; global isolation exception is F15 | DISC; - |

## Phase 2 — Company/contact intelligence — requirement matrix

| ID | Requirement | Status | Weight | Credit | Demonstrated behavior / remaining limitation | Source/test key; backlog |
|---|---|---|---:|---:|---|---|
| C01 | Company records | COMPLETE AND VERIFIED | 3 | 1.00 | Canonical prospect/company observations and APIs tested | COMPANY; - |
| C02 | Company detail pages | COMPLETE AND VERIFIED | 2 | 1.00 | Company detail loads scoped records, contacts and source status in browser tests | COMPANY; - |
| C03 | Website/domain extraction | COMPLETE AND VERIFIED | 2 | 1.00 | Public source URLs and domain normalization tested; absent official website remains unknown | COMPANY; - |
| C04 | Public company information | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Bounded official-page excerpts and structured attributes exist; broad live coverage not accepted | COMPANY; B09 |
| C05 | Products and services extraction | PARTIAL | 2 | 0.50 | Explicit JSON-LD/catalog/service snippets extracted; broader varied-site product/service coverage incomplete | COMPANY; B09 |
| C06 | Industry classification | PARTIAL | 2 | 0.50 | Source verticals and explicit website industry exist; general reliable cross-taxonomy classification incomplete | COMPANY; B09 |
| C07 | Contact records | COMPLETE AND VERIFIED | 3 | 1.00 | Actual person records, evidence, edits, lifecycle and scoped listings tested | PEOPLE; - |
| C08 | Decision-maker discovery | PARTIAL | 3 | 0.50 | Real explicit public JSON-LD Person data discovered; no invented names/roles, but wider team-page/provider coverage missing | PEOPLE; B09 |
| C09 | Professional roles | COMPLETE AND VERIFIED | 2 | 1.00 | Only source-provided jobTitle/department/seniority retained with employment-unverified labels | PEOPLE; - |
| C10 | Company/contact relationships | COMPLETE AND VERIFIED | 3 | 1.00 | Workspace-qualified canonical company association and role views tested | PEOPLE; - |
| C11 | Public business email discovery | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Published mailto/structured source addresses extracted and provenance tested; live representative yield not validated | PEOPLE; B07 |
| C12 | Public phone discovery | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Public tel/structured numbers extracted; no fresh live geographic coverage acceptance | PEOPLE; B09 |
| C13 | Contact evidence | COMPLETE AND VERIFIED | 3 | 1.00 | Public URLs, collected time, observed/unverified status and confidence basis shown and tested | PEOPLE; - |
| C14 | Source freshness | PARTIAL | 2 | 0.50 | Collection timestamps/evidence age exist; reliable refresh scheduling and stale-employment policy incomplete | PEOPLE; B11 |
| C15 | Contact deduplication | COMPLETE AND VERIFIED | 3 | 1.00 | Canonical source/company-aware person keys and revision-safe merging tested | PEOPLE; - |
| C16 | Contact search and filtering | COMPLETE AND VERIFIED | 2 | 1.00 | Scoped pagination, text/status/company filtering and detail paths tested | PEOPLE; - |
| C17 | Workspace ownership | COMPLETE AND VERIFIED | 3 | 1.00 | People/evidence inaccessible without matching organization and membership; denial tests pass | PEOPLE; - |

## Phase 3 — Enrichment/verification — requirement matrix

| ID | Requirement | Status | Weight | Credit | Demonstrated behavior / remaining limitation | Source/test key; backlog |
|---|---|---|---:|---:|---|---|
| E01 | Company enrichment | COMPLETE AND VERIFIED | 3 | 1.00 | Bounded public website information refresh persists evidence and job results; local contract tested | ENRICH; - |
| E02 | Contact enrichment | PARTIAL | 3 | 0.50 | Re-reads explicit official public person data and evidence; wider contact intelligence/provider coverage incomplete | ENRICH; B10 |
| E03 | Public website enrichment | COMPLETE AND VERIFIED | 2 | 1.00 | SSRF-protected bounded crawl and explicit structured data/excerpts tested | ENRICH; - |
| E04 | Provider abstraction | PARTIAL | 2 | 0.25 | Shared crawler/DNS/job boundary exists; no complete external enrichment-adapter registry and unified provider contract | ENRICH; B10 |
| E05 | Provider fallback/waterfall | NOT IMPLEMENTED | 2 | 0.00 | No multi-provider company/contact enrichment waterfall found; discovery fallback does not satisfy this requirement | ENRICH; B10 |
| E06 | Configured external enrichment providers | NOT IMPLEMENTED | 3 | 0.00 | No functional customer enrichment-provider adapter found; AI/Firecrawl discovery are not substitutes | ENRICH; B10 |
| E07 | Email syntax validation | COMPLETE AND VERIFIED | 3 | 1.00 | Address syntax and invalid-input labels tested | ENRICH; - |
| E08 | Domain/MX checks | COMPLETE AND VERIFIED | 3 | 1.00 | Bounded DNS/MX checks distinguish missing/unknown/domain-acceptance results; not mailbox proof | ENRICH; - |
| E09 | Provider-backed email verification | NOT IMPLEMENTED | 3 | 0.00 | No mailbox/deliverability verification provider implemented; not an external-credential-only blocker | ENRICH; B10 |
| E10 | Honest verification labels | COMPLETE AND VERIFIED | 3 | 1.00 | Publicly observed, owner-provided, technical checks and unknown states remain distinct; no deliverable claims | ENRICH; - |
| E11 | Phone normalization | PARTIAL | 2 | 0.50 | Legacy comparable-digit normalization exists; international country-aware E.164 and person-phone validation incomplete | ENRICH; B11 |
| E12 | Evidence provenance | COMPLETE AND VERIFIED | 3 | 1.00 | Source URL and observed timestamp retained with scoped parent ownership | ENRICH; - |
| E13 | Confidence and freshness | PARTIAL | 2 | 0.50 | Evidence age/status available; calibrated confidence, expiry and refresh policy incomplete | ENRICH; B11 |
| E14 | Single-record enrichment | COMPLETE AND VERIFIED | 2 | 1.00 | Reviewed one-resource job executes and records results with authorization | ENRICH; - |
| E15 | Bulk enrichment | COMPLETE AND VERIFIED | 3 | 1.00 | Bounded bulk resources, reservations and per-item results tested | ENRICH; - |
| E16 | Enrichment job tracking | COMPLETE AND VERIFIED | 2 | 1.00 | Persisted queued/running/results/error lifecycle and paginated history tested | ENRICH; - |
| E17 | Enrichment usage limits | PARTIAL | 3 | 0.50 | Resource and request safety caps work; provider spend and purchased-plan entitlements incomplete | ENRICH; B18 |
| E18 | Error handling | COMPLETE AND VERIFIED | 2 | 1.00 | Safe transient/permanent outcomes, unknown results and per-item errors tested | ENRICH; - |
| E19 | Caching and retries | PARTIAL | 2 | 0.50 | Cached public data, bounded retries/leases exist; multi-provider uncertain-spend/cache freshness policy absent | ENRICH; B10 |

## Phase 4 — AI/ICP qualification — requirement matrix

| ID | Requirement | Status | Weight | Credit | Demonstrated behavior / remaining limitation | Source/test key; backlog |
|---|---|---|---:|---:|---|---|
| Q01 | Manual ICP builder | COMPLETE AND VERIFIED | 2 | 1.00 | Validated criteria editing and scoped persistence tested in API and browser | ICP; - |
| Q02 | Multiple ICPs | COMPLETE AND VERIFIED | 2 | 1.00 | Independent named profiles, duplication and listing tested | ICP; - |
| Q03 | ICP activation | COMPLETE AND VERIFIED | 2 | 1.00 | Revisioned activation/status controls tested; activation starts no acquisition | ICP; - |
| Q04 | ICP versioning | COMPLETE AND VERIFIED | 2 | 1.00 | Version history/compare and revision-conflict handling implemented and tested | ICP; - |
| Q05 | Company-profile-based AI ICP generation | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Real authorized suggest endpoint uses saved company services and shared gateway; synthetic outputs validated, live acceptance missing | ICP; B07 |
| Q06 | Conversational AI ICP builder | PARTIAL | 3 | 0.50 | Description suggestions and bounded follow-up refinement exist; dedicated persisted conversational builder journey not complete | ICP; B12 |
| Q07 | AI-assisted ICP editing | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Leaf-path refinement preserves unrelated criteria and requires review; live model/browser acceptance incomplete | ICP; B12 |
| Q08 | Structured output validation | COMPLETE AND VERIFIED | 3 | 1.00 | Pydantic schemas, explicit patch paths, unsupported-country/claim rejection tested | AI; - |
| Q09 | Natural-language lead search | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Shared gateway interprets targeting into reviewed acquisition plan; no automatic scan or send; external model acceptance missing | AI; B07 |
| Q10 | ICP-based company qualification | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Evidence-based structured comparisons and honest unknowns work; broader live field/industry acceptance incomplete | ICP; B14 |
| Q11 | Contact relevance | COMPLETE AND VERIFIED | 2 | 1.00 | Source roles/departments/seniority compared with criteria; unverified employment remains explicit | ICP; - |
| Q12 | Explainable scoring | COMPLETE AND VERIFIED | 3 | 1.00 | Per-field reasoning, exclusions, evidence coverage and weights tested; fit is not send eligibility | ICP; - |
| Q13 | AI company summaries | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Extractive cited snippets validated against exact source text; real gateway path exists, live model acceptance pending | AI; B07 |
| Q14 | Recommendations | PARTIAL | 2 | 0.50 | Stored-company fit rows and page-local sorting/filtering work; populated end-to-end ranking/action journey not fully tested | ICP; B14 |
| Q15 | Saved targeting profiles | COMPLETE AND VERIFIED | 2 | 1.00 | Scoped persistent ICPs and revisions tested | ICP; - |
| Q16 | Saved searches | COMPLETE AND VERIFIED | 1 | 1.00 | Validated scoped drafts and explicit approvals tested | DISC; - |
| Q17 | Workspace-aware AI context | COMPLETE AND VERIFIED | 3 | 1.00 | Verified workspace companies/profiles and bounded read tools feed AI; cross-workspace denial tests pass | AI; - |
| Q18 | Existing Vertex AI integration | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Real shared Vertex structured generation adapter exists; current assessment did not use live model credentials | AI; B07 |
| Q19 | AI gateway fallback | IMPLEMENTED, NOT FULLY VERIFIED | 2 | 0.75 | Existing authorized router, retries/health and configured fallback tested with synthetic providers; live fallback failover not accepted | AI; B07 |
| Q20 | AI usage and cost controls | PARTIAL | 3 | 0.50 | Committed per-workspace/global daily reservations and token/time bounds work; unified money/plan accounting missing | AI; B18 |
| Q21 | AI tool permissions | COMPLETE AND VERIFIED | 3 | 1.00 | Fixed schemas, authorized reads and reviewed limited actions; no arbitrary SQL/URLs, sends or autonomous scan actions | AI; - |
| Q22 | Prompt-injection protections | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Untrusted-source separation, exact citations and bounded tools tested; staged broader adversarial acceptance not run | AI; B13 |

## Phase 5 — Sales workspace/outreach — requirement matrix

| ID | Requirement | Status | Weight | Credit | Demonstrated behavior / remaining limitation | Source/test key; backlog |
|---|---|---|---:|---:|---|---|
| S01 | Lead lists | COMPLETE AND VERIFIED | 2 | 1.00 | Named scoped lists, revision edits, archive/history and pagination tested | SALES; - |
| S02 | Company and contact list membership | COMPLETE AND VERIFIED | 3 | 1.00 | Owned canonical company/person membership and duplicate/foreign-resource denial tested | SALES; - |
| S03 | Saved views | PARTIAL | 1 | 0.50 | Named lists and runtime filters exist; reusable personal/team saved-view definitions incomplete | SALES; B15 |
| S04 | Prospect statuses | COMPLETE AND VERIFIED | 2 | 1.00 | Company/contact lifecycle states distinct from send eligibility and tested | SALES; - |
| S05 | Notes | COMPLETE AND VERIFIED | 1 | 1.00 | Scoped activity notes and history tested | SALES; - |
| S06 | Tasks | COMPLETE AND VERIFIED | 2 | 1.00 | Revisioned tasks, priorities, due dates and lifecycle tested in API/browser | SALES; - |
| S07 | Follow-ups | COMPLETE AND VERIFIED | 2 | 1.00 | Persisted follow-up/task paths and state handling tested | SALES; - |
| S08 | Activity history | COMPLETE AND VERIFIED | 2 | 1.00 | Owned company/outreach activity and lifecycle records tested | SALES; - |
| S09 | Assignment to team members | COMPLETE AND VERIFIED | 2 | 1.00 | Only active workspace members assignable; authorization tested | SALES; - |
| S10 | CSV/XLSX exports | COMPLETE AND VERIFIED | 3 | 1.00 | Existing CSV/XLSX generation passes; list CSV formula/count/budget/tenant safety verified on PostgreSQL; generic XLSX lacks equivalent reviewed Sheets workflow | SALES; - |
| S11 | Campaign creation | PARTIAL | 3 | 0.50 | Reviewed workflow/campaign builder exists; independent customer mailbox prerequisites and full customer launch path missing | SALES; B04 |
| S12 | Campaign drafts | PARTIAL | 2 | 0.50 | Reviewed campaigns and message previews exist; coherent customer draft-to-approval mailbox journey incomplete | SALES; B15 |
| S13 | Templates | COMPLETE AND VERIFIED | 2 | 1.00 | Editable/rendered templates and approved signatures tested; internal experiments are separate, not SaaS default | MAIL; - |
| S14 | Personalization | COMPLETE AND VERIFIED | 2 | 1.00 | Bounded factual rendering and evidence-aware copy tested; no fabricated claims | MAIL; - |
| S15 | Recipient validation | COMPLETE AND VERIFIED | 3 | 1.00 | Syntax, public/owner evidence, suppression and unsafe-recipient guards tested | MAIL; - |
| S16 | Customer-specific Gmail connections | NOT IMPLEMENTED | 3 | 0.00 | Only global internal app-password mailbox transport exists; no per-customer Gmail OAuth/token routing | MAIL; B04 |
| S17 | SMTP/IMAP or Gmail API support | COMPLETE AND VERIFIED | 2 | 1.00 | Real Gmail/Hostinger SMTP+IMAP TLS adapters tested with synthetic transports; Gmail REST API is not implemented or claimed | MAIL; - |
| S18 | Mailbox OAuth connection lifecycle | NOT IMPLEMENTED | 3 | 0.00 | Google login and Sheets OAuth do not provide mailbox scopes; no customer mail authorize/callback/refresh/revoke lifecycle | MAIL; B04 |
| S19 | Scheduling | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Persisted schedules, dispatch and time windows tested locally; customer mailbox/cloud end-to-end acceptance incomplete | SALES; B07 |
| S20 | Sending limits | COMPLETE AND VERIFIED | 3 | 1.00 | Hourly/daily caps, send spacing and transactional reservations tested for existing sender | MAIL; - |
| S21 | Campaign pause/resume | COMPLETE AND VERIFIED | 2 | 1.00 | Durable pause/resume/cancel controls and worker checks tested | SALES; - |
| S22 | Mocked or sandbox sending | COMPLETE AND VERIFIED | 3 | 1.00 | Synthetic Gmail/SMTP sending and canary protections tested; no real email sent in assessment | MAIL; - |
| S23 | Reply synchronization | COMPLETE AND VERIFIED | 2 | 1.00 | Existing internal IMAP reply/thread sync tested with fixtures; customer-mail route remains S16/S18 | MAIL; - |
| S24 | Bounce handling | COMPLETE AND VERIFIED | 3 | 1.00 | Hard/soft bounce, DSN and threshold pause protections tested | MAIL; - |
| S25 | Unsubscribe handling | COMPLETE AND VERIFIED | 3 | 1.00 | Tracking token unsubscribe lifecycle and suppression tested | MAIL; - |
| S26 | Do-not-contact suppression | COMPLETE AND VERIFIED | 3 | 1.00 | Suppression and contacted history prevent unsafe resend; historical records preserved | MAIL; - |
| S27 | Duplicate-send prevention | COMPLETE AND VERIFIED | 3 | 1.00 | Idempotency and prior-contact protections tested for existing sender | MAIL; - |
| S28 | Campaign analytics | PARTIAL | 2 | 0.50 | Status/reply/bounce/tracking counts exist; complete customer mailbox attribution and finalized analytics UX incomplete | SALES; B15 |
| S29 | Workspace-specific email ownership | PARTIAL | 3 | 0.50 | Internal transport restricted and workflow records scoped; genuine independent customer sender credentials/routing absent | MAIL; B04 |

## Phase 6 — Integrations/API/webhooks/MCP — requirement matrix

| ID | Requirement | Status | Weight | Credit | Demonstrated behavior / remaining limitation | Source/test key; backlog |
|---|---|---|---:|---:|---|---|
| G01 | Sheets OAuth connection | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Separate scoped read/write consent, state and lifecycle tested synthetically; live consent acceptance pending | SHEETS; B07 |
| G02 | Sheets redirect callback | COMPLETE AND VERIFIED | 3 | 1.00 | Real protected callback/state checks and browser synthetic callback pass | SHEETS; - |
| G03 | Sheets credential encryption | COMPLETE AND VERIFIED | 3 | 1.00 | Server-only encryption, workspace binding and redaction tested | SHEETS; - |
| G04 | Sheets import | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Reviewed bounded read, column preview and canonical import implemented; real customer sheet acceptance pending | SHEETS; B07 |
| G05 | Sheets export | IMPLEMENTED, NOT FULLY VERIFIED | 3 | 0.75 | Immutable reviewed fixed-range RAW writes, explicit retries and lease fencing tested; no live Sheets write acceptance | SHEETS; B07 |
| G06 | Sheets column mapping | COMPLETE AND VERIFIED | 2 | 1.00 | Bounded import preview, validated mapping and required fields tested; export uses fixed reviewed columns | SHEETS; - |
| G07 | Sheets duplicate handling | COMPLETE AND VERIFIED | 3 | 1.00 | Scoped canonical identity and request idempotency tested | SHEETS; - |
| G08 | Sheets real provider validation | BLOCKED | 3 | 0.00 | Live owner/customer consent and controlled read/write not run under reporting restrictions | SHEETS; B07 |
| R01 | HubSpot adapter | NOT IMPLEMENTED | 3 | 0.00 | No functional adapter, auth/callback or sync service found | CRM; B16 |
| R02 | Pipedrive adapter | NOT IMPLEMENTED | 3 | 0.00 | No functional adapter, auth/callback or sync service found | CRM; B16 |
| R03 | Other implemented CRM adapters | NOT APPLICABLE | 0 | 0.00 | None found; no other named CRM in the approved scope, so no invented additional provider requirement | CRM; - |
| R04 | CRM authentication | NOT IMPLEMENTED | 3 | 0.00 | No CRM connection authentication or encrypted refresh/revocation implementation | CRM; B16 |
| R05 | CRM data mapping | NOT IMPLEMENTED | 2 | 0.00 | No reviewed CRM company/contact field mapping implemented | CRM; B16 |
| R06 | CRM synchronization | NOT IMPLEMENTED | 3 | 0.00 | No idempotent CRM import/export/incremental sync worker | CRM; B16 |
| R07 | CRM conflict handling | NOT IMPLEMENTED | 2 | 0.00 | No remote-ID/version conflict policy or reviewed resolution | CRM; B16 |
| R08 | CRM retries | NOT IMPLEMENTED | 2 | 0.00 | No provider-specific retry, uncertainty or rate-limit handling | CRM; B16 |
| R09 | CRM connection health | NOT IMPLEMENTED | 2 | 0.00 | No CRM health/last-sync/error UI or backend status | CRM; B16 |
| A01 | Public REST API routes | COMPLETE AND VERIFIED | 3 | 1.00 | Functional scoped v1 company/contact/ICP/list/task/enrichment/campaign/search routes tested | API; - |
| A02 | REST API versioning | COMPLETE AND VERIFIED | 2 | 1.00 | Explicit v1 namespace and OpenAPI version tested | API; - |
| A03 | Workspace-scoped API keys | COMPLETE AND VERIFIED | 3 | 1.00 | Hashed one-time credentials bind verified workspace and active owner; denied foreign contexts tested | API; - |
| A04 | Key creation and rotation | COMPLETE AND VERIFIED | 3 | 1.00 | One-time creation, rotate/revoke and non-logging of secrets tested | API; - |
| A05 | API permission scopes | COMPLETE AND VERIFIED | 3 | 1.00 | Per-route and composed resource scopes enforced and tested | API; - |
| A06 | API rate limits | COMPLETE AND VERIFIED | 3 | 1.00 | Bounded credential request allowance with transactional consumption tested | API; - |
| A07 | API pagination | COMPLETE AND VERIFIED | 2 | 1.00 | Bounded public listings/page sizes implemented and tested | API; - |
| A08 | API documentation | PARTIAL | 1 | 0.50 | Live scoped OpenAPI and developer UI exist; older standalone guides need reconciliation/examples | API; B17 |
| A09 | API audit logging | PARTIAL | 3 | 0.50 | Key lifecycle/usage recorded; complete per-request success/denial/abuse audit coverage not demonstrated | API; B20 |
| W01 | Webhook event registry | COMPLETE AND VERIFIED | 2 | 1.00 | Bounded registry for company.created/contact.created/contact.updated with minimal payloads tested | WEBHOOK; - |
| W02 | Webhook subscription management | COMPLETE AND VERIFIED | 3 | 1.00 | Scoped endpoint/topics/revision/pause/rotation controls tested | WEBHOOK; - |
| W03 | Signed webhook delivery | COMPLETE AND VERIFIED | 3 | 1.00 | HMAC body/timestamp/id headers and synthetic receiver verification tested | WEBHOOK; - |
| W04 | Webhook retries | COMPLETE AND VERIFIED | 3 | 1.00 | Bounded five attempts, backoff and timeout/429 behavior tested | WEBHOOK; - |
| W05 | Webhook idempotency | COMPLETE AND VERIFIED | 3 | 1.00 | Transactional outbox identity and independent PostgreSQL reservation tested | WEBHOOK; - |
| W06 | Webhook delivery logs | COMPLETE AND VERIFIED | 2 | 1.00 | Scoped delivery/attempt history and safe error metadata tested | WEBHOOK; - |
| W07 | Webhook failure handling | COMPLETE AND VERIFIED | 3 | 1.00 | Unknown final outcome, expired lease and endpoint revision/crash recovery tested | WEBHOOK; - |
| W08 | Webhook tenant isolation | COMPLETE AND VERIFIED | 3 | 1.00 | Endpoint/event/history access and active membership worker checks tested | WEBHOOK; - |
| W09 | Real webhook receiver testing | BLOCKED | 3 | 0.00 | Fresh receivers were synthetic; approved external HTTPS receiver/cloud scheduling acceptance absent | WEBHOOK; B07 |
| M01 | Genuine MCP server | COMPLETE AND VERIFIED | 3 | 1.00 | Mounted maintained FastMCP SDK server; actual official client discovery/call tests pass | MCP; - |
| M02 | Supported MCP protocol transport | COMPLETE AND VERIFIED | 3 | 1.00 | Streamable HTTP /mcp/ lifecycle tested; no claim of stdio or legacy SSE | MCP; - |
| M03 | MCP authentication | COMPLETE AND VERIFIED | 3 | 1.00 | Bearer workspace-key middleware, host restrictions and authentication tested | MCP; - |
| M04 | MCP workspace-scoped credentials | COMPLETE AND VERIFIED | 3 | 1.00 | Fixed organization and active actor membership revalidated for tools | MCP; - |
| M05 | MCP permission scopes | COMPLETE AND VERIFIED | 3 | 1.00 | mcp:use plus domain-specific scopes required and tested | MCP; - |
| M06 | MCP available tools | COMPLETE AND VERIFIED | 2 | 1.00 | Nine registered tools backed by schema validation and bounded responses tested | MCP; - |
| M07 | MCP domain-service integration | COMPLETE AND VERIFIED | 3 | 1.00 | Real company/contact/ICP/list/campaign reads and reviewed action proposals, not mock settings placeholders | MCP; - |
| M08 | MCP client compatibility | PARTIAL | 2 | 0.75 | Official SDK client works; named external desktop/hosted AI clients not accepted | MCP; B17 |
| M09 | MCP credential revocation | COMPLETE AND VERIFIED | 3 | 1.00 | Rotation/removal/role changes invalidate subsequent calls; tests pass | MCP; - |
| M10 | MCP audit events | COMPLETE AND VERIFIED | 3 | 1.00 | Success and denial/invalid-input records with tool names, not credential payloads, tested | MCP; - |
| M11 | MCP documentation | PARTIAL | 1 | 0.50 | Developer screen and protocol implementation exist; consolidated client setup/scope/revocation guide incomplete | MCP; B17 |

## Source and automated-test evidence keys

Paths are source evidence; tests ran in the completed suites unless explicitly absent. Directory/glob entries identify a family, not additional passing suites.

| Key | Exact files/services inspected | Tests/evidence |
|---|---|---|
| AUTH | dashboard/auth.ts; app/config/settings.py; app/api/security.py | tests/unit/test_internal_auth.py; dashboard/auth-e2e/auth.spec.ts |
| ORG | app/api/organization.py; app/platform/workspaces.py; app/platform/context.py; app/platform/onboarding.py; app/api/routes/organizations.py; dashboard/components/workspaces/ | tests/unit/test_workspace_creation.py; tests/unit/test_workspace_selection.py; tests/unit/test_workspace_invitations.py; dashboard/workspace-e2e/selection.spec.ts; release-gap-probes.xml |
| COMPANY | app/platform/company_profiles.py; app/platform/company_discovery.py; app/prospecting/company_facts.py; app/api/routes/people.py; dashboard/app/leads/ | tests/unit/test_company_discovery.py; tests/unit/test_company_autofill.py; tests/unit/test_people.py; dashboard/e2e/prospecting-completion.spec.ts |
| DISC | app/discovery/overture.py; app/discovery/osm.py; app/discovery/resolver.py; app/acquisition/worker.py; app/prospecting/searches.py; app/config/locations.py; app/normalization/dedupe.py; dashboard/app/find-leads/ | tests/unit/test_acquisition*.py; tests/unit/test_discovery_searches.py; tests/unit/test_scan_resume.py; tests/unit/test_source_scheduling.py; dashboard/e2e/ |
| PEOPLE | app/people/extraction.py; app/people/service.py; app/people/verification.py; app/api/routes/people.py; dashboard/app/contacts/ | tests/unit/test_people.py; tests/unit/test_prospects.py; tests/unit/test_global_identity_aliases.py; dashboard/e2e/prospecting-completion.spec.ts |
| ENRICH | app/intelligence/jobs.py; app/platform/contact_verification.py; app/enrichment/; app/normalization/phones.py; app/api/routes/intelligence.py; dashboard/app/enrichment/ | tests/unit/test_intelligence_jobs.py; tests/unit/test_enrichment.py; tests/unit/test_people.py; dashboard/e2e/prospecting-completion.spec.ts |
| ICP | app/icp/service.py; app/icp/builder.py; app/icp/matching.py; app/intelligence/qualification.py; app/api/routes/icp.py; dashboard/app/settings/icp/; dashboard/app/recommendations/ | tests/unit/test_icp*.py; dashboard/__tests__/; dashboard/workspace-e2e/selection.spec.ts |
| AI | app/acquisition/ai_router.py; app/acquisition/ai.py; app/platform/ai_usage.py; app/intelligence/summary.py; app/assistant/service.py; app/prospecting/tools.py; dashboard/app/assistant/ | tests/unit/test_ai_router.py; tests/unit/test_lead_assistant.py; tests/unit/test_company_autofill*.py; tests/unit/test_icp*.py |
| SALES | app/sales/collections.py; app/sales/tasks.py; app/api/routes/sales.py; app/workflows/; app/exports/; dashboard/app/lists/; dashboard/app/tasks/; dashboard/app/campaigns/ | tests/unit/test_sales*.py; tests/unit/test_exports.py; tests/unit/test_workflow*.py; tests/integration/test_postgres.py; dashboard/e2e/ |
| MAIL | app/mail/config.py; app/mail/providers.py; app/mail/service.py; app/mail/templates.py; app/api/routes/mail.py; dashboard/app/outreach/; dashboard/app/settings/email/ | tests/unit/test_gmail*.py; tests/unit/test_mail_provider.py; tests/unit/test_contacted_registry.py; tests/unit/test_tracking_lifecycle.py; tests/unit/test_special_use.py |
| SHEETS | app/integrations/service.py; app/integrations/sheet_exports.py; app/acquisition/sheets.py; app/api/routes/integrations.py; dashboard/components/workspaces/integrations.tsx; dashboard/components/workspaces/sheet-exports.tsx | tests/unit/test_customer_integrations.py; tests/unit/test_customer_sheet_exports.py; tests/unit/test_customer_sheets_import.py; tests/integration/test_postgres.py; dashboard/sheet-export-e2e/; dashboard/integration-e2e/ |
| CRM | app/integrations/ currently has Sheets services only; no hubspot.py or pipedrive.py found; dashboard/components/workspaces/integrations.tsx | No CRM adapter or synchronization tests found; missing tests are NOT RUN, never passing |
| API | app/developer/keys.py; app/api/routes/public_v1.py; app/api/routes/developer.py; app/api/security.py; dashboard/app/settings/developer/ | tests/unit/test_developer_api.py; tests/unit/test_developer_migrations.py; dashboard/developer-e2e/ |
| WEBHOOK | app/webhooks/service.py; app/webhooks/worker.py; app/webhooks/dispatch.py; app/api/routes/developer.py; docs/SIGNED_WEBHOOKS.md | tests/unit/test_signed_webhooks.py; tests/integration/test_postgres.py; dashboard/developer-e2e/ |
| MCP | app/developer/mcp_server.py; app/developer/approvals.py; app/developer/keys.py; app/api/server.py; dashboard/app/settings/developer/ | tests/unit/test_mcp_protocol.py; tests/unit/test_developer_api.py; dashboard/developer-e2e/ |
| USAGE | app/platform/modules.py; app/platform/ai_usage.py; app/acquisition/worker.py; app/platform/product_help.py; dashboard/app/settings/limits/; no billing adapter found | tests/unit/test_ai_router.py; tests/unit/test_heysow_modules.py; no purchased-plan/billing acceptance tests found |
| HELP | app/platform/product_help.py; app/api/routes/help.py; dashboard/app/help/; dashboard/app/privacy/; dashboard/app/terms/ | dashboard/workspace-e2e/selection.spec.ts; dashboard/auth-e2e/auth.spec.ts |

### Exact public route inventory from current decorators

| Method | Actual route |
|---|---|
| GET | `/api/v1/companies` |
| GET | `/api/v1/companies/{business_id}` |
| GET | `/api/v1/contacts` |
| GET | `/api/v1/contacts/{key}` |
| GET | `/api/v1/icps` |
| GET | `/api/v1/companies/{business_id}/icp-fit/{profile_id}` |
| GET | `/api/v1/lists` |
| GET | `/api/v1/lists/{key}` |
| POST | `/api/v1/lists` |
| GET | `/api/v1/tasks` |
| POST | `/api/v1/enrichment/jobs` |
| GET | `/api/v1/enrichment/jobs/{key}` |
| GET | `/api/v1/campaigns` |
| GET | `/api/v1/openapi.json` |
| GET | `/api/v1/searches` |
| POST | `/api/v1/searches` |

## Customer-facing UI audit

Legend: **W** = relevant assertions in completed browser suites; **U** = frontend unit evidence; **API** = relevant backend tests; **S** = source inspection only; **B** = build compiled route, not runtime proof. Conditional pages need their feature flag and verified workspace. A successful heading/render does not certify populated data or every control. Mobile **shell W / S** means the shell has narrow-width evidence but that entire populated page has not been independently certified.

| Screen and actual route | Exists / loads | Data and backend | Core controls | Authorization | Empty/loading/error | Mobile | Tests and remaining issue |
|---|---|---|---|---|---|---|---|
| Overview `/` | B, W | Scoped overview API, W/API | Navigation/status W | Workspace API | U/S | Shell W | Backend/dashboard browser; no public customer acceptance |
| Find Leads `/find-leads`, `/find-leads/ai`, `/find-leads/import` | B, W | Maps/acquisition/search APIs | Draft/approve/progress W; live provider not run | API/W | U/W | Shell W/S | Workflow/workspace suites; taxonomy/size/global source gaps D01–D09 |
| Discovery `/discovery/[runId]`, `/acquisition/jobs/[id]` | B, W | Persisted scoped results/progress | Review/cancel/resume locally tested | API/W | API/U | S | Batch-level progress; live in-flight cancellation not certified |
| Companies `/leads`, `/leads/[leadId]`, `/master-leads` | B, W | Canonical company/intelligence APIs | Details/status/enrich locally tested | API/W | U/W | Shell W/S | People/prospecting browser; varied public-site coverage incomplete |
| Contacts `/contacts`, `/contacts/[contactId]` | B, W | Actual person/evidence APIs | Search/edit/details locally tested | API/W | U/W | S | Public Person extraction is narrow; no invented decision makers |
| Enrichment `/enrichment`, `/enrichment/[jobId]` | B, W | Persisted intelligence jobs | Reviewed bounded start/results W/API | API/W | U/W | S | External waterfall/mailbox verification absent |
| ICP `/settings/icp` | B, W | ICP CRUD/history/suggest/refine APIs | Manual create/version W; AI U/API | API/W | U/W | Shell W/S | Live AI and complete conversational journey pending |
| Recommendations `/recommendations` | B, W heading | Stored-company fit API/U | Page-local filters/list action S/U | API | S/U | S | Populated ranking/action browser journey incomplete |
| Lists `/lists`, `/lists/[listId]` | B, W | Scoped list/member/export APIs | Create/edit/archive/membership W | API/W | U/W | Shell W/S | Saved views incomplete; CSV safety freshly verified |
| Tasks `/tasks` | B, W | Scoped revisioned task APIs | Create/assign/edit/status/dates W | API/W | U/W | Shell W/S | Existing workspace path works; broader notification lifecycle pending |
| Campaigns `/campaigns`, `/campaigns/[campaignId]` | B, W | Workflow/campaign APIs | Reviewed lifecycle W/API | API/W | U/W | Shell W/S | Customer mailbox and draft-to-live journey incomplete |
| Outreach `/outreach`, `/outreach/new`, `/outreach/results`, message details | B, W | Owned workflow/internal mail APIs | Preview/pause/review W; synthetic send API | API/W | U/W | Shell W/S | Internal sender only; no customer mail readiness claim |
| Schedules `/schedules` | B, W | Persistent workflow schedules | Create/edit/pause local W/API | API/W | U/W | Shell W/S | Customer mailbox and actual cloud acceptance pending |
| Integrations `/settings/integrations`, Sheets callback | B, W when enabled | Scoped Sheets connection/import/export | Synthetic consent/import/export W | API/W | U/W | S | No CRM adapter; live Google writes not tested |
| Account `/account`, `/account/profile`, `/account/appearance`, `/account/security` | B; relevant profile W | Actor-owned profile/preferences; Google controls | Profile/preferences U/W; security is not new auth backend | API/W | U/S | Shell W/S | No proof of public onboarding or password system |
| Settings `/settings` and workspace/company/member/domain/setup pages | B, W when enabled | Organization/profile/settings APIs | Workspace/invite/profile controls W/API | API/W | U/W | Shell W/S | PostgreSQL onboarding BROKEN; domain external check pending |
| Usage/limits `/settings/limits`, system pages | B; relevant controls U/W | Safety limits/request counters | Limit editing connected S/U/API | API | S/U | S | No purchased plans/billing or unified customer spend UI |
| Help `/help` | B, W | Searchable product-help endpoint | Search/support links W | Public/authorized layout tested | W/U | W at 320/390/1440 in help test | No live chat/ticket backend claimed |
| AI Assistant `/assistant` | B; live conversation NOT TESTED | Real authorized tools and proposal backend API | Typed bounded read/propose/review API/U | API | U/S | S | Gateway synthetic; real populated AI browser journey pending |
| API/MCP `/settings/developer` | B, W when enabled | Real key/approval/webhook API and mounted MCP | One-time keys and signed receiver UI W/API | API/W | U/W | S | Named external clients and full REST audits/docs incomplete |
| Login/signup/recovery/legal | B, W | Real Google handoff; signup blocked | W at desktop/mobile/keyboard | Auth handoff W; no live customer session | W | W 360/768/1440 | Policies visibly development copy; public account admission incomplete |
| Onboarding `/onboarding`, `/settings/setup` | B, SQLite W | Real `/api/organization/onboarding` | SQLite local journey W | API/W | W locally; PostgreSQL fails | Shell W/S | P0 B01: service read cannot iterate PostgreSQL Cursor |
| Legacy automation `/automation` and direct summary API | B; source/API probe | Scoped queue plus unscoped internal runs | Legacy operational controls restricted | **BROKEN for metadata read** | S | S | P0 B02: customer summary exposes internal automation history |

The production build inventories the additional existing routes for reports/scans/runs and internal experiment/system/settings aliases. Those routes were inspected as legacy/internal surfaces; a compiled route alone is not a completed SaaS phase. No browser claim is made for every alias or every page at all viewport sizes.

## API, integrations, AI and worker inventory

### Public REST API

Actual implementation: `app/api/routes/public_v1.py`, mounted under `/api/v1/`; bearer key handling is in `app/developer/keys.py` and `app/api/security.py`.

- Company search/list/detail: `/companies`, `/companies/{business_id}`.
- Contact search/detail: `/contacts`, `/contacts/{contact_id}`.
- ICP listing and company fit: `/icps`, `/companies/{business_id}/fit`.
- Lists: GET/POST `/lists`; scoped list memberships/details supported by existing domain APIs.
- Tasks: GET `/tasks`; this is not a public campaign-send or arbitrary mutation API.
- Enrichment: POST `/enrichment/jobs`, GET `/enrichment/jobs/{key}` with required resource scopes.
- Campaign summaries: GET `/campaigns`.
- Saved searches: GET/POST `/searches`.
- Authenticated OpenAPI: `/api/v1/openapi.json`.

Keys are one-time displayed, stored as hashes, workspace-bound and revocable. Creation/rotation/revocation, per-route/composed scopes, bounded pagination, rate-limit reservations and idempotent write headers are implemented. Availability remains feature-gated. API keys do not bypass active membership, onboarding or disabled-module access. Lifecycle audits are present; full public request audit coverage is incomplete. Existing standalone API documents are not uniformly synchronized with these routes.

### MCP

`app/developer/mcp_server.py` uses maintained **MCP SDK 2.3.0 / FastMCP**, mounted at **`/mcp/`**, using **Streamable HTTP** and the actual application lifespan. Official SDK client discovery/call tests passed. This is a functioning server, not a design document or unused dependency.

Nine tools: `search_companies`, `company_details`, `search_contacts`, `match_icp`, `list_icps`, `list_lists`, `campaigns`, `propose_action`, `proposal_status`. Tools invoke real scoped domain services. `mcp:use` and corresponding resource/action scopes are required. Proposals require authorized review; MCP cannot send mail or autonomously start scans. Credential rotation/removal and actor membership are rechecked; tool success/denial audit events exist. Named desktop/hosted-client interoperability is not yet accepted. Stdio and legacy SSE are not claimed.

### Integrations

- **Sheets:** separate Google read/write OAuth consent, protected state/callback, encrypted organization credentials, refresh/disconnect, reviewed import and immutable fixed-range RAW export. Export requires matching digest and explicit overwrite approval; uncertain writes need reviewed retry. PostgreSQL duplicate workers, global worker limit, unavailable companies, stale lease fencing and recovery are tested. Live customer consent/read/write was not run.
- **Mail:** `app/mail/providers.py` contains real Gmail/Hostinger SMTP+IMAP TLS implementations using **global internal app-password configuration**. This is not customer Gmail OAuth or Gmail REST API. Owned workflow/suppression/history controls and internal synthetic mail tests work; independent customer sender tokens/routing do not exist.
- **HubSpot/Pipedrive:** no functional adapter, OAuth lifecycle, mapping, sync worker, conflict policy or connection-health tests found. This is missing code, not merely missing credentials. Unavailable CRM options are not advertised as working.
- **Discovery:** actual Overture public S3/DuckDB and OSM Overpass; actual gated Firecrawl acquisition; Nominatim location lookup. Geographic/industry coverage and live customer yield are not certified. No new provider was introduced.

### AI

The shared Vertex gateway (`app/acquisition/ai_router.py`, `app/acquisition/ai.py`) performs actual authorized structured generation. ICP suggest/refine, company-profile discovery, extractive cited summaries and assistant tools have backend implementations. Tests use synthetic providers. Strict schemas, explicit assumptions, exact citations, bounded tokens/time, committed per-workspace/global usage reservations and reviewed side effects are present. This is not independent verification of people, mailbox deliverability, buying intent or financial metrics. Full conversational ICP UX, money/plan accounting and staged adversarial/live acceptance remain incomplete.

### Jobs and database

`app/worker.py` dispatches scans, acquisition, intelligence/assistant jobs, company-profile discovery, reports, reviewed Sheets export, workflows and webhook delivery/dispatch via persisted job IDs. Scope is resolved from stored ownership; role/module checks and bounded leases/timeouts/retries exist. Webhook outbox writes occur in domain transactions; its three supported topics are `company.created`, `contact.created`, `contact.updated`. HMAC delivery, five-attempt bounds, attempt history, idempotency, revocation and crash recovery passed synthetic and PostgreSQL checks. Actual external receiver/cloud scheduling acceptance remains unperformed.

Schema migrations are versioned through **38**: ownership/resource, profile/ICP, intelligence, sales, developer keys/MCP, webhook and Sheets-export tables are additive extensions of the modular monolith. Fresh SQLite tests and isolated PostgreSQL backup/restore passed. Existing historical production data was not opened, changed, reset or restored during assessment. Two explicit data-deletion PostgreSQL tests were excluded. Schema-38 migration success does not prove PostgreSQL onboarding correctness: B01 fails above the schema layer.

## Latest recovery findings validated

| Previously reported item | Current assessment |
|---|---|
| Source checkpoint | Prior 862-file archive/manifest recorded; current assessment separately verified 1,052 copied source/assets against current files before reporting, with no drift. Restricted checkpoint path is recorded in the completion tracker |
| CSV repair | Count/budget/formula/tenant guards exist; current PostgreSQL safety cases pass, including unavailable-company rejection |
| Sheets snapshot repair | Evidence-count guard exists; independent-transaction unavailable-company race is tested and returns 409 instead of KeyError |
| 12 additional PostgreSQL cases | Present in current `tests/integration/test_postgres.py`; current suite contains 41 cases, of which 39 non-destructive cases passed |
| 43 focused tests | Exactly those 43 cases also passed within the newly completed full backend run; historical focused command/log retained, not unnecessarily rerun |
| 39 PostgreSQL passes | Repeated in new assessment-only cluster; 2 destructive cases deselected; no production data involved |
| Whitespace check | Final `git diff --check` recorded after report generation |
| Broader regression blocker | Existing backend/unit/type/build/browser suites now run successfully; narrowed to two newly reproduced release defects, supported-runtime fidelity and missing staged/customer journeys |
| Live Google/receiver acceptance | Still blocked by required owner approval and external staging acceptance; credential presence in production was not inspected |
| Cryptography mismatch | Installed 48.0.1 versus unchanged lock 50.0.2 remains; `pip check` passes but does not establish lock fidelity |
| Customer Gmail and CRM sync | Still NOT IMPLEMENTED as customer integration paths; cannot be resolved solely by supplying credentials |

## Security and release interpretation

1. **Confirmed P0:** `app/platform/onboarding.py:62` iterates the PostgreSQL adapter Cursor, causing a TypeError on setup read. Its API is `/api/organization/onboarding`; SQLite-only browser success masked the failure. No repair was made during this reporting task.
2. **Confirmed P0:** `/api/automation/summary` returns `automation_runs` globally. A completed independent customer workspace received the synthetic internal marker in run history. The confirmed exposure is **internal run status/targets/error metadata**; this probe did not demonstrate cross-workspace contact contents or credentials being exposed. No blanket customer-isolation claim is valid until this read is corrected and regressed.
3. Google auth is genuine, but `dashboard/auth.ts` blocks public signup; backend production configuration still restricts admission to one or two allowlisted identities. Successful internal login is not completed public customer onboarding.
4. Customer mail OAuth and CRM services are missing, while their absence is safely gated. Missing promised scope remains P1 or P0 customer-outreach work, not optional enhancement.
5. Installed cryptography and Node differ from declared release targets. Current tests pass on those installed versions; supported clean-install and lock fidelity remain unverified. No claim is made about the actual deployed runtime.
6. Policy pages are explicitly development-review copies. Approved legal/customer launch and external provider acceptance have not been evidenced.

**Verdict: NOT READY FOR PUBLIC SaaS LAUNCH.** Seven P0 workstreams remain open: B01 onboarding, B02 metadata isolation, B03 customer admission, B04 customer mailbox, B05 reproducible supported runtime, B06 approved policies, B07 staged external/cross-product acceptance. Billing additionally becomes a P0 condition for a paid launch; it remains required P1 foundation scope otherwise. Phase scores are engineering estimates of implemented scope, not production readiness or customer journey success.

## Verification ledger — 2026-11-08 UTC

All execution happened before report compilation. No completed suite was rerun just to resume reporting. Environment: isolated copy without root .env; Python 3.12.14; installed cryptography 48.0.1; MCP SDK 2.3.0; Node 26.13.0/npm 11.20.0; Next 16.2.6. Provider/send/automation flags were off, ADC points to a nonexistent sandbox file, credentials are synthetic. Python assessment guard blocks external network transports. Browser fixtures use local synthetic provider APIs. PostgreSQL 16.15 was a new private Unix-socket cluster, no TCP listener; its schemas/data were retained and process stopped. Existing production/local owner databases were untouched.

Raw artifact root: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108`. Every row has exact command/cwd/date/environment in its corresponding `*-command.json`; JUnit/Playwright reports and logs are retained.

| Suite | Passed | Failed | Errors | Skipped | Additional outcome | Log/report stem |
|---|---:|---:|---:|---:|---|---|
| Initial full backend | 663 | 16 | 0 | 42 | 16 PDF failures caused by missing assessment-copy fonts; retained, not product defects | `backend-full` |
| Full backend after copying existing fonts | 679 | 0 | 0 | 42 | 679 passes; 41 opt-in PostgreSQL cases and one live-mail case skipped | `backend-full-corrected` |
| Isolated PostgreSQL | 39 | 0 | 0 | 0 | 39 passes; two explicit destructive cases deselected | `postgres-current` |
| Additional release-gap probes | 0 | 2 | 0 | 0 | Two real defects reproduced; 41 established cases deselected | `release-gap-probes` |
| Frontend units | 114 | 0 | 0 | 0 | 114 tests passed | `frontend-units` |
| Type checking | PASS | 0 | 0 | 0 | Passed | `frontend-types` |
| Production build | PASS | 0 | 0 | 0 | Passed with webpack; supported Node 24 not used in current installed environment | `frontend-build` |
| Workflow/customer operations browser | 29 | 0 | 0 | 0 | No flaky tests reported | `browser-workflow` |
| Workspace/onboarding/ICP/profile browser | 11 | 0 | 0 | 0 | No flaky tests reported | `browser-workspace` |
| API/MCP/webhook settings browser | 2 | 0 | 0 | 0 | No flaky tests reported | `browser-developer` |
| Reviewed Sheets export browser | 1 | 0 | 0 | 0 | No flaky tests reported | `browser-sheets-export` |
| Scoped integration callback browser | 1 | 0 | 0 | 0 | No flaky tests reported | `browser-integrations` |
| Auth/recovery/legal responsive browser | 3 | 0 | 0 | 0 | No flaky tests reported | `browser-auth-webpack` |
| Signed local-preview new-account isolation browser | 1 | 0 | 0 | 0 | No flaky tests reported | `browser-preview-webpack` |
| Original auth dev-server attempt | 0 | 0 | 1 startup | 0 | NOT RUN: sandbox package symlinks outside Turbopack root; webpack harness subsequently passed 3 tests | `browser-auth` |

**Fresh browser total: 48 passed, 0 failed, 0 skipped, 0 flaky.** These are synthetic/local paths, not live Google/mail/CRM acceptance. The auth webpack run logged interrupted destination-stream diagnostics during navigation; assertions passed. These diagnostics remain in the log and were not promoted to a confirmed product defect. The first full-backend assessment omitted three existing font assets; copying them into the sandbox resolved all 16 failures without changing source.

### Relevant domain subsets inside the full backend command

These are JUnit selections, **not additional executions or totals to add**.

| Domain selector | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Discovery | 66 | 0 | 0 | 0 |
| Contacts | 22 | 0 | 0 | 0 |
| Enrichment | 11 | 0 | 0 | 0 |
| ICP/AI | 51 | 0 | 0 | 0 |
| Sales/outreach | 70 | 0 | 0 | 0 |
| Authorization/tenancy | 63 | 0 | 0 | 0 |
| Sheets | 20 | 0 | 0 | 0 |
| Webhooks | 15 | 0 | 0 | 0 |
| MCP | 2 | 0 | 0 | 0 |
| Developer API | 4 | 0 | 0 | 0 |
| Recovery focused 43 | 43 | 0 | 0 | 0 |

Selectors/individual testcase names are retained in `suite-summary.json`, `summarize_assessment.py` and `backend-full-corrected.xml`. SQLite migrations/history checks were included in the full backend; PostgreSQL version-38 backup/restore in its isolated suite. Historical production preservation was not newly exercised against production.

### Exact execution commands

The following argv were run with the sanitized environment above. They resolve to the source-copy working directory recorded alongside each command; no original .env was loaded.

**backend-full** — `2026-11-08T08:11:39.660954+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout`; exit 1.

```text
/Users/planebyte/Documents/Projects/planebyte-leadgen/.venv/bin/python -m pytest -p offline_assessment -p no:cacheprovider --basetemp=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/backend-full-data --junitxml=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/backend-full.xml -q tests
```

**backend-full-corrected** — `2026-11-08T08:16:01.019606+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout`; exit 0.

```text
/Users/planebyte/Documents/Projects/planebyte-leadgen/.venv/bin/python -m pytest -p offline_assessment -p no:cacheprovider --basetemp=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/backend-full-corrected-data --junitxml=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/backend-full-corrected.xml -q tests
```

**postgres-current** — `2026-11-08T08:26:57.445697+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout`; exit 0.

```text
/Users/planebyte/Documents/Projects/planebyte-leadgen/.venv/bin/python -m pytest -p retain_recovery_schemas -p offline_assessment -p no:cacheprovider --basetemp=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/postgres-current-data --junitxml=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/postgres-current.xml -q tests/integration/test_postgres.py -k 'not permanent_deletion and not legacy_company_alias_rediscovery'
```

**release-gap-probes** — `2026-11-08T08:28:17.013998+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout`; exit 1.

```text
/Users/planebyte/Documents/Projects/planebyte-leadgen/.venv/bin/python -m pytest -p retain_recovery_schemas -p offline_assessment -p no:cacheprovider --basetemp=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/release-gap-probes-data --junitxml=/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/release-gap-probes.xml -q tests/integration/test_postgres.py /var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/verification_probes.py -k 'onboarding_saved_state_reads or customer_automation_summary'
```

**frontend-units** — `2026-11-08T08:11:39.730876+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npm test -- --maxWorkers=1 --no-file-parallelism
```

**frontend-types** — `2026-11-08T08:16:01.019744+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npm run typecheck
```

**frontend-build** — `2026-11-08T08:11:39.913939+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npm run build -- --webpack
```

**browser-workflow** — `2026-11-08T08:16:01.019765+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npx playwright test --config=playwright.config.ts --reporter=list,json --max-failures=3
```

**browser-workspace** — `2026-11-08T08:19:49.497314+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npx playwright test --config=playwright.workspace.config.ts --reporter=list,json --max-failures=3
```

**browser-developer** — `2026-11-08T08:20:22.298130+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npx playwright test --config=playwright.developer.config.ts --reporter=list,json --max-failures=3
```

**browser-sheets-export** — `2026-11-08T08:20:38.477662+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npx playwright test --config=playwright.sheet-exports.config.ts --reporter=list,json --max-failures=3
```

**browser-integrations** — `2026-11-08T08:20:51.254951+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npx playwright test --config=playwright.integrations.config.ts --reporter=list,json --max-failures=3
```

**browser-auth-webpack** — `2026-11-08T08:26:57.535593+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npx playwright test --config=assessment.auth.config.ts --reporter=list,json --max-failures=3
```

**browser-preview-webpack** — `2026-11-08T08:26:57.786134+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 0.

```text
npx playwright test --config=assessment.preview.config.ts --reporter=list,json --max-failures=3
```

**browser-auth** — `2026-11-08T08:19:49.672118+00:00`; cwd `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108/checkout/dashboard`; exit 1.

```text
npx playwright test --config=playwright.auth.config.ts --reporter=list,json --max-failures=3
```

Additional dependency inspection commands: `.venv/bin/python -m pip check` → no broken installed requirements; `.venv/bin/python -c` reported Python/cryptography/MCP versions; `node --version && npm --version` → 26.13.0 / 11.20.0. These do not reproduce the exact dependency lock or supported Node engine. Clean lock install/package-index availability was **NOT RUN**; no dependencies/configuration were changed.

### Explicit NOT RUN / remaining verification

- Live Google customer login/Sheets consent/refresh/read/write, actual Vertex model/failover, real DNS ownership, public discovery yield and external HTTPS webhook receiver/cloud scheduling: no owner approval for live integration actions in this task; credentials were not inspected and may already exist.
- Independent customer Gmail OAuth/send/reply and HubSpot/Pipedrive sandbox sync: required code absent; not a passing or credential-only-blocked suite.
- Full public registration/new invited-customer journey: admission intentionally blocked; PostgreSQL onboarding additionally fails.
- Named third-party MCP AI-client compatibility and populated live assistant/recommendation journeys: no complete acceptance evidence.
- Paid plans/billing and unified spend accounting: no functioning implementation/test suite.
- Supported Node 24 clean release environment and exact cryptography lock: not reproduced; installed environment differs.
- Two explicit PostgreSQL destructive tests: deselected to avoid cleanup/deletion; one real-mail case skipped. Missing/disabled suites never count as passes.

Prior checkpoint was freshly revalidated: 862 archive members match the SHA-256 manifest; archive hash `01c346633246043912e29f35fdbd9ab7bc782bd1b2cead5ad03381bfaf2de1c1`; mode 0o600. No restore or source overwrite performed.

## Final document validation

All four requested documents exist. Programmatic checks confirmed 174 unique requirement rows, 76 mapped incomplete rows, all 24 customer questions, the 427-point/320.5-point calculation and no trailing whitespace in the generated documents. The other 1,051 existing assessment-snapshot files remain byte-for-byte unchanged; only the existing tracker was appended, alongside three new reports.

`git diff --check` returned exit 0; five existing CRLF-conversion notices were retained in `git-diff-check.log`, with command/date/cwd in `git-diff-check-command.json` under the assessment artifact root. Because the new reports are untracked, their whitespace was also validated directly. No staging or commits were performed.

Reporting changes: `docs/PLANEBYTE_LEAD_ENGINE_PHASE_1_TO_6_STATUS_REPORT.md`, `docs/PLANEBYTE_LEAD_ENGINE_PENDING_FEATURES.md`, `docs/PLANEBYTE_LEAD_ENGINE_RELEASE_READINESS.md`, and appended `docs/LEAD_ENGINE_PHASE_1_TO_6_COMPLETION.md`.
