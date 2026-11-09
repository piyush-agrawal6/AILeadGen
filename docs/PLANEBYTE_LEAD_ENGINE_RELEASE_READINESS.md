# PlaneByte Lead Engine — public SaaS release readiness

Date: 2026-11-08 UTC. **Verdict: NOT READY / BLOCKED.** **Continuation update, 2026-11-09:** the post-assessment milestone repaired PostgreSQL onboarding and the specific customer-summary metadata exposure. The saved fixes passed fresh local regressions; the recorded prior PostgreSQL milestone has not been freshly reproduced because its temporary runtime is unavailable. Gated account/invitation admission has progressed locally, while independent customer mail, CRM, runtime/legal and staged release acceptance remain open. The tables below retain historical assessment results; current evidence is in `LEAD_ENGINE_PHASE_1_TO_6_COMPLETION.md`. No production operation was performed.

## Functional completion, verification and readiness are different

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

Engineering estimates use 427 requirement-weight points, 320.5 earned points and 56.7% fully verified closure; methodology and all per-row credits are in the status report. Passing test counts are not a readiness percentage. Zero of the seven newly defined critical closure gates is fully accepted.

## Seven open critical launch workstreams

| Gate | Current result | Exact closure evidence needed |
|---|---|---|
| B01 — PostgreSQL onboarding compatibility | OPEN: Existing setup model and SQLite journey work; real PostgreSQL service read fails on cursor iteration | GET/PUT /api/organization/onboarding and POST /complete work on fresh and historical schemas; absent/foreign membership denied; no implicit scan/send |
| B02 — Internal automation metadata isolation | OPEN: Owned today/queue paths coexist with an unscoped automation_runs SELECT; customer receives internal run error marker | Customer GET /api/automation/summary contains no internal run target/status/error metadata; internal authorized behavior and owned queue remain intact |
| B03 — Public customer admission and invited-user access | OPEN: Google auth and local organization/invitations exist; public signup blocked and production permits only one or two allowlisted identities | New permitted customer logs in, creates independent organization, completes onboarding and invites permitted teammate; denied user remains denied; existing owner session works |
| B04 — Independent customer mailbox and campaign routing | OPEN: Internal Gmail/Hostinger app-password SMTP+IMAP and safety guards work; no customer Gmail OAuth/token routing exists | Customer A never sends as or reads B/internal mailbox; approved campaign uses matching sender; disconnect/membership/module removal blocks workers; uncertain sends are not duplicated |
| B05 — Supported reproducible release runtime | OPEN: Tests pass on Python 3.12.14, cryptography 48.0.1 and Node 26.13.0; lock requests cryptography 50.0.2 and package engines require Node 24 | Clean approved install reproduces dependency versions; cryptography encryption/rotation and MCP protocol tests pass; Node 24 build/typecheck/unit/browser pass |
| B06 — Approved public Privacy Policy and Terms | OPEN: Responsive legal pages exist and visibly say development review copy | Approved dated/versioned policies available before public signup; no unsupported product/legal claims; consent links work on login/onboarding |
| B07 — Approved staged cross-product and provider acceptance | OPEN: Existing suites pass with synthetic transports; fresh live Google, Vertex, DNS, external receiver and customer mailbox journey not accepted | Two isolated staging customers complete onboarding/profile/ICP/discovery/list/task/integration journey; approved Google read/write and external signed receiver pass; no unsafe automatic outreach |

B01 and B02 are **confirmed broken behavior**, not hypothetical concerns. The failing assessment probes are retained in `release-gap-probes.log/.xml`; they were deliberately not fixed during reporting. The automation defect demonstrated internal run status/targets/error metadata disclosure, not customer contact or secret disclosure. Existing resource/worker/cache denial tests still matter, but do not override this failure.

CRM and external enrichment/verification services are required Phase 1–6 gaps, currently unavailable/disabled rather than confirmed enabled-path leaks. Customer mailbox is P0 because outreach is an essential promised customer journey. Billing is additionally P0 for a paid public launch; it is required P1 scope otherwise. No approval to relax public registration or access restrictions was inferred.

## What is genuinely working locally

- Existing Google OAuth handoff and restricted owner session framework; server-derived membership/roles, workspace selection, organization/profile/ICP lifecycle with local tests. PostgreSQL onboarding exception remains separate.
- Real bounded Maps/Firecrawl acquisition implementations, saved searches/history, coarse progress, canonical company identity and provenance; live global coverage is not certified.
- Actual sourced public Person/contact records, company associations, scoped people/evidence APIs and truthful syntax/DNS/public/owner labels; decision-maker extraction remains narrow and provider deliverability verification absent.
- Manual/revisioned ICPs, typed AI proposals and explainable field fit; real authorized Vertex gateway/tools exist, current fresh model outputs are synthetic.
- Company/contact lists, task assignment/revisions, lifecycle/history and protected CSV/XLSX output.
- Real internal SMTP/IMAP transport and synthetic send/reply/bounce/unsubscribe/suppression/idempotency tests; not independent customer Gmail OAuth.
- Encrypted scoped Sheets OAuth/import/reviewed fixed-range export with PostgreSQL reservation and recovery tests; no live write approval acceptance.
- Scoped versioned REST API, hashed rotating keys, actual official-SDK Streamable HTTP MCP server/nine tools, and transactional signed-webhook retries/history/recovery. Phase 6 remains incomplete because CRM/live/client/audit gaps remain.

## Customer journey — all requested questions

YES — VERIFIED below means an existing admitted, authorized local workspace with its module enabled; it never means a new public customer can already join. PARTIAL names demonstrated behavior and missing acceptance. No missing test is interpreted as passing.

| # | Customer question | Answer | Supporting evidence and limitation |
|---|---|---|---|
| 1 | Can a new customer create an account today? | NO | F02/B03: public signup deliberately blocked; allowlisted Google identity is not public registration |
| 2 | Can they create an independent workspace? | PARTIAL | F04 is locally verified for admitted actors; a brand-new public actor cannot complete admission/onboarding, and PostgreSQL setup is broken |
| 3 | Can PlaneByte analyze their business website? | PARTIAL | F10: real bounded profile discovery and reviewed facts exist; synthetic provider tests pass, staged live acceptance missing |
| 4 | Can they generate an ICP automatically? | PARTIAL | Q05: real authorized suggest endpoint produces reviewable candidates; live model/customer acceptance incomplete, not auto-activated |
| 5 | Can they build an ICP with conversational AI? | PARTIAL | Q06/Q07: description/refine follow-ups exist; complete persisted conversational builder journey missing |
| 6 | Can they search for companies across countries? | PARTIAL | D06 is verified for explicit multi-country plans; global coverage and live source yield not certified |
| 7 | Can they see progressive discovery results? | YES — VERIFIED | D10: scoped persisted batch progress/results tested; provider-level instant streaming not promised |
| 8 | Can they discover actual public decision-maker contacts? | PARTIAL | C08: explicit public JSON-LD Person names/roles are real; wider team/provider coverage missing, no inferred people counted |
| 9 | Can they enrich company and contact information? | PARTIAL | E01/E02: website evidence and narrow person refresh work; external waterfall/full contact intelligence missing |
| 10 | Can they understand verification and evidence? | YES — VERIFIED | C13/E10: source URLs, public/owner observations, technical DNS checks and unknown states distinguished; no mailbox-proof claims |
| 11 | Can they view explainable recommendations? | PARTIAL | Q12 is verified; populated recommendation ranking/action journey Q14 not fully accepted |
| 12 | Can they organize leads into lists? | YES — VERIFIED | S01/S02: owned company/contact membership, edit/archive and browser operations pass for existing admitted workspaces |
| 13 | Can they create and assign sales tasks? | YES — VERIFIED | S06/S09: revisioned tasks and active-member assignment tested in API/browser |
| 14 | Can they connect their own business mailbox? | NO | S16/S18/B04: no customer Gmail OAuth/token routing; existing global internal mailbox is distinct |
| 15 | Can they create and approve outreach campaigns? | PARTIAL | S11/S12: reviewed workflow/previews exist; customer mailbox and full customer draft-to-approval path incomplete |
| 16 | Can they safely send and track customer campaign emails? | NO | Internal synthetic stack passes, but customer sender ownership/routing is missing; no customer outreach readiness claim |
| 17 | Can they import and export Google Sheets? | PARTIAL | G04/G05: real scoped implementation and synthetic browser/worker acceptance; fresh live owner/customer consent/write blocked |
| 18 | Can they connect a CRM? | NO | R01–R09: no functioning HubSpot/Pipedrive authentication/mapping/sync adapter |
| 19 | Can they create a scoped public API key? | YES — VERIFIED | A03/A04: one-time hashed scoped keys, rotation and denial tests pass when module enabled and actor authorized |
| 20 | Can they receive signed webhook events? | PARTIAL | W03–W08 synthetic receiver/PostgreSQL tests pass; real HTTPS receiver/scheduler acceptance blocked |
| 21 | Can they connect an MCP-compatible AI client? | PARTIAL | M01–M07 official SDK Streamable HTTP client works; named external AI client compatibility pending |
| 22 | Can they use an AI assistant with real workspace context? | PARTIAL | Q17/Q21: real authorized domain tools/proposals exist; current model tests synthetic and populated live browser journey incomplete |
| 23 | Can they view usage and plan limits? | PARTIAL | F17/Q20: request safety counters exist; unified spend, purchased plans, entitlements and billing missing |
| 24 | Is all customer data isolated between organizations? | NO | F15/B02: core resource isolation tests pass, but customer summary leaks internal automation-run metadata; no blanket guarantee |

## External configuration and approvals

- **Google account admission:** owner authorization for public/invited actors, approved consent/client/redirects and staged identities. Current production credentials were not inspected; their presence is not assumed absent. Code restriction remains regardless of credentials.
- **Sheets:** server-only encryption material, owner consent for distinct read/write scopes, a controlled staging spreadsheet/destination and separate approval before any live fixed-range write. Google sign-in is not Sheets consent.
- **Mail:** missing per-workspace connection code must be implemented first; then approved Gmail mail scopes/consent/test mailboxes and explicit staging-canary approval. Global internal app passwords are not customer mailbox ownership.
- **Vertex/discovery/DNS:** existing authorized provider setup may already work; fresh bounded model/source/geography/DNS ownership acceptance and spending approval were not granted here. No replacement provider requested.
- **Webhooks:** owner-approved HTTPS receiver, signing-key validation and verified staging scheduler/worker access; synthetic HMAC/retry tests already pass.
- **CRM:** HubSpot/Pipedrive developer app permissions, sandbox accounts and reviewed mapping/conflict policy after missing adapters are implemented. Credentials alone do not provide sync.
- **Payments/plans:** owner-approved pricing/entitlements and selected processor sandbox permissions; no billing adapter currently exists. Do not advertise paid subscriptions from availability switches.
- **Runtime:** package mirror/approved lock decision and supported Node 24 environment. Installed cryptography 48.0.1 differs from lock 50.0.2; installed Node 26.13.0 differs from package engines. No claim that production is on these installed versions.
- **Legal/release:** approved Privacy Policy/Terms and a staged two-customer acceptance decision; development review text and green synthetic tests are insufficient.

## Actual verification result

- Full backend: **679 passed, 0 failed, 0 errors, 42 skipped** (41 opt-in PostgreSQL cases plus one live-mail case).
- Isolated PostgreSQL: **39 passed, 0 failed, 0 errors; 2 destructive cases deselected**.
- Additional release-gap probes: **0 passed, 2 failed, 0 errors; 41 established cases deselected**. These remain release-blocking defects.
- Frontend: **114 unit tests passed**, typecheck passed, production webpack build passed.
- Browser: **48 passed, 0 failed/skipped/flaky** across seven suites, all local/synthetic.
- Initial assessment copy had 16 font-related PDF failures; adding three existing assets to that sandbox resolved them without source changes. Original auth dev attempt could not start because of sandbox symlink/Turbopack root limits; isolated webpack harness passed its three tests. Original logs retained.
- Prior 43 focused cases pass inside the new full backend; their previous logs remain valid. Earlier 708-pass checkpoint is historical, not the current combined release result.
- `pip check` passes; clean exact lock/supported Node install and live/customer provider journeys are NOT RUN. Exact commands, dates, cwd/environment and artifact locations are in the status report.

## Next development milestone and decision

Begin **B01/B02** minimal repairs and permanent regressions first. Then B03 customer admission only after isolation certification; resolve B05 supported runtime and B06 policy approval. Keep registration restricted while these gates are open. B04 independent mailbox work is the next essential customer workflow, with CRM/enrichment and remaining promised P1 work sequenced in the pending report. B07 staged acceptance closes the release decision after implementation; no production rollout is authorized by this report.

**Production readiness remains BLOCKED even though the established suites pass.** The assessment did not modify application features, production data/infrastructure, .env/OAuth settings, dependencies, email delivery or live integrations; it did not commit, push or deploy.
