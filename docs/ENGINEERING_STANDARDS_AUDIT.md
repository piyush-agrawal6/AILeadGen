# HeySow engineering standards audit

This audit describes the current checkout, not a production-readiness certification. The implementation preserves the Next16.4.3 / React19.3 / Auth.js5 frontend, FastAPI modular backend, PostgreSQL production adapter and SQLite test adapter. No new paid service or infrastructure has been introduced.

| Area | Current implementation | Problem | Required standard / action | Priority |
|---|---|---|---|---|
| Architecture | Python domain packages and Next App Router | Some services import HTTP handlers | Shared service boundaries; settings lookup extracted to `app/config/workspace.py` | High |
| Security | HMAC gateway, nonces, CSP, origin validation, SSRF-safe HTTP | Template upsert could transfer ownership | Scoped precheck plus conflict-update ownership predicate added; cross-tenant regression passes | Critical |
| Authentication | Verified allowlisted Google OAuth, eight-hour JWT | Public signup/password/invitations absent | Preserve verified-email/access checks; do not enable public signup until tenant and account backend is complete | Critical |
| Multi-tenancy | Additive organization migration and membership resolution | Legacy mail account/registry and callers still need complete scope audit; existing tests omit organization context | Block public release; explicit tenant context and cross-tenant tests are required | Critical |
| Database | Versioned migrations; parameterized repositories | Current foundation has integration regressions | Keep migrations/data; no reset; fix shared contracts and test migration preservation | High |
| Caching | Upstash allowlisted reads keyed by actor, organization, path, filters and generation | No measured distributed load baseline | Preserve safety-route exclusions; measure hits/latency and invalidate on writes | Medium |
| Performance | Query cache, pagination, bounded workers | Auth previously loaded product shell | Auth uses a server-derived public-page marker and renders no workspace polling; browser test verifies zero private API calls | Medium |
| Background jobs | Cloud Run workers, leases and idempotent ledgers | Old experiment tick remained reachable | Disabled-by-default module guard added before database/provider work | High |
| APIs | Pydantic, HMAC, role checks | Some unscoped legacy operations remain | Workspace/resource/permission/module checks; no public rollout until audited | Critical |
| Integrations | Gmail SMTP/IMAP, storage, Sheets, source adapters | Runtime Gmail credentials are not a general per-customer connection model | Preserve internal integration; do not represent other workspaces as connected | High |
| AI | Existing Vertex-first gateway/fallback | Legacy campaign generation is not a default SaaS workflow | Keep gateway, gate old experiment; never auto-generate unsupported findings | High |
| Testing | pytest, Vitest, Playwright | Organization-foundation regression baseline is not green | Record failures; do not weaken access checks to pass tests | Critical |
| CI/CD | Pinned locks, container validation and frontend build | No approved new deployment | Local build/test only; staging, backup/restore and approval precede production | High |
| Monitoring | Health, job events, redacted diagnostics, cache counters | No new scale/uptime measurements | Correlation IDs and measured alerts; no scalability claims without staging tests | Medium |
| Scalability | Modular monolith, bounded concurrency | Capacity not established for public SaaS | Synthetic staging load tests; no uncontrolled production load | Medium |
| Developer experience | Shared controls/services, environment templates | Generated clutter and unused dependency | Removed reproducible cache after audit/restore check; unused Recharts removed without upgrading other packages | Medium |

## Evidence

- Auth unit tests:49 passed at the first HeySow baseline; subsequent results recorded in the cleanup report.
- Auth browser tests:3 passed, including desktop/mobile, protected routes and actual Auth.js OAuth handoff with dummy credentials.
- New module/template/resource tests:7 passed; disabled jobs do no database/provider work, templates cannot cross workspace ownership, and existing lead evidence cannot be reused across workspaces.
- Production frontend bundle built successfully with isolated fixture values.
- The broader backend baseline exposed an existing missing `Request` import and organization-context integration failures. The import was fixed. Remaining failures are release blockers, not suppressed warnings.

## Backend baseline and current repair scope — 2026-11-05

The isolated full backend baseline completed with **347 passed, 70 failed,
70 errors and 15 skipped**. This is not a passing release baseline. Many fixtures
and callers omit the now-required organization context; other failures require
individual classification. Do not characterize all failures as fixture problems.

The acquisition worker now persists its job's organization on new pipeline runs,
passes it to imported-lead observation and scopes reuse of existing contact
evidence. `app/platform/workspace.py` checks the persisted business/run/campaign
ownership before canonical observation. No implicit owner default or test-only
authorization bypass was introduced. Missing and mismatched context fail before
writes. These repairs have targeted regression coverage; the entire acquisition
workflow and broader backend suite are still pending revalidation.

Remaining critical work includes legacy global Gmail/registry ownership,
organization-scoped identity aliases, complete API/job scope propagation and
public account/onboarding flows. None may be represented as implemented merely
because the corresponding standards document exists.


## Development recovery — 2026-11-05

Recovery reproduced all 140 original failing/error test IDs. Membership-backed
request/job scopes, internal-mailbox isolation, scoped registry/identity aliases,
owner propagation, scoped reconciliation and additive settings migration 17 were
implemented locally. Existing tests were retained; explicit owned fixtures replace
legacy global-owner assumptions. No production changes or sends occurred.

The recovery is **not complete**. Use `HEY SOW_REGRESSION_TRIAGE.md` for per-case
status, `HEY SOW_STABILIZATION_REPORT.md` for evidence and
`HEYSOW_STABILIZATION_TEST_RESULTS.json` for the latest verified counts. Earlier
347/70/70 figures above are historical baselines, not current results. Remaining
failures, PostgreSQL validation and incomplete path auditing continue to block
release. Public registration remains unavailable.

Latest frozen backend verification: **499 passed, 0 failed, 0 errors, 15 skipped**.
Every original failing/error case is resolved. PostgreSQL, broader browser workflow
validation and residual path certification still block the overall release.

Broader workflow browser result: **9 passed, 3 failed, 14 not run** after the
configured three-failure stop. A real legacy role-management/membership mismatch
remains, along with two outdated UI/archive contracts. Overall stabilization is
not complete despite the green backend suite.


## Subsequent foundation verification — 2026-11-05

The earlier 9-pass/3-fail browser result is historical. Scoped role management was
repaired and outdated UI/archive contracts were updated while retaining access
checks. All **26 existing workflow browser tests now pass**. The separate **3 auth
browser checks** and **6 gated workspace browser checks** also pass. Frontend units
pass **60**, and the production build with fixture settings passes.

The last completed full backend run is **530 passed, zero failures/errors, 15
skipped**. Later focused concurrency/migration/configurable-limit/typed-contract
checks pass; the next full frozen run is recorded separately after completion.
New gated foundations include creation/selection, company/personal profiles and
hashed invitations. Public signup, complete onboarding, PostgreSQL validation and
the remaining SaaS phases still block release. No production configuration, data,
sends, acquisition or infrastructure was changed.


## Latest local foundation checkpoint — 2026-11-06

Schema 26 local verification is green: 599 backend passes with PostgreSQL included,
one explicit live-mail skip, 76 UI units, successful types/build, 26 workflow,
three auth, eight workspace and one real-signed-preview browser checks. The
PostgreSQL subset has 20 passes and no skips. A real first-identity insertion race
was fixed while preserving exact ID/email matching. DNS proof, resumable validated
setup, bounded reviewed website proposals and optional reviewed ICP AI drafts are
implemented locally behind gates. Customer integrations, public admission and
later SaaS modules remain incomplete. Approved staging and the exact locked crypto
runtime still block release. Earlier results in this audit are historical.


## Lead Engine prospecting separation — 2026-11-06

The current local product no longer runs mandatory website/SEO/AEO/GEO,
Lighthouse, performance or security assessments. Company enrichment and ICP fit
use bounded workspace-owned evidence; contact availability and sending safety
remain separate. Customer-owned templates replace mandatory experiment copy/PDFs.
Historical records and migrations remain intact. Legacy company read routes were
fixed to pass verified workspace scope, and artifact reads fail before storage
access without ownership. Planned Search Visibility owns reusable saved-data
parsers and historical quality checks; no new assessment product is enabled.

Final local verification: **624 backend passes, 1 explicit live-mail skip**,
including **22 PostgreSQL passes**; **89 UI unit passes**, TypeScript and isolated
production build pass; **41 browser passes** across workflows, workspaces, auth,
real-signed local gateway and customer-connection handoff. Initial cleanup
failures and their repairs remain recorded in stage27 logs.

See `PLANEBYTE_PROSPECTING_SEPARATION.md` and
`PLANEBYTE_PROSPECTING_ACCEPTANCE.json`. No production reset, deployment, secrets,
OAuth configuration, infrastructure or real outreach was changed. This verifies
the local cleanup, not public SaaS production readiness. Approved staging and
the exact locked crypto runtime remain release requirements.
