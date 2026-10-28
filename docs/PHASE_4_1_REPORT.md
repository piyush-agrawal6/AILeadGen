# Phase 4.1 implementation, deployment and acceptance

Status: implementation deployed and controlled tracking/reply acceptance passed. The owner explicitly requested test mode remain active. Live activation and the first real prospect send have not been performed and remain owner actions; this report does not certify a live send that never occurred.

## Current production state

- Existing private LeadEngine API and worker were updated to the validated Phase 4.1 images. API revision: `leadengine-api-00017-7tx`.
- Existing Vercel dashboard deployment: `dpl_FEwb4mB3EM2YD1GmH8k7Evi2fh9G`, aliased to https://leads.planebyte.com.
- Schema 8 is additive. It adds engagement events, hashed action tokens, tracking preferences, address suppression, drafts, message attribution/tracking fields and suppression source. No Phase 4 tables were replaced.
- `EMAIL_SEND_MODE=test` and `EMAIL_LIVE_APPROVED=false` remain unchanged. The emergency switch is implemented; no live mode or first real send was activated by deployment.
- Existing database, authentication, signing, GCP, R2 and mailbox configuration/secrets were preserved. No production secret was rotated or recreated. No DNS change, autodetection, POP3 or new scan occurred.

## Data preservation and concurrent app changes

`phase41-before.json` records the schema-7 baseline: one campaign, two completed scans, 1,250 canonical prospects, 1,927 business observations, 800 opportunity scores, 742 social profiles, five client reports and two email messages, plus existing sales/email identities and hashes.

`phase41-after.json` verifies original lead/scan/report/email identities are retained, immutable original fields are unchanged, and the two original scans are unchanged. Reports and email history added through the app during development were retained, alongside the controlled acceptance additions.

The strict rollout guard stopped before routing traffic when it found the prior acceptance list had been removed through the existing app during development. Its LIST_REMOVED events predate the Phase 4.1 migration and identify the missing baseline list. The old list-delete route did not retain an actor ID, so no individual attribution is claimed. The migration has no lead-list deletion. The original baseline and strict `all_original_rows_retained=false` result remain visible; the separate passing check explicitly accounts for this concurrent list removal. No list was recreated, no baseline was rewritten, and no records were deleted to force a match. All original prospects, scans, reports, notes, activities and email history remain retained.

The prepared first-live candidate's Ready to Contact status and saved draft are intentional sales additions. No existing owner draft was overwritten.

## Tracking architecture and accuracy

Initial production surface: `https://leads.planebyte.com/t`, configurable with EMAIL_TRACKING_BASE_URL. No tracking subdomain or new hosting service was required.

A reviewed send creates separate 256-bit random opaque open/click/unsubscribe capabilities. Only SHA-256 token hashes are persisted. Public links reveal no email address or database identifier. Tokens expire after one year and only resolve for SMTP-accepted messages. Clicks use persisted, validated public HTTP(S) destinations; no destination is accepted from a request parameter. Private/local addresses, unsafe schemes, credentials and numeric IP tricks are rejected. The server does not fetch destinations.

The existing activity timeline receives normalized SMTP acceptance, definite failure, open/click signals, bounce, verified-reply and unsubscribe events. Historical sends/replies are backfilled only from accepted records with their original timestamps. No historical open/click or fake human engagement was invented. Raw IPs, raw user-agent strings, fingerprints, geolocation and cross-site cookies are not stored. Durable rate limits bound public endpoint work.

Open/click signals retain first/last times and repeated-request counts with stable event keys. Compact metrics count distinct messages, avoiding inflated proxy request totals. Known scanner/proxy agents and HEAD are AUTOMATED; explicit browser user navigation may be LIKELY_HUMAN; remaining requests are UNKNOWN. Automated events are retained and excluded from the compact human-oriented counters. Classification is conservative and cannot identify every scanner.

Open requests are always labeled Open signal, never definitive Opened. Image privacy services, Apple Mail Privacy Protection and mail proxies can fetch pixels independently of a person. Click signals may come from security scanners. SMTP acceptance displays Sent/SMTP accepted, never Delivered. Verified replies remain the highest-confidence engagement evidence. Engagement level is HIGH for verified reply, otherwise MEDIUM for a likely-human click, LOW for a non-automated open signal, and NONE otherwise; unknown clicks cannot create high intent.

## Live-send guard and review

Production requires EMAIL_SENDING_ENABLED=true, EMAIL_SEND_MODE=production and EMAIL_LIVE_APPROVED=true. A disabled kill switch or inconsistent mode/approval pair blocks outbound mail. Test mode requires live approval false and redirects both SMTP envelope and To header to the controlled mailbox. No bulk or automatic cold-email path was added.

Before SMTP the existing send flow validates stored contact, canonical suppression, account connection, reviewed payload, report ownership/readiness, idempotency and rolling limits. Production performs fresh SMTP health; those checks run again afterward to avoid stale recipients/reports/configuration. Suppression is checked repeatedly under the canonical lock. Limits remain 10/hour and 30/day. A definite failure is persisted; an uncertain outcome remains SENDING and cannot be automatically resent.

The composer includes message-level open/click choices, actual-recipient preview, PDF, template/message attribution and an unmistakable Send Live Email button for production. Draft saving/loading preserves reviewed content and recipient/attachment/tracking choices. Query invalidation and polling refresh engagement without WebSockets. Saved drafts never send by themselves.

## Bounce, reply and suppression behavior

Bounded IMAP synchronization now includes structured multipart/report DSNs. It matches stored outbound references, actual SMTP recipient, configured mailbox and plausible time. Known permanent recipient failures are hard; temporary, mailbox-full and policy/uncertain failures are soft/reviewable. Automatic invalidation requires recognized receiving-provider aligned authentication. Unverified reports remain review-only; an unsupported/unstructured bounce is not guessed from its subject. Three authenticated distinct soft bounces mark that address temporarily unusable for manual review. Test bounces cannot invalidate the real prospect address.

Confirmed production opt-out requires POST; GET shows only a generic confirmation page and cannot suppress. Production unsubscribe sets canonical DNC, records RECIPIENT_UNSUBSCRIBE, cancels reminders and retains history. Test-message opt-out records a test event without suppressing the discovered business. Manual DNC remains separate; address-level HARD_BOUNCE/OTHER suppression does not suppress an entire company with another valid contact. Rediscovery cannot clear suppression.

Existing verified replies still require message references, unambiguous conversation, expected peer/mailbox, plausible time and aligned receiver authentication. CONTACTED/FOLLOW_UP can become REPLIED; later sales states and DNC are not downgraded. In-Reply-To/newest referenced outbound attribution supports first-contact versus follow-up outcomes. Clear stop-request text offers manual Mark Do Not Contact; there is no AI classifier.

## Domain authentication and operating limits

The owner explicitly reviewed Hostinger Domain Settings on 27 October 2026 and reported green/healthy SPF, DKIM, DMARC and MX, with DKIM successfully configured/verified. This satisfies the requested owner-reviewed DKIM readiness path; `phase41-domain-auth.json` records the explanation. No selector was guessed. This does not claim an independent DNS-selector lookup or certify universal inbox placement.

Hostinger remains smtp.hostinger.com:465 and imap.hostinger.com:993 with SSL/TLS for rajendra@planebyte.com. Account-specific provider plan limits were not retrieved and were not guessed; application limits remain conservative. See LIVE_OUTREACH.md.

## Validation and controlled acceptance

- Local backend: 241 passed, 3 skipped. Validated Linux image: 241 passed, 3 skipped. The skipped tests require opt-in real PostgreSQL execution.
- All three opt-in PostgreSQL tests passed separately in disposable schemas, including migration/repository and locking behavior. Production public tables were not reset.
- TypeScript strict, ESLint, 45 frontend unit tests, production build and seven browser tests passed. New browser tests verify a real-recipient live preview requires an explicit Send Live Email action using mocked transport; no real prospect is contacted.
- Production browser smoke passed: private metrics remain authenticated, the public pixel works anonymously, tracking settings load, the saved draft loads/previews in test mode, no browser errors, and Outreach fits 1366x768, 1440x900, 1920x1080 and 390x844. Screenshots were inspected under output/qa-phase41/.
- One controlled real SMTP message with the existing private client PDF was accepted and durably persisted. Its actual recipient was the configured controlled mailbox. No discovered prospect received it.
- The emailed pixel and click endpoints were exercised with a controlled scanner agent: valid GIF/no-store behavior, safe repeated requests, stored destination redirect, scanner classification and deduplicated open event passed. These are endpoint tests, not claims that a prospect opened or clicked an email.
- GET unsubscribe confirmation and POST opt-out passed. Test opt-out preserved the real prospect; actual production suppression/cancellation and hard/soft bounce behavior passed deterministic fixture tests. No fake bounce was injected into production.
- The owner sent a genuine reply. Deployed IMAP synchronization persisted one verified inbound message, linked it to the correct thread/outbound message, created the normalized REPLIED_VERIFIED event and existing reply activity, and preserved the lead's REPLIED status. No incoming message or authentication result was simulated. See phase41-controlled.json.
- SMTP and IMAP both reported READY after deployment. New worker code retains bounded reply/DSN polling. Protected configuration equality passed during release.

## First real send and remaining owner actions

Skylark motel (existing lead 509, High commercial fit) has an evidence-based saved draft with its existing client PDF and three-day follow-up selection. It is Ready to Contact. Details are in phase41-first-live-draft.json; open https://leads.planebyte.com/leads/509, Compose email, then Load saved draft.

The draft was loaded and previewed through the deployed UI, without pressing Send. Per the owner's explicit instruction, test mode remains active. The owner must separately activate production after review and manually press Send Live Email for the first actual prospect outreach. No live-send operational acceptance is claimed before that happens. The live activation flag change is not authorized by this implementation deployment.

Optional public report landing pages and custom tracking DNS were not added; the existing private PDF attachment flow is sufficient. Gmail remains optional and disabled. Full tracking limitations, standards references and privacy controls are documented in EMAIL_TRACKING.md; activation, limits and emergency shutdown are in LIVE_OUTREACH.md.

Final evidence: the repeated production sync retained exactly one verified inbound message and one normalized reply event. The after-snapshot records 1 campaign, 2 completed scans, 1,250 canonical prospects, 1,927 observations, 800 scores, 742 social profiles, 8 retained/new client reports and 6 email messages. The production query confirms zero SMTP-accepted live messages. All controlled acceptance and production browser checks passed; no outbound live activation or first real send was performed.
