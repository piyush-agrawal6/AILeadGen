# Signed workspace webhooks

Implemented locally behind `HEYSOW_WEBHOOKS_ENABLED` (default false). Production
deployment, scheduling and a real external receiver acceptance have not occurred.
The owner-authorized `--all-features` local preview enables this implementation.

## Ownership and setup

An active workspace owner/admin can manage endpoints at Settings → Developer
access. The server resolves membership, scopes every endpoint/delivery and rechecks
the persisted creator's authority in workers. Removing that authority stops new
delivery attempts. Archived endpoints and their delivery history remain intact.

The existing `HEYSOW_INTEGRATION_ENCRYPTION_KEY` encrypts signing secrets in
authenticated envelopes bound to workspace, endpoint, provider and purpose. A
secret is returned once, with `Cache-Control: no-store`; lists/history/audits never
return it. Creation retries use a stable request ID without revealing the secret
again. Explicit rotation is available if the first response was lost.

Receivers must use public HTTPS on port 443, without URL credentials, query tokens
or fragments. Every attempt revalidates the URL; the shared public-only transport
pins DNS addresses. Redirects and environment proxies are disabled. Receiver
response bodies are neither read nor stored.

## Event contract

Subscriptions support `company.created`, `contact.created`, `contact.updated`,
`task.created`, `task.updated`, `email.sent` and verified `reply.received`. Events
contain bounded record identifiers, workspace ID, timestamp, event ID and type.
Private record details require a separately authorized scoped API key.

Domain writes enqueue events transactionally and make no HTTP requests. Existing
records are not replayed on subscription. A unique endpoint/event constraint
prevents duplicate outbox entries. Limits are ten active endpoints and 5,000
pending deliveries per workspace; capacity pauses endpoints while preserving the
underlying domain write.

The receiver verifies `X-PlaneByte-Signature` using HMAC-SHA256:

```text
signed bytes = X-PlaneByte-Timestamp + "." + exact raw request body
signature = "v1=" + hex(HMAC-SHA256(signing secret, signed bytes))
```

Compare in constant time, reject timestamps outside a five-minute tolerance and
persist `X-PlaneByte-Delivery-ID` before processing. `Idempotency-Key` contains
the same stable delivery ID. `X-PlaneByte-Event-ID` identifies the logical event.
Return 2xx only after safely accepting the event.

Delivery is **at least once**, not exactly once: a crash after the receiver accepts
an event can leave the sender uncertain. Recovery retains the same event/delivery
IDs. Receivers must deduplicate. Disabling or pausing cannot retract an HTTP
request already in flight.

## Bounded execution and recovery

The worker reserves each attempt durably before HTTP, with a 45-second lease and
a 12-second request deadline. An endpoint execution handles at most 20 deliveries
within 120 seconds. The dispatcher reserves at most two active endpoint workers
across processes, with fair endpoint rotation and a 180-second dispatch lease.

There are at most five attempts. Transient failures use increasing backoff with
jitter and bounded numeric/date `Retry-After`. Redirects and authentication/missing
receiver responses pause the endpoint. Permanent payload/configuration failures
do not loop. Manual retry preserves the delivery ID and cannot exceed five
attempts. A crash during the final reserved attempt becomes
`DELIVERY_OUTCOME_UNKNOWN`; it never triggers a sixth request.

Delivery history shows status, attempt count, timestamps, HTTP code and safe error
codes. Pausing/archiving retains history; a revision prevents stale control writes.
The worker checks membership, feature availability and endpoint state before each
request. Disconnected/revoked authority cannot fall back to another workspace.

## Local versus production

The opted-in development preview runs a bounded five-second dispatcher loop and
cancels local tasks on shutdown. Offline tests prohibit live webhook transport.
Production reuses the existing Cloud Run worker and the explicit
`LEADENGINE_AUTOMATION_MODE=webhooks-dispatch` entry point. A production schedule,
feature activation, IAM verification and real controlled receiver acceptance
remain an owner-approved rollout step; no new infrastructure was created.

Migration 37 is additive. Local verification includes upgrade/repeatability,
restore, PostgreSQL, tenant denial, real API/browser configuration, HMAC,
concurrent reservation, retries and recovery. See the Phase 1–6 completion tracker
for actual frozen regression results rather than inferring readiness from this
document.
