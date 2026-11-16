# PlaneByte master handover

Updated 2026-11-16. This is a continuation checkpoint, not certification of a full public paid launch. The owner requested a safe release and handover, with no new major features or lengthy investigations. Read the final deployment record below before relying on older reports.

## Release and repository checkpoint

- Working repository: `/Users/planebyte/.codex/worktrees/planebyte-public-launch/planebyte-leadgen`.
- Branch: `codex/public-launch-20261115`.
- Application release source: `65e9cd3ae998106e268a66f172cb098cd2146410`.
- Account/trial/payment implementation: `9b7b3cf`; preserved owner UI/branding merge: `ca1dc85`; combined verification/privacy workflow: `bd3ce74`; container contract/build-evidence fix: `65e9cd3`.
- Owner checkout: `/Users/planebyte/Documents/Projects/planebyte-leadgen`, branch `codex/intent-radar-phase4-20261113`, last inspected HEAD `15d40b8a7d23fd662b467cf9fc4c5c598947c30f`. Its newer logo, warm authentication styling, dark typography and button contrast are merged here. Dashboard, unified Settings, navigation, Graph and Discover changes are preserved.
- Owner checkout has unrelated untracked marketing directories, screenshots/verification scripts and SVG experiments. Do not stage, remove or overwrite them. The launch checkout is the release source; do not reset it to the owner checkout's older application commit.
- Documentation-only checkpoint comes after the application release. Resolve its exact commit with `git log -1 -- docs/PLANEBYTE_MASTER_HANDOVER.md`.
- Final live revisions and release outcomes are recorded in **Final production result** at the end of this file and restricted evidence under `data/artifacts/verification/public-launch/final/`.

## Architecture and infrastructure

PlaneByte is a modular monolith. FastAPI/Pydantic serves existing domain packages; Next.js 16.4.3, React 19.3.1 and Auth.js 5 beta serve the SaaS. Node 24 is pinned. PostgreSQL is authoritative in production; SQLite is for isolated tests. Do not split into additional services or replace shared auth/provider/session infrastructure without measured need.

| Component | Existing resource / code | Operational notes |
|---|---|---|
| SaaS | `https://app.planebyte.com`, Vercel project `leadengine` (`prj_xT1PDDXHTYsjdHgI776MQtLzFPZb`), root directory `dashboard` | Separate from marketing. Existing production environment/Google credentials retained. |
| Marketing | `https://planebyte.com`, Netlify site `2d443c36-f35e-4738-9dd3-3889e8629edd` | Not redeployed by this wrap-up. Owner's separate working directories remain intact. |
| API | `https://leadengine-api-befca7xg4a-el.a.run.app`, Cloud Run `leadengine-api` | GCP project `querryside`, region `asia-south1`. Existing signed server gateway; browser never receives signing secret. |
| Workers | Cloud Run Jobs `leadengine-worker`, `leadengine-acquisition`, `leadengine-quota-canary` | Same locked runtimes; bounded overrides, durable leases, cancellation and fencing. Existing scheduler settings preserved. |
| Images/builds | Artifact Registry `asia-south1-docker.pkg.dev/querryside/leadengine/{api,worker}`; Cloud Build | Source SHA labels and exact image tags checked; both image dependency checks required. |
| Database | Existing Neon PostgreSQL, `us-east-2`; secret `leadengine-database-url` | Cross-region latency is material. Production schema remains 46 for this flag-off release; source supports additive migrations through 50. |
| AI | Existing Vertex-first gateway `app/acquisition/{ai,ai_router,vertex}.py`, shared usage/accounting | Actual earlier production inference used Vertex `gemini-3.6-flash`; a successful provider call is not proof of onboarding quality. |
| Storage/cache | Existing GCS/artifact adapters; optional Upstash read cache | Access is workspace scoped; do not move hosting or invent cache hit/scale claims. |
| Email | `app/notifications/*`, existing internal/customer mail services | New encrypted Resend outbox is gated. Legacy Hostinger/Gmail and customer OAuth remain separate. |
| Billing | `app/billing/*`; native fixed-term access ledger plus preserved historic Razorpay/PayU code | No live charges, refund initiation, recurring mandate or checkout activation authorized in this wrap-up. |

See `PLANEBYTE_COMPLETE_LAUNCH_CHECKLIST.md` for feature-level acceptance and `PLANEBYTE_NEXT_AGENT_START_HERE.md` for safe commands.

## Status language

**Deployed and Verified** means the named behavior has live evidence on the stated revision. **Implemented but Not Deployed** means absent from the live source. **Not Verified** includes deployed disabled code and behavior lacking real acceptance. **Partially Working**, **Broken**, **Missing**, and **Externally Blocked** are explicit limits. A UI card, adapter, passing synthetic provider response or historical inventory label is never operational certification.

## Customer features

| Area / smaller capabilities | Current status and evidence | Remaining work |
|---|---|---|
| Existing approved Google login; secure session; sign-out; unauthorized redirect | Partially Working: existing production authenticated SyntaxWars session observed before release; real OAuth preserved; new clean OAuth round trip must be recorded on final revision | Do not change allowlist/OAuth client or replace Google with mock auth. |
| Work-email signup, password confirmation, verification/resend, recovery/reset, Google linking/add password, server revocation | Not Verified in production; implemented and isolated account/browser/PostgreSQL tests pass; intentionally disabled | Schema 48–50, mail runtime/webhooks, actual delivery and full security/legal acceptance before flags. |
| Trial, invitations, role/capacity checks, workspace membership, domain policy | Not Verified in production; approved policy and concurrent database tests implemented | One trial/person/domain; no domain auto-join; verify actual fresh-customer journey and paid-only restrictions. |
| Onboarding resume, reviewed website preview, company/services editing, saved context, ICP review/approval, completion | Partially Working: two real-app synthetic-provider browser flows pass; real SyntaxWars reliability/quality remains open | Fix and verify real website → profile → ICP → review → Graph/Discover journey. No automatic discovery or send. |
| Website research | Broken quality/reliability requirement: production job reached READY, but meaningful complete source-grounded output is not certified | Verbatim validator conflict, sparse READY threshold and static crawl limits below. |
| ICP generation, refine, explicit accept/activate, primary ICP | Partially Working: exact production job READY after second attempt; first failure unexplained; offline validation/replay/scope tests pass | Diagnose original attempt; improve errors/quality; existing maximum is three candidates, urgent request for 3–5 not implemented. |
| Setup assistant and global assistant | Partially Working: deterministic counts/follow-up and existing structured guidance implemented; earlier real Vertex guidance accepted; owner still reports broken onboarding responses | Saved/draft conversational context and compact contextual experience remain unfinished; do not relabel static help as AI. |
| Dashboard, compact signal summaries, quick entry, sidebar, account menu, theme | Source preserved; local route and responsive acceptance pass | Final live route smoke is narrower than a complete authenticated browser replay. |
| Unified Settings | Profile/company/team/workspaces, research defaults, integrations, developer/API/MCP, billing and appearance reuse canonical services | New native account/privacy controls remain disabled until account rollout; test each enabled save/refresh with real session. |
| Intelligence Graph | Existing saved company/offering/ICP/context editing, categories, list/search, zoom and links implemented; seven-width local browser checks pass | Expanded pain/brand/intent ontology is partial; no fictional graph facts. |
| Discover | Natural-language/manual configuration, sources/keywords/exclusions, review, progress/history/cancel/retry and scoped results implemented | Real HN acceptance exists on earlier source; other sources remain permission/configuration gated. No full-text internet coverage claim. |
| Signals | Lists/detail, source URL/excerpt/date, score/uncertainty, saved/dismissed review and filters implemented | Independent intent/quality evaluation not complete. Signal is not a verified buyer or permission to contact. |
| Opportunities | Grouped needs/evidence, review/status and links implemented | Live classification quality/representative corpus acceptance remains partial. |
| Monitors/schedules | Manual create/edit/pause, safe frequencies/timezone, due dispatch and revocation fencing implemented | Fresh actual worker acceptance on release required; native trial may create only one manual monitor. |
| Alerts | Source issues, monitor activity and failure states; review controls implemented | External email/Slack delivery is not established by in-app alerts. |
| Growth/research library | Evidence-grounded reports, citations, save/replay, MD/CSV/JSON exports; real earlier Vertex report acceptance | New release controlled report/worker evidence recorded separately; independent reviewer approval remains open. |
| People/lists/tasks/enrichment/recommendations | Existing Lead Engine domain code, historical records and gated pages preserved | Not launched as Radar functionality; direct APIs/workers must continue denying disabled modules. |
| Lead Engine prospecting/mail/campaigns/scans/templates/import/Sheets/PDF/history | Preserved completely, intentionally unavailable to customer-facing Radar | Future launch needs separate completion/acceptance. Mandatory five-template/static-PDF experiments are not default SaaS onboarding. |
| API/developer keys/MCP | Expiring hashed keys, scopes/rotation/revoke, signed webhooks and read tools implemented; earlier real MCP SDK 2.3.0 HTTPS acceptance with 13 tools | Named ChatGPT/Claude/VS Code client GUI certification remains not verified. Never paste actual keys into docs. |
| Billing UI/price catalog | Approved USD $59/$149/$379/custom and closed-checkout state implemented | Do not infer entitlement from frontend labels or historic subscription state. |
| Native payment history/receipt/refund request/expiry | Not Verified live; offline/PostgreSQL concurrency/security cases pass; disabled | No GST tax invoice; no automated refund initiation. Full refund observations revoke only corresponding periods. |
| Privacy export/request/reviewed closure | Not Verified live; authenticated account export/intake plus operator-reviewed deadlines implemented/tested | No production purge executed. A complete workspace archive/backup erasure operator process still needs acceptance. |
| Administration/audit/health/source controls | Existing scoped role, grant, audit and safety services preserved | Do not expose internal cleanup/operator tools to customers or change product grants globally. |

## External integrations: actual status

| Integration | Status / actual evidence | Gate or limitation |
|---|---|---|
| Resend | Not Verified live, with credential blocker resolved: updated existing key accepted HTTP 200 and `planebyte.com` verified; installed `leadengine-resend-key` version 1 | Zero acceptance messages sent at checkpoint. Confirm runtime-specific IAM/binding/from address/Svix secret, then controlled normal OTP/recovery inbox receipt. Do not ask for another API key. |
| Hostinger Mail | Partially Working: connected owner mailbox connector available; explicit existing SMTP/IMAP health probe UNAVAILABLE | Do not claim outbound transport works or change legacy credentials. Owner mailbox `contact@planebyte.com` is the controlled transactional acceptance destination. |
| Google OAuth | Partially Working: genuine existing customer session observed; no fake auth | Fresh final-revision callback/session/revocation acceptance pending. Gmail/Sheets authorization is distinct. |
| Vertex AI | Partially Working: genuine prior production guidance/report inference and token accounting | Current onboarding quality/failure recovery remains open; optional Gemini fallback not independently certified. |
| PayU | Externally Blocked: authenticated Live dashboard, merchant MID 13851032; active EMI/netbanking/credit/debit/cashcard/UPI observed | Dashboard panels sometimes server-error; amounts displayed INR. Actual USD/international permission, settlement contract, KYC identity/address and Test Mode remain unverified. Live key/salt presence proves none of these. |
| Hacker News | Deployed and Verified on previous release: official API real bounded five-result worker check, monitor paused afterward | Fresh release worker result must be read from final evidence; recent feeds, not full historical search. Jobs opt-in and not assumed buying intent. |
| Stack Exchange | Externally Blocked for commercial activation; real bounded public API evaluation succeeded earlier | Commercial API/CC BY-SA/attribution permission review, approved site list; optional key is not permission. |
| Reddit / GitHub / Slack community listening | Missing customer-operational connectors or Not Verified; no production acceptance | Do not advertise as connected. Require implemented permitted adapter, credentials/terms and tenant acceptance as applicable. |
| RSS | Partially Working: actual W3C evaluation and conditional transport tests | Publisher/host/feed-specific permission/configuration needed for customer activation. |
| Atom | Not Verified live; parser fixtures pass | Prior separate W3C Atom URL returned 404; record a genuinely permitted Atom success. |
| Discourse | Partially Working: public Meta latest.rss evaluation succeeded | No private forums/login/arbitrary search. Instance/endpoint-specific robots/terms review required. |
| Google Gmail customer OAuth | Not Verified live; encrypted scoped lifecycle implemented | Approved consent/scopes, callback, refresh/revoke and controlled sender acceptance. Customer sending remains disabled. |
| Google Sheets | Not Verified current live; scoped import/export and OAuth infrastructure preserved | Test authorized workbook/range/refresh/revocation; no broad overwrite. |
| Firecrawl | Not Verified on this release; existing bounded Lead Engine acquisition integration and server credential reference preserved | Lead acquisition remains unavailable. Do not assume website-onboarding research currently uses Firecrawl; its existing crawler is a separate path. |
| Razorpay | Preserved historical sandbox provider and ledgers, Not Verified current live | Existing test key/webhook references remain; new owner policy uses PayU one-time fixed-term access, not recurring subscriptions. No legacy financial records deleted. |
| R2/object storage | Existing server-only endpoint/bucket/key references retained, Not Verified current end-to-end access | Workspace/attachment ownership and signed access must be accepted before advertising customer storage/export capability. |
| OpenStreetMap/Overpass/Nominatim/Overture and legacy auditing/providers | Preserved disabled Lead Engine implementation, Not Verified current external acceptance | No scan, bulk acquisition, Lighthouse, performance/security audit or outreach was enabled by the Radar release. |
| CRM HubSpot/Pipedrive and other catalog cards | Missing operational adapters or Not Verified | Cards are not working OAuth/sync. Future scope, credentials, mapping/idempotency and tenant tests required. |
| MCP / REST / outgoing webhooks | Partially Working: real earlier SDK handshake/read/foreign deny/revoked 401; signed receiver foundations tested | Named-client GUI and actual customer receiver acceptance pending. |
| Neon/PostgreSQL | Deployed and Verified connectivity, scoped reads and backup/restore | Source schema 50 vs live 46 intentionally; no migration/reset in wrap-up. |
| Cloud Run/Cloud Build/Registry | Existing operational infrastructure; final exact revisions below | No new infrastructure or region move. Preserve resource identities, secrets, scheduler settings. |
| Vercel | Existing operational SaaS project; latest owner deployment 15d40b8 preserved in merged source | Final source/domain proof below. Verify current commercial plan eligibility; older Hobby finding is historical, not rechecked permission. |
| Netlify | Existing marketing deployment `6af9e0a27731179a434f6291`, 2026-11-15; public pages HTTP 200 | Not redeployed. Existing secret environment values are write-only; do not attempt recovery bypass. |
| Upstash/GCS/other legacy discovery/SMTP APIs | Not Verified current end to end | Read exact enabled configuration; presence is not acceptance. Keep legacy adapters/data intact. |

## AI failure findings and reproduction

Exact affected signed-in account is `syntaxwars@gmail.com`, active OWNER of workspace `6418a8ee-670f-4adf-922f-158299a19234`. This is an existing authorized Gmail identity; do not block it under new work-email signup policy.

- Website job `913bf739-34ca-4fea-978a-3ed59907e67f`: READY, attempt 1, 2026-11-16 03:45:52–03:46:53 UTC; execution operation `29a91847-3404-46d9-b331-f32c26489004`.
- ICP job `4eb1482c-42aa-4929-9b4b-8f858daf4fb0`: READY after **two** attempts, last update 04:00:24 UTC; latest execution operation `f3302cf8-63de-4ec3-9027-f8b83eaa7189`.
- Read-only metadata is in `final/ai-affected-job-diagnostics-private.json`. No profile/ICP was applied or changed by diagnosis. First failure reason is overwritten in the current job row; provider/worker logs must establish it. A successful retry is not a root-cause fix.
- **Confirmed code conflict:** `app/platform/company_autofill.py` permits AI summaries but rejects scalar description/positioning unless the value occurs verbatim in supporting source quotes. Service description/category paraphrases can also be discarded. This can remove useful grounded interpretation. Fix with explicit evidence/fact/inference contracts, never by accepting unsupported claims.
- Static bounded HTML collection has no confirmed JavaScript rendering fallback, prioritizes contact links, and can accept a sparse preview as READY. Research quality threshold is insufficient for the requested experience. Preserve SSRF, robots/content-use restrictions, bounds and exact quote/source validation.
- `app/icp/builder.py` has 25-second provider / 30-second outer generation bounds, 7,000 output tokens and broad safe error conversion. These are potential failure contributors, **not established cause** of the first production failure. Do not blindly extend timeout or retry unknown completed provider calls.
- Original attempt events/error classification are insufficiently durable. Structured safe stage/attempt/error/provider/duration history is unfinished; no migration 51 exists.
- `app/platform/onboarding_ai.py` answers some saved facts deterministically; compact contextual multi-turn setup guidance and 3–5 ICPs from urgent brief are unfinished. Existing max is three. No synthetic fixture change repaired production AI.

Reproduce only in an authorized clean test workspace through real login → setup → public website → reviewed company/services → real ICP job → explicit approval → persisted Graph/Discover/settings context → assistant → dashboard. Save exact job IDs, safe stage/error/timing/provider usage and source citations. Do not overwrite SyntaxWars/PlaneByte company data or create hardcoded SyntaxWars handling.

## Payment and legal policy

Approved: seven-day no-card trial, five searches, three shared AI operations, 150,000 reserved tokens, one manual monitor/member, one trial/person/domain. Schedules/reports/API/MCP require paid access.

Monthly access is exactly 30 days; manual renewals and plan changes queue after the last purchased term. No auto-renew, proration/early upgrade/unused-time credit. Yearly model is a calendar year, but prices/discounts/allowance cadence are not approved; yearly checkout remains disabled. USD list prices are $59/$149/$379. No GSTIN exists; collect no GST and do not make GSTIN mandatory. Do not convert to INR arbitrarily.

Implemented one-time PayU flow uses server immutable quote/consent, uncertain-create REVIEW, reverse callback hash plus independent v3 captured-payment verification, exact currency/amount/UDF matching and idempotent entitlement activation. Return URL/success body alone never grants access. History and JSON payment receipts preserve provider/mode classification. Refund request is review intake; read-only external refund observations are not refund initiation. Preserve legacy ledgers.

Owner approved initial-purchase refund requests within seven days, mandatory rights preserved; access continues to term expiry without auto-renew; ordinary data deletion within 30 days after verified closure, backup aging target ≤90 days, justified legal/accounting/dispute/security exceptions. Complete Terms/Privacy/Refund/Cancellation drafts are unpublished. **OWNER APPROVAL REQUIRED / verified fact needed:** actual legal contracting name, legal form and official business address from KYC/business records. Existing marketing copy “Planebyte Studios / Bangalore” is not verified KYC and must not be copied as fact.

Public signup additionally needs real mail, legal publication, reviewed isolation and full real AI onboarding acceptance. Paid checkout needs account-specific USD and settlement permission, separate test credentials/Test Mode, yearly decisions if annual plans are offered, secure live configuration and verified end-to-end fulfillment. A real test charge/refund needs separate exact owner authorization. GSTIN absence by itself is not a blocker.

## Verification, performance and risks

- Frozen application: **1,144 backend passed, one explicit real-mail skip, eight warnings**. Includes 83 PostgreSQL cases. `final/backend-approved.{log,xml}`.
- Frontend: **181 unit passes**, type check and targeted lint pass, Webpack production build passes. `final/frontend-{units-corrected,types,lint,build}.log`.
- Real-app browser with synthetic external AI/crawl/email: product 10, accounts 1, onboarding 2; zero unexpected/skipped/flaky. Product routes at 320/390/768/1024/1280/1440/1920 widths; light/dark, 32 account screenshots. This is not real email/Google/payment/AI acceptance.
- Corrected test harness failures: missing matchMedia for preserved owner animation; combined onboarding fixture lacked global Answer schema; overlapping generated build artifacts and stale selectors in earlier runs. Do not count initial failures as current product defects or suppress future failures.
- Remote initial build `73fdfd0d-3733-4604-baa7-3b915e371d36` failed because Dockerfiles asserted schema 47. Fixed to exact source schema 50 in `65e9cd3`; replacement build `0e5f2ecb-fad3-4b84-b4fc-8a3199bcb6bb` result below. No application behavior was changed by this fix.
- Previous source7eb production C2 diagnostic: summary median 3.735s, observed p95 4.5025s; full overview median 4.3077s, observed p95 4.839s. Older baseline overview median 20.8905s. These are small diagnostic samples, not broad load/SLA proof. API India vs DB US-East round trips remain material. Sub-2s/3s targets not achieved or certified.
- P0 public-release blockers: unfinished real onboarding/assistant reliability, unverified real mail/full new-account journey, actual legal identity and closed admission/payment gates. No claim of paid launch readiness.
- P1: external source licensing, independent AI quality adjudication, real customer integrations/named MCP clients, yearly business decisions and actual payment settlement/refund acceptance. Do not infer scale or regulatory compliance from unit tests.

## Database safety and recovery

Production data was not reset, deleted or migrated by this wrap-up. Current source is compatible with schema 46 while new features remain off. Migrations 48–50 add accounts/notifications, native periods/payments/refund observations and privacy requests. Migration 47 is also included in the recovery sequence. No destructive migration or purge is authorized.

Exact backup: `data/backups/beta-recovery-20261115T155200Z/production.dump`, 118,630,364 bytes, SHA256 `78cc3f1962169cbf706c62c3a595725f7a765d4124d67ed986d68014c0233dbc`. Rehearsal `final/recovery50/recovery-result.json`: exact restore, schema46→50, four migrations, second run zero, no original data-table changes/row loss. This is a Nov15 snapshot, not a fresh Nov16 production backup.

Stage A manifest `final/cleanup-manifest-private.json`: zero proposed/authorized deletions. All historical Lead/shared/contact/suppression/billing/audit/credential records retained. Do not treat names as proof a row is disposable. Before any future production migration take a fresh backup and prove restore; before cleanup additionally obtain exact scoped manifest authorization.

After migrating above 47, **old source7eb containers are not a valid cold-start rollback** because their schema maximum is lower. Retain a tested newer schema-compatible flag-off revision. Never restore a stale backup over new production customer records to undo an application release.

## Final production result

Verified **2026-11-16 04:48:15 UTC (10:18:15 IST)**. Safe flag-off backend and SaaS frontend deployment **completed**. Full public paid launch **not complete**.

| Result | Exact evidence |
|---|---|
| Application source | `65e9cd3ae998106e268a66f172cb098cd2146410` on `codex/public-launch-20261115` |
| Cloud Build | `0e5f2ecb-fad3-4b84-b4fc-8a3199bcb6bb`, SUCCESS; both API/worker image builds and dependency checks passed |
| Production API | `leadengine-api-00145-tax`, 100% traffic and all retained tags; `https://leadengine-api-befca7xg4a-el.a.run.app` |
| API immutable digest | `sha256:9be0b764e635c6ff5773241e291bc1bff79795b5dfcebdace9a34eaf3f65e7d2` |
| Workers | `leadengine-worker`, `leadengine-acquisition`, `leadengine-quota-canary` all use `worker:intent-only-65e9cd3ae9`, built digest `sha256:4af39e40749a0ca3f4b5becda529d2c4bf022f21da409fd400dc7988c68c6a3c` |
| SaaS frontend | READY `dpl_8njxByesgVJWBbuhnpvssyuTxMcU`; exact source metadata65e9; `app.planebyte.com` alias verified to `leadengine-rgt2wbpde-piyushagrawal6s-projects.vercel.app` |
| Actual production API smoke | All15 expected results passed: health200;12 enabled health/read paths total and3 intentionally disabled Lead APIs404. Health0.319s; signed read observations2.034–7.043s. No latency-SLA claim. |
| Additional production reads | Seven200s: onboarding state/progress/assistant-context, Radar settings/shared profile context, completed worker job and report. These are reads, not fresh website/ICP acceptance. |
| Actual public frontend | Login/signup/recovery/reset/verify pages200, Google provider config200, session200 without private capability; three protected routes307→login; four deployed static assets200. Signup explicitly closed. |
| Fresh real worker/provider acceptance | One owner-controlled report `9fdd46b6-1877-5677-b374-826f873ca0f6`, job `3f715b88-167e-4640-bf05-e87bb07c887a`, operation `c3d92879-60ec-439e-9900-383fd92fa169`; COMPLETE, actual Vertex `gemini-3.6-flash`,10 citations,3,878 input/1,223 output tokens; MD/CSV/JSON exports and idempotent replay passed; persisted result read back through production |
| Deterministic assistant | Count→today follow-up→greeting/replay passed; zero provider-request delta. Normal acceptance added scoped owner conversation/report records; no prospect/customer outreach or profile changes. |
| Error review | Zero severityERROR-or-higher entries for exact new API revision from04:30UTC through04:48UTC bounded query. Not a global uptime/worker/error-free certification. |
| Data/config preservation | Live schema46 confirmed; no production migration/reset/deletion; runtime settings/secret references/service identities and schedulers retained. New accounts/native periods/mail/fixed-term checkout remain defaultfalse, existing public signup/checkout/outreach/Lead flags explicitlyfalse. |
| Marketing | Not redeployed; existing Netlify site retained |

Fresh signed-in browser acceptance was **not completed**: the browser session was explicitly stopped, and browser interaction ended. The candidate's temporary Vercel URL used existing SSO protection; no bypass secret was created or protection weakened. Final public-domain HTTP checks passed after promotion. Prior local light/dark/mobile acceptance remains separate from new production browser acceptance.

Unresolved real website/ICP/setup-assistant issues above were **not fixed** by this release. New account/email/trial/privacy/payment code is included in the deployed source but **disabled and not verified live**; migration50 still required before its controlled activation. No real OTP acceptance, new customer signup, payment, refund or mandate occurred.

Restricted proof index: `release-final.json`, `backend-promoted.json`, `production-smoke.json`, `production-setup-context-smoke.json`, `staged-runtime-inventory.json`, `staged-functional-acceptance.json`, `staged-functional-state.json`, `frontend-production-http.json`, `vercel-production-alias.json`, `vercel-staged.json`, build/test/recovery logs under `data/artifacts/verification/public-launch/final/`. Exact rollback snapshots: `data/backups/product-65e9cd3ae9/`. Previous API `leadengine-api-00143-laf` source7eb and previous Vercel source15d deployment `dpl_2QjNxMpKmHBszB3mshTZyWaUZvXF` remain the recorded pre-release state.
