# Intent Radar Phase 1 — local implementation

Recovered continuation, 2026-11-10. This document and the integration report were
absent when work resumed; this records the existing implementation and completed
verification, not a reconstruction of an unavailable original specification.

## Implemented and verified locally

- Native PlaneByte product switching and workspace-scoped `/intent-radar` pages:
  overview, discovery, monitors, signals/detail, saved collections, opportunities,
  alerts, settings and shared integration/MCP guidance.
- Server-resolved membership, onboarding and explicit organization product grants.
  `Disabled` is the default. `Internal Preview` additionally requires the workspace
  allowlist; `Beta` still requires an organization grant. Roles apply on every API,
  domain mutation, worker and MCP read. Unavailable products are hidden.
- Revisioned monitor wizard, edit/duplicate/pause/resume/archive/restore; saving is
  inert. Explicit manual checks run through the existing intelligence dispatcher.
- Official Hacker News v0 API: at most 20 recent Ask HN stories per check, local
  keyword/topic/phrase/exclusion/category/date/relevance matching. Source IDs,
  canonical discussion URLs, excerpts and observation/retrieval timestamps persist.
  Authors, external target URLs and comment trees are not collected.
- Deterministic, explainable classification and confidence/unknowns. Scores do not
  establish purchase authority, budget, identity, geography or language.
- Persistent review notes/status, bulk actions, saved collections/tags, human-selected
  opportunities with membership-checked assignment, in-app alerts and shared notices.
  Discovery deduplicates per workspace/source record; repeat checks preserve review
  and bookmarks. Alert events and opportunity selections are idempotent.
- Optional structured AI configuration drafts reuse the existing gateway, owned
  cache and committed usage limits. Manual fallback works. Drafts require review
  and do not execute discovery. Read-only MCP tools reuse scoped developer keys.

## Operational contract

- Migrations **41–42** add Intent Radar records and captured monitor revisions.
  No destructive rollback: disable access and retain history. Isolated additive
  upgrade/repeatability/backup/restore checks preserve contact and suppression flags.
- Source fetch timeout: 28 seconds; HTTP timeout: 4 seconds; at most 22 requests
  per attempt. One bounded 429/503 retry honors cooldowns up to three seconds.
  Longer cooldowns fail safely. Shared jobs permit at most three attempts.
- Leases and monitor revision/status are checked before and after fetch and fenced
  at persistence. Cancellation, pause/resume races, expired/replaced leases and
  authority changes prevent stale evidence/alerts from being written.
- Default capacity: 20 workspace searches/day, 100 global/day; configurable bounded
  monitor/search limits plus existing intelligence active-job/record limits.
- Engineering owner: PlaneByte application owner. Uses the current modular monolith,
  database, gateway, authenticated product shell and worker; no added infrastructure.

## Explicit scope and acceptance

Schedules, historical/full-text source search, other sources, contact acquisition,
Lead Engine record linking, exports, outbound email/messages and MCP write tools
are not implemented by Phase 1. No paid subscription state is implied.

Local application verification is complete for the scope above. Fresh PostgreSQL
acceptance remains blocked by the absent local runtime; production/public readiness
is not certified. Exact results, failures and resume checkpoint:
[`INTENT_RADAR_PHASE_1_INTEGRATION_REPORT.md`](INTENT_RADAR_PHASE_1_INTEGRATION_REPORT.md).
