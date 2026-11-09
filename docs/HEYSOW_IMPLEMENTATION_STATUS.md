# HeySow implementation status — 2026-11-06

This is an implementation inventory for the current checkout. No product
transformation or production-readiness claim is made. Production is unchanged;
registration, real email sends and uncontrolled discovery remain disabled.

| Area | Actual state | Evidence / remaining work |
|---|---|---|
| Existing modular monolith | Complete and tested baseline | Next 16.4.3, React 19.3.1, Auth.js 5, FastAPI, SQL adapters, existing workers retained |
| Existing internal Google login | Complete and tested locally | 3 auth browser tests; real Auth.js handoff with dummy credentials; production OAuth unchanged |
| HeySow light authentication | Complete and tested locally | Responsive sign-in and truthful unsupported account states; existing HeySow assets reused |
| Backend regression recovery | Complete local regression gate | Stage-27 full result: 599 passed, zero failures/errors, one deliberate live-mail skip; PostgreSQL included after isolated Redis-fixture correction |
| Existing workflow browser regressions | Complete and tested locally | 26 passed after membership repair and updated HeySow/default-denial contracts |
| PostgreSQL validation | Implemented local disposable acceptance | Official-source PostgreSQL 16.15, private Unix socket/no TCP; 20 cases pass in the complete suite, including workflows, concurrency and real pre-upgrade recovery. Production URL never used |
| Workspace membership authorization | Implemented, partially audited | Active memberships authoritative; last-owner protection and owner-granted legacy team roles tested; residual data paths still under audit |
| Workspace role management repair | Complete and tested locally | Existing role API updates memberships, maps OPERATOR to MEMBER, audits changes; workspace isolation/last-owner tests |
| Workspace switching | Implemented and locally tested, gated off | Migration 18 personal preference; active membership/revocation checks; selector/API/browser checks; no silent cross-workspace fallback |
| Public registration | Not implemented | Existing allowlisted OAuth retained; signup page does not provision accounts; explicit production-disabled flag and real test onboarding still required |
| Invitations | Implemented locally, gated | Migration 19; hashed one-use tokens, recipient/role/expiration/revocation checks, real team UI/API; PostgreSQL concurrent acceptance grants once. Public signup/delivery remain unavailable |
| Organization/profile storage and setup | Implemented local foundation, gated | Real creation, profiles and resumable validated objectives/services/ICP/preferences; zero automatic scan/send on completion; product access blocked before setup |
| Domain discovery/verification | Implemented locally, gated | Hash-only DNS challenges, bounded checks and revocation; bounded website jobs propose literal metadata with confirmation/provenance. Live external acceptance and staging remain pending |
| Organization settings | Implemented, partially tested | Additive migration 17 fixes singleton storage; two-workspace settings and SQLite upgrade preservation pass; PostgreSQL pending |
| Customer integrations | Partially implemented infrastructure | Existing internal Gmail and read-only Sheets adapters retained; internal mailbox denied to other workspaces; general customer mailbox model absent |
| ICP management | Implemented local foundation, gated | Builder, owned versions/status/duplication, history/comparison, optional reviewed AI drafts and onboarding selection. Discovery use, saved filters and deletion safeguards remain |
| Overture/OSM and Firecrawl/import acquisition | Existing functionality, partially SaaS-ready | Source adapters, jobs and tests retained; owner propagation repaired; comprehensive ownership/usage audit and progressive customer discovery still needed |
| Separate companies and contacts | Partially implemented | Prospects/business observations and contact_people exist; full customer company/contact intelligence UI and relationship lifecycle missing |
| Contact evidence / review security | Repaired locally, under regression verification | Missing context fails closed; foreign prospect evidence denied; null-identity review rows filtered by run owner |
| Duplicate-resolution security | Repaired locally, under regression verification | Merge validates ownership and owner role; new identity decisions namespaced by organization; old decisions retained via scoped lookup |
| Sales lists/campaigns/reports | Existing functionality, partially SaaS-ready | Retained APIs and browser flows; no claims of complete customer-specific outreach/template experience |
| Internal archive | Disabled by default, tested | Direct pages/APIs/preparation cannot bypass availability; historical content remains retained |
| Public API keys/webhooks/MCP | Not implemented | Internal signed BFF API is not a customer API or genuine MCP server |
| AI gateway | Existing Vertex-first architecture retained | No provider credentials changed; model routing/batching tests remain; no new live provider acceptance claimed |
| AI Assistant/Agent | Not implemented | No conversation store, tools/approval workflow or functioning assistant UI; module stays planned |
| Usage/entitlements/billing | Partially implemented / missing SaaS layer | Existing provider counters and hard limits are not a subscription/entitlement system; no paid provider or invented plan state |
| Public staging/release readiness | Blocked | PostgreSQL, residual ownership audit, complete account/workspace/onboarding flows and subsequent phases remain |

## Execution order

1. Finish residual ownership audit and revalidate backend/frontend/browser gates.
2. Complete and freeze the combined local PostgreSQL gate, retaining separate staging approval requirements.
3. Implement SaaS account/workspace/invitation/profile contracts behind explicit
   disabled-by-default gates and isolated tests; do not expose them to customers.
4. Build actual onboarding and ICP setup, then connect existing discovery through
   the shared owned services. Continue in the attachment's dependency order.
5. Implement customer integrations, public API/MCP and Agent only over authorized,
   tested services. Never represent a planned module as available.

## Safety and checkpoints

The earlier recovery checkpoint and all user changes are retained. Environment
files remain unchanged except the explicitly owner-authorized local sign-in
allowlist addition. Production credentials, databases and infrastructure remain untouched.
No scan, campaign or email is launched by this work. Missing credentials are
recorded as external setup work, not requested while the owner is away.

## Current incremental milestone

The preceding stabilization checkpoint now has **502 backend passes**, zero
failures/errors and 15 explicitly excluded external/live tests. Workflow browser
checks now pass **26/26**, including owner-granted shared workspace access and
truthful default-denied archives. Frontend units now pass **51** after adding
workspace-selector state tests. These figures are superseded only by a later
recorded complete run, not inferred from partial tests.

Workspace selection is now **implemented and locally tested**, behind the
false-by-default HEYSOW_WORKSPACE_MANAGEMENT_ENABLED gate. It has backend
membership/ambiguity/revocation tests, a connected header selector, typed API
responses and UI loading/error/pending behavior. Migration 18 stores the personal
selection. It does not implement organization creation, invitations, signup or
onboarding. The dedicated browser checks pass. No production flag or environment file was changed.

## Foundation extension checkpoint

The latest completed full run before workspace creation is **521 backend tests
passed, 15 skipped** (14 PostgreSQL and one live-send test). Frontend units passed
**58** after the creation form was added; subsequent edits and full schema-20
verification are recorded separately once completed. The production frontend
build passed after invitations. Three real local API/browser checks passed for
workspace selection, company profile/conflicts and invitation creation/revocation.
The separate recipient acceptance browser check is being added and must not yet
be claimed as passing.

Further repaired boundaries: assignee choices are active workspace memberships;
foreign/revoked assignees cannot mutate a lead. Domain validation verifies contact
ownership before DNS. Platform-global controls remain internal-only. Acquisition
evidence, imported contact-person records and review cases now persist ownership
and reject a foreign run. API and worker startup require the current schema before
owned runtime queries. The unused test auto-provision helper was removed.

New capabilities remain behind **HEYSOW_WORKSPACE_MANAGEMENT_ENABLED=false**.
No public registration, production configuration, migration, sending, acquisition
or provider credential was activated.

## Residual acquisition isolation repair

The final foundation run before this repair completed **534 passed, 15 skipped**,
with zero failures/errors. A subsequent audit found shared acquisition preferences
and actor-only AI interpretation cache keys. Migration 21 and scoped preference
services now separate customer source budgets/toggles from platform provider
state. New AI cache records and keys are organization-owned; expiry cleanup is
scoped. Internal Sheets credentials/provider tests and archived copy generation
are unavailable to customer workspaces, including direct service calls.

These are release-blocking boundaries until the current full suite and staging
evidence pass. Initial focused acquisition regressions passed 54 tests; the
expanded source/import/copy isolation group passed 45, and upgrade/isolation
checks passed four. Later complete results supersede these focused counts.
No runtime environment or production schema was changed.

## Verified stage-21 checkpoint and next milestone

The full backend suite after acquisition/cache/internal-service repairs completed
**540 passed, zero failures/errors, 15 skipped**. A final creation-name validation
case was then added and passed in the four-test creation group; the matching full
run is in progress. The current frontend has **60 unit passes**, a successful
production/TypeScript build, **26 workflow**, **6 workspace** and **3 authentication**
browser passes. Source settings and customer integration guards are represented
truthfully; no external integration was activated.

Next implementation work remains within the disabled foundation feature: complete
manual onboarding with persisted validated objectives/services/ICP/preferences,
then bounded public company-domain discovery and real ownership verification.
Do not expose the unconditional seed completion helper. Public admission needs a
coherent explicit false-by-default registration gate across Auth.js/session and
signed backend identity; do not weaken the allowlist ad hoc. Customer integrations
need workspace-owned encrypted credentials rather than adopting internal actor
connections. PostgreSQL validation/restore remains externally blocked; no question
or credential request is made while the owner is away.

Final stage-21 full verification completed: **541 passed, zero failures/errors,
15 skipped**. Frontend **60 unit tests**, production build/TypeScript, **26 workflow**,
**6 workspace** and **3 auth** browser checks pass. The local preview requested by
the owner is running at http://localhost:3000 against a separate disposable local
backend, real sign-in, disabled providers and disabled sending. Production remains
unchanged. This is a foundation checkpoint, not completion of the SaaS roadmap.

## Structured ICP increment

Migration 22 and the gated structured ICP builder are implemented locally. Five
service/API tests and the dedicated upgrade/restore test pass. Frontend units pass
62, production/TypeScript build passes, and seven real workspace browser flows
pass including ICP creation, versioning and inactive duplication. The full backend
run is being completed; do not infer a new full count by adding targeted results.
AI-assisted ICP creation, discovery use and complete onboarding remain unfinished.

The temporary test environment disappeared after interruption. It was restored
under the ignored project .venv with Python 3.12. The pinned cryptography 50.0.2
failed to compile on this runtime, so the local environment retains its existing
48.0.1 package; repository lockfiles are unchanged. This environment difference
must be resolved/validated in staging before any release certification. The local
preview now has a repeatable scripts/local_preview.py launcher and persistent
ignored local data; real authentication is retained and provider actions are off.

Final structured-ICP checkpoint: **547 backend tests passed, zero failures/errors,
15 deliberately skipped**. **62 UI units**, TypeScript, production build and
**7 workspace browser flows** pass. Mobile pagination/actions were visually
reviewed and adjusted. No complete SaaS, PostgreSQL or production-readiness claim
is made. The remaining ICP capabilities and onboarding/integration blockers are
listed in HEYSOW_ICP_SYSTEM.md and HEYSOW_RELEASE_READINESS.md.


## Customer connection foundation and new UI brief — 2026-11-06

Schema 27 adds encrypted workspace connections and actor/workspace-bound OAuth
states. Read-only Sheets connect/reconnect/refresh/status/disconnect and metadata
inspection are locally implemented behind a default-off flag. The complete backend
passes 610 with one live-mail skip (22 real PostgreSQL cases); UI units pass 81,
types/build and one intercepted provider-handoff browser check pass. Actual owner
Google consent/reads, Sheets imports/sync, Gmail and CRM connections remain incomplete.

The newest owner brief makes **PlaneByte** the final customer-facing brand while
retaining the indigo light-first design. It overrides the earlier HeySow wordmark
requirement, not backend identifiers or isolation. Current focus is one shared
collapsible shell, dedicated resumable onboarding, organized vertical Settings and
separate personal account routes. Further connector expansion is held during this
UI work. No production or OAuth configuration is changed.
