# Intent Radar Action Center, destinations and Cloudflare release

**Decision: NO-GO for promotion.** Feature branch `feature/radar-actions-integrations-20261121`, based on the independently verified live `a21ec493d64c1116569ea663327e9cae6f88accc`. Previous production release remains live (API `leadengine-api-00208-vox`, worker 97, schema 1012). The owner grant, expiry and historical trials were not changed.

## Architecture and evidence

- Next.js uses the signed account broker to reach FastAPI. Workspace membership, the effective Radar entitlement and provider management permissions are checked server-side. Browser fixtures are not external acceptance.
- Integrations now groups compact connection rows by server-reported availability and Sheets health. Search and a labeled category filter replace decorative capability chips and disabled buttons. The HubSpot detail page only exposes connect when configured and enabled for the managing workspace. CRM OAuth uses the registered callback, server-side exchange and introspection, encrypted envelopes, hashed expiring workspace/actor state, refresh leases and revision checks. Portal ID, client ID, active token, app ID `62975250` and scopes must agree. Local disconnect removes credential authority; portal uninstall is separate.
- Existing HubSpot project has `oauth`, `crm.objects.contacts.read/write`, `crm.objects.companies.read/write`, `crm.objects.deals.read/write` (each read and write is a distinct scope). No CLI upload or additional scope grant claimed. Bounded exact-identifier matching and deal pipelines have read endpoints. Multi-step writes and synchronization are not qualified. Marketplace distribution in the manifest is not evidence of certification or approved public installation.
- Billing investigation: production had a completed Starter trial checkout, canceled production contract, current development grant, and a **separate paid Growth checkout**. The existing checkout independently returned `pending` in production with matching request/workspace. Do not label it an unpaid Starter renewal or erase it. The candidate overview reads period and charge information from the effective grant, keeps paid checkout separate and removes the expired-contract controls for complimentary users. Further plan-tab recovery acceptance remains required.
- `GET /api/intent-radar/actions`, `POST /actions/followups`, `POST /actions/{id}/approve|cancel|complete` (same prefix): feature-gated internal task review, transactional approval and insertion, workspace/assignee validation, source recheck, digest and request deduplication, scoped paging, audit and manual outcomes. Entry from the opportunity detail; the UI distinguishes a completed task from a provider-confirmed deal. No background job is needed for an atomic internal task. No source text is copied automatically into the task.
- Additive migrations 1013 (actions and follow-ups), 1014 (CRM connections and OAuth state); previous schema fingerprints retained. On an isolated restore of the last cutover archive, 1010→1013 verified structure, repeat zero and unchanged 138 prior table multisets. 1013→1014 verified structure and repeat zero. Production was not migrated. A fresh 1012 backup/restore, compatible bridge images and original release source guard remain required before cutover.
- Sheets retains `https://www.googleapis.com/auth/spreadsheets` under the existing workspace pilot gate. Writes use RAW mode, reviewed exact range and selection digest. Candidate now requires an independent bounded GET with matching cells before COMPLETED. A divergent read-back remains UNCERTAIN. Google recommends `drive.file` for per-file access; a pasted spreadsheet ID does not grant it. Switching requires an actual Picker integration, enabled APIs and renewed grants. No silent scope substitution.
- Baseline file downloads remain synchronous and bounded; historical exports are not migrated. Webhook HMAC, retry, endpoint restrictions and paused dispatcher remain baseline capabilities; no new provider-write action is implied.

## Cloudflare and configuration

Read-only DNS checks observed both named Cloudflare nameservers and a parent DS record (algorithm 13); this alone is not full DNSSEC-chain validation. The marketing project located under `planebyte-website-new` in the main checkout has its own Netlify configuration. No DNS, WAF, proxy, paid service, hosting or certificate changes were made.

| Variable | Visibility / intended destination | Evidence and gate |
|---|---|---|
| `R2_ACCOUNT_ID`, `R2_ENDPOINT`, `R2_REGION`, `R2_BUCKET` | Server-side, report API/worker | Local reports bucket and official account endpoint validated. `R2_BUCKET` is `planebyte-reports-prod`. |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | Secret, report API/worker | Local S3 signatures worked for HEAD/PUT/GET/DELETE. Existing API uses secret references for legacy storage. Do not print or ship in Next. |
| `R2_BUCKET_NAME` | Server-side legacy artifacts | Existing legacy binding differs from reports bucket locally. Do **not** replace it: historical downloads must continue resolving their original store. A separate report binding/metadata dispatch is still needed. |
| `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, `TURNSTILE_ENFORCED` | Public site key; verification secret and rollout flag Vercel server only | Existing local keys present. Signup and password-recovery forms supported; bounded server action Siteverify checks action and `app.planebyte.com`. Flag off pending end-to-end challenge validation and deployment. Existing OAuth unaffected. |
| `CLOUDFLARE_WEB_ANALYTICS_WEBSITE_TOKEN`, `CLOUDFLARE_WEB_ANALYTICS_APP_TOKEN` | Separate browser-safe tokens, Netlify/Vercel respectively | Both local tokens present. Snippets and provider receipt verification outstanding. A public token is not permission to collect private SPA paths. |
| `RADAR_HUBSPOT_CLIENT_ID`, `RADAR_HUBSPOT_CLIENT_SECRET`, `RADAR_HUBSPOT_REDIRECT_URI` | API/worker only; secret via secret manager | Local values present; candidate not bound in production. Require new revision for bindings. |
| `RADAR_HUBSPOT_ENABLED`, `RADAR_HUBSPOT_WORKSPACES`, `RADAR_ACTIONS_ENABLED` | Server feature controls | Disabled by default; no authorized pilot passed CRM acceptance yet. |

R2 smoke (`scripts/check_r2_report_bucket.py`): signed bucket HEAD, conditionally created unique `integration-tests/` object, metadata check, independent checksum read, exact-key deletion and confirmed 404. No customer object listed or used. No request to staging; least-privilege policy outside this bucket was not independently inspected. Root `.env` ignored, zero commits touching that exact root path in reachable history. A literal scan of 1,992 tracked files and 88 prior browser assets found no matches for the four inspected sensitive credential values. This is not a full historical secret audit. New account/analytics config requires deployment, not merely a local env edit. No new service added; ordinary R2 request/storage usage applies.

## Status matrix

`Baseline` refers only to features already deployed at `a21ec49`. Unmarked provider checks have **not** been performed.

| Feature | Implemented | Local test | Real provider | Deployed / live verified | Available | Remaining gate |
|---|---|---|---|---|---|---|
| Integrations UI | Yes | Filter tests, five viewport captures | N/A | No / no | No | Final regression and release |
| Billing UI | Partial | TypeScript, baseline journeys | Paid Growth checkout read | No / no | Baseline only | Plans/history and owner visual acceptance |
| HubSpot OAuth | Candidate | Isolated state, cross-workspace, replay, encrypted storage, disconnect | No | No / no | No | Operator consent, refresh and revoke acceptance |
| HubSpot contacts and companies | Exact lookup backend only | Incomplete | No | No / no | No | Mapping, approved writes and read-back |
| HubSpot deals | Exact lookup and pipeline reads only | Incomplete | No | No / no | No | Approved writes, association, stage/outcome |
| HubSpot notes/tasks | No | No | No | No / no | No | Adapter and acceptance |
| CRM synchronization | No | No | No | No / no | No | Durable reconcile and conflict handling |
| Google Sheets OAuth | Baseline | Simulated consent | No new live consent | Baseline / no | Pilot restricted | Consenting test account |
| Sheets write/read-back | Candidate enhanced | PUT then GET, mismatch, idempotency | No live worksheet | Receipt-only baseline / no | Pilot restricted | Disposable sheet and independent live acceptance |
| CSV/XLSX/PDF/JSON exports | Baseline | Existing selection/serialization and browser download | N/A | Baseline / no new live file | Eligible workspace | Additional action datasets |
| Radar webhooks | Existing outbox | Baseline tests | Prior controlled receiver | Baseline / dispatcher paused | Restricted | Approved endpoint, reviewed manual action |
| Action Center queue | Candidate internal workflow | Service tests | N/A | No / no | No | UX and full regression |
| Action suggestions | Existing assistant only | Not integrated | No | No / no | No | Reviewed brief/composer integration |
| Approval/execution | Internal follow-ups only | Digest/idempotency, stale/foreign denial | No external writes | No / no | No | External adapters and partial-failure reconciliation |
| Internal follow-ups | Candidate | Assignee, approval, completion | N/A | No / no | No | Release |
| Outcome tracking | Manual follow-up outcome | Persistence and isolation | No CRM outcomes | No / no | No | Provider reconciliation |
| Gmail action | No new action | No | No new acceptance | Baseline only | No Action Center sending | Approved draft workflow |
| Workspace security | Existing plus candidate checks | Selected suites | Not an external-provider isolation test | Baseline only | Existing controls | Full provider matrix |
| R2 | Existing storage plus verification | Storage/report tests | **PASS** synthetic production bucket | Candidate not deployed | Existing private downloads only | Address distinct legacy/report bindings and lifecycle |
| Turnstile | Signup/recovery candidate | Six offline validation cases | No real challenge | No / no | Off | Joint frontend/server smoke |
| Marketing and SaaS analytics | No new snippets | No | No | No / no | No | Privacy-safe installation, CSP and independent beacon receipts |

## Acceptance and rollback

**Hosted result for the current feature candidate:** [Actions 44883812473](https://github.com/piyush-agrawal6/AILeadGen/actions/runs/44883812473) completed successfully for `258a9a130c48365760a7efb386931b1b98f69668`. `verify` passed; `production-source` was skipped on the feature branch. No promotion was performed. External CRM execution and live provider acceptance remain open as detailed in the status matrix.

**Local backend regression for `258a9a130c48365760a7efb386931b1b98f69668`: 1,326 passed, 2 skipped, 6 warnings** in 570.74 seconds. `RUN_POSTGRES_TESTS=1 .venv/bin/python -m pytest -q --tb=short` ran with PostgreSQL 18 clients and a disposable local server. This result includes PostgreSQL integration tests and is separate from live provider acceptance.

**Hosted feature-branch evidence:** [Actions 44883481171](https://github.com/piyush-agrawal6/AILeadGen/actions/runs/44883481171) completed successfully for `551c7008695e2ee63ef4358ba636c28ed6465f56`. `verify` passed; `production-source` was skipped on the feature branch. This result applies to the earlier CRM-vault commit, not to the later report-routing and billing changes at `258a9a1`.

**Local release matrix for `258a9a130c48365760a7efb386931b1b98f69668`: 48 passed, 0 failed.** `bash scripts/verify_browser_matrix.sh` compiled Next build `es5g1W_eayeWAB481MYPq` and ran all six suites on it: legacy 29, accounts 1, workspace 11, subscription 1, onboarding 2, destinations 4. This includes the follow-up approval/completion journey and responsive Integrations checks. External providers in these browser fixtures are simulated; the R2 production-bucket smoke above is separate evidence.

**Follow-up implementation:** new generated client PDFs can opt into `REPORTS_R2_NEW_WRITES` using the existing report row's immutable server-generated key `workspaces/{workspace_id}/reports/{report_id}/report.pdf`. `R2_BUCKET=planebyte-reports-prod` and separately bound `REPORTS_R2_ACCESS_KEY_ID` / `REPORTS_R2_SECRET_ACCESS_KEY` must reference the existing authorized pair on both API and worker. Older records continue using the legacy binding. Switching new writes off does not disable reads of already routed PDFs. Any rollback image must retain this reader once new keys exist. Do not enable legacy report generation to exercise this option. No new production binding was made. Billing summary GET no longer exposes cached resume links: the owner must request a provider refresh and the pending checkout, customer, terms, trial eligibility and original creator must still match. A local test-only underqualified signal correctly received 409 on promotion; the browser journey now asserts that denial, explicitly qualifies the signal, then approves/executes/completes the follow-up. The affected journey passed (11.3 s). Storage/client-report, cloud-health and subscription suites: **40 passed**. TypeScript and **296 frontend unit tests** passed.

`pytest tests/unit/test_storage.py tests/unit/test_client_reports.py`: 16 passed. `pytest` for Radar Sheets/consolidated/billing recovery: 9 passed. Initial hosted failure was the older PostgreSQL Google fixture returning only `updatedCells` to a GET; corrected fixture keeps the asserted cell data, and the affected PostgreSQL test passed locally. `test_hubspot_workspace`, `test_customer_integrations`, `test_radar_action_center`: 10 passed. On `0d08ee1` the isolated browser matrix passed **47/47**, with Integrations captures at 1440, 1024, 768, 390 and 320. Desktop/mobile captures were inspected; narrow-header clipping drove a subsequent search-trigger fix. These runs do not qualify later source changes.

Before production: record green full matrix at the exact integration SHA, qualify compatible rollback API/worker on migrated schema, preserve existing provider refs, fresh backup/restore, zero-traffic stage and protected source guard. Roll back only images and alias after schema compatibility proof; leave provider data/history and private objects intact. Turnstile rollback disables its explicit rollout flag while retaining existing auth controls. Keep public Sheets/webhook expansion gated. No restoration of DNS records is part of rollback.

Owner interactions still needed **when a compatible restricted callback is serving**: consent in the disposable HubSpot test portal for app 62975250; consent with the approved Google test account and select a disposable worksheet and exact range. Do not submit secrets, tokens, authorization codes or production customer data. No owner payment or grant extension is needed.

References: [HubSpot OAuth](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/oauth/oauth-quickstart-guide), [HubSpot introspection](https://developers.hubspot.com/docs/api-reference/legacy/authentication/manage-oauth-tokens), [Google scopes](https://developers.google.com/workspace/sheets/api/scopes), [Cloudflare R2 credentials](https://developers.cloudflare.com/r2/api/tokens/), [Turnstile validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/), [Web Analytics SPA tracking](https://developers.cloudflare.com/web-analytics/get-started/web-analytics-spa/).
