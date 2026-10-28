# Live outreach operations

The application is private. Phase 4.1 deployment preserves `EMAIL_SEND_MODE=test` and `EMAIL_LIVE_APPROVED=false`. The owner explicitly requested that test mode remain active. No automated process may send a live message to a discovered prospect.

## Configuration and activation

Sending supports exactly `test` and `production`. Legacy `live` is rejected safely. Test mode requires sending enabled and live approval false; it redirects both To and the SMTP envelope to the controlled test mailbox and includes TEST labeling.

After reviewing controlled acceptance, the owner may manually configure all three server-side flags:

```
EMAIL_SENDING_ENABLED=true
EMAIL_SEND_MODE=production
EMAIL_LIVE_APPROVED=true
```

These are operational instructions, not values applied by deployment. An inconsistent mode/approval pair or a disabled kill switch blocks sending. There is no browser control that silently activates live sending. The composer labels LIVE OUTREACH, previews the actual stored public recipient, PDF and tracking choices, and requires a separate Send Live Email click. Bulk/automatic email remains unavailable.

Immediately before SMTP, the server rechecks the account, stored public recipient, canonical suppression, exact preview payload, attachment ownership/readiness and reserved limits. Production sending performs a fresh SMTP health check; reviewed checks run again after that potentially slow connection. Definite failures remain failed; uncertain outcomes remain SENDING for operator review and cannot be automatically resent.

## Domain and mailbox

The owner reviewed Hostinger Domain Settings on 27 October 2026 and reported SPF, DKIM, DMARC and MX all green/healthy, including successfully configured DKIM. This is the explicitly accepted owner review in `phase41-domain-auth.json`. No DKIM selector was guessed and DNS was not changed.

The mailbox remains rajendra@planebyte.com, SMTP smtp.hostinger.com:465 and IMAP imap.hostinger.com:993 with SSL/TLS. Credentials remain in ignored environment configuration/Secret Manager; existing values and secret versions are reused. No autodetection, POP3 or credential return to the browser is supported.

Application limits remain 10/hour and 30/day. Hostinger's account-specific plan allowance was not independently retrieved; do not substitute a generic plan maximum or raise app limits. Verify that allowance in the owner's current Hostinger plan before changing limits.

## Tracking and follow-up

The initial tracking URL is https://leads.planebyte.com/t. A different first-party hostname can be configured later through EMAIL_TRACKING_BASE_URL after the owner sets up hosting/DNS. Deployment does not create track.planebyte.com or modify DNS.

Open signals are privacy affected; click signals may be scanners. A verified reply remains the strongest event. See EMAIL_TRACKING.md for exact interpretation, safe redirects, DSNs and opt-out behavior. Existing private client PDFs remain attachments. There is no automatic resend because engagement is absent.

Hard bounces suppress the address, retaining any other valid public contacts. Repeated authenticated soft bounces require manual review. DNC and confirmed recipient unsubscribe suppress the canonical prospect and cancel reminders without deleting history. Review clear stop requests using the conversation's Mark Do Not Contact action.

## First real send

The first candidate and saved draft are recorded in `phase41-first-live-draft.json`. Review that existing lead's evidence, recipient, body and report in the app. Loading a draft restores the recipient, attachment, attribution and tracking choices. Test mode currently remains active, so do not use Confirm Send as a substitute for the future live action.

After the owner explicitly activates production, open the prepared lead, load the saved draft, preview the actual recipient and manually press Send Live Email. Automated acceptance never performs this action. Afterward verify persisted SENT/SMTP acceptance, correct actual recipient with test_mode false, CONTACTED status when starting Ready to Contact, activity, follow-up scheduling and valid tracking URLs. Do not wait for an open/reply to declare SMTP sending operational, and do not call SMTP acceptance delivery.

## Emergency shutdown

Set EMAIL_SENDING_ENABLED=false in the existing API's server configuration. Outbound sending is blocked while IMAP can continue. Alternatively restore test/false mode/approval together for controlled use. Never rotate platform/mailbox secrets merely to stop outreach. Review any existing SENDING reservation against the actual mailbox before a deliberate new send.
