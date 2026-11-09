# Account and workspace onboarding — current implementation

The existing verified Google/Auth.js sign-in remains the only authentication
method. Public registration is not implemented or activated. Production OAuth,
allowlists, secrets and deployment configuration were not modified. The owner
authorized `syntaxwars@gmail.com` on the local root allowlist; that grants sign-in
only, never access to another organization's data.

## Available behind the disabled workspace-management gate

`HEYSOW_WORKSPACE_MANAGEMENT_ENABLED` defaults to false. In isolated tests it
exposes workspace creation/selection, personal/company profiles and invitations.
It does not grant access to an account absent from the existing sign-in policy.

An already authenticated account deliberately creates a workspace by posting a
company name and UUID request ID. The server supplies the owner identity. A
durable account-scoped creation ledger makes retries idempotent; another account
using the same UUID receives no access to the first account's workspace. A new
workspace is explicitly selected. Retrying an old completed creation does not
silently change a later personal workspace selection.

The new workspace starts IN_PROGRESS at COMPANY. The company profile stores
user-entered fields, provenance and profile completion without marking the whole
onboarding complete. Product APIs continue to return ONBOARDING_INCOMPLETE.
Company profile editing is available so setup can resume. The legacy internal
workspace's previously completed state is preserved.

Multiple active memberships require an explicit selection with the gate enabled.
A saved selection is checked on every request. Revoked membership never silently
falls back to another company. Browser navigation reloads after successful
selection to discard the preceding workspace's cached state.

## Personal profile

`GET/PUT /api/profile` resolves only the signed account. Name, job title, phone,
IANA timezone and language/region code are editable with conflict protection.
Email and actor/workspace IDs are not writable. Viewer roles do not prevent
personal edits, and edits preserve workspace preference and company data.
The language field records a preference; interface translation is not implemented.
Profile images, notification/interface preferences, active-session management,
deactivation and deletion requests remain future account work.

## Invitations

See HEYSOW_INVITATIONS.md for the implemented one-use capability lifecycle.
The named existing permitted Google account can accept/reject, and the inviter
gets a scoped notification record. Invitation email delivery and public invitee
registration are not configured. A token alone never authorizes a membership.

## Resumable setup implemented locally (schema 23)

`/settings/setup` saves objectives, reviewed services, an owned active ICP,
geographic preferences, an explicit choice to configure integrations later and
the current step. Owner/admin edits use optimistic revisions; viewers can read
without changing setup. Completion checks the actual stored company profile,
services, objectives, active ICP and explicit preferences. It cannot be completed
by posting seed flags. Repeated completion is idempotent. No scan or email starts.
The browser test follows the real setup API and confirms product access remains
blocked until completion. A signed-in account with no memberships sees workspace
creation; an incomplete workspace sees setup rather than product data.

## Domain proof and reviewed website information (schemas 24–25)

`/settings/domains` supports public-domain normalization, a single-use displayed
DNS TXT challenge, hashed proof storage, bounded verification, expiry, rotation,
revocation and preserved proof history. Checks require owner/admin membership
and recheck it after external I/O. Proof never grants membership or connects mail.
Tests use synthetic DNS; no owner's production DNS has been edited or verified.

Company website review is separately gated by
`HEYSOW_COMPANY_DISCOVERY_ENABLED=false` by default. It reuses the existing worker
and pinned SSRF-safe HTTP transport for one bounded public page. Durable jobs have
leases, timeouts, cancellation, bounded retries, organization/global budgets and
ownership checks. Extracted literal metadata is a proposal until explicitly
reviewed and confirmed; it is not verified ownership or invented company proof.
Stored profiles have conflict protection and provenance. No new infrastructure
has been deployed and no live website extraction was used during acceptance.

## AI-assisted criteria and release boundary (schema 26)

The optional ICP assistant reuses the existing Vertex-first gateway behind
`HEYSOW_ICP_AI_ENABLED=false`. It returns an editable inactive draft and stores
nothing until the owner chooses to save. Quota reservations are persisted before
provider calls; cache hits reuse organization/actor-specific results. Failed or
unsupported output falls back to the manual builder. See HEYSOW_ICP_SYSTEM.md.

Customer integrations, public account admission/lifecycle, PostgreSQL acceptance
and staging approval remain release requirements. These local implementations
do not establish production readiness or enable public signup.
