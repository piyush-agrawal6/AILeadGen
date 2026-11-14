# Usage and entitlements

The owner approved commercial catalog **2026-11-14.2 / pilot-v1** on November 14.
These are initial monthly allocations; future catalog changes do not rewrite a
subscription's saved terms. Prices: USD59 / USD149 / USD379 monthly; Enterprise custom.

| Monthly allowance | Starter | Growth | Scale |
|---|---:|---:|---:|
| Searches, including monitoring checks | 100 | 300 | 600 |
| Shared AI operations | 20 | 60 | 120 |
| Shared reserved AI token capacity | 600,000 | 1,200,000 | 1,800,000 |
| Active monitors | 2 | 5 | 10 |
| Scheduled checks, included within searches | 60 | 150 | 300 |
| Reports, also consuming shared AI | 5 | 15 | 30 |
| Active team members | 1 | 3 | 5 |
| Developer API requests, including scoped MCP | 500 | 2,000 | 5,000 |

Monitoring frequency is daily for all three plans. Only configured, authorized
sources are available. Existing daily/global/provider safety caps still apply.
No annual discount, trial, setup fee, unlimited allowance or Lead Engine entitlement
is implied. Enterprise requires a separate agreement.

## Implemented accounting

Additive migration47 introduces commercial contract snapshots, workspace slots,
cycle counters and reservation records without changing historical Razorpay or
Lead Engine tables. An active commercial contract requires independently verified
mandate and settlement, an unexpired paid period, matching mode and a valid snapshot.
No public contract writer or fake paid grant is provided. PayU activation stays off
until its lifecycle is verified. Test contracts are restricted to approved test workspaces.

APIs and workers reuse shared reservation services: one scheduled check reserves
one search and one monitoring classification, not two searches. Stable worker
operation IDs prevent retries charging monthly AI capacity twice. Reports reserve
one report and one shared AI operation; their inference uses that same operation.
Company/ICP AI and the assistant share the monthly AI allowance. Input/output size
estimates reserve bounded token capacity before inference. API and MCP use the
existing scoped credential meter. Capacity is enforced when activating monitors
and adding seats; draft/paused monitors retain their records without consuming
paid active-monitor capacity. Operator storage limits remain independent.

Reservations, completion and release are atomic and idempotent. Release is permitted
only for work known not to have reached a provider; unknown outcomes remain reserved.
The lifecycle settlement/release primitive is implemented; not every existing AI
failure path has been connected to precise actual-token settlement. This conservative
reservation behavior must not be represented as measured token billing.

The usage page shows reserved/used capacity, remaining amounts, warning thresholds,
provider-period reset dates, and separate manual-search/scheduled-check totals.
Existing manual Beta access remains independent with real daily operator counters.
Saved evidence is readable after consumption exhaustion, subject to membership,
retention, product availability and source-withdrawal controls.

## Actual economics and remaining acceptance

The last inspected owner production sample contained three Vertex requests,
4,838 input and997 output tokens, with no approved model-cost rates and zero
priced records. Actual AI/infrastructure unit economics are **not established**.
Provider token measurements are separate from conservative capacity reservations.
No cost or margin is invented from a different model's prices.

Synthetic quota tests do not certify real PayU settlement. Provider-confirmed
recurring access, supported charge currency, authenticated lifecycle callbacks,
renewal/cancellation/refund reconciliation and controlled live acceptance remain
required before commercial activation. Existing cancelled Razorpay subscriptions,
original transaction currencies and manual Beta entitlements remain preserved.
