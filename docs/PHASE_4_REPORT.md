# Phase 4 implementation and acceptance

Status: Phase 4A and Phase 4B controlled acceptance passed. Hostinger remains in test mode; live outreach requires a separate manual owner configuration change.

## Production data

The actual working dataset is one parent campaign with two completed real scans (London and Manchester hospitality). The initial baseline in `phase4-before.json` contains 1 campaign, 2 runs, 1,250 canonical prospects, 1,927 observations, 800 opportunity scores, 742 social profiles and no notes. No discovery scan, reset, truncation or lead fabrication was performed during Phase 4.

Schema 7 adds sales, activities, follow-ups, lists, views, accounts, threads, messages, templates and inbox cursor tables. PostgreSQL changes the allowed status constraint without rebuilding existing prospect rows. The SQLite migration copies every existing column and index and checks foreign keys.

`phase4-after.json` records exact matching hashes for every original non-report table. Three authenticated user-generated READY client reports appeared while development was in progress, after the original zero-report baseline. Their IDs and creation metadata are recorded as verified concurrent additions; they were retained. The rollout initially stopped on that difference and resumed only after explicitly accounting for those three reports. Neither baseline nor reports were deleted to make the check pass. Further acceptance reports and sales activities are intentional additions on existing leads.

## Sales workspace

The Outreach page provides ready, today, overdue, waiting, replied, meeting, proposal, won, lost, not-interested and suppressed queues with real counts and pagination. Lead detail adds follow-ups, lists, editable optional deal information, reviewed email conversations and activity history. Header indicators show due follow-ups and unread verified replies. Existing discovery, scoring and intelligence remain available.

The twelve statuses include explicit READY_TO_CONTACT, FOLLOW_UP, MEETING, PROPOSAL, NOT_INTERESTED and DO_NOT_CONTACT. Suppression persists at canonical prospect level independently of a later status edit, excludes automatic contact queues, blocks compose/preview/send and cancels open reminders. Rediscovery retains that state. Lifting suppression requires an explicit action. Lost and Not Interested remain distinct; contacting a Not Interested prospect requires explicit review.

Follow-up dates are stored with time zones, with tomorrow/3/7/14-day and custom scheduling, completion and rescheduling. Today and overdue use the configured application timezone. Lists store prospect membership; deleting a list retains its leads. Saved views store validated filter and sorting definitions. Bulk actions are capped at 100 selected leads and support status, assignment, list membership, follow-up and PDF generation. There is no bulk email send.

## Hostinger integration

The primary provider uses only the user-verified SMTP and IMAP TLS endpoints. The shared mailbox is `rajendra@planebyte.com`. Credentials remain server-side and use a dedicated secret reference; existing platform secrets were preserved. Gmail is optional and disabled, as documented in `GMAIL_INTEGRATION.md`.

Email settings expose account metadata, independent connection health, disconnect/reconnect/default and bounded manual synchronization. The composer accepts only stored public business contact addresses, suggests an existing READY PDF for the same canonical lead, supports deterministic editable templates and requires preview followed by Confirm Send. No AI personalization, tracking pixels, link rewriting or attachment upload was introduced.

Test mode redirects both SMTP envelope and To header to the configured controlled test recipient, labels the message and persists its intended recipient and test mode. A successful SMTP acceptance stores SENT, conversation/thread identifiers, activity and a last-contact timestamp. It only promotes READY_TO_CONTACT to CONTACTED and can schedule an explicitly selected follow-up. SMTP acceptance does not claim delivery or an open/read event.

Polling reuses the private worker on a ten-minute scheduler. Each execution is capped at 180 seconds; an invocation reads at most 30 headers and five referenced messages, with a short loop deadline, read-only INBOX and message-size limits. UIDVALIDITY and UID cursors, a synchronization lock and database uniqueness constraints prevent duplicate processing. Polling defers when heavy workers are at their configured cap. It never sends mail.

Reply matching requires stored outbound RFC references, one unambiguous thread, the expected peer address, the configured mailbox and plausible date. Automatic REPLIED promotion additionally requires aligned DKIM/DMARC success reported by a trusted receiving-provider Authentication-Results header. A structurally matched but unverified message is retained for review without verified-reply counters or automatic status promotion. Meeting/proposal/won/lost/suppressed states are never downgraded.

## Security and operating limits

- Browser sessions and signed API requests protect all email and sales routes; request models reject unknown fields. Preview tokens bind the reviewed payload to sender, effective recipient, lead, report, thread and sending mode.
- Addresses and header values reject control characters. Subjects and bodies are bounded. Incoming HTML is converted to plain text; scripts, remote images and attachments are never rendered or loaded.
- Reports must belong to the same prospect, be READY, have a private storage object and pass PDF/size checks. Signed downloads and existing private storage are retained.
- Sending uses a durable idempotency key and content hash, a global concurrency lock, rolling limits of 10/hour and 30/day, and a second suppression check immediately before SMTP. Uncertain outcomes remain SENDING and cannot trigger automatic retransmission.
- No mailbox password is stored in ordinary records, public environment variables, browser responses, fixtures, documentation or deployment output. A connection health check never sends a message.
- Live mode requires manual server-side changes to both EMAIL_SEND_MODE and EMAIL_LIVE_APPROVED. They remain test/false during acceptance. No discovered prospect may receive automated QA email.

Read-only DNS verification found SPF `v=spf1 include:_spf.mail.hostinger.com ~all` and DMARC `v=DMARC1; p=none`. DKIM remains unverified because no actual provider selector was supplied; no selector/key was guessed and no DNS was changed. These findings do not establish inbox delivery quality. See `EMAIL_DELIVERABILITY.md`.

## Validation

- Final Linux backend image: **203 passed, 3 skipped**. The skipped tests require a separately configured real PostgreSQL integration environment.
- The three real PostgreSQL integration tests also passed separately in disposable schemas, including migrations and concurrent canonical identity handling.
- Frontend: 45 unit tests, TypeScript strict checking, ESLint and production build passed.
- Browser suite: five tests passed, including preview/send state, follow-up, suppression and reply-state behavior with mocked mail. The real controlled reply was verified separately against the production mailbox and persisted conversation.
- Local visual review covered the composer preview and responsive Outreach at 1366×768, 1440×900, 1920×1080 and 390×844. Evidence is under `output/qa-phase4/`; production screenshots are recorded separately.
- Existing scoring, discovery and client-report regression tests remain in the full backend suite. No production mass rescan or re-audit was needed.

Production acceptance results are recorded in `phase4-production.json`; scheduler and secret configuration evidence are in `phase4-email-scheduler.json` and `phase4-mail-deployment.json`. The controlled flow must demonstrate SMTP send → durable message → genuine IMAP reply → matching → reply activity → correct status before Phase 4 is marked complete. A human reply from the controlled mailbox is required; it must never be simulated in production.


## Final continuation and acceptance

The existing implementation, schema 7 rollout and controlled SMTP send were retained. This continuation made no discovery scans, ran no migrations, reset no data and changed no production secrets. `phase4-current-preservation.json` verifies one parent campaign, both completed scans, all 1,250 canonical prospects, 1,927 observations, 800 opportunity scores, 742 social profiles and all five client reports. Sales status and activity additions are intentional acceptance changes on existing leads.

The genuine controlled reply exposed a receiver-domain mismatch: the real Hostinger Authentication-Results authority is under `hostinger.io`. The verifier now recognizes that receiver domain alongside the existing provider domains, still requiring aligned DKIM or DMARC success and enforcing domain boundaries. Spoof lookalikes are rejected. The already-stored genuine reply was reread from IMAP with the corrected server code and verified once; no inbound message or authentication result was fabricated. Rechecking does not duplicate messages, activities or unread counters, and does not move the normal UID cursor backwards. This bounded operator recheck is available in server code, not as a browser option.

Transport health checks now require successful SMTP NOOP and IMAP inbox-selection responses; synchronization stops when inbox selection fails. Offline provider tests cover these failures, UIDVALIDITY reset, tracked-message body fetching and safe HTML extraction. Additional tests cover the actual receiver domain, spoof domain boundaries and idempotent re-verification.

The strengthened acceptance check ties the persisted outbound message, inbound message, verified activities and REPLIED status to the exact controlled conversation. Deployment evidence excludes email bodies and unrelated sales metadata. `phase4-production.json` records the completed flow. Production screenshots wait for loaded Outreach data and cover 1366�768, 1440�900, 1920�1080 and 390�844 without viewport overflow or browser errors.

Local backend and validated Linux image: 203 passed, 3 skipped. The skipped tests need an explicitly configured disposable PostgreSQL test schema; the earlier separate PostgreSQL acceptance remains recorded above. Frontend typecheck, ESLint, 45 unit tests, all five browser tests and production build passed during this continuation. The image-only release deployed API revision `leadengine-api-00014-b6f` and the validated worker image, without rerunning migrations or modifying secrets. Release evidence is in `phase4-reply-fix-deployment.json`. Production suppression was checked on the second existing scan and that acceptance lead was restored to its original status.

Gmail remains optional and disabled. Existing DNS was not changed. SPF/DMARC observations and unverified DKIM selector limitations remain as documented above. Live sending was not enabled; EMAIL_SEND_MODE remains test, and automated QA did not contact a discovered prospect.

Post-release verification confirmed the complete controlled conversation checks still pass through production APIs, the lead remains REPLIED, repeated sync adds no duplicate reply, SMTP and IMAP both report READY, and sending mode remains test.
