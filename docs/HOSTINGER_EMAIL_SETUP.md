# Hostinger email setup

The user verified the production mailbox `rajendra@planebyte.com`, SMTP `smtp.hostinger.com:465` with SSL/TLS and IMAP `imap.hostinger.com:993` with SSL/TLS. The app uses these explicit values; it does not autodetect providers, use POP3 or change DNS.

The mailbox credential comes from ignored environment configuration and is supplied to the existing API and worker through a dedicated Secret Manager reference. It is never stored in normal database columns, exposed in browser configuration, included in test fixtures or written in reports. Existing database, Google authentication, API signing, GCP and R2 credentials are preserved. Existing mailbox secrets are reused without creating a new version; only an absent mailbox secret is created.

Email preferences show the configured account, independent SMTP/IMAP test results, disconnect/reconnect/default actions, sending mode and last inbox synchronization. The connection test authenticates without sending mail. Gmail remains optional and disabled.

Development and acceptance keep `EMAIL_SEND_MODE=test`. The server redirects the envelope and To header to the configured controlled `EMAIL_TEST_RECIPIENT`; the composer preview explicitly shows that address and the intended public business contact. No automated acceptance sends to a prospect. The message is labeled TEST, and persisted conversations/activities identify test mode.

Configure the values in `.env.example`, supplying the actual password only through ignored configuration or Secret Manager. The explicit sender name is PlaneByte. Optional signature name and role remain blank unless intentionally supplied. Defaults are 10 messages/hour, 30/day, a three-day optional follow-up, a 30-day initial inbox window and ten-minute polling.

The polling job reuses the existing private Cloud Run worker and identity. Each execution is capped at 180 seconds; IMAP reads at most 30 headers and five relevant messages per invocation, with a short network deadline and 512 KiB message limit. It uses a UIDVALIDITY-aware cursor and persists only known referenced conversations. When heavy workers are at their configured limit, sync defers. Manual sync is also available.

Complete the controlled SMTP send, persistence, real IMAP reply, strong thread matching, authenticated reply activity and status checks before enabling live sending. Live mode requires an explicit server-side change to both `EMAIL_SEND_MODE=production` and `EMAIL_LIVE_APPROVED=true`. The UI cannot enable it. Production recipient addresses must already exist as public business contacts; Do Not Contact remains enforced regardless of sending mode.

The app records SENT when SMTP accepts a message, not DELIVERED, OPENED or READ. Uncertain SMTP outcomes remain SENDING and cannot be automatically resent with the same key. Check the mailbox before a deliberate new send.

Use Hostinger's mailbox/domain panel to obtain the actual SPF, DKIM selector and DMARC records, then follow EMAIL_DELIVERABILITY.md. Never copy an invented DKIM key or replace domain records automatically.


Controlled acceptance verified a genuine reply through Hostinger's `hostinger.io` receiving infrastructure. Reply promotion requires a recognized receiving-provider Authentication-Results authority with aligned DKIM or DMARC success, in addition to stored message references, peer address, mailbox and plausible time. The application recognizes Hostinger receiver domains with domain boundaries, so lookalike suffixes do not pass. A reply that cannot be authenticated remains visible for review without automatic status promotion.

If a provider verification fix requires revisiting an already-stored genuine reply, the bounded server-only `sync_mailbox(recheck=True)` operation rereads actual IMAP content. It does not fabricate headers, resend email, duplicate message/activity records or rewind the normal cursor. Normal scheduler polling remains incremental.

Phase 4.1 adds the EMAIL_SENDING_ENABLED emergency switch. Live activation requires enabled=true, mode=production and live_approved=true, all explicitly configured by the owner. The current owner instruction keeps test mode active. See LIVE_OUTREACH.md and EMAIL_TRACKING.md.
