# Email engagement tracking

Phase 4.1 extends the existing Hostinger message/thread records and activity timeline. The first-party base is configurable through `EMAIL_TRACKING_BASE_URL`; the initial production surface is `https://leads.planebyte.com/t`. No custom DNS change is required.

## Facts and signals

- `SMTP_ACCEPTED` means the SMTP server accepted the message. The UI says Sent or SMTP accepted, never Delivered.
- `SEND_FAILED` is a definite failed send. An uncertain SMTP outcome remains SENDING and is never automatically resent.
- `OPEN_SIGNAL` records a remote image request. Apple Mail Privacy Protection, image proxies and other software may generate these requests without a person opening the email. The UI never treats this as a definitive open or high intent.
- `CLICK_SIGNAL` records a request for a stored link. Security gateways and preview services may fetch links automatically. Known scanner/proxy agents and HEAD requests are marked AUTOMATED; an interactive browser navigation with a user gesture can be LIKELY_HUMAN; other requests remain UNKNOWN.
- `REPLIED_VERIFIED` retains the Phase 4 checks: stored outbound references, unambiguous conversation, expected peer/mailbox, plausible date and aligned DKIM/DMARC success from a recognized receiving provider. It is the strongest engagement evidence.
- Hard/soft bounce events represent structured DSN classifications. An unverified report is visible for review and cannot suppress an address.
- `UNSUBSCRIBED` is a confirmed opt-out. A test-message token records a test-only opt-out without suppressing the real prospect.

Existing historical sends/replies are backfilled from persisted facts with their original timestamps. No historical opens/clicks are invented. Drafts and SENDING remain persisted workflow states. Message type is FIRST_CONTACT, FOLLOW_UP or MANUAL_REPLY; a selected template ID supports simple outcome attribution. Replies attribute to In-Reply-To where available, otherwise the newest referenced outbound message.

## Tokens and endpoint behavior

Every action uses a separate 256-bit random opaque bearer token. Only its SHA-256 hash is stored. URLs contain no prospect ID, email address or database ID. Tokens expire after 365 days and only work for SMTP-accepted messages.

- GET/HEAD `/t/o/<token>.gif`: a valid 1x1 transparent GIF with no-store headers. An invalid token gets the same image without recording an event.
- GET/HEAD `/t/c/<token>`: record a signal and redirect only to the URL persisted while rendering the reviewed message. Request parameters never supply the destination. Private/literal local IPs, localhost, credential-bearing URLs, unsafe schemes and encoded numeric IP forms are rejected. This service does not fetch destinations.
- GET `/t/u/<token>`: a generic confirmation form with no lead information. GET cannot suppress. POST requires `confirm=stop`, or the exact one-click unsubscribe form body. Invalid tokens do not reveal prospect information.

HTML is generated from escaped plain text. Eligible public HTTP(S) links are rewritten; mailto/tel, the opt-out link, existing tracking URLs and private/signed report downloads are not rewritten. PDFs remain attachments from existing private storage. No public report-sharing page was added.

Application endpoint budgets are durable across workers: 30 requests per token/minute and 600 total/minute. Rate-limited pixels still return a valid image. Event deduplication preserves first/last timestamps and request counts per token and signal quality. Summaries count distinct messages rather than repeated proxy requests. A click summary counts messages with a click, not a claim that each HTTP request represents a person. Automated requests remain stored and are excluded from the compact activity counters.

No raw IP addresses, raw user-agent strings, location, cross-site cookies or fingerprints are stored. Only a coarse user-agent category and signal quality are retained. Tokens are bearer capabilities and should not be copied into diagnostics or deployment reports.

## Suppression and bounces

The existing bounded IMAP worker handles replies plus multipart/report delivery-status notifications. It reads at most 30 headers and five relevant bodies, retaining the existing time and size limits. DSNs require exact stored message references, the actual SMTP recipient, configured mailbox and plausible time. Unstructured mailer-daemon subject/body text cannot prove a bounce.

A failed 5.1.x recipient error or 5.2.1 disabled mailbox is classified as hard; a mailbox-full 5.2.2, a 4.x.x failure and other uncertain/policy failures remain soft/reviewable. Automatic address suppression additionally requires aligned authentication from the recognized receiver. Unauthenticated DSNs remain review-only. A hard failure invalidates the specific address, not the entire company. Three distinct authenticated soft bounces make that address temporarily unusable pending manual review. There is no automatic retry or automatic suppression clearing. Test messages cannot invalidate the prospect's real address.

Confirmed production unsubscribe persists `RECIPIENT_UNSUBSCRIBE`, marks canonical DNC, cancels open reminders and preserves all history. Manual DNC uses `MANUAL_DNC`; bad-address suppression uses `HARD_BOUNCE` or `OTHER`. Rediscovery cannot clear these controls. Explicit owner unsuppression remains available. Clear stop-request wording is highlighted with a manual Mark Do Not Contact action; no AI or automatic text classifier changes status.

## Preferences and metrics

Open/click defaults are on, with owner preferences and per-message toggles. Preferences bind the reviewed preview so a change requires a fresh review. Reply verification and bounce safety remain active infrastructure.

Outreach activity supports Today/7/30 days using the browser timezone, with separate live/test counters and template outcomes. Lead detail and conversations show compact signals and the existing chronological activity timeline. Polling/query invalidation refreshes data without WebSockets.

Engagement level is deterministic: HIGH for a verified reply; otherwise MEDIUM for a LIKELY_HUMAN click; otherwise LOW for a non-automated open signal; otherwise NONE. UNKNOWN clicks are displayed as signals and do not imply high intent. Automated signals cannot raise the level. No open-rate performance KPI or AI score is created.

Standards references: [RFC 3464 structured DSNs](https://www.rfc-editor.org/rfc/rfc3464) and [RFC 8058 one-click unsubscribe](https://www.rfc-editor.org/rfc/rfc8058). Hostinger supplies transport authentication; valid DKIM coverage of the List-Unsubscribe headers is provider-dependent and is not falsely certified by the application.
