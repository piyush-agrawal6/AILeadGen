# Billing and entitlement audit — November 15, 2026

This release does not enable payments. PayU merchant credentials are configured,
but verified Live Mode credentials do not establish Zion/SI recurring access.
Public recurring checkout remains closed. No real payment or refund was initiated.

Approved catalog `2026-11-14.2` remains byte-identical to the existing marketing
repository: SHA256 `3eb0e8ab8a8b591d16a9a6da664229ed3b43b87db1b7912ac2615e38cf02e54f`.
Prices remain USD59 / USD149 / USD379 monthly; Enterprise is separately agreed.
No subscription snapshot or historical Razorpay payment was rewritten.

| Monthly allowance | Starter | Growth | Scale |
|---|---:|---:|---:|
| Searches, including scheduled checks | 100 | 300 | 600 |
| Shared AI operations | 20 | 60 | 120 |
| Shared AI token capacity | 600,000 | 1,200,000 | 1,800,000 |
| Active monitors | 2 | 5 | 10 |
| Daily monitor checks, within searches | 60 | 150 | 300 |
| Reports, also within shared AI operations | 5 | 15 | 30 |
| Seats | 1 | 3 | 5 |
| Developer API/MCP requests | 500 | 2,000 | 5,000 |

Capacity is enforced against verified workspace membership and immutable paid
contract snapshots. Paid periods come from verified provider settlement; daily
operator safeguards use UTC and remain separate. An API/MCP request or scheduled
check is one logical usage event, not a duplicate search.

The new accounting uses existing migration47 tables. Logical AI operation IDs
survive worker retries. Each actual provider attempt obtains a separate durable
token reservation before network I/O. Provider-reported usage settles actual
tokens and releases unused capacity; explicit pre-inference rejection releases
capacity. Timeouts/crashes retain uncertain reservations. A retry cannot refund
or reuse a previous unknown attempt. Unexpected provider-reported overruns are
recorded without clipping, monetary charging or a free future allowance.

Queued report cancellation releases its unstarted report/shared-operation hold.
Failed reports can release the report dimension while retaining actual/unknown
AI usage. A report retry reserves its capacity before inference. Successful cached
or lexical reports still consume the approved shared AI operation/report allowance.
Missing operation IDs cannot become a shared `None` reservation.

Evidence: eight focused provider/ledger tests, queued cancellation coverage,
PostgreSQL atomic/concurrent reservation and upgrade-preservation coverage, and
the frozen complete backend run:1065 passed, one explicit live-mail skip.
The frontend has161 passing unit tests and 10 isolated browser checks.
These isolated paid-contract fixtures are not PayU recurring acceptance.

Production schema46 remains unchanged while PayU billing is disabled. The fresh
production backup restored exactly; local46→47 migration was idempotent with zero
row loss. Migration47 must be recovery-gated before any future paid activation.

Remaining provider gates: account-specific Zion/SI activation and API credentials/
authentication, webhook-verification contract, permitted recurring currencies and
international cards, settlement/pre-debit responsibilities, charge/tax disclosures,
then an explicitly authorized controlled real-money transaction and lifecycle tests.
No assumed currency conversion, unverified mandate or public paid entitlement is
created in their absence. Actual unit economics remain unproven where approved
model pricing or complete provider usage is unavailable.
