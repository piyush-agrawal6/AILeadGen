# Reviewed customer Sheets export

This implementation is local and gated by the existing customer-integration
feature. No live Google spreadsheet has been written during development. A real
owner-controlled write acceptance is still required before production release.

## Customer workflow

1. Connect Google Sheets with the existing read-only authorization. Import and
   metadata inspection remain available with that permission.
2. To export, explicitly choose **Authorize Google Sheets export**. This starts
   a new Google consent request for `https://www.googleapis.com/auth/spreadsheets`.
   It does not silently expand an existing token or modify OAuth client settings.
3. Select an owned company list (at most 500 companies), an existing spreadsheet,
   the tab title and first row. Destination columns are A–H.
4. Preview the saved company snapshot, headers, destination and exact overwrite
   range. Confirm authority over the destination and approve the overwrite.
5. Review worker status/history. Connecting or preparing a preview does not write
   anything, discover businesses or send email.

Exports include company, website, stored business email, country, city, lead
status, source labels and company ID. The snapshot comes from the owned list's
canonical company records. It excludes private notes, credential data, message
bodies and unrelated customer records. Contact-person list members are not
implicitly exported as companies. Source evidence remains in the application.

## Authorization and data integrity

Migration 38 adds a requested scope to the existing OAuth state and a durable
workspace-owned export table. Existing states default to read-only, and existing
connections are unchanged. OAuth callbacks bind actor, workspace, revision, state
expiry and exact requested permission. Reconnect/disconnect invalidates stale
review authority. Broader/unrelated returned scopes are rejected.

The existing encrypted integration envelope, PKCE, refresh lease, active-member
and owner/admin checks remain in force. A worker derives its workspace and actor
from the persisted job and rechecks the connection before the provider write.
The internal Sheets connection is never a fallback. Connection credentials never
reach browser code or export values.

The approved snapshot/range has a deterministic digest. A request ID reuses the
same snapshot; changed request content fails instead of producing another job.
Changing a company after review does not change an already-approved export.
Snapshots expire after 24 hours. There are at most twenty prepared exports per
workspace per hour and a one-megabyte snapshot budget.

## Provider writes and recovery

The worker uses Google's documented `spreadsheets.values.update` PUT with
`valueInputOption=RAW`. It overwrites one explicit fixed range; it never appends,
creates spreadsheets or deletes unrelated cells. RAW keeps untrusted text such
as `=IMPORTXML(...)` from executing as a formula. The range includes a header
row. All columns are supplied, including empty values.

Provider host/path are fixed, redirects/proxies disabled, response bounded to
32 KB and write deadline bounded to thirty seconds. A successful status is not
enough: the returned updated-cell count must match the snapshot. Provider bodies,
tokens and cell values are not logged by the service.

A durable reservation precedes HTTP. At most two active export workers are
reserved across processes; local dispatch also has a two-task limit. The lease
is renewed after token refresh before beginning the write. Duplicate execution
cannot reserve the same job twice. Successful jobs are not written again.

Timeouts or unverifiable successes become `UNCERTAIN`; no automatic provider
retry occurs. A worker crash leaves a visible running lease that an administrator
must inspect after expiry. Explicit retry requires another review/overwrite
confirmation, retains the exact range/values and is capped at three attempts.
Retrying can replace later edits in that range, so the UI tells the owner to
inspect the destination first. A full worker slot leaves the durable job queued;
Review export can explicitly restart dispatch. Pending jobs may be cancelled.
An HTTP write already in flight cannot be retracted.

Production uses the existing Cloud Run job with `LEADENGINE_SHEET_EXPORT_ID` and
clears unrelated scan/mail/webhook modes. No production job or infrastructure
was changed. Runtime shutdown cancels tracked local tasks; it does not erase
their recoverable records.

## Evidence and limits

Tests cover read-only rejection, exact scope/replay ownership, immutable mapping,
RAW formula safety, tenant denial, HTTP approval, disconnect/revocation,
uncertain outcomes, redirect refusal, bounded retries, concurrent workers,
additive migration/restore and PostgreSQL execution. The browser uses real
application APIs, encrypted credentials and worker logic with a synthetic Google
transport; it is not evidence of live Google acceptance.

Official API references:
[range update](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update),
[RAW values and overwrite behavior](https://developers.google.com/workspace/sheets/api/samples/writing).
