# Nov 2–6 experiment — production activation

The experiment was activated on November2,2026 after every recorded acceptance gate passed. The start date was not shifted. Production API revision is `leadengine-api-00105-cil`; frontend `dpl_DXHkvaSF1DfeVrn1zQis5iTDx8q5` is Ready.

All50 once-only source schedules were created for25 specified market/day/vertical segments. Day1 acquisition has begun; actual source executions and campaign IDs are recorded in `experiment-production-start.json`. Targets remain500 contactable businesses/day,2500 total, with planned250 Overture/250 Firecrawl per day. Targets are not achieved counts. Resource budgets, source shortfalls and actual send dates remain visible; there is no unbounded discovery or silent date shift.

Acceptance observed:
- Final exact Linux suite464 passed,15 skipped. Frontend43 tests passed; browser25 passed; strict TypeScript and production builds passed. Real PostgreSQL additive preservation and copy-cache/circuit/idempotency integration passed.
- Vertex local ADC1/5/10/40 passed, including40 matching valid outputs in one request. Production Cloud Run attached-service-identity inference passed. Mocked provider fallback, deterministic fallback, splitting and partial-item failure passed. Gemini Developer API remains secondary but currently reports HTTP402/quota exhaustion; healthy Vertex is primary.
- Five actual owner-only strategy messages were accepted by Gmail SMTP and verified in Sent with their exact3-page attachments, HTML/text, branding, tracking and opt-out behavior. All15 attachment pages were visually reviewed. Genuine owner reply matched and classified positive with campaign/source/template/experiment attribution. No real prospect was emailed during QA.
- Existing8-page Full Audit report preserved and visually verified. Catalog remainsOFF and does not block sending.
- Controlled Overture target5 completed with6 valid analyzed/public-email leads after retry; the extra existing observation was preserved and reported. No-email deep analysis0. Controlled Firecrawl5 contactable/analyzed passed. Automatic scheduled Firecrawl and Overture routing checks passed; three named temporary QA schedules were soft-deleted with history retained.
- Final signed production health, acquisition settings, foundation, experiment dashboard and copy status endpoints returned HTTP200. The acquisition-settings parser/save compatibility issue was repaired while retaining provider health/cooldown metadata. Provider usage totals now use actual request-ledger rows.
- Production acquisition, outreach and inbox schedulers are enabled. Gmail/inbox/reply tracking and suppression remain intact. No new migration, data reset, service-account key or identity change occurred during Vertex rollout.

The provider preflight counted5 controlled sends in the rolling24-hour period, leaving495 counted sends available at activation under the500/day ceiling. This is conservative accounting, not a provider guarantee. All actual sends must still pass suppression, rate/spacing, provider health and recipient-local weekday09:30–16:30 checks. Provider errors and abnormal bounce rate pause sending; inbox sync continues.

First10 existing pending copies validated (9 new Vertex results,1 cache hit). Only1 additional ready analyzed lead existed at that checkpoint, so a real next40 batch was not fabricated. Newly acquired experiment leads pass progressive10→40→normal batching through the existing worker; completed copies are reused. See `vertex-pending-copy-acceptance.json` and the live experiment dashboard for actual progression.

Rollback remains the verified81-table MVCC snapshot in private PostgreSQL schema `experiment_rollback_20261102t152525z`. No operational data was cleared. Incomplete earlier download archives must not be used for recovery.

The experiment is running, not complete. Acquisition, sending, replies and conversions are reported from observed ledger events over the Nov2–6 window.

## Owner-requested fresh start — November2,23:07IST

The owner subsequently requested clearing operational data and restarting today's500-qualified-lead+email run, using `https://planebyte.com/projects` as the portfolio/catalog link. Old dispatch was paused and old worker executions cancelled. A new88-table private PostgreSQL rollback snapshot was verified row-for-row at `owner_fresh500_20261102t173647z` before clearing. Schema14, approved configuration, Gmail, OAuth, infrastructure, suppression, provider limits and market/experiment configuration survived.

Live Master Leads, qualified leads, queue, email threads and email messages were all verified0 immediately after cleanup. Private artifact objects remain unchanged for rollback; their operational references were cleared. Fresh source allocations and schedules were then recreated from the approved market plan. The catalog is now configured inCATALOG_LINKmode, notOFF. All five template variants with the portfolio link passed their existing70–140word quality checks.

The fresh run was reactivatedLIVE for today's500 target. Sent accounting was refreshed after deleting app history:5 account-wide controlled emails remain counted, leaving495 counted sends available at restart. The reset does not reset provider quota. Live pipeline/sending counts begin anew; prior acceptance and performance observations above are historical. Fresh runtime evidence is in `owner-fresh-500-reset.json`, `owner-fresh-500-preflight.json`, `owner-fresh-500-activation.json` and `owner-fresh-500-start.json`.

## Owner stopped all acquisition — November3

The owner explicitly stopped all running and future scans because of resource/credit use, and authorized outreach only to already-found qualified leads. This supersedes the500/day acquisition plan. AUTO_SCAN_ENABLED isfalse in root.env, production API and core worker; the acquisition Cloud Scheduler ispaused; all50 scan schedules aredisabled. Existing queued/running acquisition and pipeline runs werecancelled with completed records preserved. Outreach and inbox schedulers remainenabled.

At the stop checkpoint,81 qualified business records represented80 unique prospects;28 outbound messages werealreadySENT. Qualified data and outreach history werepreserved, with no reset or deletion. Existing unsent messages continue through report/content/suppression/rate/local-time guards. Six unique qualified prospects lack sufficient verified findings for an approved experiment strategy and remainNeedsReview; no new discovery or fabricated findings are used to fill that gap.

The prior global SEND_REQUIRES_REVIEW pause was reviewed. There were noSENDING/UNCERTAIN SMTP reservations; Gmail account health remainedREADY and confirmed bounce rate did not require a pause. Twelve item statuses were reconciled to their existingSENT messages without resending. Existing ready outreach resumed while the individual review item remainedheld. That item subsequently passed preview, audience, content-hash and exact3-page productionR2PDF checks; with no priorSMTP reservation it was returned once to its existing queue/idempotency key. Portfolio https://planebyte.com/projects ispreserved.

This experiment no longer acquires new leads. Final stop/queue evidence: owner-stop-scans-final-20261103.json.
