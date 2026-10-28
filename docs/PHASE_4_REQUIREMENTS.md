# LEADENGINE PHASE 4
# SALES WORKSPACE + FOLLOW-UPS + EMAIL INTEGRATIONS

You are Astra acting as the principal product engineer, sales-workflow architect, email-integration engineer, backend engineer, frontend engineer, security engineer and QA owner for the existing private LeadEngine application.

This is the FINAL planned feature phase for LeadEngine.

LeadEngine will remain a **private PlaneByte lead-intelligence and sales workspace**.

Do NOT turn it into a public SaaS.

Do NOT introduce billing, subscriptions, public signup, multi-tenant SaaS architecture, AI marketing, generic CRM functionality or unrelated features.

Phase 4 has TWO workstreams:

```text
Phase 4A
Sales Workspace

Phase 4B
Email Integrations
```

The end goal is:

```text
Discover
↓
Qualify
↓
Prioritize
↓
Contact
↓
Follow up
↓
Reply
↓
Meeting
↓
Proposal
↓
Won / Lost
```

while keeping the application lightweight, premium and useful for PlaneByte's real sales workflow.

---

# 1. CURRENT PRODUCTION DATA — CRITICAL

The previous test/history database was intentionally cleared.

The current production database now contains:

```text
2 newly completed real scans
+
many fresh discovered leads
```

THESE RECORDS ARE THE WORKING DATASET FOR PHASE 4.

Do NOT:

```text
delete them
truncate tables
reset production DB
rerun all discovery
backfill by re-scanning every lead
replace current campaigns
create fake sample leads
```

Before any schema migration:

record exact current production counts.

Create:

```text
docs/phase4-before.json
```

including at minimum:

```text
campaign count
pipeline run count
canonical prospect count
opportunity-score count
report count
notes count
current statuses
```

After implementation compare counts and verify existing data survived.

---

# 2. NEW SCANS

Do NOT run additional large discovery scans during development.

Use the CURRENT production leads to develop and verify:

```text
outreach
lists
follow-ups
statuses
activities
email
reports
reply detection
```

If an actual new scan becomes technically necessary for final acceptance:

maximum:

```text
1 campaign
1 location
1 vertical
target <= 5
```

and only after existing current data has already been used for the main acceptance work.

---

# 3. CURRENT ACCEPTED PLATFORM

Preserve everything from Phase 3 / 3.5 / 3.6.

Do NOT regress:

```text
Discover campaigns
company/lead intelligence
Website opportunity
SEO opportunity
Security opportunity
commercial fit
business size
social profiles
social activity
PDF client reports
R2 private storage
PostgreSQL
Cloud Run worker
Google login
Lead Workspace
Lead Detail
filters
status controls
reports library
```

---

# 4. PHASE 4 PRODUCT PRINCIPLE

Do NOT build Salesforce.

Do NOT build HubSpot.

We need only the functionality required to take a qualified LeadEngine prospect and manage it through PlaneByte's sales process.

The product should answer:

```text
Who should I contact?

Who needs follow-up today?

Who replied?

Who has a meeting?

Who received a proposal?

Who became a client?

Who should never be contacted again?
```

---

# ==========================================================
# PHASE 4A — SALES WORKSPACE
# ==========================================================

# 5. NEW OUTREACH PAGE

Create:

```text
/outreach
```

This becomes the primary daily sales page.

Navigation:

```text
WORKSPACE

Overview
New scan
Campaigns & scans
Lead workspace
Outreach
Reports & exports
```

Do not create unnecessary separate pages for every status.

---

# 6. OUTREACH HEADER

Design direction:

```text
Outreach
Work the leads that need your attention today.
```

Top summary:

```text
Ready to contact
Follow-ups today
Overdue
Replies
Meetings
Proposals
```

Do not show fake counts.

Use real persisted state.

---

# 7. OUTREACH QUEUES

Create clear queue tabs/views:

```text
Ready to contact

Follow up today

Overdue

Waiting

Replied

Meetings

Proposals

Won
```

Secondary:

```text
Lost

Not interested

Do not contact
```

---

# 8. SALES STATUS MODEL

Expand statuses to:

```text
NEW

SHORTLISTED

READY_TO_CONTACT

CONTACTED

FOLLOW_UP

REPLIED

MEETING

PROPOSAL

WON

LOST

NOT_INTERESTED

DO_NOT_CONTACT
```

Preserve current records.

Existing statuses must migrate without changing their meaning.

---

# 9. STATUS COLORS

Use the existing minimal semantic style.

Suggested:

```text
NEW
soft neutral blue

SHORTLISTED
teal

READY_TO_CONTACT
emerald

CONTACTED
blue

FOLLOW_UP
amber

REPLIED
violet

MEETING
indigo

PROPOSAL
purple

WON
green

LOST
muted red

NOT_INTERESTED
gray

DO_NOT_CONTACT
red
```

Always display text labels.

Never rely on color alone.

---

# 10. STATUS TRANSITIONS

Do not enforce an overly rigid state machine.

However, support logical progression:

```text
NEW
→ SHORTLISTED
→ READY_TO_CONTACT
→ CONTACTED
→ FOLLOW_UP
→ REPLIED
→ MEETING
→ PROPOSAL
→ WON
```

Users must be able to jump statuses manually when needed.

Example:

```text
CONTACTED
→ NOT_INTERESTED
```

must be allowed.

---

# 11. ACTIVITY TIMELINE

Add a persistent timeline to each lead.

Example:

```text
26 Oct 10:12
Lead discovered

26 Oct 11:42
PDF report generated

27 Oct 09:21
Moved to Ready to Contact

27 Oct 10:04
Email sent

30 Oct 09:00
Follow-up due

30 Oct 10:11
Follow-up email sent

31 Oct 14:24
Reply received

1 Nov 13:00
Moved to Meeting
```

---

# 12. ACTIVITY EVENT MODEL

Create structured activity records.

Possible event types:

```text
LEAD_DISCOVERED

STATUS_CHANGED

ASSIGNED

NOTE_ADDED

PDF_GENERATED

LIST_ADDED

LIST_REMOVED

FOLLOW_UP_CREATED

FOLLOW_UP_COMPLETED

EMAIL_SENT

EMAIL_RECEIVED

REPLY_DETECTED

MEETING_SCHEDULED

PROPOSAL_SET

WON

LOST

DO_NOT_CONTACT
```

Fields:

```text
id
prospect_id
actor_user_id
event_type
event_at
metadata_json
created_at
```

Use existing conventions where appropriate.

---

# 13. AUTOMATIC ACTIVITY

Create timeline entries automatically for important changes.

Do NOT require manual notes such as:

```text
I changed the lead to Contacted.
```

The system already knows.

---

# 14. FOLLOW-UPS

Create persistent follow-up records.

Fields conceptually:

```text
id
prospect_id
assigned_to
due_at
status
reason
note
created_by
created_at
completed_at
```

Statuses:

```text
OPEN
COMPLETED
CANCELED
```

---

# 15. QUICK FOLLOW-UP OPTIONS

Allow:

```text
Tomorrow

3 days

7 days

14 days

Custom
```

Use user's local timezone correctly.

---

# 16. FOLLOW-UP UX

On lead detail:

```text
Next follow-up

30 Oct 2026
10:00 AM

[ Reschedule ]
[ Complete ]
```

If none:

```text
Schedule follow-up
```

---

# 17. FOLLOW-UP TODAY

Outreach queue:

```text
Follow up today
```

contains OPEN follow-ups due today.

---

# 18. OVERDUE

If:

```text
due_at < now
AND
status = OPEN
```

display:

```text
Overdue
```

with appropriate emphasis.

Do not silently change lead status.

---

# 19. FOLLOW-UP REMINDER IN APP

Add in-app indicators.

Example top bar:

```text
3 follow-ups due
```

Do NOT implement push notifications or SMS in Phase 4.

---

# 20. SAVED LISTS

Add user-created lists.

Examples:

```text
High Priority

October Outreach

Mid-Market Dentists

London Hospitality

Website Opportunities

SEO Prospects
```

---

# 21. LIST MODEL

Conceptually:

```text
lead_lists

id
name
description
created_by
created_at
updated_at
```

and:

```text
lead_list_members

list_id
prospect_id
added_by
added_at
```

Avoid duplicating lead records.

---

# 22. LIST UX

Allow:

```text
Add to list
```

from:

```text
Lead Workspace
Lead Detail
Outreach
bulk actions
```

---

# 23. SAVED VIEWS

Lists and saved views are DIFFERENT.

List:

```text
manually selected prospects
```

Saved View:

```text
stored filter configuration
```

---

# 24. SAVED VIEW EXAMPLE

```text
Mid-Market SEO Leads
```

Filters:

```text
Business size:
MID_MARKET

SEO opportunity:
>= 70

Commercial fit:
HIGH

Status:
NEW / SHORTLISTED

Contactability:
HIGH / MEDIUM
```

---

# 25. SAVED VIEW MODEL

Persist:

```text
name
filters_json
sort
created_by
created_at
updated_at
```

Validate stored filters through allowlisted schemas.

Do not execute arbitrary query definitions.

---

# 26. SAVED VIEW UX

Lead Workspace:

```text
Saved views ▾
```

Options:

```text
High Fit
Mid-Market
New SEO Leads
Needs Follow-up
```

Allow:

```text
Save current view
```

---

# 27. BULK SELECTION

Add row selection in:

```text
Lead Workspace
Outreach
```

Keep visual design clean.

---

# 28. BULK ACTIONS

Allow:

```text
Add to list

Change status

Assign

Schedule follow-up

Generate PDF
```

DO NOT implement:

```text
Bulk Send Email
```

in Phase 4.

Email must remain human-reviewed.

---

# 29. DO NOT CONTACT

This is a critical safety and workflow rule.

If status becomes:

```text
DO_NOT_CONTACT
```

persist suppression at canonical prospect level.

---

# 30. SUPPRESSION BEHAVIOR

A DO_NOT_CONTACT business must:

```text
remain stored

remain discoverable historically

remain visible when explicitly requested

never appear in Ready to Contact

never appear in automatic follow-up queues

never be included in email composer defaults
```

---

# 31. REDISCOVERY

If a future scan rediscovers the same canonical prospect:

```text
DO_NOT_CONTACT
```

must remain.

Never reset it to:

```text
NEW
```

because of rediscovery.

---

# 32. LOST VS DO NOT CONTACT

Keep different meanings:

```text
LOST
sales opportunity did not close

NOT_INTERESTED
prospect declined

DO_NOT_CONTACT
explicit suppression
```

---

# 33. LEAD DETAIL — SALES PANEL

Enhance Lead Detail right rail.

Suggested:

```text
Sales status

Assignment

Next follow-up

Lists

Email

Reports

Notes
```

Keep the main intelligence/evidence content unchanged.

---

# 34. ACTIVITY TAB

Add:

```text
Activity
```

to Lead Detail.

Timeline should include both sales and relevant system activity.

---

# 35. SALES INFORMATION

Add optional fields:

```text
service_interest

estimated_value

currency

meeting_at

proposal_value

proposal_at

close_at

loss_reason
```

Do not turn these into required fields.

---

# 36. SERVICE INTEREST

Values can include:

```text
Website Design / Redesign

SEO

AEO / GEO

Security Hardening

Combined Engagement

Other
```

This is internal PlaneByte information.

Do NOT include automatically in client PDF.

---

# ==========================================================
# PHASE 4B — EMAIL INTEGRATIONS
# ==========================================================

# 37. IMPORTANT CHANGE

Do NOT architect Phase 4 email as Gmail-only.

We currently have access to a professional Hostinger business email subscription.

Support:

```text
HOSTINGER / STANDARD EMAIL
+
GMAIL
```

through one provider abstraction.

---

# 38. EMAIL ARCHITECTURE

Create:

```text
EmailProvider
```

interface.

Conceptually:

```text
sendMessage()
listThreads()
getThread()
syncMessages()
findReplies()
healthCheck()
```

Implement:

```text
HostingerEmailProvider

GmailEmailProvider
```

---

# 39. PRIMARY BUSINESS EMAIL

The private LeadEngine should allow PlaneByte's professional business mailbox to be the primary sender.

Do NOT require Gmail for normal operation.

---

# 40. HOSTINGER SUPPORT

Hostinger email supports standard:

```text
SMTP
IMAP
```

Use:

```text
SMTP
→ outbound sending

IMAP
→ incoming message / reply synchronization
```

Do NOT use POP3.

---

# 41. HOSTINGER CONFIGURATION

Do not blindly hard-code provider settings.

Support configuration such as:

```text
MAIL_PROVIDER=hostinger

MAIL_FROM_ADDRESS=
MAIL_FROM_NAME=PlaneByte

MAIL_SMTP_HOST=
MAIL_SMTP_PORT=
MAIL_SMTP_SECURE=true

MAIL_IMAP_HOST=
MAIL_IMAP_PORT=
MAIL_IMAP_SECURE=true

MAIL_USERNAME=
MAIL_PASSWORD=
```

Document recommended Hostinger defaults separately.

Secrets must never reach browser bundles.

---

# 42. GMAIL SUPPORT

Also support:

```text
Connect Gmail
```

through OAuth.

Do NOT ask users to paste Gmail passwords.

---

# 43. GMAIL SCOPES

Use the least privileged scopes actually required.

If Phase 4 only needs:

```text
send
+
reply/thread detection
```

do not request unrelated full-mailbox privileges.

Document:

```text
requested scope
reason
data accessed
```

---

# 44. EMAIL ACCOUNTS

Create:

```text
email_accounts
```

Conceptual fields:

```text
id
user_id
provider
email_address
display_name
status
is_default
last_sync_at
created_at
updated_at
```

Never store raw secrets unencrypted in normal database columns.

---

# 45. CREDENTIAL STORAGE

For Hostinger:

prefer:

```text
Secret Manager
```

or strong application-level encryption with a server-only encryption key.

Do NOT:

```text
store mailbox password plaintext
log mailbox password
return mailbox password from API
```

---

# 46. EMAIL SETTINGS UI

Under:

```text
Preferences
→ Email
```

show:

```text
Connected account

PlaneByte
name@domain.com

Hostinger Email
Connected
```

Actions:

```text
Test connection
Set default
Disconnect
```

---

# 47. EMAIL HEALTH CHECK

Test independently:

```text
SMTP connection

IMAP connection
```

Report:

```text
Sending ready
Inbox sync ready
```

Never display credentials.

---

# 48. COMPOSE EMAIL

Lead Detail:

```text
Compose Email
```

opens a premium composer.

Fields:

```text
From

To

Subject

Body

Attachment
```

---

# 49. RECIPIENT

Use only a public contact email actually stored for the business.

Do not infer:

```text
firstname.lastname@domain
```

or fabricate addresses.

If multiple public emails exist:

allow selection.

---

# 50. PDF ATTACHMENT

Composer should automatically suggest the latest PlaneByte client PDF.

Example:

```text
Attachments

✓ Digital Growth Audit — GK Dental.pdf
```

Allow user to remove it.

---

# 51. NO REPORT EXISTS

If no PDF exists:

show:

```text
Generate client report
```

Do not automatically generate a PDF without user action unless explicitly selected.

---

# 52. EMAIL TEMPLATES

Create persistent email templates.

Categories:

```text
Website

SEO

Security

General
```

---

# 53. TEMPLATE VARIANTS

Initially include professionally written templates for:

```text
Website redesign

No website

Website unreachable

SEO opportunity

Local SEO opportunity

Basic security opportunity

Mid-market modernization
```

---

# 54. VERTICAL VARIANTS

Allow optional variants for:

```text
Home Services

Dentists

Auto Repair

Real Estate

Legal

Hospitality

Veterinary
```

Do not create hundreds of near-duplicate templates.

Use sensible template inheritance.

---

# 55. TEMPLATE VARIABLES

Supported variables may include:

```text
{{business_name}}

{{website}}

{{city}}

{{vertical}}

{{primary_opportunity}}

{{top_finding}}

{{sender_name}}

{{sender_company}}
```

Only render variables with real persisted values.

Missing optional values must not create ugly placeholders.

---

# 56. EMAIL EVIDENCE

Emails should be grounded in LeadEngine findings.

Example:

```text
I reviewed your website and noticed that
some of the technical local-search foundations,
including structured data and page metadata,
could be improved.
```

NOT:

```text
Your SEO is terrible.
```

---

# 57. NO AI PERSONALIZATION YET

Do NOT add:

```text
OpenAI
Gemini
Claude
automatic email rewriting
```

in Phase 4.

Use deterministic templates and actual evidence.

This gives us a clean baseline for real outreach.

---

# 58. MANUAL REVIEW REQUIRED

Every first-contact email must require:

```text
human review
+
explicit Send click
```

No automatic send.

No background mass campaign.

No send-on-status-change.

---

# 59. SEND FLOW

```text
Compose
↓
Preview
↓
Send
↓
Persist message
↓
Create EMAIL_SENT activity
↓
Update status if appropriate
```

---

# 60. STATUS AFTER SEND

If lead is:

```text
READY_TO_CONTACT
```

successful manual email send may change to:

```text
CONTACTED
```

with confirmation.

Do not overwrite later-stage statuses.

---

# 61. SEND FAILURE

If email sending fails:

```text
do not change lead status
```

Show clear generic error.

Log technical error internally.

---

# 62. MESSAGE STORAGE

Store message metadata.

Conceptually:

```text
email_messages

id
prospect_id
account_id
provider_message_id
thread_id
direction
from_address
to_addresses
subject
body_text
body_html_sanitized
sent_at
received_at
sync_at
created_at
```

Avoid unnecessary duplication of full mailbox contents.

---

# 63. THREAD MODEL

Create:

```text
email_threads
```

Conceptually:

```text
id
prospect_id
account_id
provider_thread_id
subject
last_message_at
last_direction
created_at
updated_at
```

---

# 64. ATTACHMENT STORAGE

For messages sent from LeadEngine:

store attachment metadata.

Do not copy the PDF again if existing private R2 report can be referenced safely.

---

# 65. EMAIL THREAD UI

Lead Detail:

```text
Conversation
```

Example:

```text
YOU
26 Oct · 10:32 AM

Hi Sarah,
...

────────────────────

PROSPECT
27 Oct · 1:14 PM

Thanks for reaching out...
```

---

# 66. REPLY DETECTION

For Hostinger:

use bounded IMAP synchronization.

For Gmail:

use Gmail APIs.

Detect replies belonging to known sent threads.

---

# 67. HOSTINGER IMAP SYNC

Do NOT continuously hold expensive connections unnecessarily.

Use bounded polling.

Suggested:

```text
every 5–15 minutes
```

for this private application.

Make cadence configurable.

---

# 68. REPLY MATCHING

Prefer strong identifiers:

```text
Message-ID

In-Reply-To

References

provider thread ID
```

Fallback carefully to:

```text
sender
recipient
subject normalization
time window
```

Never match only by subject if stronger evidence exists.

---

# 69. REPLY EVENT

On reliable reply detection:

create:

```text
EMAIL_RECEIVED

REPLY_DETECTED
```

activities.

---

# 70. REPLY STATUS

If current status is:

```text
CONTACTED
or
FOLLOW_UP
```

a verified reply may change it to:

```text
REPLIED
```

If current status is:

```text
MEETING
PROPOSAL
WON
LOST
DO_NOT_CONTACT
```

do NOT downgrade/change automatically.

---

# 71. MANUAL OVERRIDE

Users can always correct a status.

Keep timeline evidence of:

```text
automatic status update
manual status update
```

---

# 72. EMAIL SYNC SCOPE

Do NOT ingest the entire historical mailbox.

Initial sync:

```text
bounded recent window
```

and only persist relevant threads.

Example:

```text
30 days
```

configurable.

---

# 73. PRIVACY

Do not turn LeadEngine into a general inbox.

Persist only messages associated with LeadEngine prospects or tracked threads.

---

# 74. CONTACT SUPPRESSION

If lead is:

```text
DO_NOT_CONTACT
```

email composer must be disabled.

Show:

```text
This prospect is marked Do Not Contact.
```

---

# 75. NOT_INTERESTED

Default composer behavior:

warn before new outreach.

Do not completely block if manually overridden unless business rules later require it.

---

# 76. FOLLOW-UP EMAIL

For:

```text
CONTACTED
```

allow:

```text
Send follow-up
```

using the same thread when possible.

---

# 77. FOLLOW-UP TEMPLATE

Add templates:

```text
Follow-up 1

Follow-up 2

After no response

After meeting
```

Keep copy professional and non-spammy.

---

# 78. FOLLOW-UP AFTER SEND

Allow user to choose:

```text
Schedule follow-up in:

3 days
7 days
14 days
Custom
```

directly after sending.

---

# 79. NO TRACKING PIXELS

Do NOT add:

```text
email open tracking pixels
```

in Phase 4.

They introduce privacy, deliverability and accuracy issues.

---

# 80. NO LINK TRACKING

Do not rewrite every link through a tracking redirect.

Keep normal PlaneByte links.

---

# 81. DELIVERY STATE

Use conservative states:

```text
DRAFT

SENDING

SENT

FAILED

RECEIVED
```

Do not claim:

```text
DELIVERED
OPENED
READ
```

unless provider evidence genuinely supports it.

---

# 82. EMAIL SIGNATURE

Allow configured signature.

Example:

```text
Name
PlaneByte
Website
Professional email
```

Do not hardcode personal details.

---

# 83. TEMPLATE EDITOR

Create:

```text
Preferences
→ Email Templates
```

Allow:

```text
create
edit
duplicate
disable
```

Keep it simple.

No drag/drop email builder.

---

# 84. EMAIL SAFETY LIMITS

Even though this is private:

introduce conservative server-side limits.

Example:

```text
MAX_EMAILS_PER_HOUR=
MAX_EMAILS_PER_DAY=
```

Use reasonable configurable defaults.

Do not allow one UI bug to send hundreds of emails.

---

# 85. DUPLICATE SEND PROTECTION

Double clicking Send must NOT send twice.

Use an idempotency key.

---

# 86. SEND CONFIRMATION

For first outreach:

show:

```text
Send email to hello@example.com?
```

with:

```text
PDF attachment
Subject
Sender
```

---

# 87. EMAIL AUTHENTICATION GUIDANCE

Create documentation for the PlaneByte domain.

Check/configure:

```text
SPF
DKIM
DMARC
```

Do not modify DNS automatically.

Create:

```text
docs/EMAIL_DELIVERABILITY.md
```

with configuration verification steps.

---

# 88. DO NOT CLAIM DELIVERY QUALITY

Do not display:

```text
Perfect deliverability
```

based only on SPF/DKIM.

Use:

```text
configured
missing
unknown
```

---

# 89. OUTREACH COMPLIANCE

LeadEngine should retain:

```text
email source
source URL
date discovered
country
```

where available.

DO_NOT_CONTACT must be persistent.

Avoid automated mass emailing.

---

# 90. EMAIL ACTIVITY UI

Timeline example:

```text
EMAIL SENT

To:
hello@gkdental.com

Subject:
A few opportunities we noticed on GK Dental's website

PDF:
Digital Growth Audit.pdf
```

---

# 91. INBOX REPLY UI

On new reply:

```text
NEW REPLY
```

badge in:

```text
Outreach
```

and Lead Detail.

---

# 92. TOPBAR INDICATOR

Optionally show:

```text
2 replies
5 follow-ups
```

Keep it subtle.

---

# 93. OVERVIEW UPDATE

Current overview may add:

```text
Ready to contact

Follow-ups today

Replies

Meetings
```

Do not transform Overview into a huge CRM dashboard.

---

# 94. CURRENT LEADS ACCEPTANCE

Use the two existing completed campaigns.

Select real prospects with:

```text
valid public email

PDF report availability

strong opportunity

commercial fit
```

Test the entire workflow on these.

---

# 95. EMAIL TEST MODE

Before sending to real prospects:

support a safe development/test mode.

Example:

```text
EMAIL_SEND_MODE=test
```

In test mode:

redirect recipient to an explicitly configured internal test mailbox.

Do not silently change real production recipients.

Clearly label:

```text
TEST MODE
```

---

# 96. FIRST REAL SEND

Do NOT send a real cold outreach message automatically during acceptance.

Production acceptance should stop at:

```text
composer verified
provider verified
test message sent to controlled mailbox
reply received from controlled mailbox
reply detected
```

Actual outreach remains a user action.

---

# 97. HOSTINGER ACCEPTANCE

Use the professional Hostinger mailbox.

Verify:

```text
SMTP authentication

test send

Message-ID captured

message stored

IMAP authentication

test reply arrives

reply synced

reply linked to correct thread

REPLY_DETECTED activity created
```

---

# 98. GMAIL ACCEPTANCE

Only if Gmail credentials are configured.

Verify:

```text
OAuth connect

least-privilege scopes

send controlled test

thread metadata stored

controlled reply detected
```

If Gmail is not configured:

Hostinger acceptance is sufficient.

Document Gmail as available but not production-verified.

---

# 99. DATABASE MIGRATIONS

Add versioned migrations for:

```text
activities

followups

lead_lists

lead_list_members

saved_views

email_accounts

email_threads

email_messages

email_templates

suppression data

sales/deal fields
```

Adapt to existing schema instead of duplicating equivalent tables.

---

# 100. DATA PRESERVATION

Before migration:

```text
docs/phase4-before.json
```

After migration:

```text
docs/phase4-after.json
```

Existing:

```text
campaigns
runs
prospects
scores
reports
notes
social profiles
```

must remain intact.

---

# 101. SECURITY

Email integration introduces high-value credentials.

Perform specific threat review.

Protect against:

```text
credential leakage

SMTP injection

email header injection

HTML/script injection

cross-prospect thread leaks

unauthorized attachment access

IDOR

reply spoof matching

duplicate sends

CSRF

secret logging
```

---

# 102. EMAIL HEADER SAFETY

Strictly validate:

```text
From

To

Reply-To

Subject
```

Reject newline/header injection.

---

# 103. BODY SANITIZATION

Stored inbound HTML must be sanitized before rendering.

Do NOT render arbitrary email HTML directly into application DOM.

---

# 104. REMOTE EMAIL CONTENT

Do not automatically load arbitrary remote images from inbound messages.

Prefer:

```text
plain text
or
sanitized HTML
```

---

# 105. ATTACHMENT SECURITY

Phase 4 only needs the existing LeadEngine PDF as outbound attachment.

Do NOT implement arbitrary inbound attachment download/execution.

You may show:

```text
Attachment received
```

metadata without processing unknown files.

---

# 106. EMAIL CREDENTIAL LOGGING

Never log:

```text
SMTP password

IMAP password

Gmail refresh token

OAuth access token

email body containing secrets

session cookie
```

---

# 107. EMAIL SECRET HEALTH

System Health can show:

```text
Email provider
READY

SMTP
READY

IMAP
READY

Last inbox sync
2 minutes ago
```

Never expose credentials.

---

# 108. SYSTEM HEALTH

Add:

```text
Email Sending

Inbox Sync

Reply Detection
```

health items.

---

# 109. WORKER ARCHITECTURE

Do not create another large infrastructure platform unnecessarily.

For this private app:

```text
bounded scheduled sync
```

is sufficient.

Reuse existing API/worker architecture where appropriate.

---

# 110. EMAIL POLLING

A small scheduled job/process may:

```text
sync connected mailboxes
find relevant replies
persist messages
create activities
```

Must be:

```text
idempotent
bounded
retry-safe
```

---

# 111. MESSAGE DEDUPLICATION

Use:

```text
provider message ID
+
account ID
```

as strong uniqueness.

Do not duplicate messages after every sync.

---

# 112. THREAD DEDUPLICATION

Same applies to threads.

Repeated sync must produce identical persisted state.

---

# 113. UI DESIGN

Use the existing Phase 3.5/3.6 design language.

Do NOT redesign the whole application.

Outreach page should look:

```text
premium
minimal
information dense
calm
professional
```

---

# 114. OUTREACH ROW

Recommended columns:

```text
Business

Opportunity

Commercial Fit

Contact

Status

Last Contact

Next Follow-up

Report

Email
```

Do NOT reintroduce unnecessary Assigned columns if assignment can be shown compactly elsewhere.

---

# 115. BUSINESS CELL

Continue existing pattern:

```text
Business name
website
phone
email
social icons
```

---

# 116. EMAIL BUTTON

If public email exists:

```text
Compose
```

If missing:

```text
No public email
```

Do not display a disabled mystery icon.

---

# 117. RESPONSIVENESS

Test:

```text
1366×768
1440×900
1920×1080
390×844
```

Outreach is primarily desktop but must remain usable on mobile.

---

# 118. ACCESSIBILITY

All controls:

```text
keyboard accessible
visible focus
semantic labels
screen reader friendly
```

Composer/dialog:

```text
ESC
focus management
accessible errors
```

---

# 119. TESTS — SALES WORKSPACE

Test:

```text
status migration

all status changes

activity creation

follow-up creation

follow-up reschedule

follow-up complete

overdue calculation

lists

list membership

saved views

bulk status

bulk lists

bulk follow-up

do-not-contact suppression

rediscovery does not reset suppression
```

---

# 120. TESTS — EMAIL

Test:

```text
provider abstraction

SMTP send

send failure

header injection rejection

duplicate-send protection

IMAP sync

message dedup

thread dedup

reply detection

wrong-thread rejection

status update on reply

no downgrade of MEETING/PROPOSAL/etc.

PDF attachment

DO_NOT_CONTACT blocking

email HTML sanitization
```

---

# 121. TEST SMTP / IMAP

Do not depend exclusively on real external email services for unit tests.

Use deterministic mocks/fixtures/local test servers where appropriate.

Then perform one controlled real provider acceptance.

---

# 122. BROWSER E2E

At minimum:

```text
open Outreach

move lead to Ready to Contact

schedule follow-up

open saved view

create list

add lead to list

compose email

attach PDF

send in test mode

see sent activity

receive controlled reply

sync

see reply

status becomes Replied

mark Do Not Contact

verify composer disabled
```

---

# 123. EMAIL VISUAL QA

Inspect:

```text
email account settings

composer empty

composer populated

PDF attachment

sending

send failed

sent

reply thread

long subjects

long emails

multiple replies
```

---

# 124. SALES VISUAL QA

Inspect:

```text
Ready to Contact

Follow up today

Overdue

Waiting

Replied

Meeting

Proposal

Won

Lost

Do Not Contact
```

---

# 125. CURRENT DATA QA

Use multiple leads from BOTH existing completed scans.

Do not test Phase 4 entirely on one manually fabricated prospect.

---

# 126. NO REAL PROSPECT OUTREACH DURING AUTOMATED QA

Never send to a real discovered client during tests.

All provider tests must use controlled PlaneByte/test addresses.

---

# 127. ENVIRONMENT

Document additions.

Example:

```text
# Email
EMAIL_PROVIDER=hostinger

EMAIL_SEND_MODE=test
EMAIL_TEST_RECIPIENT=

MAIL_FROM_NAME=PlaneByte
MAIL_FROM_ADDRESS=

MAIL_SMTP_HOST=
MAIL_SMTP_PORT=
MAIL_SMTP_SECURE=true

MAIL_IMAP_HOST=
MAIL_IMAP_PORT=
MAIL_IMAP_SECURE=true

MAIL_USERNAME=
MAIL_PASSWORD=

EMAIL_SYNC_ENABLED=true
EMAIL_SYNC_INTERVAL_MINUTES=10
EMAIL_INITIAL_SYNC_DAYS=30

MAX_EMAILS_PER_HOUR=20
MAX_EMAILS_PER_DAY=100

# Gmail optional
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REDIRECT_URI=

# Follow-up
DEFAULT_FOLLOWUP_DAYS=3
```

Actual naming should match repository conventions.

---

# 128. HOSTINGER DOCUMENTATION

Create:

```text
docs/HOSTINGER_EMAIL_SETUP.md
```

Include:

```text
where to find SMTP/IMAP settings

required mailbox address

how to configure secrets

connection test

SPF

DKIM

DMARC

test mode

production send mode
```

Do not include actual password.

---

# 129. GMAIL DOCUMENTATION

Create:

```text
docs/GMAIL_INTEGRATION.md
```

Document:

```text
OAuth client

redirect URI

required scopes

why each scope exists

test users

token storage

disconnect/revoke process
```

---

# 130. PHASE 4 REPORT

Create:

```text
docs/PHASE_4_REPORT.md
```

Include:

```text
architecture

schema changes

sales workflow

follow-up system

lists

saved views

suppression behavior

email architecture

Hostinger integration

Gmail integration status

reply detection

security controls

data preservation

tests

visual QA

production acceptance

known limitations
```

---

# 131. PHASE 4 ACCEPTANCE CHECKLIST

Do NOT mark Phase 4 complete until:

```text
[ ] Existing two campaigns remain intact

[ ] Existing current leads remain intact

[ ] No unnecessary new discovery scans were performed

[ ] Outreach page implemented

[ ] Expanded statuses implemented

[ ] Status migration safe

[ ] Activity timeline implemented

[ ] Follow-ups implemented

[ ] Follow-up today works

[ ] Overdue works

[ ] Lists implemented

[ ] Saved views implemented

[ ] Bulk actions implemented

[ ] Do Not Contact suppression implemented

[ ] Rediscovery preserves suppression

[ ] Lead Detail sales workflow updated

[ ] Hostinger email provider implemented

[ ] SMTP send works

[ ] IMAP sync works

[ ] Email account settings works

[ ] Email composer works

[ ] Templates work

[ ] Template variables work

[ ] Existing client PDF attaches

[ ] Message storage works

[ ] Thread storage works

[ ] Reply detection works

[ ] Reply timeline works

[ ] Reliable reply updates status appropriately

[ ] Duplicate sends prevented

[ ] Duplicate sync prevented

[ ] DO_NOT_CONTACT blocks composer

[ ] Gmail provider implemented or clearly documented as optional

[ ] No real prospect contacted during automated QA

[ ] Email secrets protected

[ ] Security tests pass

[ ] Existing discovery/scoring/report features pass regression

[ ] TypeScript strict passes

[ ] ESLint passes

[ ] Python tests pass

[ ] Browser tests pass

[ ] Production build passes

[ ] Production Hostinger controlled send/reply acceptance passes
```

---

# 132. IMPLEMENTATION ORDER

Follow:

```text
1. Inspect current production/schema state

2. Record phase4-before counts

3. Run complete regression baseline

4. Design migration

5. Add activity model

6. Expand sales statuses

7. Implement follow-ups

8. Implement lists

9. Implement saved views

10. Implement suppression

11. Build Outreach page

12. Update Lead Detail

13. Implement bulk actions

14. Create EmailProvider abstraction

15. Implement Hostinger SMTP provider

16. Implement Hostinger IMAP sync

17. Implement secure email account configuration

18. Implement templates

19. Build composer

20. Attach existing client PDFs

21. Persist sent messages/threads

22. Implement reply detection

23. Implement Gmail provider

24. System health additions

25. Security pass

26. Automated tests

27. Visual QA

28. Controlled Hostinger send/reply acceptance

29. Compare production data counts

30. Deploy

31. Production UI smoke test

32. Write Phase 4 report
```

---

# 133. WHAT NOT TO BUILD

Do NOT add:

```text
public signup

billing

Stripe

multi-tenant SaaS

AI email generation

automated bulk campaigns

email sequencing engine

tracking pixels

link tracking

SMS

WhatsApp

social DMs

HubSpot

Salesforce

Slack

calendar integration

AI marketing

new lead-scanning systems

conversion-learning models

complex analytics dashboards
```

These are outside the private LeadEngine requirement.

---

# 134. FINAL PRODUCT PRINCIPLE

At the end of Phase 4, LeadEngine should give PlaneByte one private workflow:

```text
FIND

LeadEngine discovers a business.

↓


UNDERSTAND

Website
SEO
Security
Social
Commercial Fit
Client PDF

↓


PRIORITIZE

Lists
Saved Views
Sales Status

↓


CONTACT

Professional PlaneByte email
Client PDF attached

↓


FOLLOW UP

Follow-up date
Outreach queue

↓


RESPOND

Reply automatically detected

↓


CLOSE

Meeting
Proposal
Won / Lost
```

That is enough.

Do not turn this final phase into another large platform rewrite.

Use the EXISTING real production leads from the two completed scans.

Preserve the accepted scanning engine.

Make the sales workflow exceptionally good.

START WITH CURRENT PRODUCTION DATA INSPECTION AND REGRESSION BASELINE.