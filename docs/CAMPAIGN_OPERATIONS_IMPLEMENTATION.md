# Campaign operations upgrade

Deployment evidence is recorded in `CAMPAIGN_OPERATIONS_DEPLOYMENT_STATE.json`; acceptance results are recorded separately in `campaign-operations-test-evidence.json` and `campaign-operations-production-smoke.json`.

## Workspace

- Dashboard: compact operating metrics, needs-attention links, current work, upcoming schedules, recent campaigns/leads and activity.
- Leads: dense paginated workspace, sort/search/filter controls, built-in and editable saved views, bulk sales/assignment/list/follow-up/manual/DNC/export actions, inline state changes and a detail drawer with evidence, notes, report generation and existing sales/thread tools.
- Campaigns: permanent historical scans, market/vertical/date/status/search filtering and pagination; eligibility/accounting, progress, scan history, outreach runs and reports in a drawer. Run Emails preselects its campaign. Historical workflow-linked records are protected from destructive deletion.
- Outreach: Messages, Email Runs, Replies and Manual Contact tabs; campaign/pitch/status/date/sender/engagement filters, unread/awaiting/closed reply queues, exact body/PDF inspection and delivery/engagement timelines. Campaign filters are searchable and paginated. Replies inherit campaign and actual pitch metadata from the original outbound thread without changing reply matching. Owner-controlled historical deliveries remain visibly labeled.
- Schedules: compact searchable/filterable table, configuration/history drawers, grouped create/edit form, existing actions retained. Combined scans default to no email; all-eligible delegation is explicit.
- Reports: paginated/filterable client versions, export runs and generated-file inventory; PDF preview, download, regeneration and source links.
- Settings: shared section navigation, clearer existing configuration panels, grouped system health and a searchable paginated market editor.

## Campaign audience contract

`app/workflows/campaigns.py` is the single audience and accounting implementation. Manual Outreach, campaign actions, scheduled delegation and the final pre-SMTP check share it. Every run requires a campaign. The arbitrary email count is rejected by the API and absent from forms.

All qualified canonical leads from the selected campaign receive a disposition: ready, reserved elsewhere, previously contacted, replied, manual contact, needs review or suppressed. No global selection cap or daily-limit truncation applies to audience membership. An open review page continues bounded preparation batches without starting delivery; preparation does not depend on an enabled outreach scheduler. A 110-lead fixture accounts for all 110 and prepares 107 eligible recipients even with a 20/day cap.

Actual pitch families require at least two meaningful stored findings and a stored score of at least 40. Selected unsupported families are removed; no supported selection routes to Needs Review. Generated email and PDF snapshots are scoped to those actual families and bound into the reviewed message token.

Default mode excludes previous real contact conservatively across campaigns. Re-contact requires explicit confirmation and still excludes DNC, unsubscribe, rejection/closed sales, hard bounce, uncertain delivery and active conversations. Controlled redirected messages do not become real-contact history. Provider failure, restart recovery, idempotency, spacing, hourly/day limits and recipient-local windows stay in the existing engines.

## Schema 11

One additive campaign foreign key/index links existing workflow runs. Historical orphan scans are assigned deterministic entries in the existing campaign table; lead identities, observations, reports, messages and tracking records are preserved. Legacy count-bounded schedules retain their rows and bounded intent audit value, become `email_all_eligible=false` / `needs_owner_review=true`, and cannot run until edited. Old run configuration remains available as history; old bounded runs cannot be silently broadened.

`scripts/campaign_operations_migrate.py` creates a private binary-COPY rollback archive, verifies its hashes, applies only migration 11 and checks original row preservation with explicit allowances for campaign linkage and conservative legacy configuration conversion. It requires all automation flags false, operator pauses and no active scans/report jobs. It refuses unnecessary migration reruns.

## Safety

No discovered prospect send, controlled acceptance email or live scan is part of this upgrade. Browser scans use the existing explicit offline fixture mode only. Production review must retain all three false flags and acquisition/outreach pauses. Gmail credentials, account configuration, tracking/reply/bounce architecture, secret references and security controls remain unchanged.

## Verified review release — 2026-11-01

- Live review: https://leads.planebyte.com (frontend deployment `leadengine-fsi4dmi4k-piyushagrawal6s-projects.vercel.app`).
- API revision `leadengine-api-00029-9gh`, schema 11; exactly one migration applied. A verified private schema-10 rollback archive was created first, and preservation checks passed for all 51 checked tables.
- Backend unit tests: 310 passed, 1 skipped. Frontend unit tests: 41 passed. Browser checks: 16 passed, covering all seven pages at 1440/1024/390 widths, panel bounds, campaign selection, batching without sending, filters, pagination, saved-view CRUD and lead/message/report/schedule drawers.
- Real PostgreSQL regression: 8 passing checks plus 2 focused preservation/read-model checks. Parameterized saved-view and thread-inheritance queries also verified read-only against PostgreSQL. Both API/worker image builds passed; the API image ran the full container regression suite.
- Production signed smoke checks passed for the operational endpoints, every campaign’s qualification/accounting invariant, required campaign validation and removal of arbitrary email-count input. Published pages retain authentication and `nosniff` protection. TypeScript and production build pass; lint has no errors and one existing unused-variable warning in `dashboard/scripts/phase41-sync.mjs`.
- Both runtimes retain `AUTO_SCAN_ENABLED=false`, `AUTO_EMAIL_ENABLED=false`, `EMAIL_SENDING_ENABLED=false`, existing environment values and secret references. Acquisition/outreach Cloud Schedulers and database pauses remain paused. Existing inbox sync remains enabled every five minutes.
- No production email, live scan or user schedule was started. This release is for owner review and does not approve or activate real outreach.

Historical messages without a recoverable workflow or report source retain an explicit individual/legacy label; no campaign attribution is invented. Full machine-readable evidence lives in the deployment, migration, smoke, frontend and test-evidence JSON files beside this report.


## Subsequent owner-authorized activation

The owner explicitly approved “Yes—activate this one-time campaign” for a United States hospitality campaign targeting 10 qualified leads. Live capability flags and existing production send-mode gates are now enabled on both runtimes and synchronized to the existing root `.env`; Gmail secret references and unrelated configuration were preserved. Acquisition/outreach dispatchers are resumed, with exactly one enabled, once-only user schedule. Limits: 5/hour, 10/day, 12-minute spacing, weekdays 09:00–17:00 recipient-local time. Automatic outreach is restricted to eligible qualified leads in this campaign and existing content/PDF gates. Actual execution and authorization: `owner-us-hospitality-10.json`. This subsequent authorization supersedes the review-release paused state recorded above.
