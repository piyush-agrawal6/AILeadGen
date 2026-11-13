# Intent Radar Phase 4 implementation

Implementation started 2026-11-13 from `a03f7a0`, existing deployed schema 44.
This file records contracts and evidence, not a readiness claim.

## Dependency matrix

| Capability | Latest verified foundation | Phase 4 work |
|---|---|---|
| Identity/workspaces | Real Google, server membership, owner-only Beta | Reuse; real approved-owner browser acceptance still required |
| Signals/sources | Owned normalized evidence, cursors, quotas, bounded HN production acceptance | Reuse; cross-post grouping and coverage-aware aggregate snapshots |
| AI | Existing Vertex router, exact quotations, accounting and reservations | Reuse for bounded theme/research jobs; no new provider |
| Ranking/ICP/feedback | Versioned explained ranking, current ICP/profile and private feedback | Reuse in opportunity and research context; no purchase probabilities |
| Worker | Durable leased intelligence jobs and existing Cloud Run dispatcher | Add owned Growth analysis kind with cancellation/recovery fences |
| Monitoring | Actual deployed scheduled monitor completed | Link Growth watchlists to existing monitors and in-app alerts |
| Market dashboard/themes/trends | Not implemented in current source | Implement real stored-data analytics, persisted cited themes, safe comparisons |
| Research/reports/competitors | No complete Growth workflow | Implement saved cited research/reports and deliberate competitor/watchlist controls |
| Developer API/MCP | Genuine scoped deployed reads and revocation | Add least-privilege Growth reads under existing intent scope |
| Independent evaluation | Approved protocol; no reviewers/adjudicator or complete labeled corpus | Implement blind packaging/review/adjudication/metrics; never invent human labels |
| Additional sources | Approval-dependent, currently HN-only production | Keep unapproved collection off; do not block independent engineering |

## Release constraints

Frontend stays on existing Vercel, backend/jobs on existing Google Cloud, database
remains existing PostgreSQL. No marketing changes, public signup, live outreach,
paid infrastructure or expanded provider/source quotas. New storage is additive;
backup, exact restored-history validation and compatibility checks precede release.

Growth belongs to the existing Intent Radar entitlement. A default-off capability
flag blocks direct API and worker execution until the schema and security checks
pass. Historical records remain intact when disabled. Evidence and exports recheck
workspace membership, entitlement, retention and current source availability.

Theme names and summaries are interpretations; source quotations and cited IDs are
validated. Counts use deduplicated collected conversations, never invented market
size. Period percentages require adequate samples and comparable collection
coverage; otherwise show the observed counts and explicit insufficiency.

Owner approved the unchanged 120-case independent evaluation protocol. Two actual
independent reviewers and a third adjudicator are not yet arranged. Tooling may
be complete while independent acceptance remains pending. No fabricated people,
human labels, publisher permissions or quality results are allowed.

## Implemented contracts and current verification

Schema 45 adds owned research snapshots, immutable theme/evidence relationships,
competitors, watchlists linked to the existing monitor service, revisioned team
notes, and deliberate existing-company links. Source availability, retention,
membership and job leases are rechecked before persistence/export. All old tables
and historical migrations remain intact.

The dashboard, theme/detail views, collection trends, cited research, saved
research, competitor criteria, draft watchlists, report generation and actual
Markdown/CSV/JSON exports use shared signed APIs and leased workers. Research
selects at most 12 candidates for bounded semantic interpretation; this is not
global embedding retrieval. Date comparisons require comparable checks/settings
and adequate per-period samples. Missing history is explicitly unavailable.
Lexical fallback and cached output are labeled separately from new AI output.

Four Growth MCP reads are separately gated; the original nine Radar read contracts
remain unchanged. Intent-only credentials work without Lead Engine, while company
scopes still require that separate entitlement. Product revocation blocks affected
credentials before protocol dispatch.

Blind-review packaging, exact-ID/evidence validation, frozen hashes, two-reviewer
agreement, third-person adjudication, post-inference safety review, metrics,
confidence intervals, slices and error analysis are implemented as offline tools.
Offline attestations require owner-verified human provenance. No independent human
labels, publisher approval, reviewed price or metric result is fabricated.

Fresh schema 44 backup was restored exactly and upgraded to 45 locally. Every
original column in 157 tables compared equal after migration. The original data,
including email/suppression history, was preserved. Recovery evidence remains in
restricted `data/backups/beta-recovery-20261113T110656Z`.

Initial browser runs exposed and repaired numeric date-query parsing and a generic
job-control route that shadowed note saves. The subsequent full local Growth
browser journey passed. One initial assertion matched unsaved textarea text; the
corrected test waits for a persisted note record and verifies it after reload.
The full first regression run recorded 940 passes/two MCP-contract failures; both
are repaired and a fresh complete regression run is required before rollout.

Manual theme merge/split, global semantic retrieval, independent multilingual
quality calibration, external alert delivery and additional vendor sources are
not claimed complete. Current production source permissions remain unchanged.
