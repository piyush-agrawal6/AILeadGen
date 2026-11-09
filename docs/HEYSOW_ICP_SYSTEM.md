# Ideal customer profiles — gated foundation

The structured ICP model, workspace-owned storage, typed API and builder UI are
implemented behind the default-disabled workspace-management feature. No deployed
flag, production schema or provider credentials were changed. Creating or
activating an ICP does not run discovery, analysis, qualification or outreach.

## Implemented

Company criteria cover industry/category, size, employee/revenue ranges, business
model, technology, maturity, geography, language and website characteristics.
Contact criteria cover roles/functions, seniority, department, responsibilities,
geography and professional requirements. Intent criteria cover needs, pain points,
signals, relevant services, qualification conditions and exclusions.

These are user-entered targeting preferences, not verified business facts. Empty
criteria, invalid ranges, non-finite revenue, oversized lists/terms and unknown
ownership fields are rejected. Monetary criteria have a currency label and do not
imply that prospect revenue data exists. No email requirement is inserted into
company-fit criteria, and no imported lead is requalified by this module.

Owners/administrators can create/edit, activate/deactivate/archive and duplicate
profiles. Members can read. Every read/write/history/compare operation uses the
verified current workspace. Foreign resource IDs are denied. Creation has durable
workspace/request-key idempotency; retries with changed contents are rejected.
Duplicates start inactive. A configurable operational limit defaults to 50
profiles; this is not a paid-plan entitlement.

Edits check the expected revision under an organization lock. Every real change
creates an immutable version and scoped audit event; unchanged saves do not add
versions. History is paginated and an API compares two stored revisions. The UI
shows saved criteria and preserves unsaved edits on errors. Its list is paginated
and filterable by status. There is no deceptive delete or AI-generation button.

## Migration and API

Additive migration 22 creates ideal_customer_profiles and icp_versions. The
version table has a composite workspace/profile foreign key. Existing tables are
retained. SQLite upgrade/preservation/idempotency/snapshot restore are tested;
PostgreSQL concurrency and restoration remain staging gates.

The authenticated routes are under /api/organization/icps: list/create, get/update
by UUID, duplicate, versions and compare. They are organization-onboarding routes
so criteria can be configured before product access is granted. Viewer writes
remain forbidden. The frontend is /settings/icp with the same disabled gate.

## AI draft assistance and onboarding (local schema 26)

The natural-language assistant uses the existing Vertex-first gateway behind
`HEYSOW_ICP_AI_ENABLED=false`. It proposes only explicitly requested criteria,
rejects unsupported model additions and never activates/saves a profile itself.
The owner reviews editable fields and explicitly saves an inactive draft. Errors
leave the manual builder available. No live provider request was used in these
tests. Logical-request budgets default to 10/organization/day and 100/global/day;
reservations commit before provider calls, and failed calls consume budget.
Organization/actor-specific cache hits avoid a new reservation. This budget is
not a provider-token charge estimate or customer billing entitlement.

The resumable company setup now selects an owned ACTIVE ICP; completion validates
that persisted selection. Another workspace's profile cannot be adopted.

## Remaining

Discovery usage links, saved filters, version-comparison presentation and safe
deletion with reference/retention checks remain unfinished. This module does not
alter the current acquisition policy. ICP-based
company qualification must remain separate from contact availability and sending
eligibility when that integration is implemented. Do not claim a complete ICP
or end-to-end SaaS workflow from the structured builder alone.
