# PlaneByte complete feature and launch checklist

> **Current verified checkpoint — 17 November 2026, 08:25 PM IST:** Approved42-row test-account reset complete. Zero customer accounts/active customer workspaces; old-session401; prior Creem Live subscription cancelled with no next transaction. Protected billing/audit/consent references, schema, Creem products and archive preserved. Fresh controlled signup for contact@planebyte.com: https://app.planebyte.com/signup . Step5andCreemLive remain enabled onAPI`leadengine-api-00178-juv`/frontend`dpl_Bnw3PDBXntW1sAEyCbirdHbqK7NU`. [Exact current result](PLANEBYTE_TEST_CUSTOMER_RESET_20261117.md). Do not repeat this reset; older statuses below are historical.

> **Current checkpoint — 17 November 2026:** Creem-only Live checkout is enabled on API `leadengine-api-00178-juv` and frontend `dpl_Bnw3PDBXntW1sAEyCbirdHbqK7NU`. The owner-approved exact test-account reset deleted21rows; zero customer accounts/workspaces remain. Backup/exact restore and post-reset checks passed. Fresh controlled signup for contact@planebyte.com: https://app.planebyte.com/signup . Mandatory Step5 and72-hour card trial are deployed; the owner performs the real signup/payment test. [Exact current result](PLANEBYTE_TEST_CUSTOMER_RESET_20261117.md). Older account, trial, checkout-disabled and revision statements below are historical. Do not repeat the reset.

> **Current P0 — 17 November 2026: clean Neon migration completed.** See [clean database release](PLANEBYTE_CLEAN_NEON_MIGRATION_20261117.md). Production API `leadengine-api-00168-his` (100%) and both database-using workers run source `b2e27ac`, use the new pinned database secret and schema profile1004. Zero customer accounts/users/workspaces/sessions/trials were verified at04:57UTC; no historical customer data was copied. Old Neon schema51/201tables and checked customer/financial/security records remain unchanged. All old revision tags were removed. Five schedulers and API database polling are off; bounded request-driven mail/AI remain configured. Final backend1,197pass/one real-outreach skip; actual clean-schema Vertex website/five-ICP workers and actual Cloud Run write/read/rollback pass. **Fresh contact@planebyte.com signup is ready for the owner's production test**; OTP and the full new-database customer journey remain pending that test. Public registration and checkout stay closed. Older reset/schema51/revision161 statements below are historical. The operator root `.env` DATABASE_URL remains the archive: use DATABASE_URL_NEW explicitly for current product operations, never default mutation scripts on the archive.

## Current clean database P0 checklist

| Item | Status |
|---|---|
| [x] Distinct empty destination; no copied customer data | Independently verified before and after promotion |
| [x] Ordered migrations, exact structure and failed-batch rollback | Versions1001–1004;110 application tables plus metadata |
| [x] New structure backup and tested local restoration | Schema-only; no customer row export |
| [x] Authentication, trial, onboarding, dashboard, billing and tenant-isolation regression | Final1,197pass/one explicit real-outreach skip |
| [x] Actual provider acceptance on clean schema | Real website research and exactly five Vertex ICPs in disposable local workspace |
| [x] Actual deployed worker acceptance | Both diagnostic and rebound production worker write/read/rollback passed |
| [x] All production database consumers switched | API and two workers pinned to new secret; diagnostic has no DB |
| [x] Old archive and Lead Engine preserved | Old schema and checked protected/customer digests unchanged; source retained |
| [x] Reduce unnecessary compute | All five schedulers paused; API polling disabled; pool minimum0/idle30s |
| [x] Production health, native forms and admission denials | API/auth/legal200; personal password/Google403; protected access401 |
| [ ] Owner fresh production journey | Owner enters password/OTP and tests trial→research→five ICPs→assistant→dashboard |
| [ ] Public paid launch | Separate public acceptance and genuine PayU permissions/sandbox gates remain; checkout closed |

Historical feature inventory follows; use the current migration report for present database/release facts.

> **Latest P0 checkpoint supersedes the historical status below.** See [reset and authentication execution](PLANEBYTE_P0_RESET_EXECUTION_20261116.md). Reset complete:747rows deleted after exact201-table backup/restore/dry run; protected financial/security/system records preserved. Do not repeat it. Legal version planebyte-2026-11-16-v1 is published. Real work-email OTP delivery/verification, exact7-day trial, website research, reviewed profile/3ICPs, setup AI assistant and completion passed on production. The initial3-versus5 count and dashboard pool timeout were repaired in sourceb71e1c3, now API161100% with matching workers; frontendf4f1708 remains live. Final backend1,173passes/one explicit live-mail skip; onboarding browser2passes; actual isolated Vertex returned5distinct segments. Browser control was stopped before the final signed-in dashboard recheck; owner deferred password login/recovery. Fresh production exact-five acceptance remains unverified; do not reset the trial or raise caps. Public signup and checkout stay closed. Old Gmail admission, legal approval, flag-off, rollback149 and reset-authorization statements below are historical. Preserve Lead Engine source. No hosting-plan decision is pending; the owner handles it separately.

Updated16 November2026. Backend `dbfe6a6`, API151, all three workers, frontend `64e9f0b` / `dpl_8wWL8WssS7nfp9s2VcuS1t56DXE6`, production schema51. Transactional mail and setup diagnostics are live and genuinely verified. Native signup/trial and unverified checkout stay closed. Full paid launch is NOT READY.

See `PLANEBYTE_LAUNCH_VERIFICATION_20261116.md` for exact proof and remaining gates. Earlier versions are archived under `archive/20261116-before-ai-repair/`. `[x]` applies only to the specifically evidenced scope; fixtures are separate from genuine provider/production acceptance.

Status vocabulary: **Deployed and Verified**, **Implemented but Not Deployed**, **Partially Working**, **Broken**, **Missing**, **Externally Blocked**, **Not Verified**. Disabled code included in a deployed image is **Not Verified** live, not a launched feature. Priority P0 blocks public launch; P1 blocks the corresponding promised feature; P2 is follow-up improvement. Work type: DEV development, CFG configuration, EXT permission/credential, OWNER business approval, VERIFY actual acceptance.

## Release, data and production operations

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] Preserve owner improvements | Merged 15d40b8/cc5870c/a5df275; latest dashboard/settings/navigation/Graph/Discover retained | Other checkout has unrelated untracked marketing work | VERIFY; P0; compare Git status/history before every change; never reset another checkout |
| [x] Full backend regression | 1,153 pass, one explicit live-mail skip, eight warnings; PostgreSQL and real isolated Chromium included | Real external journeys remain separate | VERIFY; P0; backend-approved.xml/log in onboarding-repair-20261116 |
| [x] UI unit/types/lint/build | Final UI181 pass; types/focused lint/fresh Webpack build pass | Exhaustive lint/accessibility is not claimed | VERIFY; P0; frontend-*-final-ui.log |
| [x] Responsive local acceptance | Product10/onboarding2/accounts1; final UI account replay pass;12 actual production guest theme/mobile screenshots | Fresh authenticated customer callback/full private live UI replay pending | VERIFY; P1; production-public-browser.json,320/390/1440,theme persistence/control bounds |
| [x] Schema recovery | Fresh118,860,123-byte exact restore;46→51;five migrations;second0;original data preserved | Do not use restored customer DBs for fixtures | CFG/VERIFY; P0; recovery-result.json, current production51 |
| [x] Cleanup Stage A | Zero proposed/authorized deletions; all historic records protected | No disposable-row proof; no Stage B performed | OWNER; P0; no deletion without exact new scoped manifest and restore proof |
| [x] Exact Cloud Run release | API151100% customer traffic; three workers source dbfe6a6; exact images/secrets/safety flags verified | Native admission/checkout remain disabled | VERIFY; P0; backend-final-audit.json; explicit rollback tag149 |
| [x] Exact Vercel domain release | READY dpl_8wWL… source64e9f0b; authoritative app.planebyte.com mapping verified | Completed authenticated callback not recorded | VERIFY; P0; vercel-production.json and actual guest browser/Google handoff |
| [x] New-release worker acceptance | Actual Vertex setup guidance on final source; schema51 follow-up retains four durable events; original profile unchanged | Final-source report/global semantic acceptance waits for operator capacity | VERIFY; P0; final-setup-worker.json and production-setup-diagnostics.json |
| [x] Current production errors | Zero ERROR-or-higher entries in bounded API151 release review; signed/public health checks pass | No long-running uptime or scale claim | VERIFY; P0; backend-final-audit.json exact timestamp window |
| [ ] Commercial hosting eligibility | Existing team reverified Hobby; owner explicitly authorizes continued current development/deployment | Owner reviews eligible commercial hosting before paid public launch | OWNER/EXT; P1; no automatic upgrade or unrelated work pause |
| [ ] Performance targets | Previous summary observedp95≈4.50s; full≈4.84s; earlier≈20.89s median | Sub2s/3s and scale unproven; regional round trips | DEV/VERIFY; P1; controlled representative concurrency and browser timings, no production load flood |

## Public signup, authentication and email OTP

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [ ] Existing Google login | Actual final deployed Google authorization handoff uses canonical callback and S256 PKCE; existing users preserved | Fresh completed authorized callback/session still unverified | VERIFY; P0; production-public-browser.json; no fake callback or new OAuth config |
| [ ] Native signup | Work-email/MX, KDF, server challenge, tenant/trial concurrency tests pass; schema51/mail ready | Native/public flags off pending legal and actual fresh production journey | CFG/VERIFY; P0; approved terms/admission then controlled real signup |
| [x] Password security | Isolated real scrypt, concurrency bound, exact normalization, invalid input tests | Runtime load/complete mail acceptance separate | VERIFY; P0; retain wrong-OTP/password/limits/concurrent verification tests |
| [ ] OTP/resend | Normal isolated account with actual Resend delivery and OTP consumption; invalid-code/resend denial pass | Native production account flow remains closed; mailbox contents not independently retrieved | VERIFY; P0; real-owner-mail-1/result.json; do not claim production browser signup |
| [x] Resend runtime | Existing key/version1 and webhook secret securely bound; actual production worker delivered in one attempt | Hostinger/customer mailbox integration not certified | CFG/VERIFY; P0; production-mail-acceptance.json; no new API key or secret disclosure |
| [x] Resend webhook | Actual provider-signed delivered callback persisted; correct/tampered-signature probes pass; endpoint enabled | Bounce/complaint/race acceptance is isolated, no deliberately bounced customer mail sent | VERIFY; P0; actual notification DELIVERED and encrypted payload purged |
| [ ] Recovery/reset | Actual delivered recovery/password-change mail plus local real service one-use/reset/revocation/relogin pass | Native production accounts remain gated | VERIFY; P0; no production customer password changed |
| [ ] Google linking/add password | Explicit fresh session plus challenge; no implicit email merge | Live linking/OTP not verified | VERIFY; P0; original authenticated identity, OTP, reauth, revocation; foreign/expired denial |
| [ ] Logout/session expiry | Native8h opaque session, exchange120s, reset/logout revocation tested | Native sessions disabled live | VERIFY; P0; actual private cookie, no token exposed through auth/session, old session denied |
| [ ] Invites/team admission | Explicit intended recipient, role/capacity, no auto-join or implicit trial | Native live flow disabled | CFG/VERIFY; P0; two authorized isolated identities; revoked/wrong recipient denied; no unsolicited mail |
| [ ] Legal consent | Versioned exact consent/purchase snapshot implemented | Actual legal identity and published approved pages missing | OWNER/CFG; P0; verify KYC legal name/address then publish/version; never accept terms for owner silently |
| [ ] Public signup opening | Backend/mail/migration/security repairs complete in recorded scope; public page confirms closed | Legal identity/publication and complete fresh production customer acceptance missing | OWNER/CFG/VERIFY; P0; separate opening sequence in verification report |

## Trial, onboarding and AI functionality

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] Approved trial policy | Seven days,5 searches,3 AI ops,150k reserved tokens,1 manual monitor/member | Disabled native ledger live | CFG/VERIFY; P0; exact-policy same-day concurrency tests and no second-domain/person claim |
| [x] Paid-only trial exclusions | Schedules/reports/API/MCP gated in shared native access paths | Real new-customer production acceptance pending | VERIFY; P0; trial denial through direct APIs and workers, not only UI |
| [x] Setup resume/steps | Actual scoped cloud setup→review→five ICPs→save→assistant/follow-up→completion; local reload/manual paths pass | Fresh admitted-customer authenticated browser journey remains unverified | VERIFY; P0; cloud-setup-private.json; no product grant/search/monitor/outreach |
| [ ] Website crawl quality | Deployed bounded static/metadata/JSON-LD extraction and meaningful previews; actual SyntaxWars2pages yields useful company/offering | Optional JS-only path still production-off pending container sandbox acceptance | DEV/VERIFY; P1; real isolated Chromium fencing passes; never weaken SSRF/robots |
| [x] Grounded company profile | Paraphrases independently grounded; atomic facts/quotes exact; source assertions/AI interpretation/unknowns distinguished | Independent broad-site quality coverage is not certified | VERIFY; P0; unsupported claims/sparse preview regressions and genuine source acceptance |
| [x] Profile review/save | Canonical versioned company/offering store; shared Graph/settings | Real AI quality separate | VERIFY; P1; edit/reload/cross-workspace reject and approved snapshot only |
| [x] ICP generation reliability | New cloud generation returns five distinct profiles; typed validation/provider errors and retries preserve causes | Exact first historical ICP rejected criterion was not retained and is irrecoverable | VERIFY; P0; actual old provider-success/post-validation failure evidence; no invented diagnosis |
| [x] ICP count/quality | Consistent max5; five distinct cloud recommendations inspected with roles/needs/pains/assumptions/services | Audiences remain hypotheses; no verified buyer/customer claim | VERIFY; P1; service canonicalization, duplicate-criteria rejection and reviewed save |
| [x] ICP refine/accept/defaults | Explicit reviewed patch/approval, idempotency/profileversion, active/primary/context defaults tested | Real generated recommendation quality open | VERIFY; P1; reviewed accept creates once, graph/discover reflect same saved data, no automatic run |
| [x] Attempt telemetry | Schema51 and live safe event history; four actual production events including Vertex/model/duration | Historical missing attempts are not fabricated/backfilled | VERIFY; P0; production-setup-diagnostics.json |
| [x] Setup AI assistant | Compact saved/draft/private follow-up context; real cloud and final production guidance pass | Not a completed new-customer Google/native browser journey | VERIFY; P0; saved profile unchanged; interpretations/hypotheses labelled |
| [x] Global count assistant | Final source real scoped count/today/greeting/replay pass with zero provider delta | Semantic answers use a different budgeted path | VERIFY; P1; final-counts.log and staged-functional-state.json |
| [ ] Global semantic assistant | Canonical company/offering context repaired; no invented documentation fallback; isolated grounding/history tests pass | Fresh final production semantic acceptance deferred by daily operator capacity | VERIFY; P1;95,884/100,000 reserved; do not raise/reset cap to force success |
| [ ] Real final customer journey | Genuine owner cloud onboarding and production mail/diagnostics pass; real public Google handoff passes | Native signup/admission/legal and completed fresh browser callback still closed/unverified | VERIFY; P0; full normal fresh-customer journey after those gates |

## Product pages, settings and workflows

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] Dashboard layout | Preserved compact summaries/alignment/quick entry; local route checks | Fresh authenticated visual checks narrower | VERIFY; P1; real saved counts/evidence, no placeholder successful activity |
| [x] Sidebar/navigation | Simplified Radar navigation, collapsible/mobile, account menu, hidden Lead Engine | Exhaustive keyboard/screen-reader audit pending | VERIFY; P1; direct links/back/reload and320px menu in both themes |
| [x] Theme/branding | Owner pixel mark/warm auth/cubes/dark contrast merged; responsive browser passes | Complete accessibility/contrast certification not claimed | VERIFY; P1; theme persistence/reduced-motion/focus/auth/settings/Graph |
| [x] Unified Settings routes | Existing account/company/team/research/integrations/API/billing consolidated | New native controls disabled; not every live save replayed | VERIFY; P1; each enabled form save/reload/validation and viewer/foreign denial |
| [x] Company/services/markets/preferences | Canonical persisted editable context and defaults | AI interpretation quality separate | VERIFY; P1; shared state across settings/Graph/Discover; no duplicate profile model |
| [x] Graph | Saved company/services/ICP, categories/list/search/zoom/navigation | Expanded semantic ontology partial | DEV/VERIFY; P2; real data only, mobile nodes/list controls and versioned editing |
| [x] Discover configuration | Manual/natural-language request, sources/keywords/exclusions/ICP/defaults | Provider availability differs; no universal web search | VERIFY; P1; explicit preview→one bounded job→results→history, cancellation/replay |
| [x] Signals/review | List/detail/filter/sort/source/date/excerpt/save/dismiss/uncertainty | Independent semantic quality open | VERIFY; P1; exact citation attribution/tombstones/retention and saved states |
| [x] Opportunities | Grouped needs/status/evidence links and reviewed actions | Quality not independent buyer validation | VERIFY; P1; useful groups and negative evidence; no outreach eligibility inference |
| [x] Monitors | Manual create/edit/pause/schedule/timezone, job linkage | Public trial enforcement not live | VERIFY; P1; pause/revoke blocks queued work; frequencies and partial-source failures |
| [x] Alerts/source health | Source issues/monitor activity/acknowledgement/settings | External alert delivery unverified | VERIFY; P1; provoke safe disposable source failure and reconcile alert/read state |
| [x] Research library/reports | Existing cited save/export/replay preserved; unique-source citation contract, truthful cache and measured output budget fixed | Final-source production report acceptance deferred by operator cap; genuine isolated Vertex contract4themes/8findings/20citations passed | VERIFY; P1; preserve ordinary quota and distinguish lexical fallback from AI success |
| [x] API/MCP keys | Fresh schema51 production SDK2.3.0 HTTPS,13 read tools, scoped read/unknown deny, hidden Lead tools absent; test key revoked and401 verified | Named GUI-client acceptance pending | VERIFY; P1; external-mcp-acceptance.json; no discovery/AI/outreach/payment tools invoked |
| [ ] Customer Gmail/Sheets/webhooks | Partially Working/Not Verified live | Approved destination/OAuth scopes/receiver acceptance needed | EXT/VERIFY; P1; owned connect→callback→refresh→revoke; exact reviewed range/receiver |
| [ ] CRM/social integrations | Missing operational integrations despite catalog references | No verified adapter/auth/sync | DEV/EXT; P1 if advertised; otherwise keep unavailable |
| [x] Preserved Lead Engine | Source/APIs/tables/data remain, customer access disabled | Future separate launch not complete | VERIFY; P0; direct APIs/workers404/deny, retain contacts/history/suppressions; never delete |
| [ ] Help/legal/admin usability | Actual guest auth links/themes reviewed; mobile theme control and unverified corporate suffix fixed | Legal identity/publication and exhaustive private enabled-form acceptance remain | OWNER/VERIFY; P1; retain latest UI and truthful availability labels |

## Sources and licensing

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] HN official API | Earlier genuine production5-result worker; local all feed/comment bounds | Historical whole-index search unsupported | VERIFY; P1; bounded recent feed worker, attribution, monitor paused afterward |
| [ ] Stack Exchange | Real public evaluation, quota/backoff/attribution code | Commercial terms/CC BY-SA review; productionflag off | EXT/OWNER; P1; document permission, approved sites, real bounded source check |
| [ ] RSS | W3C genuine evaluation/cache/ETag and safe XML | Per-publisher permissions/configuration | EXT/CFG; P1; allowlisted exact permitted feed, real fetch/dedupe/retention |
| [ ] Atom | Parser implemented/tested | No separate successful live Atom endpoint recorded | VERIFY; P1; permitted endpoint actually returns Atom; preserve provenance |
| [ ] Discourse | Public Meta latest.rss actual evaluation | Customer instance/endpoint approval; no private forum support | EXT/CFG; P1; robots/content-use/retention review, bounded public feed only |
| [ ] Reddit/GitHub/Slack | Missing/Not Verified customer operations | Credentials/terms/implementation absent or unaccepted | DEV/EXT; P1 if promised; keep unavailable |
| [ ] Incremental/cross-family coverage | Partially Working; replay/checkpoints/dedupe foundations | Complete cursor/historical/cross-family policy not certified | DEV/VERIFY; P2; retain native IDs, withdrawal and no repeated provider fetch after completed checkpoint |
| [ ] Independent AI quality | Not Verified | Independent reviewers/corpus/thresholds not complete | OWNER/VERIFY; P1; approved representative permitted corpus, two reviewers/adjudication, measured errors |

## Pricing, PayU checkout and monthly/yearly access

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] USD list prices | $59/$149/$379/custom retained | List currency does not prove charging support | VERIFY; P0; quote/catalog/UI exact and server immutable totals |
| [x] No GSTIN requirement | GST not collected, no fabricated registration/invoice | Tax treatment must remain truthful | OWNER/VERIFY; P0; no GST field/charge without verified registration/treatment |
| [ ] Merchant USD/international/settlement | Live authenticated MID13851032 observed; owner personally verifying exact permissions | Account-specific USD/international/settlement proof absent | OWNER/EXT; P0; keep unverified checkout closed; no live charge |
| [ ] KYC legal entity/address | Externally Blocked | Payment key/salt cannot retrieve partner KYC; profile panels insufficient | OWNER/EXT; P0; verified business/KYC record; no invented Studios/address |
| [ ] Test Mode credentials | One-time integration and isolated/PostgreSQL security/fulfillment tests pass | Separate valid merchant Test Mode credentials/capabilities not available | EXT/VERIFY; P0; never use live key/salt against sandbox blindly |
| [x] Hosted one-time creation | Implemented immutable consent/quote/UDF, allowed HTTPS host, durable CREATING/REVIEW | Actual merchant acceptance not verified; disabled | VERIFY; P0; test provider accepted request and uncertain outcome no duplicate creation |
| [x] Server verification/webhook | Reverse hash+independent v3 exact captured original currency/amount/UDF; dedupe tests | Real signed callback/verification not accepted live | CFG/VERIFY; P0; tamper/duplicate/late callback/race tests + genuine test payment; redirects never grant |
| [x] Monthly access policy | Native30-day periods, same-plan renew/plan changes queued, no overlap/proration | Disabled live | VERIFY; P0; confirmed payment exactly once, UTC boundaries and expiry all direct paths/workers |
| [ ] Yearly paid plans | Calendar-year model implemented | Price/discount/annual allowance cadence unapproved | OWNER/DEV/VERIFY; P1; retain disabled until decisions and leap-date/entitlement tests |
| [x] History/receipts | Immutable provider/mode rows, payment receipt JSON | Not a GST invoice; genuine purchased history acceptance pending | VERIFY; P1; owned/foreign access, paid/refunded reference and preserved legacy history |
| [x] Refund/cancellation handling | Owner-reviewed request, no auto-renew, read-only external refund reconciliation | Actual refund workflow/settlement acceptance unverified | OWNER/VERIFY; P0; seven-day initial request policy, full vs partial, no unauthorized financial action |
| [ ] Public checkout activation | Externally Blocked plus live verification pending | USD/legal/TestMode/verification/mail gates | CFG/OWNER/EXT; P0; exact checklist in next-agent guide; no real charge without separate amount authorization |

## Security, privacy and launch decision

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] Workspace isolation | Fresh membership, owned resources/jobs/cache/attachments/keys; denial tests | New live-account acceptance remains | VERIFY; P0; absent context and two workspaces, revoked worker/provider access; never weaken fixtures |
| [x] Secret boundaries | Existing HMAC/OAuth retained; API keys/server cookies encrypted/redacted | Verify each new runtime binding before activation | CFG/VERIFY; P0; inspect names/references only; no secret frontend bundle/logs/commit |
| [x] Async/retry/cost fences | Durable jobs/leases, quotas, cancellation/idempotency/unknown outcome accounting | Exact AI attempt diagnosis still incomplete | DEV/VERIFY; P0; crash/revocation/late result tests, no unbounded retries/spend |
| [ ] Legal publication | Complete four drafts; policy decisions recorded | Legal identity/address/applicable obligations unverified | OWNER; P0; publish final approved Terms/Privacy/Refund/Cancellation on intended domains/version |
| [x] Privacy intake/export | Native account export/request/reviewed closure deadlines tested | Disabled live; complete workspace/backup deletion process pending | DEV/VERIFY; P0; identity/authority review,30/90-day deadlines, justified holds/exceptions, no blanket purge |
| [x] Restore/rollback drill for next migration | Exact fresh restore and51 migration verified; live schema51 rollback-tag health/scoped reads pass | Flag-off149 is unsuitable after native workspace enrollment without retained enforcement | CFG/VERIFY; P0; rollback-schema51.json; no old65 cold start or stale production restore |
| [ ] Full public paid launch | NOT READY; verified non-payment repairs safely deployed | Legal/native fresh customer/merchant Test Mode/checkout and remaining acceptance gates | OWNER/EXT/CFG/VERIFY; P0; ten-part verification report separates facts from unverified scope |

## Complete source inventory and route appendix

The historical `FINAL_PRODUCT_FEATURE_INVENTORY.json` contains 1,839 requirement/technical-surface records, including small controls, API routes and internal gated features. It is a discovery index, not 1,839 certified distinct features. Preserve it; use each source location for verification. Historical statuses and recurring-payment assumptions there are superseded by the fixed-term policy and evidence above. No unreviewed item becomes verified just because the source is deployed.

The following generated route list covers every current `dashboard/app/**/page.tsx`. Each entry requires actual authenticated navigation, save/reload for forms, same-workspace data, foreign/viewer denial, mobile320/390px and light/dark checks before full live certification. Lead Engine routes must remain inaccessible when the module is disabled. Auth/terms routes are public only as intended; public signup remains closed. Direct routes and redirects are included so small legacy/settings pages are not lost.

| Current page route | Status / verification requirement |
|---|---|
| `/accept-invitation` | Partially Working / Not Verified; approved Google only; new native flow closed; follow account checklist |
| `/account/appearance` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/account` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/account/profile` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/account/security` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/acquisition/jobs/[id]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/acquisition/sheets/callback` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/assistant` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/automation` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/billing/cancel` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/billing/checkout` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/billing` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/billing/sandbox` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/billing/success` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/campaigns/[campaignId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/campaigns` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/contacts/[contactId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/contacts` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/discovery/[runId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/enrichment/[jobId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/enrichment` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/experiments/nov-2026` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/find-leads/ai` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/find-leads/import` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/find-leads` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/forgot-password` | Partially Working / Not Verified; approved Google only; new native flow closed; follow account checklist |
| `/help` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/intent-radar/[[...segments]]` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/lead-engine` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/leads/[leadId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/leads` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/leads/review` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/lists/[listId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/lists` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/login` | Partially Working / Not Verified; approved Google only; new native flow closed; follow account checklist |
| `/master-leads` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/onboarding` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/outreach/messages/[messageId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/outreach/new` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/outreach` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/outreach/results` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/privacy` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/recommendations` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/reports` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/reset-password` | Partially Working / Not Verified; approved Google only; new native flow closed; follow account checklist |
| `/runs/[runId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/scans/[scanId]` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/scans/new` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/scans` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/schedules` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/settings/access` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/acquisition` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/billing` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/company` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/developer` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/domains` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/email` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/foundation` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/icp` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/integrations/gmail-callback` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/integrations` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/limits` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/markets` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/members` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/preferences` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/profile` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/scanning` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/setup` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/system` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/team` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/templates` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/website` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/settings/workspaces` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/signup` | Partially Working / Not Verified; approved Google only; new native flow closed; follow account checklist |
| `/system` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/tasks` | Not Verified live; preserved disabled Lead Engine surface; verify direct-route/module denial |
| `/terms` | Not Verified at individual live-action level; source preserved; follow page acceptance above |
| `/verify-email` | Partially Working / Not Verified; approved Google only; new native flow closed; follow account checklist |
