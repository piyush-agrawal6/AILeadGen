# Gated Google account admission

Local implementation for F02/F08 (B03), schema 39. Public release and real
external-account acceptance remain pending. This work has not enabled registration.

## Identity and ownership

- Auth.js keeps the real Google provider, verified-email policy, state/PKCE,
  eight-hour JWT and existing production allowlist.
- Non-allowlisted Google identities are admitted only through the server-only
  signed `POST /api/organization/admission/google` broker. A browser header,
  invitation code or email alone cannot authenticate an account.
- The backend binds normalized email, Google subject and the configured client
  ID. Subject/email conflicts, suspended/closed accounts and malformed or stale
  consent are rejected. Responses omit subjects, credentials and invitation codes
  and use `Cache-Control: private, no-store`.
- Admission creates account/consent records only. Workspace creation and invitation
  acceptance remain separate domain actions. No mailbox, internal organization,
  provider credential, discovery job or send permission is inherited.

## Independent, disabled-by-default controls

| Control | Purpose |
|---|---|
| `HEYSOW_CUSTOMER_ACCESS_ENABLED` | Allow active admitted accounts to use signed APIs and verified worker scopes |
| `HEYSOW_PUBLIC_REGISTRATION_ENABLED` | Permit creation of new accounts without an invitation |
| `HEYSOW_INVITED_REGISTRATION_ENABLED` | Permit new named invitees while public registration remains closed |
| `HEYSOW_GOOGLE_ADMISSION_CLIENT_ID` | Backend identity check against the configured Google broker client |
| `HEYSOW_TERMS_VERSION` | Approved current policy version required for customer access |

No environment or OAuth configuration was changed. Setting a version is an
activation input, not evidence of legal approval or completed isolation acceptance.
Workspace-management configuration, approved policies and staged two-customer
Google acceptance are still needed before enabling these controls.

## Invitation-only journey

1. An owner/admin creates an existing hashed, expiring, manually shared invitation.
2. The invitee opens `/signup`, provides the private code, accepts current policies,
   and signs in with the named Google account.
3. The backend rechecks the invitation's recipient, pending status, expiry, active
   workspace, inviter role and inviter account. It does not consume the invitation
   or create membership during admission.
4. A signed, HTTP-only, ten-minute cookie carries the code to the fixed
   `/accept-invitation` review page. The code is not added to OAuth redirect URLs.
5. The invitee explicitly accepts or declines. Existing invitation services enforce
   role, replay and revocation checks and never silently switch the active workspace.

Returning admitted accounts may sign in with both registration controls closed.
When policies change, customer APIs/workers require the new version; the signed
account-only broker can renew consent even for a viewer in an existing workspace.
An existing signed-in customer can confirm terms from `/signup`. Account renewal
does not confer another organization's role.

## Migration and verification

Migration 39 adds only `account_admissions` and `account_terms_acceptances`, their
constraints and an index. Existing users, tenants, setup, contact/suppression
history and integrations are retained. Schema-38 upgrade, repeatability and
isolated SQLite backup/restore checks pass. Do not restart an older local preview
against schema 39 without the existing fresh-backup/tested-restore workflow.

Permanent coverage: `test_account_admission.py`, the schema-39 foundation migration
case and `test_postgres_gated_invitation_account_admission_and_explicit_membership`;
frontend broker/action tests and `playwright.admission.config.ts`. Browser checks
intercept Google, and backend claims are synthetic: they do not certify a real
Google callback, external invited account, PostgreSQL race or production rollout.
Fresh PostgreSQL validation is blocked because the previous temporary cluster and
runtime are unavailable in this session. See the continuation tracker and
`data/artifacts/verification/phase6/recovery-20261109/` for actual outcomes.
