# Final product overhaul — working audit

Date: 2026-11-14. This is implementation tracking, not a commercial launch certificate.
Starting production application source: `ca4e374742a5e49f25e05e2a1a51d8a9bc700cd3`.
Starting repository HEAD: `a608210`.

| Area | Implemented change / existing behavior | Acceptance still required |
|---|---|---|
| Overview | Batched counts; bounded current evidence; source-health history removed from critical overview response | Staged and production latency after rollout |
| Discovery | Existing bounded public-source workers and source-specific coverage retained | Controlled real-source run with new worker |
| Signals | Current-source checks and page-level ranking batches retained | Real evidence and analysis acceptance |
| Opportunities | Source details hydrated in one bounded batch; optional intelligence loaded when opened | Production populated page |
| Monitors | Existing activation, schedule, lease, cancellation and revision fences preserved | Real scheduled run and recovery evidence |
| Alerts | PostgreSQL wildcard bug in source/activity filters repaired with bound parameters | Live filter and alert history |
| Market overview | Existing scoped analytics retained; layout uses available width | Production acceptance |
| Themes | Evidence validity and small-sample limitations preserved | Real source interpretation |
| Trends | No invented market-wide statistics | Historical coverage remains limited |
| Research | Existing durable research reused for private assistant turns | Real Vertex multi-turn acceptance |
| Watchlists | Existing draft-first monitor linkage retained | Scheduled worker acceptance |
| Competitors | Existing reviewed names and aliases retained | Real workspace review |
| Reports | Existing evidence-linked exports and stale-source denial retained | Real report export |
| Library | Saved-signal hydration batched; saved research remains distinct | Production persistence |
| Assistant | Global contextual drawer, bounded structured Vertex gateway, citations, private conversations, explicit fallback; no action execution | Production Vertex and owner browser acceptance |
| Integrations | Existing source catalog and scoped MCP remain; no invented OAuth connections | External client setup and production read probe |
| Workspace/settings | Existing membership, profile, domain, ICP and team controls retained | Production save/reload matrix |
| Account/security | Existing real Google access retained; billing added to account menu | Owner and approved second-account acceptance |
| Billing | Actual Beta access/usage separated from commercial catalog; inert plan handoff preserved | PayU recurring implementation/acceptance and owner commercial gates |
| Usage | Current operator limits and provider-reported tokens displayed; unpriced AI cost remains unknown | Approved commercial numeric limits and provider pricing |
| Help | Contextual assistant cites scoped evidence and product documentation | Broader help content review |
| Navigation | Single grouped product navigation; duplicate eight-tab Growth navigation removed; all routes retained | Six-viewport screenshots and real owner review |

## Performance evidence

Eight sequential authenticated reads were sampled against the existing production
revision `leadengine-api-00135-paw`. Two samples per route are diagnostic, not a
statistically reliable p95 or load certification. Overview: 48.405 seconds and an
85.237-second client timeout (the server eventually logged 102.360 seconds).
Source health: 13.994 / 13.808 seconds. Opportunities: 14.892 / 15.316 seconds.
Saved signals: 19.764 / 10.137 seconds. This fails a responsive SaaS read budget.
After-rollout measurements must be recorded separately; local SQL counts are not
production latency claims.

Changes reduce repeated membership/onboarding round trips while retaining fresh
server checks, reduce count/ranking hydration queries, and add request-local
`Server-Timing` DB round-trip instrumentation. No permission cache, broad response
cache or provider request is added to mask a slow read.

## Design references

The grouped navigation and contextual controls follow the general productivity
patterns documented by [Linear display options](https://linear.app/docs/display-options)
and [initiatives](https://linear.app/docs/initiatives), using PlaneByte's own
components and identity. No third-party product imagery or proof is fabricated.

## Preservation

No Lead Engine route, provider, worker, database table, migration or customer
record is removed. Availability remains reversibly server-gated. There is no
database migration in this changeset. Existing marketing work is a separate
repository; the new owner pricing brief authorizes its pricing changes only.

## Financial gates

Monthly USD list prices are approved. Numeric commercial allowances, actual
PayU recurring currency, tax/conversion terms, account-enabled Zion contract,
real recurring acceptance, exact real-money test approval and public checkout
authorization remain separate gates. A one-time payment must not satisfy them.
