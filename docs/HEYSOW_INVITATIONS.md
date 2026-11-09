# Workspace invitations — local implementation

This feature is implemented behind `HEYSOW_WORKSPACE_MANAGEMENT_ENABLED=false`.
No environment file, production database or OAuth configuration was changed.
Public Google registration remains disabled; an invitee must currently be allowed
to authenticate through the existing sign-in policy. This is a staging foundation,
not a claim that public team onboarding is ready.

## Implemented behavior

An owner or administrator can create a seven-day invitation to a named email.
Owners may invite administrators; administrators may invite members/viewers.
Invitations cannot grant ownership. Pending invitations are bounded to 100 per
workspace, listed in pages of 25, and can be revoked by an authorized manager.
An existing active member is not silently granted a different role.

Creation returns a random 256-bit capability exactly once. Only a SHA-256 digest
is persisted. The team page offers a private link with its token in the URL
fragment rather than the server query string. The recipient deliberately imports
the code and accepts or declines through a POST. The signed account must match
the invitation email. Caller-supplied actor and workspace fields are rejected.
Neither a matching company domain nor possession of a token grants access alone.

Acceptance rechecks workspace status, expiration, single-use state and the
inviter's current authority under an organization lock. Revoking the inviter's
membership removes that latent grant capability. Acceptance creates the exact
invited membership and does not change the user's selected workspace. A viewer
in another current workspace may accept their own invitation; that exception
does not permit mutations to their current workspace.

The inviter receives a workspace-scoped in-app notification record for acceptance
or rejection. Records are available through the authenticated notification API.
Notification presentation/read-state controls and automated invitation email
delivery remain unfinished. No invitation uses prospect outreach SMTP.

## API and UI

- `GET/POST /api/organization/invitations`: manager list/create.
- `DELETE /api/organization/invitations/{id}`: manager revocation.
- `POST /api/organization/invitations/respond`: recipient accept/reject.
- `GET /api/organization/notifications`: current member's scoped notifications.
- `/settings/team`: gated list/create/revoke and one-time private link.
- `/accept-invitation`: existing authentication design; authenticated response
  form is available only when the feature gate is enabled.

Token-bearing POST responses are marked `Cache-Control: no-store`. Invitation and
notification GETs are outside the read-cache allowlist. Tokens are not audit
details. Do not record request/response bodies for these endpoints in telemetry.

## Migration and release boundary

Additive migration 19 creates invitation and notification tables plus indexes.
It does not alter existing memberships, leads or histories. SQLite upgrade,
idempotency and snapshot restoration are tested. PostgreSQL locking, unique-index
concurrency and restore validation still require an isolated staging database.
Public registration, an invitation delivery service, end-to-end Google acceptance
for new accounts, staging approval and release authorization remain blockers.
