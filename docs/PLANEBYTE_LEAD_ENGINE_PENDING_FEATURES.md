# PlaneByte Lead Engine — pending features and implementation sequence

Date: 2026-11-08 UTC. Historical assessment backlog; none was implemented during that assessment. **Continuation update, 2026-11-09:** B01/F12 and the specific B02 summary exposure were repaired after assessment. F02/B03 now has a gated Google admission/consent implementation and invitation-only admission with explicit separate membership acceptance. Fresh local regressions pass; PostgreSQL and real two-customer OAuth acceptance remain pending. The original rows/counts below are preserved as the assessment baseline. Use `LEAD_ENGINE_PHASE_1_TO_6_COMPLETION.md` for current progress; do not reapply the completed fixes.

P0 = secure public launch or essential customer journey; P1 = required promised Phase 1–6/foundation scope; P2 = enhancement only. No promised requirement below was downgraded to P2. Complexity Small/Medium/Large is a scoped engineering estimate, not a time guarantee. Safely disabled missing features differ from confirmed enabled-path security defects.

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

## Every incomplete requirement

Each row maps to a detailed workstream below, which supplies its root cause, exact target services, required tests, completion criteria and external dependencies. Shared groups avoid inventing separate rewrites for the same missing service. Status/source details and partial credits are in the status matrix. P0 counts are **seven root workstreams**, not the number of rows referencing them.

| Requirement ID / phase | Feature | Current status | Demonstrated subset / exact missing behavior | Files/evidence key | Workstream | Priority | Complexity |
|---|---|---|---|---|---|---|---|
| F01 / SaaS foundation | Google OAuth | IMPLEMENTED, NOT FULLY VERIFIED | Real Auth.js provider and protected handoff; no fresh live customer login acceptance | AUTH | B07 | P0 | Medium |
| F02 / SaaS foundation | Public registration | NOT IMPLEMENTED | Signup blocked; Google admission and backend production validation remain restricted to one or two allowlisted accounts | AUTH | B03 | P0 | Large |
| F08 / SaaS foundation | Team invitations | IMPLEMENTED, NOT FULLY VERIFIED | Scoped tokens, acceptance, rejection and expiry tested; external invited-account admission not accepted | ORG | B03 | P0 | Large |
| F10 / SaaS foundation | AI website-to-company-profile extraction | IMPLEMENTED, NOT FULLY VERIFIED | Bounded website discovery, cited editable proposals and AI validation tested synthetically; live website/model acceptance pending | COMPANY | B07 | P0 | Medium |
| F11 / SaaS foundation | Domain verification | IMPLEMENTED, NOT FULLY VERIFIED | DNS challenge and role/isolation controls tested with synthetic resolver; external DNS ownership acceptance pending | ORG | B07 | P0 | Medium |
| F12 / SaaS foundation | Onboarding workflow | BROKEN | SQLite browser path exists; PostgreSQL read raises TypeError because its Cursor is not iterable, reproduced in release-gap probe | ORG | B01 | P0 | Small |
| F15 / SaaS foundation | Workspace isolation | BROKEN | Core resource isolation tests pass, but customer automation summary exposes internal run metadata; blanket isolation claim fails | ORG | B02 | P0 | Medium |
| F16 / SaaS foundation | Notifications | PARTIAL | Invitation activity menu works; broader job/campaign notifications and read-state lifecycle absent | ORG | B19 | P1 | Medium |
| F17 / SaaS foundation | Usage tracking | PARTIAL | AI request and source counters exist; unified customer metering/cost ledger and dashboard incomplete | USAGE | B18 | P1 | Large |
| F18 / SaaS foundation | Plans and entitlements | NOT IMPLEMENTED | Feature switches are availability controls, not purchased plans; no plan entitlement service found | USAGE | B18 | P1 | Large |
| F19 / SaaS foundation | Billing readiness | NOT IMPLEMENTED | No payment adapter, checkout, subscription lifecycle or billing webhook implementation found | USAGE | B18 | P1 | Large |
| F21 / SaaS foundation | Approved Privacy Policy and Terms | BLOCKED | Responsive development-review text exists; owner/legal approval not evidenced | HELP | B06 | P0 | Small |
| F22 / SaaS foundation | Security and audit logging | PARTIAL | Signed requests, nonce/RBAC and audit records exist; confirmed metadata exposure and incomplete release certification remain | ORG | B02 | P0 | Medium |
| D01 / Phase 1 — Discovery | Global company discovery | PARTIAL | Country-aware Maps and reviewed acquisition work locally; global geographic/provider coverage not accepted | DISC | B08 | P1 | Large |
| D02 / Phase 1 — Discovery | Overture and existing maps discovery | IMPLEMENTED, NOT FULLY VERIFIED | Real Overture DuckDB/public S3 and OSM Overpass adapters with bounded queries; fresh live source yield not run | DISC | B07 | P0 | Medium |
| D03 / Phase 1 — Discovery | Other configured discovery providers | IMPLEMENTED, NOT FULLY VERIFIED | Firecrawl search/scrape adapter exists behind explicit feature/configuration gates; synthetic tests pass, live acceptance pending | DISC | B07 | P0 | Medium |
| D04 / Phase 1 — Discovery | AI/natural-language search | IMPLEMENTED, NOT FULLY VERIFIED | Real structured interpretation and reviewed search plan endpoints; gateway mocked in fresh checks | AI | B12 | P1 | Medium |
| D05 / Phase 1 — Discovery | Country, region and city selection | IMPLEMENTED, NOT FULLY VERIFIED | ISO country validation and bounded Nominatim selection/cache work; live global city lookup not validated | DISC | B08 | P1 | Large |
| D07 / Phase 1 — Discovery | Industry and category filters | PARTIAL | Configured vertical/category mappings work; arbitrary industry taxonomy/provider coverage incomplete | DISC | B08 | P1 | Large |
| D08 / Phase 1 — Discovery | ICP-based discovery | PARTIAL | Approved ICP prefills industries/geography and displays unsupported evidence criteria; not all ICP criteria are executable discovery filters | ICP | B08 | P1 | Large |
| D09 / Phase 1 — Discovery | Company size and other supported filters | PARTIAL | Typed targeting fields exist; size evidence mainly website employee count, not a reliable discovery-provider filter | DISC | B08 | P1 | Large |
| D12 / Phase 1 — Discovery | Search progress and cancellation | IMPLEMENTED, NOT FULLY VERIFIED | Progress, pause/cancel/resume and leases tested locally; blocking provider calls cannot guarantee immediate cancellation | DISC | B08 | P1 | Large |
| D17 / Phase 1 — Discovery | Geographic coverage | PARTIAL | ISO/global inputs supported; no country-by-country source coverage, contact yield or unsupported-region acceptance matrix | DISC | B08 | P1 | Large |
| D18 / Phase 1 — Discovery | Search quotas and cost controls | PARTIAL | Raw/result/query/scrape caps and reservations exist; customer-plan spending ceilings and complete cost metering absent | DISC | B18 | P1 | Large |
| C04 / Phase 2 — Company/contact intelligence | Public company information | IMPLEMENTED, NOT FULLY VERIFIED | Bounded official-page excerpts and structured attributes exist; broad live coverage not accepted | COMPANY | B09 | P1 | Large |
| C05 / Phase 2 — Company/contact intelligence | Products and services extraction | PARTIAL | Explicit JSON-LD/catalog/service snippets extracted; broader varied-site product/service coverage incomplete | COMPANY | B09 | P1 | Large |
| C06 / Phase 2 — Company/contact intelligence | Industry classification | PARTIAL | Source verticals and explicit website industry exist; general reliable cross-taxonomy classification incomplete | COMPANY | B09 | P1 | Large |
| C08 / Phase 2 — Company/contact intelligence | Decision-maker discovery | PARTIAL | Real explicit public JSON-LD Person data discovered; no invented names/roles, but wider team-page/provider coverage missing | PEOPLE | B09 | P1 | Large |
| C11 / Phase 2 — Company/contact intelligence | Public business email discovery | IMPLEMENTED, NOT FULLY VERIFIED | Published mailto/structured source addresses extracted and provenance tested; live representative yield not validated | PEOPLE | B07 | P0 | Medium |
| C12 / Phase 2 — Company/contact intelligence | Public phone discovery | IMPLEMENTED, NOT FULLY VERIFIED | Public tel/structured numbers extracted; no fresh live geographic coverage acceptance | PEOPLE | B09 | P1 | Large |
| C14 / Phase 2 — Company/contact intelligence | Source freshness | PARTIAL | Collection timestamps/evidence age exist; reliable refresh scheduling and stale-employment policy incomplete | PEOPLE | B11 | P1 | Medium |
| E02 / Phase 3 — Enrichment/verification | Contact enrichment | PARTIAL | Re-reads explicit official public person data and evidence; wider contact intelligence/provider coverage incomplete | ENRICH | B10 | P1 | Large |
| E04 / Phase 3 — Enrichment/verification | Provider abstraction | PARTIAL | Shared crawler/DNS/job boundary exists; no complete external enrichment-adapter registry and unified provider contract | ENRICH | B10 | P1 | Large |
| E05 / Phase 3 — Enrichment/verification | Provider fallback/waterfall | NOT IMPLEMENTED | No multi-provider company/contact enrichment waterfall found; discovery fallback does not satisfy this requirement | ENRICH | B10 | P1 | Large |
| E06 / Phase 3 — Enrichment/verification | Configured external enrichment providers | NOT IMPLEMENTED | No functional customer enrichment-provider adapter found; AI/Firecrawl discovery are not substitutes | ENRICH | B10 | P1 | Large |
| E09 / Phase 3 — Enrichment/verification | Provider-backed email verification | NOT IMPLEMENTED | No mailbox/deliverability verification provider implemented; not an external-credential-only blocker | ENRICH | B10 | P1 | Large |
| E11 / Phase 3 — Enrichment/verification | Phone normalization | PARTIAL | Legacy comparable-digit normalization exists; international country-aware E.164 and person-phone validation incomplete | ENRICH | B11 | P1 | Medium |
| E13 / Phase 3 — Enrichment/verification | Confidence and freshness | PARTIAL | Evidence age/status available; calibrated confidence, expiry and refresh policy incomplete | ENRICH | B11 | P1 | Medium |
| E17 / Phase 3 — Enrichment/verification | Enrichment usage limits | PARTIAL | Resource and request safety caps work; provider spend and purchased-plan entitlements incomplete | ENRICH | B18 | P1 | Large |
| E19 / Phase 3 — Enrichment/verification | Caching and retries | PARTIAL | Cached public data, bounded retries/leases exist; multi-provider uncertain-spend/cache freshness policy absent | ENRICH | B10 | P1 | Large |
| Q05 / Phase 4 — AI/ICP qualification | Company-profile-based AI ICP generation | IMPLEMENTED, NOT FULLY VERIFIED | Real authorized suggest endpoint uses saved company services and shared gateway; synthetic outputs validated, live acceptance missing | ICP | B07 | P0 | Medium |
| Q06 / Phase 4 — AI/ICP qualification | Conversational AI ICP builder | PARTIAL | Description suggestions and bounded follow-up refinement exist; dedicated persisted conversational builder journey not complete | ICP | B12 | P1 | Medium |
| Q07 / Phase 4 — AI/ICP qualification | AI-assisted ICP editing | IMPLEMENTED, NOT FULLY VERIFIED | Leaf-path refinement preserves unrelated criteria and requires review; live model/browser acceptance incomplete | ICP | B12 | P1 | Medium |
| Q09 / Phase 4 — AI/ICP qualification | Natural-language lead search | IMPLEMENTED, NOT FULLY VERIFIED | Shared gateway interprets targeting into reviewed acquisition plan; no automatic scan or send; external model acceptance missing | AI | B07 | P0 | Medium |
| Q10 / Phase 4 — AI/ICP qualification | ICP-based company qualification | IMPLEMENTED, NOT FULLY VERIFIED | Evidence-based structured comparisons and honest unknowns work; broader live field/industry acceptance incomplete | ICP | B14 | P1 | Medium |
| Q13 / Phase 4 — AI/ICP qualification | AI company summaries | IMPLEMENTED, NOT FULLY VERIFIED | Extractive cited snippets validated against exact source text; real gateway path exists, live model acceptance pending | AI | B07 | P0 | Medium |
| Q14 / Phase 4 — AI/ICP qualification | Recommendations | PARTIAL | Stored-company fit rows and page-local sorting/filtering work; populated end-to-end ranking/action journey not fully tested | ICP | B14 | P1 | Medium |
| Q18 / Phase 4 — AI/ICP qualification | Existing Vertex AI integration | IMPLEMENTED, NOT FULLY VERIFIED | Real shared Vertex structured generation adapter exists; current assessment did not use live model credentials | AI | B07 | P0 | Medium |
| Q19 / Phase 4 — AI/ICP qualification | AI gateway fallback | IMPLEMENTED, NOT FULLY VERIFIED | Existing authorized router, retries/health and configured fallback tested with synthetic providers; live fallback failover not accepted | AI | B07 | P0 | Medium |
| Q20 / Phase 4 — AI/ICP qualification | AI usage and cost controls | PARTIAL | Committed per-workspace/global daily reservations and token/time bounds work; unified money/plan accounting missing | AI | B18 | P1 | Large |
| Q22 / Phase 4 — AI/ICP qualification | Prompt-injection protections | IMPLEMENTED, NOT FULLY VERIFIED | Untrusted-source separation, exact citations and bounded tools tested; staged broader adversarial acceptance not run | AI | B13 | P1 | Medium |
| S03 / Phase 5 — Sales workspace/outreach | Saved views | PARTIAL | Named lists and runtime filters exist; reusable personal/team saved-view definitions incomplete | SALES | B15 | P1 | Medium |
| S11 / Phase 5 — Sales workspace/outreach | Campaign creation | PARTIAL | Reviewed workflow/campaign builder exists; independent customer mailbox prerequisites and full customer launch path missing | SALES | B04 | P0 | Large |
| S12 / Phase 5 — Sales workspace/outreach | Campaign drafts | PARTIAL | Reviewed campaigns and message previews exist; coherent customer draft-to-approval mailbox journey incomplete | SALES | B15 | P1 | Medium |
| S16 / Phase 5 — Sales workspace/outreach | Customer-specific Gmail connections | NOT IMPLEMENTED | Only global internal app-password mailbox transport exists; no per-customer Gmail OAuth/token routing | MAIL | B04 | P0 | Large |
| S18 / Phase 5 — Sales workspace/outreach | Mailbox OAuth connection lifecycle | NOT IMPLEMENTED | Google login and Sheets OAuth do not provide mailbox scopes; no customer mail authorize/callback/refresh/revoke lifecycle | MAIL | B04 | P0 | Large |
| S19 / Phase 5 — Sales workspace/outreach | Scheduling | IMPLEMENTED, NOT FULLY VERIFIED | Persisted schedules, dispatch and time windows tested locally; customer mailbox/cloud end-to-end acceptance incomplete | SALES | B07 | P0 | Medium |
| S28 / Phase 5 — Sales workspace/outreach | Campaign analytics | PARTIAL | Status/reply/bounce/tracking counts exist; complete customer mailbox attribution and finalized analytics UX incomplete | SALES | B15 | P1 | Medium |
| S29 / Phase 5 — Sales workspace/outreach | Workspace-specific email ownership | PARTIAL | Internal transport restricted and workflow records scoped; genuine independent customer sender credentials/routing absent | MAIL | B04 | P0 | Large |
| G01 / Phase 6 — Integrations/API/webhooks/MCP | Sheets OAuth connection | IMPLEMENTED, NOT FULLY VERIFIED | Separate scoped read/write consent, state and lifecycle tested synthetically; live consent acceptance pending | SHEETS | B07 | P0 | Medium |
| G04 / Phase 6 — Integrations/API/webhooks/MCP | Sheets import | IMPLEMENTED, NOT FULLY VERIFIED | Reviewed bounded read, column preview and canonical import implemented; real customer sheet acceptance pending | SHEETS | B07 | P0 | Medium |
| G05 / Phase 6 — Integrations/API/webhooks/MCP | Sheets export | IMPLEMENTED, NOT FULLY VERIFIED | Immutable reviewed fixed-range RAW writes, explicit retries and lease fencing tested; no live Sheets write acceptance | SHEETS | B07 | P0 | Medium |
| G08 / Phase 6 — Integrations/API/webhooks/MCP | Sheets real provider validation | BLOCKED | Live owner/customer consent and controlled read/write not run under reporting restrictions | SHEETS | B07 | P0 | Medium |
| R01 / Phase 6 — Integrations/API/webhooks/MCP | HubSpot adapter | NOT IMPLEMENTED | No functional adapter, auth/callback or sync service found | CRM | B16 | P1 | Large |
| R02 / Phase 6 — Integrations/API/webhooks/MCP | Pipedrive adapter | NOT IMPLEMENTED | No functional adapter, auth/callback or sync service found | CRM | B16 | P1 | Large |
| R04 / Phase 6 — Integrations/API/webhooks/MCP | CRM authentication | NOT IMPLEMENTED | No CRM connection authentication or encrypted refresh/revocation implementation | CRM | B16 | P1 | Large |
| R05 / Phase 6 — Integrations/API/webhooks/MCP | CRM data mapping | NOT IMPLEMENTED | No reviewed CRM company/contact field mapping implemented | CRM | B16 | P1 | Large |
| R06 / Phase 6 — Integrations/API/webhooks/MCP | CRM synchronization | NOT IMPLEMENTED | No idempotent CRM import/export/incremental sync worker | CRM | B16 | P1 | Large |
| R07 / Phase 6 — Integrations/API/webhooks/MCP | CRM conflict handling | NOT IMPLEMENTED | No remote-ID/version conflict policy or reviewed resolution | CRM | B16 | P1 | Large |
| R08 / Phase 6 — Integrations/API/webhooks/MCP | CRM retries | NOT IMPLEMENTED | No provider-specific retry, uncertainty or rate-limit handling | CRM | B16 | P1 | Large |
| R09 / Phase 6 — Integrations/API/webhooks/MCP | CRM connection health | NOT IMPLEMENTED | No CRM health/last-sync/error UI or backend status | CRM | B16 | P1 | Large |
| A08 / Phase 6 — Integrations/API/webhooks/MCP | API documentation | PARTIAL | Live scoped OpenAPI and developer UI exist; older standalone guides need reconciliation/examples | API | B17 | P1 | Small |
| A09 / Phase 6 — Integrations/API/webhooks/MCP | API audit logging | PARTIAL | Key lifecycle/usage recorded; complete per-request success/denial/abuse audit coverage not demonstrated | API | B20 | P1 | Medium |
| W09 / Phase 6 — Integrations/API/webhooks/MCP | Real webhook receiver testing | BLOCKED | Fresh receivers were synthetic; approved external HTTPS receiver/cloud scheduling acceptance absent | WEBHOOK | B07 | P0 | Medium |
| M08 / Phase 6 — Integrations/API/webhooks/MCP | MCP client compatibility | PARTIAL | Official SDK client works; named external desktop/hosted AI clients not accepted | MCP | B17 | P1 | Small |
| M11 / Phase 6 — Integrations/API/webhooks/MCP | MCP documentation | PARTIAL | Developer screen and protocol implementation exist; consolidated client setup/scope/revocation guide incomplete | MCP | B17 | P1 | Small |

## Prioritized workstreams and acceptance contracts

### B01 — PostgreSQL onboarding compatibility — P0 / Small

- **Requirements:** F12.
- **Already implemented / root cause:** Existing setup model and SQLite journey work; real PostgreSQL service read fails on cursor iteration.
- **Exact existing or proposed target files:** app/platform/onboarding.py:62; app/api/routes/onboarding.py; dashboard/app/onboarding/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Repair adapter-compatible result consumption, preserve existing setup/services/revisions and add permanent PostgreSQL read/save/complete regression.
- **Acceptance criteria:** GET/PUT /api/organization/onboarding and POST /complete work on fresh and historical schemas; absent/foreign membership denied; no implicit scan/send.
- **Required tests:** verification_probes.py onboarding reproduction; permanent tests/integration/test_postgres.py coverage; browser onboarding on PostgreSQL.
- **External credential/approval/dependency:** None beyond approval of the next development milestone.

### B02 — Internal automation metadata isolation — P0 / Medium

- **Requirements:** F15, F22.
- **Already implemented / root cause:** Owned today/queue paths coexist with an unscoped automation_runs SELECT; customer receives internal run error marker.
- **Exact existing or proposed target files:** app/api/routes/automation.py summary; app/database/automation_schema.py; app/platform/modules.py. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Make internal run history inaccessible to customer workspaces or use verified scoped metadata; do not weaken workspace resolution.
- **Acceptance criteria:** Customer GET /api/automation/summary contains no internal run target/status/error metadata; internal authorized behavior and owned queue remain intact.
- **Required tests:** Preserve failing probe as permanent API isolation regression; two customers plus internal workspace; anonymous/removed member; cached response tests.
- **External credential/approval/dependency:** Owner decision on whether legacy summary is internal-only or a scoped customer resource.

### B03 — Public customer admission and invited-user access — P0 / Large

- **Requirements:** F02, F08.
- **Already implemented / root cause:** Google auth and local organization/invitations exist; public signup blocked and production permits only one or two allowlisted identities.
- **Exact existing or proposed target files:** dashboard/auth.ts; app/config/settings.py:147; app/api/security.py; app/platform/workspaces.py; app/api/organization.py. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Implement approved account admission and invitation lifecycle with no inherited workspace or internal credentials; lift restriction only after isolation certification.
- **Acceptance criteria:** New permitted customer logs in, creates independent organization, completes onboarding and invites permitted teammate; denied user remains denied; existing owner session works.
- **Required tests:** Real staging Google login; two independent new actors; invite expiry/replay/removal; Google callback; no-context APIs; end-to-end PostgreSQL onboarding.
- **External credential/approval/dependency:** Owner authorization to open registration/admission; configured Google consent and redirects; prior B01/B02 closure.

### B04 — Independent customer mailbox and campaign routing — P0 / Large

- **Requirements:** S11, S16, S18, S29.
- **Already implemented / root cause:** Internal Gmail/Hostinger app-password SMTP+IMAP and safety guards work; no customer Gmail OAuth/token routing exists.
- **Exact existing or proposed target files:** app/mail/config.py; app/mail/providers.py; app/mail/service.py; app/workflows/; dashboard/app/settings/email/; app/integrations/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Add per-workspace authorized mail connection contract, encrypted tokens, refresh/revoke and sender-specific send/reply routing; preserve internal mailbox.
- **Acceptance criteria:** Customer A never sends as or reads B/internal mailbox; approved campaign uses matching sender; disconnect/membership/module removal blocks workers; uncertain sends are not duplicated.
- **Required tests:** Synthetic two-mailbox OAuth/refresh/revocation; campaign draft/approve/schedule/send/reply/bounce/suppression tests; owner-approved staging canary only later.
- **External credential/approval/dependency:** Approved Gmail scopes/consent and test mailbox accounts; explicit live-canary approval; no live mail during reporting.

### B05 — Supported reproducible release runtime — P0 / Medium

- **Requirements:** Cross-cutting release prerequisite (not an additional scored product requirement).
- **Already implemented / root cause:** Tests pass on Python 3.12.14, cryptography 48.0.1 and Node 26.13.0; lock requests cryptography 50.0.2 and package engines require Node 24.
- **Exact existing or proposed target files:** requirements.lock; requirements.txt; dashboard/package.json; current .venv/package runtime. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Validate and use an owner-approved reproducible locked dependency set on supported Node; investigate package availability rather than silently changing pins.
- **Acceptance criteria:** Clean approved install reproduces dependency versions; cryptography encryption/rotation and MCP protocol tests pass; Node 24 build/typecheck/unit/browser pass.
- **Required tests:** pip check is already green but not lock fidelity; clean isolated lock install and supported-runtime suites required.
- **External credential/approval/dependency:** Owner approval if locked version selection changes; package mirror access; production runtime was not inspected or modified.

### B06 — Approved public Privacy Policy and Terms — P0 / Small

- **Requirements:** F21.
- **Already implemented / root cause:** Responsive legal pages exist and visibly say development review copy.
- **Exact existing or proposed target files:** dashboard/app/privacy/; dashboard/app/terms/; app/platform/product_help.py. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Obtain approved policy text matching actual processing, integrations, suppression/history retention and customer access model.
- **Acceptance criteria:** Approved dated/versioned policies available before public signup; no unsupported product/legal claims; consent links work on login/onboarding.
- **Required tests:** Legal owner review; mobile/accessibility/link tests; actual retention/integration descriptions reconciled with code.
- **External credential/approval/dependency:** Owner/legal approval; legal drafting itself is external to engineering.

### B07 — Approved staged cross-product and provider acceptance — P0 / Medium

- **Requirements:** F01, F10, F11, D02, D03, C11, Q05, Q09, Q13, Q18, Q19, S19, G01, G04, G05, G08, W09.
- **Already implemented / root cause:** Existing suites pass with synthetic transports; fresh live Google, Vertex, DNS, external receiver and customer mailbox journey not accepted.
- **Exact existing or proposed target files:** app/integrations/; app/acquisition/ai_router.py; app/platform/company_discovery.py; app/webhooks/dispatch.py; app/workflows/; staging configuration. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Run narrowly approved non-production acceptance after code blockers; capture scopes, costs, isolation, destination ownership and recovery evidence.
- **Acceptance criteria:** Two isolated staging customers complete onboarding/profile/ICP/discovery/list/task/integration journey; approved Google read/write and external signed receiver pass; no unsafe automatic outreach.
- **Required tests:** Staged live provider matrix; actual Google consent/refresh/sheet read and separately approved fixed-range write; approved HTTPS receiver signature/retry; Vertex/DNS checks; full frozen suites plus new P0 regressions.
- **External credential/approval/dependency:** Explicit owner approvals and staging identities/resources; actual credentials may already exist and were not inspected; no production reset/deploy implied.

### B08 — Discovery coverage and executable filters — P1 / Large

- **Requirements:** D01, D05, D07, D08, D09, D12, D17.
- **Already implemented / root cause:** Maps/Firecrawl, saved searches, coarse progress and typed filters exist; full geography/taxonomy/size execution and immediate provider cancellation are incomplete.
- **Exact existing or proposed target files:** app/discovery/overture.py; app/discovery/osm.py; app/config/locations.py; app/icp/discovery.py; app/prospecting/criteria.py; app/acquisition/worker.py; dashboard/app/find-leads/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Define supported provider/country/industry matrix; execute or explicitly reject filters; show unsupported size/ICP predicates; preserve bounded cancellation and source shortfalls.
- **Acceptance criteria:** Representative country/industry searches show sourced companies, progress and cancel outcomes; unsupported inputs never silently disappear; provider budgets remain bounded.
- **Required tests:** Country/industry/category fixtures and approved source acceptance; multi-country job tests; in-flight cancel/retry; size/ICP unsupported-field contracts.
- **External credential/approval/dependency:** Approved source access and provider capacity; no new provider introduction during reporting.

### B09 — Public company and real-person intelligence breadth — P1 / Large

- **Requirements:** C04, C05, C06, C08, C12.
- **Already implemented / root cause:** Official website snippets/JSON-LD Person extraction are real but narrow; broader team/contact/service/site coverage incomplete.
- **Exact existing or proposed target files:** app/people/extraction.py; app/people/service.py; app/prospecting/company_facts.py; app/intelligence/jobs.py; dashboard/app/contacts/; dashboard/app/leads/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Expand evidence-backed public person/company extraction with explicit employer/role association and no fabricated contacts; document supported formats and industry coverage.
- **Acceptance criteria:** Every displayed person has name/role source and company association; public business channels are sourced; unsupported facts remain unknown; repeated sources deduplicate safely.
- **Required tests:** Representative public structured/team/service fixtures; no-person/generic mailbox cases; source citation, employer mismatch, tenant and dedupe tests.
- **External credential/approval/dependency:** Approved public sources; any future contact provider requires separate owner selection/credentials.

### B10 — Enrichment adapter contracts, waterfall and genuine email verification — P1 / Large

- **Requirements:** E02, E04, E05, E06, E09, E19.
- **Already implemented / root cause:** Website refresh/DNS jobs exist; external enrichment/verification adapters and multi-provider fallback do not.
- **Exact existing or proposed target files:** app/intelligence/jobs.py; app/platform/contact_verification.py; app/people/verification.py; app/enrichment/; proposed adapter modules do not yet exist. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Define unified bounded provider contract and approved waterfall; implement genuine provider verification with technical checks kept distinct; safe uncertainty/cache/retry semantics.
- **Acceptance criteria:** Single/bulk jobs provide provider-labelled evidence and truthful verdicts; paid failed/uncertain calls are not blindly rebilled; absent configuration gives unavailable, not verified.
- **Required tests:** Adapter contract, rate-limit/timeout/fallback/uncertainty, suppression, cross-workspace cache and bulk-idempotency tests; approved provider acceptance.
- **External credential/approval/dependency:** Owner-selected enrichment/email-verification providers, API permissions and budgets; no named new provider assumed.

### B11 — International phone and confidence/freshness policy — P1 / Medium

- **Requirements:** C14, E11, E13.
- **Already implemented / root cause:** Comparable digits and source timestamps exist; country-aware person/company phone validity and calibrated refresh policy incomplete.
- **Exact existing or proposed target files:** app/normalization/phones.py; app/people/service.py; app/platform/contact_verification.py; app/intelligence/jobs.py. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Define country-aware normalization and explicit evidence ageing/refresh rules without overstating validity or employment confidence.
- **Acceptance criteria:** UK/US/DE/IN ambiguous numbers retain honest states; stale source/employment evidence is visible and refreshable; unknown inputs are not fabricated.
- **Required tests:** Country-specific phone fixtures; stale/updated/deleted-source simulations without deleting historical data; evidence-cache invalidation and ownership.
- **External credential/approval/dependency:** Product approval of refresh/confidence semantics; no external phone-verification service assumed.

### B12 — Conversational ICP and AI-assisted customer journey — P1 / Medium

- **Requirements:** D04, Q06, Q07.
- **Already implemented / root cause:** Description/suggest/refine and assistant proposals exist; dedicated persisted conversational builder and live editing acceptance incomplete.
- **Exact existing or proposed target files:** app/icp/builder.py; app/assistant/service.py; app/prospecting/tools.py; dashboard/app/settings/icp/; dashboard/app/assistant/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Finish reviewed conversational ICP turns/drafts or explicitly map supported follow-up flow; keep unrelated criteria unchanged; test real UI/backend proposals.
- **Acceptance criteria:** Customer profile produces editable candidates; follow-up changes only requested fields; conversation/draft revisions persist; approval creates targeting only, not scans/sends.
- **Required tests:** Conversation/revision/idempotency tests; populated browser AI draft/refine/approve; injection/invalid-output/disabled-provider/error states; approved model check.
- **External credential/approval/dependency:** Existing Vertex configuration plus owner approval for bounded live acceptance; no new AI provider required.

### B13 — AI adversarial acceptance and permission evidence — P1 / Medium

- **Requirements:** Q22.
- **Already implemented / root cause:** Schemas, fixed tools, citations and cost caps work; broader staged adversarial input acceptance is incomplete.
- **Exact existing or proposed target files:** app/acquisition/ai_router.py; app/intelligence/summary.py; app/icp/builder.py; app/prospecting/tools.py; app/assistant/service.py. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Validate hostile source text and proposed actions across roles, revisions and module removal; preserve approved-action boundaries.
- **Acceptance criteria:** Untrusted content cannot choose arbitrary URLs/SQL, reveal foreign workspace context, send mail or bypass review; failures remain truthful and bounded.
- **Required tests:** Cross-product injection/citation/tool-scope corpus; revocation during execution; oversized context/schema failures; staged model acceptance.
- **External credential/approval/dependency:** Owner-approved bounded model usage; independent security review for launch.

### B14 — Populated qualification and recommendation journey — P1 / Medium

- **Requirements:** Q10, Q14.
- **Already implemented / root cause:** Explainable field fit and stored-company rows exist; broader industry/evidence criteria and populated UI ranking/action acceptance incomplete.
- **Exact existing or proposed target files:** app/icp/matching.py; app/intelligence/qualification.py; dashboard/app/recommendations/; dashboard/app/leads/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Complete supported evidence comparisons and test populated recommendation selection/sorting/pagination/add-to-list; keep page-local ranking labels honest.
- **Acceptance criteria:** Recommendations explain unknown/exclusion/coverage; list action respects role/tenant; absent contact never implies send eligibility.
- **Required tests:** Populated browser recommendation actions with multiple ICPs/pages; source/employee/role unknowns; exclusions, sorting and cross-workspace tests.
- **External credential/approval/dependency:** Representative owner-approved source examples; provider/model acceptance depends on B07/B09.

### B15 — Saved views, campaign drafts and customer analytics — P1 / Medium

- **Requirements:** S03, S12, S28.
- **Already implemented / root cause:** Lists/tasks and message previews exist; reusable views, coherent customer draft approval and sender attribution incomplete.
- **Exact existing or proposed target files:** app/sales/; app/workflows/; app/mail/; dashboard/app/campaigns/; dashboard/app/outreach/; dashboard/app/lists/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Persist personal/team view contracts; finish draft-to-approval UX and customer mailbox-specific analytics after B04.
- **Acceptance criteria:** Views persist without leaking workspace filters; draft changes require renewed approval; counts/attribution agree with owned send/reply/bounce events.
- **Required tests:** Saved-view permissions/persistence; populated campaign draft/preview/review browser tests; analytics reconciliation; duplicate/uncertain-send tests.
- **External credential/approval/dependency:** Customer mailbox implementation B04; live-canary approval only for later external tests.

### B16 — HubSpot and Pipedrive integration lifecycle and synchronization — P1 / Large

- **Requirements:** R01, R02, R04, R05, R06, R07, R08, R09.
- **Already implemented / root cause:** No functioning CRM adapters/auth/mapping/sync/conflict/health implementations found.
- **Exact existing or proposed target files:** app/integrations/; dashboard/components/workspaces/integrations.tsx; proposed hubspot.py/pipedrive.py and CRM sync worker are missing. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Implement approved CRM authorize/callback/refresh/revoke, reviewed company/contact field mapping, stable remote IDs, bounded incremental sync, conflicts and health.
- **Acceptance criteria:** Each CRM sync is workspace-owned and idempotent; conflicts reviewed, rate limits retried safely, revocation blocks jobs; unavailable adapters stay inaccessible.
- **Required tests:** Two-tenant synthetic CRM OAuth/mapping/conflict/pagination/rate-limit/recovery tests; browser connection/mapping/sync status; approved CRM sandbox acceptance.
- **External credential/approval/dependency:** HubSpot/Pipedrive developer apps/scopes, sandbox accounts and owner consent; incomplete safely unavailable, not an immediate enabled-path leak.

### B17 — Public API/MCP documentation and named-client compatibility — P1 / Small

- **Requirements:** A08, M08, M11.
- **Already implemented / root cause:** v1 OpenAPI and real SDK/client/tool tests exist; older guides and external-client compatibility evidence are incomplete.
- **Exact existing or proposed target files:** app/api/routes/public_v1.py; app/developer/mcp_server.py; app/developer/keys.py; docs/HEYSOW_API.md; dashboard/app/settings/developer/. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Publish current route/tool/scope/examples/revocation guides; validate named supported AI clients over Streamable HTTP; do not advertise unimplemented stdio/SSE or autonomous sends.
- **Acceptance criteria:** Documented client can list/call allowed tools and loses access on rotation/removal; API examples match live schemas and permissions.
- **Required tests:** Documentation contract tests; official client already passes; named external client authentication/read/proposal/revocation checks.
- **External credential/approval/dependency:** Chosen supported clients and owner-approved staged credentials; no new SDK/provider needed.

### B18 — Customer usage, plans, entitlements and billing — P1 / Large

- **Requirements:** F17, F18, F19, D18, E17, Q20.
- **Already implemented / root cause:** Safety counters/feature availability exist; purchased plans, monetary metering and payments do not.
- **Exact existing or proposed target files:** app/platform/modules.py; app/platform/ai_usage.py; app/acquisition/worker.py; dashboard/app/settings/; proposed billing/entitlement service missing. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Define customer usage/plan ledger and bounded provider spend; implement approved plan entitlements and billing lifecycle without equating flags to paid access.
- **Acceptance criteria:** Limits enforced consistently across API/worker/provider; retries/uncertain outcomes do not double-charge; billing webhooks idempotent; no paid-plan claim before activation.
- **Required tests:** Metering conservation/tenant/race tests; downgrade/disabled-history retention; synthetic checkout/subscription/webhook reconciliation; approved payment sandbox.
- **External credential/approval/dependency:** Approved pricing/plan scope and payment processor/sandbox credentials; P0 additionally if launch is paid, P1 for full promised foundation otherwise.

### B19 — Notification lifecycle beyond invitations — P1 / Medium

- **Requirements:** F16.
- **Already implemented / root cause:** Invitation activity menu works; broader job/campaign notifications and read-state controls missing.
- **Exact existing or proposed target files:** app/api/routes/organizations.py; dashboard/components/layout/notifications.tsx; organization_notifications schema. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Add scoped event notifications and read/unread lifecycle for agreed product events without leaking payloads.
- **Acceptance criteria:** Only permitted workspace events visible; notification state persists and revoked members lose access; errors/loading/empty states work.
- **Required tests:** Event/idempotency/read-state/tenant tests; browser async job/campaign notification and keyboard/mobile checks.
- **External credential/approval/dependency:** Product-approved event/notification scope; outbound notification email requires B04 and separate approval.

### B20 — REST request audit completeness — P1 / Medium

- **Requirements:** A09.
- **Already implemented / root cause:** Key lifecycle and MCP tool audits exist; complete public REST success/denial/abuse audit trail not demonstrated.
- **Exact existing or proposed target files:** app/developer/keys.py; app/api/routes/public_v1.py; app/api/security.py; audit_log schema. Proposed modules/endpoints are missing, not created by this report.
- **Required work:** Define and record bounded public request audit metadata, excluding credentials/content; reconcile cache/failed-scope/rate-limit paths.
- **Acceptance criteria:** Allowed/denied/rate-limited requests produce organization-qualified audit records with no key/token/customer content leakage.
- **Required tests:** Public API success/denial/rate-limit/cache/revocation audit tests; retention/permission tests and review.
- **External credential/approval/dependency:** Owner-approved audit retention and privacy scope; B02 remains the separate immediate isolation blocker.

## Shortest safe implementation sequence

These are recommended next milestones, not changes performed in this assessment. Existing providers/session integrations and the modular monolith should be reused. Endpoint/module names labelled proposed are missing contracts, not claims of current implementation. No promised Phase 1–6 item is silently downgraded to an enhancement.

### 1. Critical SaaS/customer-access blockers — B01, B02, B03, B05, B06
- Work: repair PostgreSQL onboarding result consumption; gate or scope `/api/automation/summary` history; certify account admission/invitation ownership; reproduce supported locked runtime; approve policy text.
- Dependencies: owner admission/summary-scope decisions and legal approval. Preserve current restricted access until the new isolation tests pass.
- Done: GET/PUT `/api/organization/onboarding` and completion preserve historical setup; internal/customer metadata never mixes; new admitted actor receives no inherited workspace/credential; existing Google owner session remains functional.
- Tests/approvals: move both external failing probes into permanent isolated API/PostgreSQL regressions; new-user/invite/no-context/revocation/cache tests; supported Node/lock build; approved staging Google login and legal text.
- Deliverables: minimal fixes, permanent regressions, migration-free preservation evidence where possible, customer-admission contract and approved policies. No production reset required.

### 2. Phase 1 discovery completion — B08 plus B07/B18 source acceptance
- Work: publish executable source/country/category/filter matrix; complete or reject size/ICP filters in existing `app/icp/discovery.py` and `app/prospecting/criteria.py`; improve bounded in-flight cancellation reporting; retain saved search/history/provenance.
- Dependencies: milestone 1, approved existing source capacity and customer metering contract.
- Done/tests: representative multiple-country/industry source yields with evidence; unknown filters explicit; progressive results and cancellation verified under slow providers; quotas/reservations survive retries. Existing `/find-leads` controls must match backend behavior.
- Approvals/deliverables: bounded source acceptance plan, supported-coverage document, schema/API/UI contracts and regression fixtures; no new provider assumption.

### 3. Phase 2 contact intelligence completion — B09/B11
- Work: complete explicit public team/person/company extraction in `app/people/extraction.py` and `app/prospecting/company_facts.py`; improve role/employer evidence and varied product/service formats; country-aware phone/evidence-age handling.
- Dependencies: discovery quality and approved public source corpus.
- Done/tests: real source-backed named people, no generated contact patterns; role/company attribution survives dedupe; source freshness visible; missing persons remain empty. Populated company/contact pages work at narrow widths and with errors.
- Approvals/deliverables: accepted source-format/coverage corpus, contact evidence policy, scope/dedupe/freshness tests and populated UI acceptance.

### 4. Phase 3 enrichment completion — B10/B11/B18
- Work: define missing enrichment adapter contract and approved provider waterfall; implement actual provider-backed verification alongside truthful DNS/syntax states; complete uncertain-spend/cache/refresh semantics using existing bounded jobs.
- Dependencies: owner-selected providers, budgets and verified person/company ownership. No provider is introduced by this report.
- Done/tests: single/bulk jobs produce independently labelled provider verdicts; no double-billing uncertain requests; explicit rate-limit/fallback/refresh behavior; all resources/cache entries scoped. Existing `/enrichment` and job pages show honest outcomes.
- Approvals/deliverables: provider/scope decisions, typed contracts, adapter tests and approved sandbox/live acceptance with controlled cost.

### 5. Phase 4 AI/ICP completion — B12/B13/B14/B18
- Work: finish persisted conversational ICP draft/refine journey using existing `/api/organization/icps/suggest`, `/refine`, history and assistant services; complete populated recommendation actions; preserve exact-citation and proposal review boundaries.
- Dependencies: approved company-profile/ICP evidence and shared Vertex configuration, not a replacement AI stack.
- Done/tests: candidate/refinement assumptions visible, requested fields preserved, no autonomous send/scan, role/revocation checks enforced; populated ranking/add-to-list/browser journey and adversarial context tests pass.
- Approvals/deliverables: bounded real-model acceptance, conversation/revision/usage contracts, complete customer AI UI and test evidence.

### 6. Phase 5 customer outreach completion — B04/B15/B19
- Work: add missing per-workspace mailbox lifecycle and sender routing. Proposed missing contracts: `/api/organization/integrations/google-mail/authorize`, protected callback/connect, refresh/disconnect/health; encrypted mail-connection service and owned send/reply dispatch. Preserve internal transport and suppression/contact history. Complete customer draft-to-approval, saved views and analytics attribution.
- Dependencies: milestone 1 isolation; approved Google mail scopes/test mailboxes; bounded usage and campaign contracts.
- Done/tests: customer A cannot send/read as B/internal mailbox; pause/revocation blocks queued work; uncertain delivery never blindly resends; reply/bounce/unsubscribe counts match owned events. Full synthetic campaign lifecycle and two-mailbox tests precede any live canary.
- Approvals/deliverables: OAuth consent configuration, mailbox ownership service, sender-specific worker paths, campaign browser tests and separately approved staging canary. Reporting itself sends no email.

### 7. Phase 6 integration completion — B16/B17/B20/B07
- Work: implement missing HubSpot/Pipedrive adapters and sync using proposed authorize/callback/health/mapping/sync contracts under `/api/organization/integrations/{provider}`; stable remote IDs, reviewed mapping/conflicts, bounded retries and encrypted credentials. Finish current API/MCP guides, REST request audits and named-client compatibility. Validate real Sheets and signed receiver/cloud dispatch with approval.
- Dependencies: approved CRM sandbox apps/scopes and existing scoped job/key services. API/MCP/webhook foundations already work and must not be rewritten.
- Done/tests: two-workspace CRM sync idempotent across retry/revocation, conflict resolution explicit; provider unavailable stays inaccessible; existing v1 API examples and nine MCP tools match schemas; external receiver verifies HMAC; approved fixed-range Sheet export targets only reviewed destination.
- Approvals/deliverables: CRM connection/mapping/sync/health pages and workers, contract fixtures, client setup guide, receiver/provider acceptance logs. CRM absence is a safely disabled scope gap, not evidence Phase 6 is complete.

### 8. Final integrated release checkpoint — B07 and all preceding acceptance criteria
- Work: freeze actual scope/runtime, reconcile policies/plans/usage and run the complete suites plus new P0 regressions; exercise two new staging customers across profile/ICP/discovery/person/enrichment/list/task/mail/Sheets/CRM/API/MCP/webhook journey.
- Dependencies: all P0 closures and promised P1 scope; paid launch additionally requires approved billing/entitlements B18.
- Done/tests: no critical security/data-integrity regression; supported clean dependency install; SQLite and isolated PostgreSQL migration/history preservation; complete frontend type/build/unit/browser and staged external acceptance; all skips explicitly justified.
- Approvals/deliverables: owner-approved customer acceptance, release gap closure log, exact commands/artifact checksums and rollback/recovery evidence. Only a separate authorized deployment task may change production.
