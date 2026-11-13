# Razorpay Test Mode integration

Status: implementation under verification; not a live-payment launch certificate.

The existing FastAPI app owns the only billing system. The Next.js app at
`app.planebyte.com` forwards authenticated same-origin requests through the
existing signed gateway. No API secret or webhook secret enters browser code.
Razorpay's publishable Test Key ID is returned only for an owner-approved checkout.

## Provider contract

Subscriptions use native `/v1/plans`, `/v1/subscriptions`, subscription cancellation,
and independent subscription, invoice and payment reads. Checkout is the official
`https://checkout.razorpay.com/v1/checkout.js`. Signature verification uses
HMAC-SHA256 of `payment_id|server_stored_subscription_id` with the API secret.
A successful redirect, valid signature, `authenticated` status or nominal
mandate-authorization payment never establishes a paid period. Access requires
an active subscription and matching current-period paid invoice, captured payment,
customer, order, amount, currency and non-refunded settlement.

References: [integration](https://razorpay.com/docs/payments/subscriptions/integration-guide/),
[plans](https://razorpay.com/docs/api/payments/subscriptions/create-plan/),
[invoices](https://razorpay.com/docs/api/payments/subscriptions/fetch-invoices/),
[cancellation](https://razorpay.com/docs/api/payments/subscriptions/cancel-subscription/),
[webhook validation](https://razorpay.com/docs/webhooks/validate-test/).

## Webhooks

Intended existing-backend URL (deployment verification is recorded separately):
`https://leadengine-api-befca7xg4a-el.a.run.app/api/billing/webhooks/razorpay`

Select Test Mode in Razorpay Dashboard. Add the exact HTTPS URL; do not use the
marketing website, an authenticated dashboard page or a local URL. Configure the
secret to be exactly the server-only `RAZORPAY_WEBHOOK_SECRET` value, using an
independent random secret, distinct from `RAZORPAY_KEY_SECRET`. Never put it in
chat, a URL or the frontend. Preserve it for provider retry verification when
planning a future secret rotation.

Enable these subscription events:

- `subscription.authenticated`
- `subscription.activated`
- `subscription.charged`
- `subscription.completed`
- `subscription.updated`
- `subscription.pending`
- `subscription.halted`
- `subscription.cancelled`
- `subscription.paused`
- `subscription.resumed`

The raw body is bounded and HMAC-verified with `X-Razorpay-Signature` before
processing. `x-razorpay-event-id` and a body digest protect against duplicate or
conflicting event deliveries. Receipt is durable; a bounded existing dispatcher
re-fetches authoritative state. No webhook-provided notes, amounts, status or
workspace identifier directly grants access. Missed notifications are reconciled
periodically. Five failed event attempts become an operator-visible failure;
transient provider errors use capped backoff. No infinite retries.

## Creation recovery

A workspace/mode slot and unique reviewed request ID reserve creation before the
provider POST. Unknown outcomes block another mandate. The explicit recovery
operation finds exactly one matching provider subscription using server-persisted
workspace/local-ID/mode notes within at most 500 records. No matching record or
multiple matches requires operator review; never blindly retry a POST.

Sandbox plans are internal fixtures, not commercial prices. The plan preparation
script reuses matching verified IDs and journals creation before calling Razorpay.
No live mode, real charge or public checkout is enabled by this release.
