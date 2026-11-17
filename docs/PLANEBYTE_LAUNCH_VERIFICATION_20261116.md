# PlaneByte launch verification — 16 November 2026

Completed non-payment improvements are deployed. **The full public paid launch is not ready.** Signup and checkout remain closed. This report distinguishes actual provider/production acceptance from isolated tests and unresolved external decisions.

## 1. Completed and deployed

| Surface | Exact current release |
|---|---|
| SaaS | https://app.planebyte.com |
| Frontend | `64e9f0bada442c1e2c3bf2c7178601ffccc0c1cc`; READY `dpl_8wWL8WssS7nfp9s2VcuS1t56DXE6`; `leadengine-r5ykoikx4-piyushagrawal6s-projects.vercel.app` |
| Backend | `dbfe6a6148a3c057770b69fb4971c28a6fd3d519`; `leadengine-api-00151-tij`, 100% customer traffic |
| API | https://leadengine-api-befca7xg4a-el.a.run.app |
| Build | `b164ea2e-ae0f-4b5f-8549-54acd4758822`, SUCCESS |
| Workers | `leadengine-worker`, `leadengine-acquisition`, `leadengine-quota-canary`: `worker:intent-only-dbfe6a6148` |
| Database | Production schema **51**; five additive migrations from 46; second run zero; no row loss |
| Email | Existing Resend key bound securely to API/normal worker; actual delivery and provider-signed callback passed |
| Diagnostics | Actual production AI job retained four attempt/stage events, including Vertex identity and duration |

Implemented repairs:

- Source-backed company summaries and positioning can be paraphrases after an independent grounding review. Atomic facts and quotations remain exact; unsupported numerical/commercial claims remain rejected. Source assertions, AI interpretations and unknowns are distinguished.
- Name/URL-only AI research no longer qualifies as useful success. Bounded extraction includes public metadata/JSON-LD and prioritizes business/offerings pages. Existing SSRF, robots, content-use, timeout and resource controls remain.
- Onboarding consistently supports up to five ICPs, validates distinct targeting criteria and retains exact known service references. Recommendations remain reviewable hypotheses.
- The compact setup assistant receives saved company context, unsaved draft and private server-resolved follow-up history. It does not silently save changes or substitute documentation for failed AI answers.
- Schema 51 preserves safe attempt-level diagnostics; retries do not erase the previous attempt's cause. No prompt, credential or raw model response is added to production diagnostic logs.
- Research/global-assistant context now reads canonical company fields and actual saved offerings. A completed lexical fallback cannot be cached and relabelled as a validated AI interpretation.
- Report generation explicitly requires one quote per distinct discussion in each item. The bounded combined output allowance is 7,000 tokens, accounting for measured provider thinking consumption; ordinary daily limits, one attempt/provider and timeouts remain enforced.
- The authentication header keeps the theme control visible on small screens. The unverified corporate suffix “Inc.” was removed. The owner's branding, dashboard, navigation, Settings, Graph, Discover and themes were preserved.

Lead Engine code, APIs, tables, contacts, history and suppression records are preserved. Customer-facing Lead Engine access and unrelated outbound sending remain disabled. Netlify marketing was not redeployed. No real payment, refund, mandate, production reset or cleanup was performed.

## 2. Implemented but awaiting genuine live verification

- Full fresh native production signup → delivered OTP → verified account/trial → browser onboarding journey. Native account/admission flags remain off pending approved legal publication and final opening checks.
- A fresh completed authorized Google callback/session on this final frontend. The actual deployed Google authorization handoff passed, including canonical callback and S256 PKCE; no Google credentials or mocked callback were used. Auth.js retains its existing default `checks=["pkce"]`; no extra state check was configured or claimed.
- Final-source production report and global semantic-assistant acceptance after ordinary operator capacity resets. The owner workspace has reserved **95,884/100,000** daily tokens, leaving 4,116, below the report's output ceiling alone. No limit was raised or reservation refunded to force a pass.
- Optional JavaScript-only extraction in the actual hardened Cloud Run browser runtime. The renderer's isolated real-Chromium security test passes, but the production flag stays **false** until container/sandbox acceptance is recorded. Static/metadata extraction is live.
- Real customer Gmail/Sheets/destination webhooks, named MCP GUI clients and independently adjudicated semantic quality remain limited to the evidence in the checklist. Unavailable adapters must not be advertised as connected.

## 3. Credentials, approvals and merchant permissions

**OWNER APPROVAL REQUIRED — verified legal fact:** legal contracting name, legal form and official service address. The existing complete Terms/Privacy/Refund/Cancellation drafts remain unpublished. Do not invent these details or repeat already-approved refund/retention questions.

The owner is personally verifying PayU account-specific USD charging, international activation, settlement currency/conditions and merchant permissions. Separate valid Test Mode credentials/capabilities are still required securely for genuine sandbox acceptance. Existing live key/salt are already present; do not request them again or assume they work in Test Mode.

Vercel reports the existing team is on Hobby. The owner explicitly authorized continuing development/deployment there and will review commercial hosting before paid public launch. Do not upgrade or move infrastructure without the applicable authorization. Vercel's published commercial-use restriction is documented at https://vercel.com/docs/limits/fair-use-guidelines.

Resend is **not** a missing-key blocker. `leadengine-resend-key:1` and `leadengine-resend-webhook-secret:1` are bound and verified without exposing values. Existing Hostinger SMTP/IMAP acceptance remains unavailable; the working Resend transport does not certify Hostinger.

## 4. Remaining defects and limits

| Priority | Finding / cause | Required next step |
|---|---|---|
| P0 launch acceptance | Native production signup and complete new-customer journey are gated and unverified, rather than established as working | Verified legal facts/publication, versioned consent, controlled admission/account activation and full real journey |
| P1 | JS-only sites lack accepted production browser execution; feature remains off | Verify the existing container's sandbox and network fencing before enabling; retain manual/insufficient-evidence states |
| P1 verification | Final-source production reports/global semantic answers cannot be exercised within today's remaining operator reservation capacity | Retest after normal UTC capacity reset; preserve the cap and unknown-outcome accounting |
| P1 performance | Representative private reads still take roughly 3–7 seconds in the small release sample; API India / DB US-East round trips are material | Measured query/latency work and an approved topology plan if needed; no sub-2-second or scale claim |
| P1/permission | Several external integrations/sources lack customer permission or operational acceptance | Keep unavailable; obtain the specific adapter, source permission or controlled destination and verify it |
| P2 quality | Broad independent AI relevance/intent evaluation and exhaustive accessibility are not certified | Approved representative permitted corpus/reviewers and focused acceptance |

No current failure in the final isolated security/data-integrity/regression suite is hidden. Passing tests and the verified scope above do not establish every customer journey or commercial readiness.

## 5. Actual onboarding AI results

The original SyntaxWars jobs were inspected only within authorized workspace `6418a8ee-670f-4adf-922f-158299a19234` and verified owner `syntaxwars@gmail.com`.

- Website `913bf739-34ca-4fea-978a-3ed59907e67f` had returned only name/website despite READY.
- The first ICP execution for `4eb1482c-42aa-4929-9b4b-8f858daf4fb0` logged an application review failure after an actual successful Vertex call (7,493 ms). The specific rejected criterion was not retained and cannot truthfully be reconstructed. No timeout or particular validation guard is asserted as the historical cause.
- No original customer profile/ICP was overwritten and no historical attempt events were fabricated.

An authorized clean owner workspace (`1a1a7969-dbbe-4488-ab7c-c63127807fcc`) exercised genuine website research, reviewed save, five ICPs, approval, saved defaults, contextual AI guidance/follow-up and completion. No Intent Radar grant, monitor, search, mail or payment was started by setup. The original owner profile and selected workspace were restored unchanged.

| Stage | Actual cloud job |
|---|---|
| Website READY | `5e80eabd-73bc-47e9-b72c-a2ef41d39b24` |
| Five ICPs READY | `23f635b5-965f-415e-87d9-2e54eb0ae562` |
| Contextual guidance READY | `a1abea53-fb08-4692-a447-f131144f5f20` |
| Follow-up READY | `2f6df774-2d8f-45f5-9fce-cecaf832f97d` |
| Final backend source, real Vertex guidance PASS | `1955fb57-aa24-4712-803e-dce859d3f435` |
| Final production/schema51 follow-up and durable diagnostics PASS | `78c8de87-fe36-477a-a44d-fca4b316a6a6` |

The complete five-ICP flow ran on source `125497a`; the relevant setup modules are unchanged in final backend `dbfe6a6`. The final-source worker and post-migration production checks above separately prove actual execution. These are server-authenticated owner checks, not a completed fresh-customer Google/native browser login.

The generated profile contained an evidenced platform description and Code Ops offering. Five distinct reviewed hypotheses covered higher education, bootcamps, corporate L&D, school STEM and technical assessment providers, with different roles/needs/pains and explicit assumptions. This is not proof of existing customers, budgets or outcomes.

Report acceptance exposed duplicate-source citations and a 3,000-token combined cap that left only 105 response tokens after 2,879 thinking tokens. These were not relabelled as success. The repaired real-provider contract passed with **4 themes, 8 findings and 20 exact citations**, one source per item citation set. Its production worker acceptance remains deferred by the operator cap described above.

## 6. Actual Resend and account results

Normal isolated account services sent three real emails to the authorized `contact@planebyte.com` inbox: signup OTP, password recovery and password-change notice. Resend confirmed delivery. Verification, wrong-code/resend rejection, exact trial limits, one-use reset, old-session revocation, old-password denial and new-password login passed. Codes/tokens/passwords were kept in process memory; no production password/account was changed. Mailbox contents were not independently retrieved, so this is not claimed as manual inbox/browser signup acceptance.

Production independently passed normal invitation → encrypted outbox → Cloud Run worker → Resend → **actual provider-signed webhook** → DELIVERED. One attempt, encrypted payload purged, test invitation revoked, no membership granted.

- Notification `cb8b14ad-5fa2-41ca-a4c9-2401246ba4c6`.
- Resend message `01a1e3f7-114a-79e6-8be4-7144111678e0`.
- Enabled webhook `dc76f72e-4e6b-491a-b394-bdae2d3b3ff5`.
- Correct-key/malformed-event and tampered-signature probes passed without creating synthetic production events.
- Bounce/complaint suppression, deduplication and races have isolated tests; a deliberately bounced customer email was not sent.

## 7. PayU results

Authenticated Live merchant dashboard MID **13851032** and active payment methods were observed. INR dashboard amounts do not prove the charging or settlement contract. USD/international permissions, legal KYC record and separate Test Mode remain unverified; the owner is checking them.

One-time hosted initiation, immutable quote/consent, independent captured-payment verification, callback integrity/idempotency, history, fixed-term activation/expiry and refund-observation handling pass isolated and PostgreSQL tests. No genuine merchant sandbox payment or real transaction was performed. Checkout is closed. No GSTIN was invented or required, no GST added, no automatic recurring mandate enabled, and yearly checkout remains off.

## 8. Exact steps to open public signup

1. Obtain verified contracting identity/address; finalize and approve publication of the existing legal drafts and consent version. Approved refund/cancellation and 30/90-day retention policies are already recorded.
2. Recheck schema51, secret bindings, actual mail delivery/signatures, abuse/isolation and compatible rollback; do not rerun completed repairs or reset data.
3. Configure approved native access/admission and terms version through the established controlled rollout, preserving existing authorized Google/Gmail users.
4. Execute one authorized fresh work-email or real Google journey through verification, exact trial, website/profile/ICP review, saved context, assistant and dashboard/Discover; test foreign/revoked access and paid-only trial denial.
5. Open public admission only after those real checks pass. Do not merely change a public-registration boolean.

## 9. Exact steps to open checkout

1. Complete signup/access/legal gates and the owner's commercial-hosting review.
2. Record account-specific PayU USD/international and settlement authorization; securely obtain valid separate Test Mode credentials/capabilities.
3. Complete genuine sandbox hosted checkout, callback/server verification, duplicate/tampered/late delivery, exact currency/amount/UDF, single entitlement, history and expiry acceptance.
4. Keep monthly fixed terms at 30 days and manual renewal; no early upgrade/proration/auto-renew. Keep yearly disabled until prices and allowance cadence are approved. Collect no unverified GST.
5. Obtain separate exact authorization before any real charge/refund/mandate. Only enable the accepted scope after final configuration/merchant approval.

## 10. Release, evidence and rollback

Restricted evidence: `data/artifacts/verification/onboarding-repair-20261116/`. Do not commit its customer/provider outputs or credentials.

- Backend: **1,153 passed, one explicit live-mail skip, eight warnings**, PostgreSQL and actual isolated Chromium included. `backend-approved.{xml,log}`.
- Frontend: **181 passed**, types and focused lint pass, fresh Webpack build; final UI account browser passed. `frontend-*-final-ui.log`, `accounts-browser-final-ui.log`.
- Local app browser: product10, onboarding2, accounts1; external transports are synthetic and labelled separately from real acceptance.
- Actual deployed guest browser: twelve screenshots at 1440/390/320 in light/dark; theme persistence/control bounds, closed signup and real Google handoff pass. Fresh authenticated callback is not claimed.
- Fresh production MCP acceptance passed with official SDK2.3.0: HTTPS handshake,13 available read tools, authorized monitor read, unknown-resource denial, hidden Lead Engine tools absent, test key revoked and subsequent access401. Named GUI-client certification remains separate. No discovery, AI, outreach or payment tool was invoked.
- Final image/traffic/secret/safety audit passed; bounded API151 error review recorded zero ERROR-or-higher entries. This is not an uptime/scale guarantee.
- Fresh snapshot `data/backups/beta-recovery-20261116T071702Z/production.dump`, **118,860,123 bytes**, SHA256 `31bd74ca2c8626755ea98855ce0e242ca0087416ecbda84054f68f09ce053b13`. Exact isolated restore and 46→51 migration preserved original data; second run zero.
- Production migration: zero row loss; only migration history and routine worker health/retention cursors changed among existing tables.
- Compatible flag-off rollback: **`leadengine-api-00149-luc`**, checked against live schema51 through https://schema51-rollback---leadengine-api-befca7xg4a-el.a.run.app while customer traffic stayed on151. Runtime/job snapshots and images are retained. Never cold-start old source65e9 against schema51.
- **After native workspace enrollment, retain access-period enforcement in any rollback.** The flag-off149 baseline is appropriate only while native managed-workspace enrollment remains empty; schema verification intentionally refuses a rollback that would weaken enrolled-customer quota enforcement.
- Frontend rollback: prior deployment `dpl_8qft5cRk9oGjRJRkCz6uh1fX9Xsa` is retained, but it still has the old footer/mobile-header defects. Prefer a corrective release unless an actual regression requires rollback.

Approved policy remains seven days/no card/no auto-renew; five searches, three shared AI operations, 150,000 reserved tokens, one manual monitor/member and one trial per person/domain. Monthly USD list prices are $59/$149/$379. Initial-purchase refund requests within seven days, mandatory rights preserved; ordinary verified-closure deletion within 30 days and backup aging target ≤90 days with justified exceptions. No deletion/purge was performed by this release.
