# HeySow security boundaries — implemented and remaining

This records tested implementation boundaries, not a security certification or
legal-compliance claim. Production configuration and credentials are unchanged.

## Identity and authorization

The existing Google/Auth.js flow checks verified email and the configured account
policy. JWT sessions, secure production cookies, CSP, private route protection and
the signed frontend/backend gateway are retained. The gateway verifies a bounded
request body, timestamp, nonce, actor and HMAC; reused nonces are rejected. Public
registration is not enabled and is not yet a coherent implemented account flow.

Every owned request/job binds an active membership of an active organization.
Missing context fails closed. Resource IDs do not grant access. Active workspace
preference is revalidated; revocation does not silently switch tenants. Workspace
roles, not global account_roles or a first-account shortcut, authorize actions.
Role changes lock the organization and preserve its final active owner.

Personal profile and workspace-selection exceptions let viewers manage their own
account preferences. They do not authorize organization writes. Invitation
response uses the signed recipient identity; body-supplied actors are rejected.

## Owned resources and caches

Canonical observation validates persisted scan/business/campaign ownership.
Identity aliases and duplicate overrides are workspace-namespaced. Foreign leads,
notes, contact evidence, reports and workflow operations are denied. Assignees must
be active members of the current workspace; historical assignments are preserved
when unrelated fields change. Contact-domain validation checks ownership before
any DNS operation and does not claim recipient delivery verification.

Migration 17 splits workspace settings from the retained legacy singleton.
Migration 21 splits source toggles/budgets from platform provider state and scopes
new AI interpretation cache records/keys to organization and actor. The same
account and prompt in another organization do not share a result. Expiry cleanup
only removes the current organization's cache rows. Historical unowned cache rows
are retained and cannot be adopted by a customer cache lookup.

The authenticated page cache uses actor, verified workspace, route/query and
generation keys after authorization. Its allowlist excludes inbox bodies,
eligibility, previews, sending, tracking, provider checks and new account APIs.
Failures fall back to live database reads, not stale authorization.

## Integration and capability isolation

Internal Gmail and the existing actor-keyed Sheets credentials are unavailable to
customer workspaces, including domain/worker entry points. Customer integration
configuration is incomplete; internal credentials never count as their connection.
Platform provider diagnostics/global controls remain internal-only. Shared Vertex
provider routing/cooldown is platform operational state, not a workspace setting.

The experiment archive is disabled by default and internal-only even when its
flag is enabled. Its legacy copy cache/generator is not a customer copy service.
Customer templates and provider-scoped usage still need a separate complete flow.

Invitations store only a random capability's digest, expire, and recheck current
inviter authority on acceptance. Raw tokens are returned once through no-store
responses, not audit fields. The private share link uses a URL fragment; response
is a deliberate POST by the named account. Stored public tracking capabilities
bind a separate constrained context and do not authorize mailbox access.

## Still required before public activation

Approved staging and exact locked-runtime validation, completed ownership review,
public identity admission and account lifecycle, customer encrypted integrations,
live acceptance of the locally implemented domain proof, per-workspace usage/entitlements, API scopes,
webhook/MCP security and permission-aware Agent tools remain unfinished. Customer
privacy/export/deletion/retention controls and legal review require explicit work.
Do not claim coverage merely because these requirements are documented.

## Local foundation verification additions

DNS proof stores a SHA-256 digest, not the one-time displayed value. Concurrent
checks reserve an attempt before DNS I/O; successful proof still rechecks the
current manager role and challenge. Proof grants neither membership nor mail
access. Website-review jobs use bounded pinned HTTP, explicit ownership/leases,
cancellation and owner confirmation. External content is literal untrusted data.
Optional ICP interpretation has default-off availability, bounded inputs/output,
committed logical-request reservations and reviewed inactive drafts.

PostgreSQL concurrency exposed a first-user insertion race across the two unique
identity indexes. Account insertion now handles both conflicts and re-reads only
the exact ID/email pair. An inconsistent historical identity is rejected rather
than adopted. Membership/role checks were retained. Diagnostic authentication
warnings identify rejection stages without logging credentials, signatures,
actors, request bodies or tokens.
