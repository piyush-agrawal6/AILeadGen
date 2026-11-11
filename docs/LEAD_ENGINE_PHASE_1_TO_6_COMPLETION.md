# Lead Engine Phase 1–6 completion tracker

Authoritative implementation tracker for the 2026-11-06 owner directive. The starting local baseline is schema 28: 624 backend passes (22 PostgreSQL), 89 frontend units, 41 browsers, types/build passing. Those results cover existing code, not the roadmap. Production, root environment/OAuth settings, customer data and real outreach remain unchanged.

Statuses: **Complete and tested**, **Implemented, integration testing pending**, **Partially implemented**, **Blocked by external credentials/approval**, **Not implemented**. No phase is complete until its customer workflow and acceptance criteria pass. Existing independent customer integration flags remain disabled by default; public signup remains blocked.

| Feature | Phase | Current implementation status | Backend / database | Frontend | Tests / integration / remaining issues |
|---|---|---|---|---|---|
| Structured multi-country geography and existing sources | 1 | Partially implemented | `app/config/locations.py`, `app/discovery/`, `app/workflows/service.py` | Find Leads, location selector | Owned runs exist; custom filters, category coverage, broader industries and measured initial-result latency incomplete |
| Natural-language reviewed discovery | 1 | Partially implemented | `app/acquisition/ai.py`, `search_plan.py`, worker | AI acquisition | Existing Vertex gateway; custom industries/schema and unsupported-filter handling incomplete; live acceptance pending |
| Progressive source/results and recovery | 1 | Partially implemented | `app/discovery/resolver.py`, `app/pipeline/runner.py`, `app/prospecting/intake.py` | Discovery/run progress | Company enrichment commits progressively; first source now commits companies before the next provider/crawl; per-source resume checkpoints tested; broader live coverage acceptance remains pending |
| Saved searches / duplicate / history | 1 | Complete and tested locally | `app/prospecting/searches.py`, migration 29, `/api/discovery/searches` | Reviewed save/load/update/duplicate/archive in Find Leads | SQLite/PostgreSQL/API/browser checks pass; loading never starts jobs |
| Source budgets / cancel / canonical dedupe | 1 | Partially implemented | Existing executors, source ledgers, context and prospect repositories | Discovery details | Existing tests pass; new source-progress and seven-country fixture acceptance required; live coverage must be labeled honestly |
| Company profiles, evidence and related data | 2 | Partially implemented | `businesses`, `prospects`, source tags, `app/prospecting` | Companies/detail | Lightweight crawling implemented; structured products/services and company/contact relationship workflow incomplete |
| Real professional contacts and decision-makers | 2 | Partially implemented | Reuse `contact_people`, `contacts`; no parallel company/contact model | Contacts list/detail and company-linked editor implemented | Migration 30 extends existing contact_people. Owned CRUD, notes, lists, source evidence, archive and professional discovery jobs implemented; conservative extraction requires explicit public employment relationship; live provider breadth acceptance pending |
| Company/contact enrichment waterfall and bulk jobs | 3 | Partially implemented | `app/acquisition/enrichment.py`, `app/platform/contact_verification.py`, existing safe crawler | On-demand/bulk UI incomplete | Migration 31 adds durable bounded jobs with leases, recovery, cancellation, quotas and owned item histories. Fresh company/contact evidence is reused. SQLite/PostgreSQL and no-email browser workflow pass; additional providers are not activated |
| Verification and field provenance | 3 | Partially implemented | Existing DNS/public evidence and review records | Contacts/detail, Enrichment history/detail, company and bulk actions implemented | Explicit UNKNOWN / INVALID / DOMAIN_VALID / MX_AVAILABLE / UNCERTAIN results; no deliverability claim; source/check timestamps and honest unreported monetary cost shown. Email changes invalidate checks |
| Multiple ICPs, revisions and reviewed AI drafts | 4 | Partially implemented | `app/icp`, `app/platform/ai_usage.py` | ICP builder/assistant | Existing local API/browser checks; configurable per-criterion weights now saved/versioned and browser tested; organization-informed assistant context implemented. Broader live AI acceptance remains pending |
| Explainable company/contact qualification and summaries | 4 | Partially implemented | `app/prospecting/intake.py`, existing Vertex gateway | Company evidence and basic ICP results | Weighted matching, evidence coverage, unknowns, cited exact-quote AI summary jobs and paged recommendations implemented. These do not automatically change qualification or send eligibility. Live AI and full customer acceptance remain pending |
| Workspace-aware assistant and authorized tools | 4–6 | Implemented locally, broader acceptance pending | `app/assistant`, migration 32, existing Vertex gateway + enrichment workers | Private conversations, read results, exact proposals and review/confirm UI | Owned read tools, private-history isolation, bounded AI usage, expiring approved/idempotent actions, disabled-worker/API guards and PostgreSQL tests pass. No send/start-scan tool. Feature stays disabled until configured/approved |
| Lists, tasks, lifecycle, activities, imports/exports | 5 | Partially implemented | `app/sales`, existing lists/activities/followups | Company/outreach collaboration | Migration 33 extends existing lists/followups: paginated company/contact membership, archived lists/history, CSV export and revisioned assigned sales tasks. SQLite/PostgreSQL and real browser list/task lifecycle pass. UI refinements add dialogs, task metadata editing and date/priority views. 2026-11-08 targeted recovery regression passes; CSV refuses incomplete lists and retains formula/tenant safety. Broader customer acceptance remains open |
| Customer-owned mailbox connection/send/sync | 5 | Not implemented | Existing internal Gmail retained; encrypted customer connection foundation exists | Connections foundation | Customer Gmail/OAuth scope lifecycle, independent identity/send/sync and mock/sandbox acceptance needed; never share internal sender |
| Reviewed templates/campaigns/rate limits/engagement | 5 | Partially implemented | `app/workflows`, `app/mail`, tracking/ledger | Campaigns, templates, preview/edit, schedules | Current local regression passes; general customer mailbox routing and complete campaign wizard/analytics acceptance missing |
| Integration framework and Sheets lifecycle | 6 | Partially implemented | `app/integrations`, schema 38 | Connections | Encrypted scoped OAuth/refresh/metadata tested; reviewed import and immutable fixed-range export implemented. Import ten-row acceptance and synthetic Google export browser/worker pass. 2026-11-08 focused schema-38 recovery checks pass, including independent PostgreSQL workers, unavailable evidence and reviewed lease recovery. Historical final regression artifacts recovered; real consent/write acceptance remains pending |
| HubSpot / Pipedrive adapters and sync | 6 | Not implemented | Extend same integration layer | Mapping/sync UI missing | Complete adapter contracts/configuration and isolated tests; live activation requires approved credentials |
| Public versioned API, scoped keys and developer UI | 6 | Implemented and tested locally | Schema 34; hash-only scoped keys, expiry/rotation/revocation, durable limits, idempotent v1 domain APIs and OpenAPI | Gated Developer settings, one-time token display | SQLite/PostgreSQL and actual browser/gateway tests pass; feature remains disabled by default; external rollout pending |
| Signed outgoing webhooks and delivery worker | 6 | Implemented and tested locally | Schema 37; transactional outbox, encrypted signing secrets, bounded existing worker/executor | Owned endpoint controls, one-time secret, delivery history/retries | Tenant/role/disabled guards, HMAC, duplicate reservation, backoff, final-attempt crash recovery, SQLite/PostgreSQL and real UI/API browser checks pass. No live receiver or production schedule acceptance yet |
| Genuine authenticated MCP server/client | 6 | Implemented and tested locally | Official MCP SDK 2.3.0, stateless Streamable HTTP; schema 35 expiring manual approvals; shared domain tools | Developer setup and exact proposal approval UI | Official SDK client and real Next gateway browser round trip pass; scopes, revocation, Host/Origin, tenant and denied-call audit tested. Production backend host allowlist/configuration still requires approved activation |
| Essential independent customer journey | All | Partially implemented | Workspace/profile/onboarding/invitations/domain proof local foundations | PlaneByte shell/settings/onboarding | Public admission and provider activation blocked; approved staged full journey and exact locked runtime still release requirements |

## Current implementation sequence

1. Finish saved searches, explicit criteria handling and per-source progressive discovery; test API, migration, security, source recovery and browser workflow.
2. Complete the existing contact entity and company relationship workflow, then enrichment/verification jobs.
3. Complete evidence-based qualification, summaries and assistant tools using the shared AI gateway.
4. Finish customer mailbox/outreach and lists/tasks over the existing transport and safety ledgers.
5. Finish integration sync and external acceptance for the locally implemented public API/keys, signed webhooks and actual MCP; run the full A–I customer acceptance set.

External credentials/consent/DNS/provider coverage are activation constraints, not permission to leave safe implementation unfinished. No feature will be called live based on a mock or a screen alone. Record changes and actual validation below as milestones land.


## Implemented milestones and actual evidence

### Local discovery/contact/enrichment checkpoint

- Migrations 29–31 add saved searches, extend existing professional contacts, and add bounded intelligence jobs. Existing schema/history is retained. Upgrade/repeatability/restore tests pass.
- Maps sources commit canonical companies before the second provider or any website work. A controlled cancellation/resume test confirms the completed source is not called twice. The measured first-result fixture latency is recorded in `phase6/backend-phase4.xml`; it is not a production latency claim.
- Arbitrary requested Firecrawl industries and explicit post-discovery filters are retained; unsupported/missing employee and company-size observations stay unknown. Seven-country input coverage is tested; real provider coverage is not certified.
- Public professional extraction uses stated structured relationships, never inferred people or mailbox patterns. Fresh positive/negative contact evidence is reusable. MX/domain checks do not claim recipient delivery.
- A real PostgreSQL adapter issue (cursor iteration) was found and fixed using explicit fetches. Contact email changes clear stale verification. Archived contacts cannot be enriched.

### Local qualification/assistant checkpoint

- Weighted ICP criteria, observed fit, evidence coverage, contact relevance and source explanations are implemented without changing suppression or qualification automatically.
- Stated company structured attributes include source/type and unverified labels. No employee/revenue estimates are invented.
- AI company summaries select exact quotes from stored pages; unsupported quotes fail validation. The shared gateway and existing daily AI reservations are reused. New summary work remains disabled with the existing company-AI gate.
- Migration 32 adds private conversations, durable turns and explicit action approvals. The Lead Engine assistant uses the shared gateway and existing worker, at most three read tools and two proposals per turn. It has no SMTP, arbitrary SQL/URL, scan-start or permission-changing tool. Approved search/list/task/enrichment actions reuse domain services. The new assistant feature gate defaults false; no environment file was changed.

### Verification (local only)

| Check | Actual result | Evidence |
|---|---|---|
| Full backend checkpoint before assistant addition | 642 passed, 1 deliberate live-mail skip | `data/artifacts/verification/phase6/backend-phase4.log` / `.xml` |
| PostgreSQL including assistant approval/private history | 24 passed | `phase6/postgres-assistant.log` |
| Assistant API, migration restore, qualification/summary tests | 9 passed | `phase6/assistant-api-migration.log` |
| Frontend units through qualification/assistant | 97 passed | `phase6/frontend-phase4-final.log` |
| TypeScript / isolated production build through assistant | Pass | `phase6/types-phase4.log`, `phase6/build-phase4-fixed.log` |
| Existing + new workflow browsers | 28 passed | `phase6/browser-phase4-workflows.log` |
| Workspace/onboarding/weighted ICP browsers | 10 passed | `phase6/browser-phase4-workspaces.log` |
| Sales lists/tasks + assistant targeted tests | 13 passed initially; subsequent shared-service subset 9 passed | `phase6/sales-operations-initial.log`, `phase6/sales-assistant.log` |

The full backend checkpoint above predates the assistant and list/task additions; it is not claimed as a full verification of schema 33. The next frozen run must include all current code. Existing auth, signed-preview and integration-handoff browsers must also be rerun before release.

## Remaining implementation and acceptance

1. Targeted lists/tasks and schema-38 CSV/Sheets export safety now pass local recovery checks, including PostgreSQL and tenant denial. Complete the broader customer/release checkpoint; any private preview restart still requires a fresh backup and tested restore.
2. Complete independent customer Gmail connection/refresh/disconnect, account-selected transport/send/sync and campaign routing. Existing internal Gmail remains scoped to its internal owner and has not been shared or changed.
3. Complete real HubSpot/Pipedrive adapters/mapping/sync and reviewed customer integration sync. Sheets import/export, scoped API/keys, signed webhooks and maintained-SDK MCP are implemented locally; approved live external acceptance and activation remain pending.
4. Complete broader AI/qualification recommendations and full A–I customer journey acceptance. No live external acceptance is inferred from mocks or schemas.
5. Run the final full SQLite/PostgreSQL/frontend/browser regression, approved staged external-provider acceptance and exact locked-runtime verification. Public signup remains blocked; no production deployment or real outreach is authorized by this development directive.


## UI/UX + AI ICP extension — 2026-11-07 (in progress)

The owner added `a272035c-53a9-4712-9389-f201e6b487e2/Pasted text.txt` to the same Phase 1–6 implementation task. This extends the scope; it does not authorize production, environment/OAuth changes, real outreach or a database reset.

Implemented locally:

- Schema 36 adds private expiring AI proposal receipts and source attribution to the existing versioned ICP entity. Existing profiles/history remain intact. SQLite backup/restore and PostgreSQL checks pass.
- The shared AI gateway accepts saved approved company details and returns up to three inactive recommendations, with reasons and reviewable assumptions. It never crawls implicitly or treats suggested audiences as existing customers. Missing company context links to the existing reviewed website-analysis/profile workflow.
- The existing natural-language interpreter remains compatible and gains owned provenance. Follow-up refinements use validated leaf patches, preserve unrelated criteria/weights and show changed fields. Unsupported fields, markets, sizes, unrequested numeric ranges and provider failures fail safely. Per-workspace/global AI reservations and cache reuse remain in force.
- ICP UI adds business-based generation, explicit candidate comparison, editable assumptions, structured removable terms, refinement, draft/activation controls, source summaries and meaningful empty states. Active-profile replacement requires explicit confirmation.
- Discovery exposes an owned ICP filter preview, warns about unsupported Maps categories/post-discovery criteria and keeps reviewed searches inert. New runs retain the exact ICP snapshot; Maps and Firecrawl batch configurations carry it forward. Country aliases match consistently.
- Lists/tasks use accessible focused dialogs; task metadata editing has revisions, member/contact ownership checks and suppression protection. Date views use an explicit timezone; no task action sends email.
- Recommendations has useful no-ICP/no-company states, profile summaries, criterion reasoning, honest page-local ranking/filtering and owned add-to-list actions. The company page is queried in a bounded batch instead of one company read per row.
- Help now searches maintained product guidance with a real support email. The gated assistant can retrieve the same guidance through a read-only tool. No live-chat claim is made.
- Legal pages use readable document layouts with accurate development disclosures. They remain explicitly unapproved review copies. Canonical published Privacy Policy/Terms and legal approval are still public-release requirements.

Actual evidence so far: 8 business-builder/interpreter checks, 4 snapshot/task-edit checks, 29 discovery/import/matching regression checks, 1 new PostgreSQL provenance/task check; 105 UI units at the earlier bounded checkpoint, plus 4 subsequent workflow-refinement units. Earlier parallel UI runs exposed timing-sensitive fixture waits; those failures remain logged, and the bounded frozen run is recorded separately. A newly introduced missing-profile snapshot lookup regression was detected, corrected and its 29-test source subset rerun green. The interrupted first full run is **not** acceptance evidence.

Latest prior full backend baseline (schema 35): **664 passed, 1 explicit live-mail skip**, including **26 PostgreSQL passes** (`phase6/backend-current.log`). Official MCP protocol tests: 2 passes (`mcp-sdk-client-audited.log`); real browser key/protocol/manual-approval/revocation: 1 pass (`browser-developer-protocol.log`). Customer Sheets: 3 real HTTP/service/worker passes with ten retained qualified imported rows and no emails (`customer-sheets-http.log`). The prior tracker rows describing API/MCP as absent were stale and have been corrected.

Remaining Phase 1–6 scope is still substantial: independent customer Gmail send/sync and campaign routing; Sheets export; HubSpot/Pipedrive adapters and reviewed sync; signed outgoing webhooks/delivery histories; full A–I external customer acceptance; exact locked crypto runtime; approved staged provider/legal/public-registration release. These are not certified by local mocks or UI labels. Current UI browser/full backend regression is in progress; do not mark the whole upgrade complete.


### Verified UI refinement checkpoint and owner local enablement

- Full backend checkpoint: **675 passed, 1 deliberate live-email skip, 7 recorded deprecation warnings**, including **27 PostgreSQL passes**, `phase6/backend-refinement-corrected.log` and `.xml`. A subsequent 13-test ICP/refinement/assistant delta also passes after adding refinement of saved profiles. The new launcher modes have four passing boundary checks.
- UI units: **109 passed**, `phase6/frontend-refinement-frozen.log`; TypeScript and the isolated build pass. The final tiny availability-message change has six additional targeted UI passes and types passing.
- Browser: **29 workflow**, **11 workspace**, **3 auth**, **1 official API/MCP developer**, **1 Sheets handoff**, **1 real-signed preview** pass. A final mobile-header test passes at desktop, 390px and 320px and checks that title/workspace controls do not overlap. Logs: `browser-refinement-workflows.log`, `browser-refinement-frozen-*.log`, `browser-refinement-mobile-header.log`.
- The private local preview was backed up and restored/upgraded from schema 35 to 36 with original-value hashes, integrity and foreign keys verified. Backup: `data/backups/local-preview-pre36-20261107T045608Z/`. No production data was migrated or reset.
- The owner then explicitly requested all implemented features enabled locally. `scripts/local_preview.py ... --all-features` enables company discovery/AI, ICP AI, assistant, customer integration UI, developer API/MCP and acquisition/import sources in memory. Local database, cache namespace, artifact storage and workers remain isolated. Real authentication, membership, quotas and suppression remain enforced. Archived SEO/security experiments are not revived.
- **Real Vertex acceptance now passes**, using the existing project/model and local ADC: one description-based candidate and three business-profile-based candidates returned HTTP 200, with required review, no saved ICP, no scan and no email. No new AI provider, key, root environment edit or production configuration change was introduced. Repeating identical requests can reuse the existing owned cache.
- The owner corrected the integration encryption key; current validation passes without displaying it. The local Sheets callback is registered, while customer consent still requires the owner’s explicit Google authorization. The owner authorized controlled local mail only to agrawaljoy1@gmail.com; the preview forces that recipient at the transport boundary with live approval false. Gmail SMTP NOOP and read-only IMAP health both pass. No email has been sent by this development checkpoint.
- The historical crypto release blocker is now diagnosed precisely: the configured package index offers runtime 48.0.1 but cannot resolve the repository's existing `cryptography==50.0.2` lock. The dry-run result is `locked-crypto-availability.log`; no dependency was installed and the existing pin was not silently rewritten. `pip check` passes but does not resolve this clean-install blocker.

Broader implementation remains open: independent customer Gmail routing/send/sync, Sheets export, CRM adapters/sync, signed webhooks and the full external A–I release journey. This checkpoint completes a substantial local UI/ICP extension; it does not certify Phase 1–6 as finished or authorize real outreach/production rollout.


### Live local follow-up

The owner corrected the server integration key and named agrawaljoy1@gmail.com for controlled local testing. Validation confirms a valid key in the existing root file; credentials remain server-only. Local Gmail health is READY, the envelope is forced to the controlled address and live approval remains false. This does not implement customer-owned mailbox routing or authorize prospect delivery.

`local-all-features-acceptance.json` records HTTP-verified enabled/configured ICP, company website AI, Assistant, Developer/MCP and source/import flags. The **actual three-candidate business-profile request returned HTTP 200**, with no profile saved or discovery started. Root environment secrets were read only, never printed. The preview forces a private SQLite database, empty production DB URL, local artifacts and local executors. A very narrow development-only tracking base permits exact loopback preview URLs; production still requires public HTTPS and redirect destinations remain public-only. All ten relevant local-mode/mail/tracking regressions pass. Gmail proxy open tracking cannot reach a private loopback server; that external acceptance still needs an approved public HTTPS environment.

Completed UI checkpoint source archive: `data/backups/ui-icp-local-enablement-20261107T051810Z/source.zip`. No production activation or customer Gmail/CRM/webhook completion is implied.


### Signed webhooks checkpoint — 2026-11-07

Schema 37 implements owned subscriptions, encrypted one-time signing secrets,
transactional identifier-only events, durable HMAC-signed delivery, fixed public
HTTPS transport, bounded attempts/backoff, stable IDs, explicit retries and
archive/history. Revoked authority stops workers. Final-attempt crash recovery
records an uncertain outcome without a sixth send. The local preview dispatcher
is enabled; production infrastructure and receiver activation are untouched.
See `SIGNED_WEBHOOKS.md` for the contract and limits.

Actual frozen checks: **698 backend passes, one deliberate live-mail skip**,
including **28 PostgreSQL passes** (`backend-webhooks-frozen.log/.xml`); **112 UI
passes**, TypeScript/build pass; **two real developer/API/MCP/webhook browser
passes** (`browser-webhooks-corrected.log`). Initial migration-count and fixture
minimum failures are retained in earlier logs and were corrected, not suppressed.
The private database upgrade from 36 to 37 preserved all original values and
passed restored integrity/foreign-key checks before preview restart. Restricted
backup: `data/backups/local-preview-pre37-20261107T093930Z/`.

### Reviewed Sheets export extension — historical final verification recovered

Schema 38 extends the existing OAuth state with explicit requested permission and
adds private immutable export jobs. Default authorization remains read-only. A
separate owner/admin consent grants export; every write requires review of the
company-list snapshot, destination and overwrite range. The existing worker uses
RAW cell values, a fixed range, durable reservations, time/size/concurrency limits,
verified cell counts and at most three explicitly reviewed attempts. Unknown
provider outcomes do not automatically retry. No actual Google spreadsheet or
prospect was contacted. See `CUSTOMER_SHEETS_EXPORT.md`.

The controlled browser uses real scoped application APIs/credentials/worker with
a synthetic Google transport; this is not live Google acceptance. Recovery found
completed final regression/browser and private restore artifacts that had not yet
been reflected in this tracker. Their results and the fresh targeted checks are
recorded below. No preview restart was performed during recovery.

### Export/webhook development recovery — 2026-11-08

**Scope:** source preservation, PostgreSQL export safety and focused offline
regression. This is not full Phase 1–6 completion or production acceptance.

Source checkpoint: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-recovery-20261108T075439Z/`.
`source.zip` contains 862 selected source/documentation files; archive contents
were read back and compared byte-for-byte. A SHA-256 manifest is retained alongside
it. Directory permission is 0700, archive/manifest permissions 0600. Environment
files, credential files, databases and generated/runtime artifacts were excluded.
No Git commit, deployment, push or production operation was performed.
Final checkpoint comparison verified that only the two repaired source files,
PostgreSQL test file and this tracker differ; the other 858 checkpoint files are
unchanged and the original archive hash still matches.

Recovered **historical** schema-38 artifacts in
`data/artifacts/verification/phase6/` record 708 backend passes, one deliberate
live-mail skip and seven warnings (`backend-export-final.log`), 114 UI passes
(`frontend-export-final-corrected.log`), a successful frontend build and 48 browser
passes (`browser-export-final-*.log`). `local-preview-pre38-restore.log` records
verified local schema-37 to 38 restoration. These predate the recovery changes;
they are not a fresh full-suite/build/browser certification of this checkout.

Confirmed issues and minimal repairs:

- PostgreSQL reproduced a CSV download silently omitting an unavailable company.
  `app/api/routes/sales.py` now checks final snapshot counts and the download
  budget before returning output. Incomplete company/contact lists return 409;
  existing formula escaping and private-response headers remain enforced.
- An independent PostgreSQL transaction made company evidence unavailable between
  list selection and Sheets evidence lookup, reproducing an unhandled `KeyError`.
  `app/integrations/sheet_exports.py` now rejects that incomplete snapshot with 409
  before inserting an export job. No provider retry or worker behavior was rewritten.
- Twelve additional PostgreSQL cases exercise unavailable records, snapshot races,
  formula/foreign-workspace safety, independent duplicate reservations, the two-worker
  limit, reviewed crash recovery, active/exhausted/expired review bounds, stale-worker
  fencing, and webhook reservation/final-attempt recovery. Existing tests were retained.

Fresh verification artifacts are under the checkpoint's `runtime/` directory:

| Check | Actual result | Evidence |
|---|---|---|
| Existing Sheets export/connection/webhook baseline | 32 passed before edits | Recovery session command output |
| PostgreSQL safety reproduction | 1 failed, 7 passed; separate snapshot race failed with `KeyError` | `postgres-safety-initial.log`, `postgres-snapshot-race-initial.log` |
| Focused PostgreSQL export/webhook checks after repair | 14 passed, 27 deselected | `postgres-export-webhook-verified.log/.xml` |
| Sheets export/connections/import, webhook, sales/task and CSV/XLSX domain regression | 43 passed | `focused-domain-regression.log/.xml` |
| Broader non-destructive PostgreSQL regression, including backup/restore through schema 38 | 39 passed, 2 deselected | `postgres-regression-final.log/.xml` |
| Whitespace validation | `git diff --check` passed | Recovery session command output |

The first broader PostgreSQL run had 38 passes and one test-harness failure:
the temporary schema-retention guard lacked context-manager support during restore
cleanup. Only that external guard was corrected; the final 39-test run passed.
The original failure remains in `postgres-nondestructive-regression.log/.xml`.

PostgreSQL 16.15 ran in a freshly initialized private cluster using a restricted
Unix socket with **no TCP listener** and an explicitly supplied test database URL.
The temporary test guard rejected other PostgreSQL connection destinations and
retained all test schemas. The two existing tests that explicitly delete data
(`permanent_deletion`, `legacy_company_alias_rediscovery`) were deselected. Ordinary
SQLite tests also used isolated data. Google OAuth/Sheets writes and webhook
receivers were synthetic transports; no live Google write or email occurred.
The private PostgreSQL process was stopped after verification; files/schemas were
retained rather than cleaned up.

Remaining blockers: a new full backend/frontend/browser checkpoint after these
repairs; approved live Google consent/write and webhook receiver/scheduling
acceptance; exact locked cryptography runtime (installed 48.0.1 versus the unchanged
`requirements.lock` pin 50.0.2, verified during recovery); independent customer Gmail routing,
CRM adapters/sync and the broader staged customer/public-release journey.


### Comprehensive Phase 1–6 assessment — 2026-11-08 UTC

This supersedes the prior pending full-regression note without replacing historical evidence. Existing suites now pass: 679 backend cases (42 explicit skips), 39 isolated PostgreSQL cases (2 destructive cases deselected), 114 frontend units, typecheck/webpack production build and 48 local browser tests. The prior 43 focused cases passed inside the new full backend.

### Implementation milestone 1 — 2026-11-08 12:52 UTC

Both confirmed defects are now repaired and verified. `app/platform/onboarding.py`
uses adapter-compatible `fetchall()` and rechecks active membership on reads.
`app/automation/views.py` provides owned parent-joined aggregate counts; the summary
route uses `app/api/schemas/automation.py` as a strict nested response allowlist,
omits all internal runs/controls/provider flags, and returns `private, no-store`.
No schema migration or historical deletion was needed.

Permanent tests: `tests/unit/test_automation_summary.py`, updated
`tests/unit/test_onboarding.py` and `tests/integration/test_postgres.py` cover
new/saved/resumed/completed setup, profile loading, inactive service retention,
revision conflicts, all four workspace roles, revocation, missing/foreign context,
two-workspace summaries, unexpected nested fields and alternate internal routes.

Actual targeted verification: **29 SQLite/API/cache cases passed**, **20 real
PostgreSQL cases passed; 27 deselected** (including existing export/webhook safety).
Logs, JUnit and exact command/cwd/environment metadata are under
`/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-implementation-20261108-115909/`:
`milestone1-sqlite-final.*`, `milestone1-postgres-final.*` and `*-command.json`.
The initial run's invalid fixture membership status and nonexistent queue-tenant
column assumptions were corrected; `milestone1-sqlite.*` retains that failed run.

**B01 and the specific B02 exposure are closed. F12 is verified; F15 is partial
pending the broader customer/mail/CRM isolation acceptance.** Fixed weights yield
**76.3% functional credit, 57.4% fully verified closure, 75 incomplete requirements**.
Five P0 workstreams B03–B07 remain. Historical assessment rows/counts below describe
their original checkpoint and are not current defect status.

Current source checkpoint: verified 865-file source-only archive at
`/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-recovery-20261108T115909Z/`.
Next requirement: **F02/B03**, gated Google customer admission; production allowlist,
mail sending, OAuth/credentials, billing and deployment settings remain unchanged.

**Historical assessment probes (superseded by milestone 1 above):** PostgreSQL onboarding read raised TypeError at `app/platform/onboarding.py:62`; independent customer `/api/automation/summary` received internal automation-run status/target/error metadata. These failures describe the reporting checkpoint before the saved repairs.

Historical assessment estimate **75.1%**, fully verified requirement closure **56.7%**, from 174 audit rows / 427 weighted points (320.5 earned); no entire phase or public release was complete. The seven assessment P0 workstreams included the subsequently repaired defects. Current milestone-1 estimates and closures are above; customer CRM/enrichment, conversational/recommendation flows, metering/plans/billing and other P1 scope remain.

| Area | Earned / weight | Functional estimate | Verified closure | Production readiness |
|---|---:|---:|---:|---|
| SaaS foundation | 29.5 / 51 | 57.8% | 37.3% | NOT READY; required gaps remain |
| Phase 1 — Discovery | 32.25 / 43 | 75.0% | 41.9% | NOT READY; required gaps remain |
| Phase 2 — Company/contact intelligence | 35.75 / 42 | 85.1% | 61.9% | NOT READY; required gaps remain |
| Phase 3 — Enrichment/verification | 32.5 / 48 | 67.7% | 54.2% | NOT READY; required gaps remain |
| Phase 4 — AI/ICP qualification | 44 / 53 | 83.0% | 47.2% | NOT READY; required gaps remain |
| Phase 5 — Sales workspace/outreach | 57.75 / 70 | 82.5% | 71.4% | NOT READY; required gaps remain |
| Phase 6 — Integrations/API/webhooks/MCP | 88.75 / 120 | 74.0% | 65.0% | NOT READY; required gaps remain |
| Overall including foundation | 320.5 / 427 | 75.1% | 56.7% | BLOCKED: seven P0 workstreams |

Definitive reports: `docs/PLANEBYTE_LEAD_ENGINE_PHASE_1_TO_6_STATUS_REPORT.md`, `docs/PLANEBYTE_LEAD_ENGINE_PENDING_FEATURES.md`, `docs/PLANEBYTE_LEAD_ENGINE_RELEASE_READINESS.md`. They preserve actual failed/skipped/not-run outcomes and specify every incomplete requirement and milestone. Raw assessment evidence: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/leadengine-assessment-20261108`. Existing 862-file checkpoint revalidated; reporting left application source unchanged. No production database reset/modification, live mail/Sheet write, commit/push/deploy or cleanup occurred. **Verdict: NOT READY FOR PUBLIC SaaS.**

## Continuation checkpoint — 2026-11-09

### Recovered state and exact continuation

- **Last completed requirement:** B01/F12 and the specific B02 automation-summary
  exposure, saved in implementation milestone 1. Earlier assessment failures/counts
  are historical. Fresh local checks confirm both repairs still work; the original
  temporary PostgreSQL evidence paths are now missing and cannot be hash-revalidated.
- **Current requirement:** F02/F08, B03. Gated Google account admission, consent
  renewal and invitation-only access are implemented and tested locally. B03 remains
  **implemented, broader integration acceptance pending**, not release-closed.
- **Next exact implementation/verification step:** obtain an isolated PostgreSQL
  runtime, run the seven onboarding/summary/admission cases and schema-39 recovery
  plus identity/invitation concurrency validation; then complete the staged
  two-customer real Google callback/onboarding/invitation journey with approval.
  In parallel safe local development, the next unimplemented essential service is
  B04/S16/S18: customer Gmail authorization/refresh/disconnect and owned routing,
  extending `app/integrations/service.py` and its encrypted envelope/lease services.
  No Gmail lifecycle adapter or customer sender has been claimed complete here.

### Preservation and saved work

Recovery started on `main`: 120 modified tracked files, 727 individual untracked
files, none staged. Existing schemas 29–38, exports/webhooks/API/MCP and partial
schema-39 account-admission source survived. All changed Python source parsed.
Git history still ends at `a23b937` / `d009e5f`. OpenCode's local session database,
shell artifacts, snapshot store and repository backup/test directories were located;
session metadata was inspected read-only without exporting messages/credentials.
The prior temporary recovery directories are unavailable. A new private 856-file
source-only checkpoint was byte/hash verified at
`/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/recovery-20261109/`.
Environment files, credentials, databases and customer/runtime payloads were excluded.

Final durable private source checkpoint: **871 files**, read-back/hash verified,
`data/backups/leadengine-continuation-20261109T082004Z/source.zip` and restricted
`manifest.json`. Comparison also detected three newer frontend changes saved during
recovery (`globals.css` uses the existing JS Tailwind configuration;
`local_frontend.cjs` selects webpack; `local_frontend_env.cjs` resolves the fixed
dashboard directory). They were inspected and preserved. They are not attributed
to this continuation's patches. The checkpoint captures them alongside all other
surviving source. A final localhost check again confirmed HTTP 200 after the other
IDE-started process briefly stopped/restarted; no unrelated process was terminated.

Completed interrupted changes and added behavior:

- The signup page's optional default argument broke Next's generated `PageProps`;
  its saved function contract is now corrected.
- The local frontend launcher uses the verified webpack path after the default
  Turbopack CSS worker failed. An existing IDE-started server owns port 3000;
  `/login` and `/signup` now return HTTP 200 at `http://localhost:3000`.
- Invitation-only admission has a separate false-by-default gate. The existing
  invitation validator now checks recipient, expiry/replay, active organization,
  inviter role and admitted inviter account. Account admission does not consume an
  invitation or grant membership. Suspended/removed/demoted inviters cannot admit
  new accounts through their old invitations.
- Current terms gate signed customer APIs/workers. Returning admitted users can
  renew consent through the signed account-only broker, including viewers, with
  both registration gates closed. Subject/email/client binding is retained.
- HTTP-only signed consent/review cookies are bounded to ten minutes; invitation
  codes stay out of OAuth redirect URLs. The review page checks the authorized
  session and explicit acceptance reuses existing invitation services.
- Migration 39 was already partially saved; its ordered additive DDL was retained.
  Schema-38 upgrade/repeatability and restored historical organization/contact
  values are now tested. No existing local or production database was upgraded.

**Files changed this continuation:** `app/config/settings.py`,
`app/platform/admission.py`, `app/platform/invitations.py`, `app/api/security.py`,
`app/api/routes/admission.py`, `scripts/local_preview.py`,
`dashboard/lib/server/env.ts`, `dashboard/lib/server/admission.ts`,
`dashboard/app/signup/{page.tsx,actions.ts}`,
`dashboard/app/accept-invitation/page.tsx`,
`dashboard/components/workspaces/invitations.tsx`, `dashboard/vitest.config.ts`,
`dashboard/__tests__/{account-admission.test.ts,signup-actions.test.ts}`,
`dashboard/playwright.admission.config.ts`, `dashboard/admission-e2e/admission.spec.ts`,
`tests/unit/{test_account_admission.py,test_foundation_additive_migrations.py}`,
`tests/integration/test_postgres.py`, this tracker, the three assessment-report
continuation notices, and `docs/GOOGLE_ACCOUNT_ADMISSION.md`. Saved prior source
changes were retained; no historical DDL was rewritten.

### Actual verification and failures

Durable evidence: `data/artifacts/verification/phase6/recovery-20261109/`.
Backend/XML and backend/frontend/build command records include source hashes.
The browser outcomes below are the actual earlier commands from this session,
not live Google acceptance. Build used a source copy and synthetic server values,
leaving the running frontend's build directory and environment files intact.

| Check | Actual result |
|---|---|
| Recovered onboarding/summary/cache/admission first check | 24 passed |
| Additional automation/tenant/local-launcher check | 12 passed |
| Final admission/invitation/critical API check | 44 passed |
| Broader frozen backend, including owned workers/integrations/API/MCP and schema-39 backup/restore | **116 passed**, `backend.log`, `backend.xml` |
| Full frontend units after runner repair | **123 passed**, `frontend.log` |
| Frontend type check | Pass after fixing signup contract; final `npm run typecheck` passes |
| Isolated production webpack build | Pass, `build.log` |
| Existing auth browsers | 3 passed using private webpack override config; responsive/denial/recovery and real protected OAuth handoff |
| Invitation admission browser | 1 passed, `npx playwright test --config=playwright.admission.config.ts`; synthetic destination, no Google callback/account creation |
| Fresh PostgreSQL critical/admission cases | **7 skipped, 43 deselected** because no isolated runtime is available; `postgres.log` / `postgres-unavailable.xml` |
| Whitespace / Python syntax | `git diff --check` and changed-source AST checks pass |

Failures retained accurately:

1. Frontend start attempt returned `EADDRINUSE`; another IDE-started frontend had
   obtained port 3000. That frontend initially returned HTTP 500 from Turbopack CSS
   subprocess startup. Local webpack now responds successfully.
2. Typecheck initially failed the interrupted signup `PageProps` contract; fixed.
   A later typecheck caught generated files disappearing during development-server
   regeneration; subsequent stable typecheck passes without loosening configuration.
3. Full Vitest initially had **123 passes and one failed suite** because it picked
   up the new Playwright admission test. Its browser directory is now excluded using
   the established runner convention; the full 123-test run passes.
4. First isolated build failed because the recovery copy omitted the existing
   `tailwind.config.js`; the copy filter was corrected, with no application workaround.
   The final build passes. `frontend-initial.log` and `build-initial.log` are retained.

### Remaining blockers and boundary

Fresh PostgreSQL/concurrency/migration acceptance and real staged Google callback,
new-customer/invitation acceptance remain open. B04 customer Gmail and B16 CRM
adapters/sync are unimplemented. Other backlog/provider/usage/plans/billing,
supported Node24/exact cryptography lock, approved policy and external acceptance
requirements remain. Node26 validation does not close the Node24 release gate.
The last recorded weighted milestone remains 76.3% functional / 57.4% fully
verified closure; no new full assessment or percentage reset was performed.
Public/customer/invited registration flags were not enabled by this session.
No environment/OAuth/DNS/production setting, customer data, real email, Sheet/CRM
write, database reset, Git stash/commit/push or deployment was performed.

## B04 continuation — core verified, broader checks in progress (2026-11-09)

- **Last completed local slice:** B04/S16/S18 core: customer Gmail PKCE lifecycle,
  encrypted/revisioned tokens, mailbox-owned transport, campaign route, explicit
  owner approval/limits, idempotent send reservation, and owned reply/DSN sync.
- **Current requirement:** B04 frontend and broader worker/API regression closure.
  No production/external Gmail acceptance is claimed. One owned mailbox per workspace
  is supported; owner/admin connectors only. Existing internal sender and Sheets
  integrations are preserved and cannot serve unrelated customer workspaces.
- **Files:** additive `customer_gmail_schema.py` (schema 40), integration
  `service.py` / `gmail.py`, mail `customer.py` / service/providers/bounces/tracking,
  API mail/workflows/security, workflow/automation dispatch, settings; Gmail UI,
  callback and campaign mailbox form; `test_customer_gmail.py` and schema-40 recovery.
- **Passed:** 61 targeted backend checks; dashboard TypeScript. Evidence:
  `data/artifacts/verification/phase6/b04-local/backend.xml`. Initial failures are
  preserved in `first-backend.xml` (40 passed, one onboarding gate failure; repaired).
  Earlier internal reply regression failures and introduced indentation errors were
  diagnosed and fixed; the selected internal mail/Sheets regressions now pass.
- **PostgreSQL:** **BLOCKED — NOT RUN**. No local PostgreSQL server/initdb/pg_ctl,
  Docker, Homebrew or MacPorts; previous private cluster is absent. Preserve the
  seven-case command in `recovery-20261109/postgres-command.json` and existing
  admission/concurrency cases. No repeat unavailable run or production DSN use.
- **Next exact action:** finish frontend unit checks, broaden campaign/worker/
  suppression/API regression coverage, verify the isolated frontend build, then
  checkpoint B04 local acceptance and continue the next dependency-ordered backlog.
  All new Gmail/send/schedule controls remain false by default. No live email,
   external Sheet/CRM write, environment/OAuth/deployment change or commit occurred.

### Intent Radar integration handback — 2026-11-10

Lead Engine remains paused at the B04 continuation above. Radar Phase 1 is locally
integrated: 757 backend passes/51 explicit skips, 134 UI passes, types/build pass,
4 Radar and 29 Lead Engine production-bundle browsers pass; real HN fetch passes.
Review the fenced rejected-token ciphertext cleanup in `app/integrations/service.py`
before continuing B04. Shared notifications and disabled-archive HTTP status were
also repaired. No customer mail was sent and no production settings/data changed.
PostgreSQL remains blocked. Resume the existing B04 next action; this does not close
the broader Lead Engine roadmap. See `INTENT_RADAR_PHASE_1_INTEGRATION_REPORT.md`
and its readback-verified source checkpoint for exact results and preserved changes.

### B04 customer Gmail lifecycle closure — 2026-11-10

**B04 is implemented and locally verified with mocked transports. STOP here.**
The historical B04 continuation above is superseded by this checkpoint. No next
milestone, remaining Phase 1–6 backlog work or Intent Radar Phase 2 is authorized.

Completed the remaining lifecycle safeguards:
- Kept encrypted, actor/workspace/context-bound OAuth and refresh leases. The shared
  provider error path now invokes Gmail authority revocation only after its existing
  tenant/revision/lease fence succeeds. Rejected refresh, API authorization and
  changed mailbox identity clear credentials, disable mailbox/policy authority and
  invalidate sync work. Disconnect/reconnect retain historical conversations;
  reconnect never inherits prior sending approval.
- Inbox requests recheck ownership, revision and active lease before provider work;
  expired/replaced leases cannot persist evidence or advance the saved cursor.
  Concurrent reads cancel on failure, async mail I/O has a real cancellation timeout,
  temporary retries remain bounded and expired history requires explicit, revisioned
  `RESTART_RECENT_SYNC` review. This restarts only the bounded recent inbox position,
  preserving messages, suppression records and audit history.
- Gmail management UI shows sync/re-authentication state, exposes reviewed history
  recovery, refreshes revoked state after errors and allows removal of stale approval.
  Composer preview/send payloads explicitly bind the workspace mailbox. Account and
  compose readiness reflect connection, workspace approval, recipient/mode and live
  environment gates rather than advertising unavailable sends.
- Verified campaign-to-mailbox routing, inert preparation, fresh reviewed previews,
  explicit owner approval, final recipient/suppression guards, authenticated replies,
  idempotent bounce handling, tenant-local soft/hard suppression, bounded throttle
  retries and uncertain-delivery reservations that are never automatically resent.

Exact local results, all under
`data/artifacts/verification/phase6/b04-completion-20261110/`:

| Verification | Result | Evidence |
|---|---|---|
| Full backend/security/regressions | **775 passed, 51 skipped**, 7 warnings | `backend-full.log`, `backend-full.xml` |
| Final Gmail/campaign/tenant/worker/shared/Radar focus | **109 passed**, 1 warning | `backend-focused-verified.log`, `.xml` |
| Frontend units | **137 passed**, 35 files | `frontend-final.log` |
| Type checking / isolated production build | **PASS / PASS** | `typecheck-final.log`, `build.log` |
| Gmail production-bundle browser journeys | **2 passed** | `browser-production-final.log`, `browser-results.json` |
| Lead Engine production-bundle regressions | **29 passed** | `lead-engine-browser.log`, `lead-engine-browser-results.json` |
| Intent Radar production-bundle regressions | **7 passed** | `radar-browser.log`, `radar-browser-results.json` |

The final focused run additionally covers the rejected-refresh regression added
after the full run; do not relabel the full run as 776 passes. Frontend units exclude
`intent-radar-ui-e2e/**` on the CLI because those are separate Playwright tests.
The 51 backend skips remain **50 PostgreSQL checks BLOCKED** by unavailable local
infrastructure plus one deliberately skipped live-mail acceptance. No production
DSN was substituted. Additive schema **40, 41–42** remains intact; no migration was
edited or reset. Completed Radar services, workers, permissions, navigation and UI
were preserved; shared changes passed its regressions.

Intermediate failures were recorded and repaired: test-fixture import/indentation;
an open unapproved draft retaining its audience reservation (explicitly stop the
draft, then create a newly reviewed run); a collapsed conversation hiding the
composer; ambiguous loading/status selectors in the production browser; and a new
refresh test mistakenly targeting a SQL expiry column instead of encrypted token
expiry. The initial lifecycle assertions exposed six actual revocation/lease/history
gaps, now passing. Provider rate/DNS interruptions (`getaddrinfo ENOTFOUND`) are
harness/provider events, not application acceptance failures.

The browser harness uses disposable SQLite, synthetic OAuth/Gmail responses and a
bounded fixture clock calling the existing owned-run worker. Its sole delivered
browser message is a mocked Gmail API response to a controlled fixture recipient;
no real Google OAuth, external inbox access or email delivery occurred. Initial
preparation leaves sending unapproved and cannot start delivery. Existing follow-up
composer review does not bypass permanent contact/suppression or uncertain-send guards.

Outstanding external approvals/acceptance (not completed by these mocks): owner
approval/provisioning of the Gmail OAuth client, callback URI, server encryption
key and scope/access verification; authorized real-account connect/refresh/revoke
and inbox acceptance; separately authorized controlled live-send acceptance and
explicit live runtime/owner gates; local PostgreSQL restore/concurrency validation.
Public signup/customer rollout and production readiness remain uncertified.

Reproduce from the repository root: `.venv/bin/python -m pytest tests -q`.
In `dashboard/`: `npm run typecheck`; `npm run test -- --exclude
'intent-radar-ui-e2e/**' --maxWorkers=2`; use `build-command.json` for the isolated
fixture production bundle; `B04_BROWSER_PRODUCTION=1 npx playwright test
--config=playwright.gmail.config.ts`; `npx playwright test
--config=playwright.b04-regressions.config.ts`; and `B04_BROWSER_SUITE=radar npx
playwright test --config=playwright.b04-regressions.config.ts`.

`source-checkpoint.zip` and `results.json` in the evidence directory preserve dirty
source, source-only diff/status, hashes and verified archive readback. Generated
Next build caches, including already-tracked test caches present on resume, are
excluded from the source archive and were not reset or untracked. Source whitespace
check passed (Git noted the existing generated `next-env.d.ts` CRLF normalization).
**B04 is closed locally; development stops pending further owner instructions.**
