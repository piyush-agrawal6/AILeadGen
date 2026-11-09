# HeySow cleanup report — 2026-11-05

Status: **in progress; not approved for production release**. Changes described
here are local implementation work. No production deployment, operational database
cleanup, credential change or scheduler activation was performed in this stage.

## Implemented

- Premium light HeySow authentication layout, branding, metadata, responsive
  states and real Google OAuth handoff. Password and public registration actions
  are not fabricated; unavailable flows are stated explicitly.
- Customer navigation omits the internal experiment results and report-first
  workflow. Historical code and records remain recoverable.
- Disabled-by-default internal experiment policy enforced at the API, preparation
  and worker boundaries, with owner/internal-workspace restrictions for archives.
- Workspace template rendering uses the organization's identity and signature
  without requiring audit findings or a PDF. Cross-workspace template upserts
  are blocked atomically. Complete campaign template selection remains pending.
- Acquisition contact evidence reuse is workspace-scoped. New acquisition runs
  carry the job's organization, and observation validates persisted resource
  ownership before writes.
- Removed reproducible caches after a dry run and restore test; removed the
  unused Recharts dependency and 35 lock entries without changing retained
  dependency versions. See `DATA_CLEANUP_REPORT.md`.
- Added the engineering audit, standards documents, decision record and repository
  instructions. Documents distinguish current implementation from planned work.

## Verification

- Frontend unit suite: 49 passed at this stage's last complete frontend run.
- Authentication browser suite: 3 passed, including responsive layouts, route
  boundaries, sanitized errors and the actual Auth.js Google handoff with dummy
  credentials. The test does not claim a real provider login was completed.
- Frontend type check and production build passed with fixture authentication
  configuration. No production credentials were changed.
- Targeted module/template/workspace resource security tests: 7 passed.
- Full backend baseline: 347 passed, 70 failed, 70 errors, 15 skipped. This is a
  failing baseline; missing organization context is a common cause, but failures
  still require individual classification and repair.

## Remaining release blockers

Complete tenant-aware integration and registry access; repair remaining caller
and fixture ownership contracts; validate identity alias isolation; implement and
test real onboarding/public registration safely; implement the ICP-based default
and complete workspace-template campaign preparation. Operational archival needs
a fresh database-specific dry run, backup, tested restore and ownership review.
The local cache backup is not a production database backup. End-to-end staging
validation and owner-approved deployment remain outstanding.
