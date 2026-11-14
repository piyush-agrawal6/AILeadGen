# Production environment checklist

Keep all existing OAuth/session/database/Gmail/provider configuration unchanged.
Billing uses server-only secrets from the existing root environment for local work
and Google Secret Manager references for production; never commit `.env`.

Required Test Mode secrets: `RAZORPAY_KEY_ID` (must start `rzp_test_`),
`RAZORPAY_KEY_SECRET`, distinct `RAZORPAY_WEBHOOK_SECRET`.
Nonsecret settings: `RAZORPAY_MODE=test`, `BILLING_PROVIDER=razorpay`,
`BILLING_TEST_MODE=true`, `BILLING_PUBLIC_CHECKOUT_ENABLED=false`,
`LEAD_ENGINE_PUBLIC_ENABLED=false`. `BILLING_ENABLED` remains false until the
additive migration and gated implementation are verified. Set
`BILLING_TEST_WORKSPACES` only to verified owner-approved UUIDs.
Optional catalog/mappings are documented in BILLING_ENTITLEMENTS.md.

Production architecture remains Vercel dashboard at app.planebyte.com, existing
Google Cloud API/workers, existing PostgreSQL. Marketing is unchanged. Do not add
Razorpay API/webhook secrets to Vercel browser variables. The dashboard obtains the
publishable test key only through the authenticated owner checkout endpoint.

Preserve public registration, customer admission and public checkout as disabled
until independent critical launch gates pass. Preserve all real email sending as
disabled. Billing acceptance does not authorize prospect contact or scanning.

Before release: verify exact Git SHA, full security/data/regression checks, isolated
Next build, migration recovery and original-column preservation, owner login,
wrong-workspace denial, raw webhook invalid-signature denial and actual Razorpay
Test Mode transaction/lifecycle evidence. Record unverified gates as blocked.

## Applied restricted release

The recovery-tested schema 46 is live. `BILLING_ENABLED=true` is deployed only
with `BILLING_TEST_MODE=true`, `RAZORPAY_MODE=test`, public checkout false and the
single verified owner workspace allowlist. Three test plan mappings are stored
in the database; no duplicate plan environment names or frontend secrets were
introduced. This supersedes the earlier pre-migration disabled state above.
