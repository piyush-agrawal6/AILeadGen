# Production release — November 14, 2026

**LIMITED GO: verified non-payment updates for approved Beta accounts.**
**NO-GO: public recurring paid checkout.** Payment acceptance and broader launch
quality gates remain open; this is not a claim that the entire SaaS transformation
or PayU recurring integration is complete.

## Actually deployed

| Component | Verified release |
|---|---|
| SaaS application code | `0077fe32d1a0dc8b36daec38be03d0d89980c452` |
| Vercel | `dpl_FtEzeN1F8dzQhw2XFda54nrMabwX`, READY, promoted to https://app.planebyte.com |
| API | `leadengine-api-00138-suf`, 100% traffic and all existing API tags |
| Worker, acquisition, quota-canary | Existing Google Cloud jobs, image `intent-only-0077fe32d1` |
| Marketing | `04ff0901368603c259d79a98c934b50164913d30`, Netlify deployment `6af8808515984dc64ea4c39c`, published at https://planebyte.com |
| Commercial catalog | `2026-11-14.2`, approved prices and pilot allowances on both sites |
| Catalog SHA256 | `3eb0e8ab8a8b591d16a9a6da664229ed3b43b87db1b7912ac2615e38cf02e54f` |

Existing Vercel/GitHub, Cloud Run, PostgreSQL and Netlify architecture is preserved.
No frontend Cloud Run hosting, subscription upgrade, DNS or OAuth change was made.
All runtime settings and scheduler definitions were compared across the image rollout.
The existing PayU Live pair is pinned in Secret Manager for the API and billing
worker; no credentials or key fragments enter frontend code or these reports.
`PAYU_BILLING_ENABLED=false` and public checkout remain false. Live merchant
configuration alone is not treated as a recurring mandate or paid entitlement.

## Verification

- **1,029 backend passes**, one intentional live-email skip, zero failures/errors;
  includes real disposable PostgreSQL quota races and additive migration checks.
- **159 frontend unit passes**, successful typecheck and production build.
- **7 product browser checks**: assistant multi-turn persistence and22 routes at
 1440/1280/1024/768/390/320px. These use isolated synthetic fixtures.
- Marketing:15 unit passes, production build, inert plan-selection browser check,
  and six approved-pricing viewport checks.
- Fifteen authenticated staging checks passed, including the two alert filters
  formerly broken by PostgreSQL placeholder parsing and disabled Lead Engine APIs.
- A real owner-scoped production worker completed a grounded Vertex assistant
  turn. Replaying the same request reused its turn/job. No outreach or payment
  was initiated. Private verification IDs are in the restricted artifact directory.
- Live domain inspection resolved to the exact promoted Vercel deployment.
  `/login` is branded/HTTP200, Google OAuth provider discovery is present,
  unauthenticated workspace usage is HTTP401, and root redirects to login.
  A fresh real owner browser sign-in was not repeated: browser control was stopped.
- Live marketing and authenticated billing reads confirm identical approved
  prices/allowances, the catalog hash and closed checkout.
- Credential scans found zero credential matches, generated/private artifacts or
  oversized outgoing blobs. The unrelated owner website directory and marketing
  audit-document edit were left untouched.

## Data and recovery

Production remains schema46. Migration47 is implemented and recovery-tested, not
unnecessarily applied while PayU commercial activation is disabled. Its code is
compatible with schema46 under that gate. No reset, truncation, broad deletion,
Lead Engine table alteration, or production migration occurred in this release.

Fresh backup:118472311 bytes, SHA256
`a1b38fbd83040da1cdde0bc11e4fb60389495c82677708cfbe91841dcf8ac12f`.
The first rehearsal exposed a SQL_ASCII restore-database encoding issue. The
recovery helper now explicitly creates UTF-8 databases. The same fresh snapshot
restored exactly; local46→47 applied once, then zero migrations on replay. All173
original data tables retained identical full-row fingerprints; only migration
history changed among174 original tables. Production preservation separately
confirmed original tables, Lead Engine counts, stored grants and zero tracked
source deletions.

Lead Engine is preserved completely behind reversible availability controls.
A future approved release can restore its API/worker/frontend availability with
`LEAD_ENGINE_AVAILABLE=true` and the retained product-switch/navigation controls,
using existing entitlements and records. It does not require feature rebuilding
or recovering deleted data. Do not automatically enable scans, email sending,
public product admission or outreach as part of that future visibility change.

## Actual performance and economics

Two sequential authenticated samples per endpoint, not a load test or reliable
population p95:

| Read | Post-release median |
|---|---:|
| Overview |20.891s |
| Source health |8.261s |
| Opportunities |8.737s |
| Saved signals |13.055s |

All eight returned HTTP200. The earlier overview sample included one48.405s
success and one85s timeout. Batching improved latency, but the overview remains
slow and the performance work is **not complete**. Server-Timing exposes SQL
round trips without SQL text or private values; further reduction is needed.

The owner workspace now has four recorded Vertex requests:7,221 reported input
and1,161 output tokens, with no unreported request in this sample. Approved
model-cost rates and measured infrastructure cost allocation are unavailable;
actual dollar cost, gross margin and sustainable broad-launch economics remain
**unproven**, not estimated from another model's rates.

## Remaining payment work and account dependency

The existing merchant key/salt pass a genuine non-chargeable Live v3 verification
lookup. Exact-body dated signing, original-currency/money/attribution checks,
official-host validation and bounded provider requests are implemented. A
successful captured payment never becomes proof of a recurring mandate.

Commercial contract snapshots and monthly accounting are built and tested, but
not activated without verified settlement. Reports share AI operations/tokens,
monitor checks count once within searches, and API/MCP share request capacity.
Conservative reservations remain held for unknown outcomes; precise actual-token
settlement is not connected to every existing AI failure path.

Not yet complete/accepted: account-specific Zion/SI mandate creation,
authenticated PayU callbacks, renewal/cancellation/refund reconciliation and
live paid-contract activation. No PayU recurring webhook URL or complete payment
lifecycle is certified. Historical Razorpay records/lifecycle remain preserved;
new production Razorpay checkout is retired.

The owner is obtaining from PayU:
1. Zion/Standing Instructions activation and current merchant-specific API
   authentication, invoice/settlement and webhook-signature contracts.
2. Permitted recurring charge/settlement currencies, monthly USD support,
   international recurring cards, payment methods and pre-debit responsibilities.
3. Any additional credentials required by that confirmed contract, through secure
   configuration. No additional secret names or public documentation tokens are invented.

If PayU only supports INR mandates, obtain an explicit commercial decision;
never silently convert USD59/149/379 or charge INR59/149/379. Complete controlled
lifecycle tests and request exact amount/currency/method authorization before a
real-money acceptance. Public recurring checkout remains disabled.

Independent human AI evaluation still requires two actual reviewers and an
adjudicator; no human labels or pass are fabricated. External MCP client
acceptance and final performance acceptance remain open. These gates are not
silently waived by a successful deployment or the approved pilot prices.
