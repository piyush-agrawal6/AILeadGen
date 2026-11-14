# PayU integration and approved pricing

## Approved catalog

Canonical file: `app/billing/commercial_catalog.json`, version `2026-11-14.2`.
Starter USD59/month; Growth USD149/month; Scale USD379/month; Enterprise custom.
Intent Radar includes Growth Intelligence; Lead Engine is excluded. No approved
annual plan, discount, setup fee or trial. Existing subscription snapshots are
not rewritten when the commercial catalog changes.

`scripts/sync_commercial_catalog.py --marketing-root <Planebyte-Landing> --check`
must pass before either site's pricing release. The marketing JSON is a checked
copy; both billing comparisons render this catalog. No payment backend or PayU
credential is added to marketing.

## Verified so far

- Existing root `.env` securely loads `PAYU_MERCHANT_KEY`,
  `PAYU_MERCHANT_SALT`, `PAYU_MODE=live`; no values/fragments are logged.
- A real non-chargeable `verify_payment` request to the official Live API on
  2026-11-14 returned HTTP200 and the expected nonexistent-transaction result.
  This confirms a useful transport response, not captured funds, a mandate,
  merchant capabilities or recurring acceptance.
- Hosted SHA512 request/consent hashing, reverse response verification,
  transaction/workspace/mode attribution, exact amount checks, no added fees,
  bounded provider reads, no redirects and no blind POST retries are implemented.
- New production Razorpay subscription creation and checkout are retired.
  Reconciliation, cancellation and original historical records remain intact.
- New PayU checkout is blocked. No real transaction has been initiated.

## Current integration limitation

Hosted payment verification primitives are implemented; the complete PayU
subscription ledger, callbacks, recurring lifecycle and commercial entitlements
are not yet accepted or activated. Do not represent these primitives or a
nonexistent-payment probe as a completed PayU integration. No public PayU webhook
URL is certified by this changeset.

## Official contract evidence

Reviewed 2026-11-14:

- [Hosted consent](https://docs.payu.in/reference/payment-consent-transaction-payu-hosted):
  hosted collection and SI-specific hash; card details stay at PayU.
- [Verify Payment](https://docs.payu.in/reference/verify_payment_api):
  independent transaction verification after a callback.
- [Additional charges](https://docs.payu.in/docs/collect-additional-charges):
  reverse hash variant; undisclosed extra amounts are rejected.
- [Zion activation](https://docs.payu.in/docs/using-zion-subscription-automation-platform):
  requires the PayU account manager; Live merchant status alone is insufficient.
- [Define subscription](https://docs.payu.in/reference/old_create-a-subscription):
  the available reference says INR only, while examples and base-host/auth
  conventions differ across pages. The current linked `create-a-subscription.md`
  returns404. Resolve the enabled account contract before sending financial writes.
- [Subscription list](https://docs.payu.in/reference/get-list-of-subscriptions-api):
  signature text refers to a subscription ID absent from the list request, while
  the example includes a bearer credential. Do not invent that credential or
  substitute a public documentation token.
- [Cancellation](https://docs.payu.in/reference/cancel-subscription-api):
  immediate and irreversible in the documented Zion model; do not invent proration
  or resume of a cancelled mandate.
- [International checkout](https://docs.payu.in/docs/payu-hosted-checkout-integration-dynamic-currency-conversion):
  requires account enablement and does not prove USD recurring availability.

## Required account/commercial evidence

1. PayU-confirmed Zion activation and the current endpoint/authentication,
   webhook authentication and invoice/settlement contract for this merchant.
2. Supported recurring charge and settlement currencies, international card
   mandates, pre-debit responsibilities and permitted payment methods.
3. A reproducible owner-approved conversion policy if recurring INR is required;
   never silently convert the approved USD prices.
4. Tax terms and supported merchant capabilities. Numeric pilot allowances are approved; do not request their approval again.
5. Real sandbox lifecycle acceptance, then exact amount/currency/method approval
   for one restricted live transaction. Public checkout needs separate approval.

## Existing policy review

The inspected marketing terms mention monthly/annual billing and a seven-day
money-back guarantee subject to a20% usage condition; renewal refunds are
excluded and technical-failure relief is described. These are existing published
promises, not newly approved commercial policy. Do not silently replace them.
Before paid activation, reconcile monthly-only launch, undefined numeric usage
and applicable charge/tax terms with those existing legal obligations.

## Secrets

Only the three Hosted variables above are currently required. Production secrets
belong in the existing Secret Manager; the frontend and Netlify must receive no
merchant salt. Additional Zion credentials must be requested only when PayU
confirms its actual contract. Production secret installation remains to be
verified; root credential presence is not a production configuration claim.


## November 14 approved-allowance update

The owner approved the full pilot table; see `PLANEBYTE_USAGE_AND_ENTITLEMENTS.md`.
The shared marketing/application catalog now contains explicit versioned limits.
Migration47 and scoped commercial accounting are implemented locally. This is
separate from provider lifecycle activation: no real PayU contract is created.

The current PayU v2 dated-JSON / v3 verification protocol is implemented with
exact-body SHA512 signing, fixed endpoints, bounded reads and no blind POST retries.
A genuine Live v3 lookup returned HTTP200/status1 with one expected unknown
transaction. Original-currency/amount/workspace checks reject absent or mismatched
currency, surcharges, discounts and unsettled payments. A captured payment still
never proves a recurring mandate. Hosted URL validation only accepts the configured
mode's official PayU HTTPS host. No checkout or charge was created by these probes.

The owner confirmed a verified Live merchant profile and is obtaining Zion/SI
activation, account-specific authentication/webhook instructions, permitted
recurring currency and international recurring-card support from PayU. No
additional secret name is invented until that contract specifies one. The existing
merchant key and salt must not be requested again without an actual rejection.

References:
- https://docs.payu.in/v2/reference/collect-payment-api-payu-hosted-v2-_payment
- https://docs.payu.in/v2/reference/v2_verify_payment_api
