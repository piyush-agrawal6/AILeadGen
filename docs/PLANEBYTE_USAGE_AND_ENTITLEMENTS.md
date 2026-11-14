# Usage and entitlements

## Access is not a payment

Membership, completed onboarding, product availability and an actual product
grant are enforced server-side. Manual owner Beta grants remain independent of
settled sandbox subscriptions. Lead Engine's stored grants are preserved while
its availability gate remains false. Admission remains restricted to the approved
accounts; no pricing link opens public registration.

## What the customer usage page measures

- Requested daily searches: persisted workspace discovery reservations.
- Source capacity: committed per-source upper-bound request reservations,
  including failures whose transport consumption may be unknown.
- AI operations and tokens: committed daily capacity reservations; these are
  distinct from provider-reported input, output, cached and thinking tokens.
- Active capacity: non-archived monitors and active workspace memberships.
- Historical sandbox plan usage: only an independently settled current sandbox
  period. Historical Razorpay amounts never become the commercial catalog.
- Provider cost: unknown unless actual usage and an approved model price exist.
  No price is inferred from a model name or a different model's rate.

The page does not invent separate export/report quotas where they are not
implemented. Research/report inference uses the shared AI capacity. The private
assistant uses the same gateway and reservations, without SMTP or tool execution.

## Existing atomicity

Search/source/AI reservations use existing workspace/global locks and durable
records. Cycle reservation IDs are idempotent and immutable. Retrying an accepted
research request reuses its durable job instead of silently generating another
copy. Fresh authorization and lease/revision fences apply before persistence.
Saved evidence remains readable when a consumption quota is exhausted, subject
to membership, retention and source-withdrawal controls.

## Commercial allocations are not approved yet

The approved prices are not approved numeric quotas. The commercial catalog has
`limits: null`, explicitly meaning **not finalized**, never unlimited. Do not
reuse sandbox20/40/60 quotas or Lead Engine contact credits.

Inspected operator defaults are20 searches/workspace/day,100 globally/day,
10 AI calls and60000 reserved AI tokens/workspace/day, and a12-hour minimum
scheduled interval. Production runtime overrides must be inspected before
capacity approval. The verified owner workspace has only three recorded Vertex
requests,4838 input and997 output tokens, with zero priced records. This sample
cannot establish commercial unit economics or justify a binding allocation.

Before approval, prepare candidate monthly allocations alongside the required
operator ceilings, actual model costs, source requests/search, monitor runs
sharing search capacity, expected active workspace count and report/AI accounting.
Obtain owner approval once for the full numeric table, then implement and test
the identical versioned limits in APIs, workers, developer API and MCP. Do not
claim this commercial enforcement is complete while the table is undecided.

## Billing periods

Operator safety windows currently reset at UTC midnight. Paid-cycle quotas must
use verified provider period boundaries, not client dates or a calendar-month
approximation. Existing cancelled sandbox records stay cancelled. No subscription
snapshot is rewritten by a catalog version change, and no payment mandate is
transferred between providers.
