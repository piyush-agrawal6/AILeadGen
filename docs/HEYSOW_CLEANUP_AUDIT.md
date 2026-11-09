# HeySow cleanup audit

Scope: authentication redesign plus the owner-supplied HeySow cleanup brief. Latest cleanup rules supersede the old contactable-only/fixed-template experiment. No database reset, truncation, production deployment, infrastructure changes or real email tests are authorized for this work.

| Category | Item | Current purpose | Used? | Proposed action | Risk |
|---|---|---|---|---|---|
| Authentication | `dashboard/auth.ts`, `proxy.ts`, server session helpers | Verified, allowlisted Google OAuth; eight-hour JWT sessions | Yes | Preserve policy, cookies, sessions and credentials; replace presentation | High if access checks change |
| Authentication | Registration/password/recovery/invitation endpoints | No implemented routes or credential provider found | Missing | Capability-aware screens; public account backend requires a safe additive implementation and tenant bootstrap | High; never silently open legacy access |
| Branding | Login, root metadata, sidebar/header, orange CSS overrides | PlaneByte identity | Yes | Central HeySow brand, light indigo auth system and product chrome | Low |
| SaaS foundation | `organization_schema.py`, `api/organization.py`, tenant middleware | New additive organization/membership/onboarding foundation | Yes; incomplete routes | Preserve existing work; verify interfaces before extending | High |
| Qualification | `qualification/contactable.py`, source ProcessingOptions | Legacy contactability-only qualification | Yes | Retire as customer default; separate ICP match, contacts, verification, send eligibility | High |
| Campaigns | Workflow/campaign/source membership services | Shared production operations and historical attribution | Yes | Preserve relationships; classify records before any archive | High |
| Experiments | `app/experiments`, experiment routes and dispatcher | Old five-day sales experiment | Shared services and legacy tests depend on it | Gate customer/API/dispatcher entry points; retain reusable services and history | Medium |
| Templates | PB_INTRO_01–05 and `outreach/fixed.py` | PlaneByte experiment copy and immutable PDF | Historical/shared tests | Remove customer defaults; preserve immutable historical content | Medium |
| Data | Contacted registry, suppressions, sent messages, audit logs | Permanent safety/history | Yes | Preserve unconditionally; no broad deletion | Critical |
| Pages | `/experiments/nov-2026`, `/outreach/results` | PlaneByte experiment controls/analytics | Legacy | Hide and disable customer entry points; preserve read-only history separately | Medium |
| Workflows | Find Leads, campaign runs, schedules, settings | Working discovery/mail orchestration | Yes | Simplify labels/navigation; never advertise missing modules as functional | Medium |
| Dependencies | Next16, React19, Auth.js5, query, UI and Python integrations | Active runtime/build/test dependencies | Yes | Remove only after import and runtime-reference verification | Medium |
| Scripts | `scripts/operators`, release/migration/acceptance scripts | Operators, tests and container builds import/copy them | Yes/mixed | Keep; classify and document rather than deleting by filename | High |
| Files | `.pytest_cache`, `.next/cache`, test-results | Reproducible generated development outputs | Regenerable | Manifest and safely remove generated caches; archive relevant test artifacts first | Low |
| Files | `data/backups`, generated PDFs, private artifacts, environment files | Rollback, immutable assets, historical material and secrets | Yes | Retain; do not change `.env` or credentials | Critical |
| Jobs | Cloud Scheduler/Run, existing paused campaigns | Production infrastructure | Live state not verified in this task | Prepare guards and dry-run plan; no production mutation without approval | High |

## Verified constraints

The current authentication code has only the Google provider, strict `email_verified === true`, an allowlist, secure production cookies and signed server-to-server API forwarding. There is no password store or public signup implementation to connect a password form to. The organization foundation does not by itself prove public onboarding or tenant isolation is fully released.

Production access for the preceding task was blocked by an automatic approval-review usage-limit failure. That is not a finding that an action was unsafe. No bypass is permitted, and no production cleanup is claimed here. Existing snapshots are historical evidence, not a substitute for a fresh verified backup before a new operational cleanup.
