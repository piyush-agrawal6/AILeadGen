# LeadEngine automation — final controlled acceptance report

Status: controlled acceptance passed; production activation remains an explicit owner action. Acquisition, automatic outreach and sending remain disabled. No schema migration was rerun during this completion pass; production remains on schema 9. No database reset/truncation, service-account key creation, credential rewrite or frontend secret exposure occurred.

## Readiness

READY means the controlled acceptance described here passed. It does not claim a 100-lead/100-message production volume benchmark; that run was deliberately not performed.

| Component | Status | Evidence |
|---|---|---|
| Gmail | READY | Live SMTP/IMAP health, controlled delivery and SPECIAL-USE All/Sent selection |
| Master Leads | READY | Permanent identities, 19 new qualified production records, complete views and bulk actions |
| Daily acquisition | READY | Existing pipeline small run completed; state-machine target/rotation/shortfall fixtures passed |
| Market rotation | READY | 304 DB combinations, untouched-market priority/cooldown, editable paginated controls |
| Email queue | READY | One real controlled queue send, duplicate tick blocked, 10/hour and 100/day fixture enforcement |
| Tracking | READY | Same production message recorded sent/open/click/verified reply/unsubscribe and timeline events |
| Reply sync | READY | Genuine authenticated reply matched; production five-minute worker executions succeeded |
| Bounce handling | READY | Owner-authorized simulated hard/soft DSNs, suppression, deduplication and manual routing |
| Scheduler | READY | Existing private worker/IAM, guarded invocations and regular inbox execution verified |
| Recovery/idempotency | READY | Concurrent ticks, independent PostgreSQL connections, restart states and provider/bounce pauses tested |
| UI | READY | Strict TypeScript, frontend tests, browser regression and live signed endpoint checks passed |

## Implemented and retained

The existing prospects/identities/observations remain the single permanent source. Reports, sales workflow, outreach, tracking, reply verification, DNC, follow-ups, notes, lists and chronological activity history remain intact. Existing SSRF/private-IP protections, signed internal requests, cookies, CSP/HSTS, bounded pagination, parameterized SQL and private report storage were retained.

Master Leads now includes New Today, every requested contact/sales view with server counts, search and country/city/vertical/scale/fit/opportunity/contact/sales/email/social/date/assignment/list filters, stable pagination, and selection-based sales-status, assignment, list, manual follow-up, DNC and CSV actions. Exports escape spreadsheet formula prefixes. Existing lead details retain reports, findings, messages, notes, follow-ups and scan history. Identity conflicts are visible for review with links to scan history and existing profiles.

Automation includes paginated searchable market editing, priority/cooldown/enabled controls, daily email history and editable targets/timezone/follow-up settings. Settings links to automation management. Target values use the existing shared-settings JSON record, preserve unrelated settings and cannot bypass environment flags or hourly/day caps. Overview displays stored daily counts.

Company-name-plus-domain/public-email aliases extend the existing global evidence. Source IDs, domain/location, phone/name and name/address evidence remain available. Legacy aliases are attached on rediscovery only when a unique permanent profile is supported. Shared-host tenants remain distinct. Existing conflicting profiles are never automatically merged: the new candidate is held with CANONICAL_IDENTITY_REVIEW_REQUIRED, recorded in scan history and excluded from automatic qualification/outreach while remaining candidates continue. No destructive historical identity backfill was performed.

Gmail All/Sent discovery uses IMAP LIST SPECIAL-USE flags, preserves safe wire-format mailbox names and includes the selected mailbox in cursor identity. It does not rely on English folder names. Missing/unsafe folder advertisements fail closed. Gmail/Hostinger provider separation and existing secret references remain intact.

Queue attempts are durable and spaced at least six minutes. Global rolling caps stay at most 10/hour and 100/day; the configured daily target can be lower. Recipient-city/country business-hour mappings and fallback timezone remain enforced. Duplicate ticks see the same durable spacing/reservation. Provider/ambiguous SMTP errors pause and require review. Restart recovery distinguishes no SMTP reservation, accepted messages and uncertain outcomes; accepted/uncertain messages are never automatically resent. High confirmed bounce rates pause outreach. Real unsubscribe cancels queued outreach and updates master contact state; test-mode unsubscribe remains explicitly simulated. Advanced or terminal sales states are preserved.

## Controlled production acquisition

Run 3 reused the deployed discovery/analysis/qualification pipeline with the API's smallest supported manual target of 5:

- 197 raw listings; 134 deduplicated candidates; 40 websites processed.
- 19 qualified observations became 19 genuinely new, unique Master Leads; qualification history exists for all 19.
- 6 entered the unsent queue. 13 entered Manual Contact Needed, retaining phone/social routes.
- 5 exported results; all 19 qualified records remain permanent.
- Zero discovered-prospect email messages and zero duplicate observation keys.
- Runtime about 19 minutes. No full 100-lead run was launched or benchmarked.

The daily worker uses the stricter high_intent policy. Read-only replay over the scan's stored audit facts found 20 candidates meeting that policy against a controlled target of 3, without changing qualification records or counting them as additional leads. The independent small state-machine fixture exhausted its two-market supply with 1 new lead against target 3 and correctly reported shortfall 2. No standards were lowered, rediscoveries counted as new, or businesses fabricated to fill targets.

Evidence: controlled-small-acquisition.json, controlled-acquisition-routing-acceptance.json, controlled-high-intent-acceptance.json.

## Controlled email and tracking

Only contact@planebyte.com was used for current live acceptance. The deleted former mailbox was superseded earlier and retained only as audit evidence. No discovered prospect was contacted.

A real Gmail queue send used a disposable database and acceptance-only process settings; the duplicate tick sent nothing. Production flags were not changed. One separate owned, unqualified production acceptance record exercised real tracking capabilities: SMTP acceptance, HTTP 200 open signal, HTTP 302 click signal, verified reply on the same Message-ID/thread, unsubscribe and all corresponding timeline events. Production unsubscribe suppression was then verified only on that owned acceptance record: DO_NOT_CONTACT with RECIPIENT_UNSUBSCRIBE source. It never entered Master Leads or the automated prospect queue. Open/click events are signals, not proof of human reading.

As the owner instructed, hard/soft bounce acceptance used simulated Gmail-style DSNs. Tests cover hard-address suppression, soft thresholds, mailbox-full remaining soft, duplicate DSNs, untrusted authentication rejection, phone retention/manual routing and high-bounce automation pause. No real bounce-test email was sent to a random, external or deliberately nonexistent address. A future real rejection test requires separate confirmation of an owned-domain rejection address/catch-all behavior.

Evidence: controlled-live-queue-acceptance.json, controlled-production-tracking.json, gmail-special-use-acceptance.json, gmail-reply-activity-acceptance.json, gmail-bounce-fixture-acceptance.json.

## Validation

- Backend: 285 unit tests passed; one opt-in live-send test skipped in the general suite and passed separately against Gmail. Additional targeted suites passed throughout.
- PostgreSQL: dedicated disposable-schema acceptance passed for schema-9 view counts/filters and target storage, enabled queue duplicate prevention across independent connections, and legacy global-alias rediscovery. Earlier three core PostgreSQL integration tests also passed. Production migrations were not rerun.
- Frontend: 45 unit tests, strict TypeScript and ESLint passed (one pre-existing unused-variable warning).
- Browser: all 9 regression/management tests passed; final identity-review notice and both management pages passed an additional focused browser run.
- Verification build and release container regression checks passed. Webpack was used locally because the default Turbopack worker cannot bind its sandbox port; production Vercel builds succeeded.
- Live signed smoke checks passed for overview, pause controls, Master Leads/counts/email filter, market pagination, targets, email history, identity review and Gmail health. Login/CSP and anonymous API rejection remained verified.

## Deployment and activation

Primary UI: https://leads.planebyte.com. Exact final revisions, images, build IDs, secret-reference preservation and scheduler states are recorded in AUTOMATION_DEPLOYMENT_STATE.json and deploy/automation-builds.json. Image updates preserve all existing environment values and secret references. Temporary staging tags are removed after live acceptance.

Current state:

- AUTO_SCAN_ENABLED=false
- AUTO_EMAIL_ENABLED=false
- EMAIL_SENDING_ENABLED=false
- Database scan_paused=1 and email_paused=1
- Acquisition/outreach schedulers PAUSED
- Five-minute inbox scheduler ENABLED; former ten-minute scheduler retained PAUSED

The initial schema-9 deployment preservation evidence remains in the before/after/rollback files: all original row hashes survived that migration. This completion pass used no production DDL, migration reset or destructive data cleanup.

Controlled acceptance is complete. Owner activation is intentionally not performed. Exact production configuration changes, scheduler resume commands and emergency-stop commands are in FINAL_ACTIVATION_CHECKLIST.md. Review the current queue before activating real outreach. Quality supply and recipient-local windows may cause legitimate shortfalls; the system must report them rather than weaken standards or exceed quotas.


## Owner-authorized clean-start acceptance — 2026-11-01

This supersedes the historical lead/queue counts and completion statement above. The upgrade is awaiting the owner's personal email/PDF inspection; production activation and the proposed 50-qualified-lead run are NOT authorized yet.

- One private rollback archive was checksum/CRC verified and all 50 tables were successfully restored into a disposable schema before cleanup. All existing private objects were archived; already-missing object references are documented in its manifest. Evidence: `owner-clean-start.json`.
- Operational data was removed with explicit-table TRUNCATE RESTRICT. Master Leads, Qualified Leads, Queued Leads, prospect email threads and messages were all verified zero. Schema 9, migrations, authentication, mailbox/configuration, markets and infrastructure were preserved. No migrations were rerun.
- Two individual public businesses were assessed, never a citywide/full daily scan. Lime Tree Dental Practice did not qualify; its failure was retained. Homestay Hotels was freshly crawled and passed the existing high-intent policy as A+. No old findings/qualification records were restored. One published Overture seed was reused and its official website reconfirmed live.
- The shared production composer/queue renderer now supplies the normal signature. The public signature name/spelling was aligned in root/API/worker; Gmail credentials/endpoints were preserved. Local stale limits were aligned with the specified 10/hour, 100/day, daily target 100.
- The normal immutable client-report service generated a 10-page PDF; every page was visually inspected. No separate acceptance template or PDF was introduced.
- Exactly one SMTP call sent the production subject/body/PDF to agrawaljoy1@gmail.com. The genuine business contact was retained only as intended recipient; the controlled To/envelope was used. OWNER_CONTROLLED_REDIRECT activity/message type and test_mode=1 prevent this being mistaken for real prospect contact. No last-contact timestamp or follow-up was applied. Its automation queue entry was canceled.
- Gmail SMTP accepted and the exact message was found once in the SPECIAL-USE Sent folder. Its sender/recipient, HTML/text, subject, signature, unsubscribe footer and exact PDF bytes were checked. Production open/click endpoints recorded explicitly automated QA signals; the click destination and unsubscribe confirmation returned 200. No unsubscribe was applied. Evidence: `owner-clean-start-send.json`, `owner-clean-start-report.json`.
- Unit suite: 286 passed, one live opt-in skipped; container regression builds and read-only staged API/Gmail smoke passed. API revision leadengine-api-00024-bh9 is live.
- All three activation flags remain false on API/worker/root; database scan/email pauses remain set; acquisition/outreach schedulers remain PAUSED. The previously enabled inbox-only sync was restored. There is one qualified Master Lead and zero active queue entries after the controlled send.


## Superseding manual-first/content release

The manual-first navigation, explicit runs/schedules and client-content redesign are deployed on schema 10. See MANUAL_FIRST_IMPLEMENTATION_REPORT.md for the full final implementation, validation, database/API changes and current deployment state. Existing row preservation across all 50 tables passed. The redesigned Homestay example was sent only to the owner-controlled recipient; real activation remains unapproved. Earlier background-only activation commands are superseded by explicit manual runs or enabled user schedules. Owner inspection remains pending; do not mark the upgrade complete.


## Final client-content polish

The company-specific opening, business-language email findings, concrete reply CTA, configured Piyush/Founder signature and stronger WHY PLANEBYTE copy are deployed on API revision leadengine-api-00026-zvx. The approved eight-page PDF structure is retained. This pass used zero migrations and changed no Gmail settings, schedules or reply/bounce/tracking architecture. Deployment preservation evidence is in FINAL_CONTENT_DEPLOYMENT_STATE.json; the single controlled-send evidence is in final-content-acceptance.json. All activation flags remain false and owner inspection remains pending.


## Campaign-centric operations review release — 2026-11-01

Schema 11 and API revision `leadengine-api-00029-9gh` are live with the scalable operations UI at https://leads.planebyte.com. Campaign-scoped audience/accounting, evidence-constrained pitches, explicit re-contact, safe legacy schedule intent, paginated workspaces and review drawers are implemented. Validation and preservation evidence: `CAMPAIGN_OPERATIONS_IMPLEMENTATION.md`, `CAMPAIGN_OPERATIONS_DEPLOYMENT_STATE.json`, `campaign-operations-migration.json`, `campaign-operations-test-evidence.json`, and `campaign-operations-production-smoke.json`. All three automation flags remain false; acquisition/outreach schedulers and database controls remain paused. This review deployment does not activate or declare completion of the owner’s real-outreach acceptance/activation process.

## Workflow repair and fresh-start checkpoint — 2026-11-02

Schema 12 is live. Reported limits-save, schedule linkage/dispatch and non-sendable Run Emails failures are repaired. Owner-requested workspace targets are 500 qualified/day, 500 emails/day, 50/hour, three-day follow-up and Asia/Kolkata; lower campaign limits still apply. Exact Linux tests, browser acceptance and safe deployed dispatch passed. Redis response caching, connection pooling and campaign query batching are live. A restore-tested full backup preceded the authorized operational reset; prospects/campaigns/schedules/queues/mail/tracking/report records are empty. Gmail/auth/configuration/market definitions/security/suppression protections remain. All three automation flags and both operator controls remain off/paused. No new real campaign was started. See `WORKFLOW_REPAIR_ACCEPTANCE.md` and machine-readable evidence for results and the explicit remaining broader Phase 4.9 acceptance gaps. Do not mark the entire automation upgrade complete on this checkpoint alone.
