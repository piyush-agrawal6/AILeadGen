# HeySow SaaS architecture — current implementation

The application remains a modular monolith: Next App Router/Auth.js frontend,
signed FastAPI BFF gateway, existing Python domain services and existing background
workers. PostgreSQL is the production adapter; SQLite is isolated-test storage.
No new runtime service, paid provider or production infrastructure was introduced.

Authentication identifies a user. Active organization membership authorizes
workspace operations. Role administration now updates that membership, protects
the last active owner under a transaction lock and records a scoped audit event.
Legacy account_roles rows remain historical data, not an authorization fallback.

Request-local WorkspaceContext validates membership before scoped data access.
Workers derive context from persisted job ownership. The internal mailbox cannot
be used by customer workspaces. Public tracking capability context is separate
from membership authority and cannot authorize mailbox operations.

Migration 18 adds a personal active_organization_id preference without granting
membership. Selection revalidates target membership; a revoked selected membership
never silently falls back to another workspace. With the workspace-management
feature enabled, multiple memberships require explicit selection. The existing
single-workspace behavior remains unchanged while the feature is disabled.

## Feature gate

`HEYSOW_WORKSPACE_MANAGEMENT_ENABLED` defaults to false on both the backend and
frontend runtime. No environment file or deployed value was changed. In an
isolated test environment, enabling this nonsecret flag exposes the current
membership list, validated workspace selection, explicit idempotent workspace
creation, personal/company profiles and invitation lifecycle. It does not enable
public signup, scans, email sending or customer mailboxes. The local gated setup
now validates persisted steps before explicitly completing onboarding.

The browser reloads after confirmed selection so data cached under the previous
workspace is discarded. Failed selection retains the previous workspace. Backend
membership and ownership are always rechecked, including for VIEWER accounts;
changing one's own selected workspace does not grant write permission to either
organization.

## Incomplete platform capabilities

Customer registration, ownership-transfer UI, complete discovery-connected onboarding,
entitlement billing, public API/MCP and Agent features remain incomplete. Workspace
creation and invitations are now connected behind the disabled management gate;
public invitation delivery and new-account acceptance still require later work. They remain separate milestones over the same
identity and domain services. Do not advertise missing modules or make the
internal Gmail integration appear connected for customers.

Disposable local PostgreSQL 16.15 acceptance now exercises current migrations,
workflows, independent concurrent connections and pre-upgrade backup restoration.
Approved staging and exact locked-runtime acceptance remain separate gates.

## Additional foundation storage and contracts

Migration 19 adds hashed invitation capabilities and scoped in-app notifications.
Migration 20 adds account/request-key workspace-creation idempotency. These are
additive and locally tested; no deployed schema was changed. Creation assigns the
server-authenticated account an explicit owner membership and starts incomplete
onboarding. Retrying a completed creation does not change later workspace choice.

Personal profile data remains keyed by user, independent of organization profile
and membership. Viewers may edit their own profile but not company information.
All new API bodies reject caller-selected actor/ownership fields. Invitation and
creation responses have typed server schemas. Invitation responses carrying raw
one-time capabilities are no-store, and only their hashes are persisted.

Concurrent SQLite and PostgreSQL tests demonstrate one accepted membership and
one creation result for duplicate concurrent requests. PostgreSQL also exercises
last-owner preservation, optimistic ICP revisions and atomic DNS-check reservation.
The real first-user race fix retains exact ID/email matching. Configurable
operational limits default to five
owned workspaces and 100 pending invitations; they are safety ceilings, not paid
plan entitlements. No billing state is invented.

Migrations 23–26 add resumable setup, domain proof, asynchronous website-review
jobs and logical AI usage reservations. Website extraction reuses existing
workers and safe HTTP; optional ICP interpretation reuses the Vertex-first
gateway. Both provider features default off and require reviewed confirmation.
No competing job system, authentication service or paid infrastructure was added.
