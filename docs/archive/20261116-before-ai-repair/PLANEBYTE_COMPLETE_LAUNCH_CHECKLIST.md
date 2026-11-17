# PlaneByte complete feature and launch checklist

2026-11-16 wrap-up. Application release source `65e9cd3ae998106e268a66f172cb098cd2146410`; final live proof is in `PLANEBYTE_MASTER_HANDOVER.md`. This checklist supersedes historical completion labels. `[x]` means the specifically described evidence exists, not that an entire feature is publicly launched. `[ ]` remains unfinished. No percentage is a readiness claim.

Final deployment update04:48UTC: safe source65e9 is live on API145 and Vercel `dpl_8njxByesgVJWBbuhnpvssyuTxMcU`, with all three worker images updated. Exact traffic/alias/digest and production read/public-auth checks passed. Native accounts/mail/trial/PayU code remains disabled; live schema46 unchanged. New signed-in browser acceptance was stopped and remains pending. No public paid-launch completion is implied.

Status vocabulary: **Deployed and Verified**, **Implemented but Not Deployed**, **Partially Working**, **Broken**, **Missing**, **Externally Blocked**, **Not Verified**. Disabled code included in a deployed image is **Not Verified** live, not a launched feature. Priority P0 blocks public launch; P1 blocks the corresponding promised feature; P2 is follow-up improvement. Work type: DEV development, CFG configuration, EXT permission/credential, OWNER business approval, VERIFY actual acceptance.

## Release, data and production operations

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] Preserve owner improvements | Merged 15d40b8/cc5870c/a5df275; latest dashboard/settings/navigation/Graph/Discover retained | Other checkout has unrelated untracked marketing work | VERIFY; P0; compare Git status/history before every change; never reset another checkout |
| [x] Full backend regression | 1,144 pass, one explicit live-mail skip; 83 PostgreSQL cases included | Real providers are distinct acceptance | VERIFY; P0; frozen hashes and XML in `public-launch/final` must match source |
| [x] UI unit/types/lint/build | 181 pass; types/targeted lint/Webpack build pass | Full lint is not asserted by targeted lint | VERIFY; P0; read exact logs, no suppressed current failures |
| [x] Responsive local acceptance | Product10/accounts1/onboarding2 pass, 320–1920px and selected light/dark | External transports synthetic; exhaustive accessibility not certified | VERIFY; P1; replay genuine deployed key journeys on desktop/mobile |
| [x] Schema recovery | Exact 118.6MB restore; 46→50; four migrations; second0; no row loss | Production intentionally remains46 | CFG/VERIFY; P0; fresh backup/restore and compatible rollback before later migrations |
| [x] Cleanup Stage A | Zero proposed/authorized deletions; all historic records protected | No disposable-row proof; no Stage B performed | OWNER; P0; no deletion without exact new scoped manifest and restore proof |
| [x] Exact Cloud Run release | Deployed and Verified: build0e5fSUCCESS, API145 at100%, all three jobs source65e9, exact image digests and15 production reads/denials pass | New disabled features are not live accepted | VERIFY; P0; retained exact final record, no production settings/data migration |
| [x] Exact Vercel domain release | Deployed and Verified: READY dpl_8njx…, source65e9, actual app.planebyte.com alias, public auth/assets/redirects pass | Fresh signed-in browser acceptance stopped/pending | VERIFY; P0; preserve prior deployment rollback, test authenticated visual journey next |
| [x] New-release worker acceptance | Deployed and Verified bounded report: normal worker→real Vertex→10citations→save/3exports/replay→production readback | This does not verify website/ICP/setup assistant | VERIFY; P0; evidence job3f715…; no outreach/payment/profile mutation |
| [x] Current production errors | Zero ERROR-or-higher entries exact API145,04:30–04:48UTC bounded review; health200 | Long-running uptime/all-service error coverage not claimed | VERIFY; P0; continue ordinary monitoring; investigate actual new critical errors |
| [ ] Commercial hosting eligibility | Existing Vercel deployment operational | Prior Hobby-plan finding not revalidated | EXT/OWNER; P1; verify eligible commercial team contract; deployment success is not plan approval |
| [ ] Performance targets | Previous summary observedp95≈4.50s; full≈4.84s; earlier≈20.89s median | Sub2s/3s and scale unproven; regional round trips | DEV/VERIFY; P1; controlled representative concurrency and browser timings, no production load flood |

## Public signup, authentication and email OTP

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [ ] Existing Google login | Partially Working; genuine SyntaxWars session observed, standard OAuth preserved | Fresh final-release complete redirect/callback not recorded | VERIFY; P0; authorized browser Google login → canonical app → scoped session; preserve existing Gmail users |
| [ ] Native signup | Not Verified live; work-email/MX, password confirmation and server challenge implemented | Accounts/public flags off and schema46 | CFG/VERIFY; P0; schema50, mail/legal/security gates then authorized fresh test signup |
| [x] Password security | Isolated real scrypt, concurrency bound, exact normalization, invalid input tests | Runtime load/complete mail acceptance separate | VERIFY; P0; retain wrong-OTP/password/limits/concurrent verification tests |
| [ ] OTP/resend | Not Verified live; six digits,10min,5 attempts,HMAC storage,60s resend, encrypted outbox | No genuine inbox-delivered OTP acceptance yet | CFG/VERIFY; P0; normal service → Resend accepted → authorized owner inbox → consume code → one account/trial |
| [ ] Resend runtime | Valid updated key/domain; secret `leadengine-resend-key:1` installed | Confirm secret-specific API/worker IAM and bindings/from; mail gate remains false | CFG; P0; metadata and controlled ordinary send, never print key or create unnecessary replacement |
| [ ] Resend webhook | Implemented Svix HMAC, timestamp/size/dedupe and bounce/complaint suppression tests | Actual webhook secret/endpoint acceptance not recorded | EXT/CFG/VERIFY; P0; install server secret, signed event/replay/tampering/suppression acceptance |
| [ ] Recovery/reset | Implemented opaque one-use token/session revocation and real local browser test | Genuine recovery delivery/reset/relogin not verified | VERIFY; P0; owner-controlled disposable identity only; never reset real customer password |
| [ ] Google linking/add password | Explicit fresh session plus challenge; no implicit email merge | Live linking/OTP not verified | VERIFY; P0; original authenticated identity, OTP, reauth, revocation; foreign/expired denial |
| [ ] Logout/session expiry | Native8h opaque session, exchange120s, reset/logout revocation tested | Native sessions disabled live | VERIFY; P0; actual private cookie, no token exposed through auth/session, old session denied |
| [ ] Invites/team admission | Explicit intended recipient, role/capacity, no auto-join or implicit trial | Native live flow disabled | CFG/VERIFY; P0; two authorized isolated identities; revoked/wrong recipient denied; no unsolicited mail |
| [ ] Legal consent | Versioned exact consent/purchase snapshot implemented | Actual legal identity and published approved pages missing | OWNER/CFG; P0; verify KYC legal name/address then publish/version; never accept terms for owner silently |
| [ ] Public signup opening | Externally Blocked plus software acceptance incomplete | Email/legal/real AI journey/security gates unmet | OWNER/CFG/VERIFY; P0; complete ordered activation in next-agent guide; no boolean-only launch |

## Trial, onboarding and AI functionality

| Check | Status / what works | Missing / why | Type; priority; exact verification / next action |
|---|---|---|---|
| [x] Approved trial policy | Seven days,5 searches,3 AI ops,150k reserved tokens,1 manual monitor/member | Disabled native ledger live | CFG/VERIFY; P0; exact-policy same-day concurrency tests and no second-domain/person claim |
| [x] Paid-only trial exclusions | Schedules/reports/API/MCP gated in shared native access paths | Real new-customer production acceptance pending | VERIFY; P0; trial denial through direct APIs and workers, not only UI |
| [ ] Setup resume/steps | Partially Working; persisted reviewed/manual setup and two local browser flows | Complete real provider/user journey not certified | VERIFY; P0; reload every stage, preserve edits/version, cancel/retry and explicit completion |
| [ ] Website crawl quality | Broken requested experience; bounded static source collection works | Modern JS sites, meaningful completeness and link selection inadequate | DEV/VERIFY; P0; representative public sites including SyntaxWars, actual extracted source/page counts and duration |
| [ ] Grounded company profile | Broken quality contract; source quotes validated | Summary allowed in prompt but rejected unless verbatim; sparse READY possible | DEV; P0; fact/inference/unknown contracts + grounded paraphrase and claim rejection tests; no guessed clients/revenue |
| [x] Profile review/save | Canonical versioned company/offering store; shared Graph/settings | Real AI quality separate | VERIFY; P1; edit/reload/cross-workspace reject and approved snapshot only |
| [ ] ICP generation reliability | Partially Working; production job4eb… READY on attempt2 | Original failure cause not retained in current row | DEV/VERIFY; P0; exact scoped provider/worker log trace, typed safe stage errors; no blind unknown-outcome retries |
| [ ] ICP count/quality | Existing1–3 structured candidates, distinct names/assumptions/services checks | Requested3–5 not implemented; distinct useful targeting unreviewed | DEV/VERIFY; P1; consistent limits through builder/choice/accept/UI, source-grounded reviewer acceptance |
| [x] ICP refine/accept/defaults | Explicit reviewed patch/approval, idempotency/profileversion, active/primary/context defaults tested | Real generated recommendation quality open | VERIFY; P1; reviewed accept creates once, graph/discover reflect same saved data, no automatic run |
| [ ] Attempt telemetry | Partially Working; job stage/status/error and shared provider usage exist | Prior error overwritten; durable attempt history unfinished | DEV; P0; safe append-only attempt/stage/duration/provider/error events, no prompt/secret logs |
| [ ] Setup AI assistant | Partially Working; saved-fact route and structured guidance | Owner-reported poor responses; compact context/multi-turn improvements unfinished | DEV/VERIFY; P0; current reviewed/draft context, helpful follow-up, real provider answer; no fake documentation fallback |
| [x] Global count assistant | Implemented deterministic saved-data counts/follow-up with no provider calls | Fresh deployed check logged separately | VERIFY; P1; count+today+replay match scoped DB; no AI budget consumed |
| [ ] Global semantic assistant | Partially Working; existing async conversation/evidence architecture | Full production conversational acceptance remains open | VERIFY/DEV; P0; real saved context/citations, state/refusal/retry, mobile drawer, no automatic actions |
| [ ] Real final customer journey | Not Verified | Synthetic transport success cannot establish real signup/AI/payment | VERIFY; P0; signup→delivery/Google→research→company review→ICPs→approval→persisted context→assistant→dashboard |

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
| [x] Research library/reports | Cited AI report, save/replay/export MD/CSV/JSON | Broad quality coverage/current release real acceptance separate | VERIFY; P1; genuine normal worker/provider, current citations and export integrity |
| [x] API/MCP keys | Scope,hash/expiry/show-once,rotation/revocation,usage and configured endpoint | Named GUI-client acceptance pending | VERIFY; P1; actual HTTPS SDK and foreign/expired/revoked denial; revoke canary key |
| [ ] Customer Gmail/Sheets/webhooks | Partially Working/Not Verified live | Approved destination/OAuth scopes/receiver acceptance needed | EXT/VERIFY; P1; owned connect→callback→refresh→revoke; exact reviewed range/receiver |
| [ ] CRM/social integrations | Missing operational integrations despite catalog references | No verified adapter/auth/sync | DEV/EXT; P1 if advertised; otherwise keep unavailable |
| [x] Preserved Lead Engine | Source/APIs/tables/data remain, customer access disabled | Future separate launch not complete | VERIFY; P0; direct APIs/workers404/deny, retain contacts/history/suppressions; never delete |
| [ ] Help/legal/admin usability | Existing help/internal guides and legal draft pages | Production legal publication/complete link audit pending | OWNER/VERIFY; P1; every visible link/role controls, current truthful availability labels |

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
| [ ] Merchant USD/international/settlement | Externally Blocked; live dashboard shows INR/active methods | Account-specific USD and settlement evidence absent | EXT; P0; merchant dashboard/support confirmation bound to actual account/key; live mode insufficient |
| [ ] KYC legal entity/address | Externally Blocked | Payment key/salt cannot retrieve partner KYC; profile panels insufficient | OWNER/EXT; P0; verified business/KYC record; no invented Studios/address |
| [ ] Test Mode credentials | Externally Blocked | Distinct approved test credential/capability not verified | EXT; P0; securely retrieve existing test credentials; never use live key against test blindly |
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
| [ ] Restore/rollback drill for next migration | Schema50 rehearsal passes | Fresh production snapshot + compatible live rollback required | CFG/VERIFY; P0; retain new flag-off image; no old7eb cold-start after50 |
| [ ] Full public paid launch | NOT READY | Real AI/mail/legal/merchant/payment and customer journey gates remain | DEV/CFG/EXT/OWNER/VERIFY; P0; do not mark complete from image deployment or passing fixtures |

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
