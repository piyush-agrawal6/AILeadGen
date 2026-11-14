# Razorpay Subscriptions API access — resolved 2026-11-14

The earlier restriction is resolved. The same configured Test Mode key pair now
returns **HTTP 200** from Payments, Plans and Subscriptions. No key replacement,
key rotation, Live Mode switch or alternate-account workaround was needed.

The earlier 401 responses were product-specific: Payments and Customers already
accepted the credentials. The real Test Mode Subscriptions dashboard initially
showed Get Started. Its non-binding setup entry was opened; access subsequently
became available. The exact provider-side cause or propagation mechanism was not
independently established.

Three real internal Test Mode plans (Starter, Growth, Scale) were created and
independently verified, then mapped in the existing database. One controlled
Starter subscription was created through the production application. Repeating
its request ID returned the same local/provider mandate.

The owner completed the real Test Mode Checkout. The deployed signature handler
returned successfully, and the backend independently verified a captured payment,
matching paid invoice, customer, plan, amount/currency and subscription period.
No real money was charged. These observations do not establish live billing or
public commercial readiness.

Genuine merchant webhook delivery, renewal, failure and cancellation acceptance
are tracked separately in PAYMENT_TEST_RESULTS.md. The webhook endpoint remains:
https://leadengine-api-befca7xg4a-el.a.run.app/api/billing/webhooks/razorpay

Public checkout, public registration and live charges remain disabled.
