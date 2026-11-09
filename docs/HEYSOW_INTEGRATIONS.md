# Customer integration lifecycle — local implementation

Latest extension, 2026-11-07: reviewed customer imports are implemented, and the
new reviewed export workflow is documented in `CUSTOMER_SHEETS_EXPORT.md`.
Exports request a separate explicit write consent; default authorization and
existing connections remain read-only. The sections below describe the earlier
schema-27 foundation and its historical verification. They must not be read as
the current implementation inventory. Customer Gmail and CRM adapters and live
external integration acceptance remain incomplete.

This is a gated customer connection foundation. It is not a completed mailbox,
CRM synchronization or Google Sheets lead-import product. No production OAuth
configuration, deployment, internal account, credential or real mail was changed.

## Implemented

Schema 27 stores organization-owned connections and OAuth states. The first
adapter supports Google Sheets authorization, reconnect, encrypted offline tokens,
bounded token refresh, safe status/error history, read-only spreadsheet metadata
inspection and workspace disconnect. It reuses the existing Google client
configuration, provider token exchange and bounded Sheets HTTP transport. The
existing internal Sheets connection remains separate and internal-only.

APIs are under `/api/organization/integrations`; the UI is
`/settings/integrations`. An owner/admin manages connections and reads provider
documents. Other active members see safe status metadata only. Both the page and
domain/API services fail closed when their feature is unavailable. Onboarding
can open the settings screen without granting product or mail access.

## Credential and authorization boundaries

Fernet envelopes bind organization, connection, provider and purpose inside
authenticated ciphertext. Swapping encrypted values between tenants fails even
when one person belongs to both. The encryption key is separate from the gateway
signing secret, excluded from settings serialization and never sent to browser
code. APIs, audit events and list responses omit tokens, ciphertext and PKCE
verifiers. Account email is not inferred from a Sheets token response.

Random OAuth state is stored as a digest and bound to the signed actor, exact
workspace, connection revision and ten-minute expiry. Only one callback consumes
it, before provider I/O. PKCE uses S256. Reconnect cancels preceding attempts;
disconnect increments the revision, clears credentials and pending verifiers,
and prevents late exchange/refresh results from restoring access. Privileged
membership is rechecked after external I/O. A token must grant exactly the
requested spreadsheets.readonly scope; broader returned permission is rejected.

Authorization starts are limited to ten/workspace/hour. Token exchange has a
25-second outer limit, document reads 30 seconds, bounded response sizes and no
redirects. Refresh uses a durable 45-second lease and bounded failure cooldown.
Independent PostgreSQL connections verify one refresh call, with the second
caller told to retry. No automatic retry or polling loop is introduced.

Disconnect removes only this workspace's local authority and encrypted secrets.
It intentionally does not revoke the entire Google grant, because the same
Google client/account may also support the existing internal connection. The UI
states this distinction. Historical connection/audit records are retained.

## Server configuration, still disabled

Use the existing root environment source; add only missing names:

```ini
HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED=false
HEYSOW_INTEGRATION_ENCRYPTION_KEY=
```

The second value must be a privately generated Fernet key (URL-safe base64 of
32 random bytes), stored server-side and ultimately in approved Secret Manager
configuration. Do not paste it into chat, print it in test output, commit it or
create a public frontend counterpart. No owner key has been generated or written
by this work. Tests use generated synthetic keys in process memory only.

Keep `HEYSOW_WORKSPACE_MANAGEMENT_ENABLED` and the existing Google client setup
consistent with the approved environment. The adapter uses the existing
`GOOGLE_SHEETS_REDIRECT_URI` and `/acquisition/sheets/callback`; the callback routes
customer-prefixed state to the new API, which independently verifies ownership.
The prefix is a routing hint and grants no authority. Existing internal callback
behavior is retained. A local live test would need an owner-approved localhost
redirect on the existing client; this has not been configured or requested here.

Missing/changed encryption keys require a new explicit connection. Automated
key-ring migration is not implemented. Preserve the key separately from encrypted
database backups. Never rotate it casually or treat an unreadable connection as
someone else's global account.

## Verified versus remaining

Synthetic tests cover cross-workspace state/resource/ciphertext denial, replay,
expiry/replacement, broader-scope rejection, manager revocation, disconnect races,
refresh rotation/concurrency/cooldown, API redaction and default-off gates. The
browser exercises the real authorization API, then intercepts Google navigation
before any real consent or exchange. UI tests cover safe unavailable/viewer/read/
disconnect states and both callback routes.

Live owner consent, provider refresh/read acceptance, customer Sheets import and
sync jobs, mapping/conflict/retry controls, Gmail and CRM adapters remain required.
The current UI describes metadata inspection only; it has no fake sync/import
button. Internal Gmail credentials are never represented as a customer mailbox.
Public registration stays disabled, and production release remains blocked.

Implementation references: [Fernet 48.0.1](https://cryptography.io/en/48.0.1/fernet/)
and [Google server-side OAuth](https://developers.google.com/identity/protocols/oauth2/web-server).
