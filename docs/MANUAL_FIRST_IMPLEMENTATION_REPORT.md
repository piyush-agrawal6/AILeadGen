# Manual-first workflow and client content release

Deployed for owner review on 2026-11-01. No production scan/email run was started. The automation upgrade is not marked complete while owner inspection is pending.

## Product

Navigation is Dashboard, Leads, Campaigns, Outreach, Schedules, Reports and Settings. System Health is in Settings. `/master-leads` redirects to `/leads`, `/automation` to `/schedules`, `/scans` to `/campaigns`, `/scans/new` to `/find-leads`, and `/system` to `/settings/system`. Existing scan/campaign detail routes remain available for history.

The Find Leads wizard reviews qualified target, markets/rotation, verticals, business size, fit and opportunities before invoking the existing scan executor. Saved scan defaults are available under Settings. Manual run pages show live stages, child scans, emerging leads, counters and pause/resume/stop. They preserve shortfalls rather than weakening qualification.

The email wizard selects eligible qualified leads with filters, requested count, hourly/daily limits, spacing and send window. Each item prepares a real client report and an exact HTML/plain-text preview. Content can be edited before sending. PDF view/download/regeneration and message details expose recipient, sender, body, report, SMTP result, IDs, thread and engagement timeline. Replies and manual contact retain the existing CRM/conversation capabilities.

Explicit schedules support scan, outreach and combined workflows; once/daily/weekdays/weekly/numeric cron, timezone, enable/disable, pause, edit, duplicate, delete confirmation, Run Now and history. Schedule claims are durable and unique per due occurrence. Overlapping active work is not launched again. Existing inbox/tick worker infrastructure dispatches database schedules and advances explicit runs; no per-schedule GCP jobs were created. Capability flags alone do not launch scans or outreach. Inbox sync remains independently enabled.

## Client content

Four deterministic first-contact variants: website/redesign, SEO/visibility, technical trust and combined. Personalisation uses stored company/industry/location and deduplicated observations, business consequences, approved services, conditional included value and a reply CTA. The Homestay body is 153 words before the opt-out footer. The company signature is PlaneByte / Software Engineering · SEO · Security / website / configured contact email. The opt-out footer is subtle and retains the same token mechanism and headers.

The normal PDF generator now produces an eight-page opportunity brief, findings, business impact, transformation plan, PlaneByte approach, included value, roadmap and next step. It keeps the dark/orange identity, omits unknown score cards and shows only recorded measurements. Findings have one primary explanation, with cross-references elsewhere. Services come from approved report-brand configuration; the existing offer gates inclusions. No monetary values, traffic/ranking/revenue claims or security incidents were invented.

First-contact quality checks require company, real findings, business impact, solution, reply CTA, approved signature and a valid current PDF. Reports with fewer than two meaningful distinct findings, unresolved placeholders, missing services/CTA, dominant missing measurements or failed generation cannot enter a real automatic send. Workflow items route to Needs Review. Follow-ups/replies retain their existing reviewed communication path.

The SMTP/IMAP provider, reply matching, bounce handling, tracking routes, suppression, quotas, spacing, durable reservation and uncertain-send recovery remain the existing architecture. Final HTML/text is persisted and deterministic preview capabilities are registered only when the existing send reservation is made. Preview frames are sandboxed and block external images so opening a dashboard preview does not create an email-open signal.

## Database/API

Exactly one required additive migration: schema 9 to 10. Added workflow_runs, outreach_run_items, automation_schedules and automation_schedule_runs; added rendered_html/rendered_text to email_messages. Existing data, schema history and configuration were preserved. The migration verified original-row hashes across all 50 pre-existing tables. No reset or unnecessary migration replay occurred. Evidence: manual-first-migration.json.

New authenticated `/api/workflow` APIs expose runs, eligibility/preparation, progress/actions, item editing/cancellation/review, schedules/history, saved defaults, safety limits and message inspection. They delegate execution to the existing pipeline and reviewed mail service. No secrets are returned to the frontend.

## Validation

- 297 backend unit tests passed; one opt-in live test skipped in the general suite.
- Seven real PostgreSQL integration cases passed across the initial run and isolated reruns. The changed queue test now uses an explicit reviewed run. The new schema/dispatcher test was rerun alone after a parallel global migration-lock timeout.
- 41 frontend unit tests, strict type checking and production builds passed. ESLint has only the pre-existing unused-variable warning in scripts/phase41-sync.mjs.
- Five focused browser acceptance cases passed: navigation/legacy redirects, manual scan plan/start, exact email/PDF/edit preview, scan/outreach/combined schedule forms, desktop/mobile overflow. Older browser specifications describe the retired navigation and should not be treated as validation of the redesigned UI; the focused suite is the release evidence.
- Production signed smoke passed for dashboard, runs, schedules, defaults, safety, message history, leads, pause controls and composer. Gmail SMTP/IMAP health both READY. These checks started zero scans, email runs or schedules.
- Every page of the exact regenerated Homestay PDF was visually reviewed before the controlled send.

## Deployment/state

Live UI: https://leads.planebyte.com. API revision: leadengine-api-00025-xnh. API/worker images and preserved secret references: MANUAL_FIRST_DEPLOYMENT_STATE.json. Frontend deployment: https://leadengine-gmyy0qo4k-piyushagrawal6s-projects.vercel.app.

AUTO_SCAN_ENABLED=false, AUTO_EMAIL_ENABLED=false, EMAIL_SENDING_ENABLED=false. Database acquisition/outreach pauses remain set; acquisition/outreach Scheduler jobs remain PAUSED. Five-minute inbox sync is ENABLED. No enabled user schedule was silently created. Infrastructure capability/owner approval guards remain required before real sending; normal manual and scheduling controls are in the frontend.

The redesigned Homestay email was sent exactly once only to agrawaljoy1@gmail.com through the normal service with the private owner-controlled envelope redirect. It is marked OWNER_CONTROLLED_REDIRECT/test_mode in persistent history and does not advance genuine prospect contact state. Final SMTP/Sent/PDF/tracking evidence and the full body are in redesign-owner-acceptance.json. Stop for owner inspection; no real prospect run or activation is authorized by this release.
