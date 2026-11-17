# Subscription release — 17 November 2026

This report distinguishes implementation, actual provider tests and deployed configuration. Public checkout is not approved merely because webhook receipts or catalog creation succeeded.

## Verified before release

- The owner approved Terms, Privacy, Refund and Cancellation version `planebyte-subscriptions-2026-11-17-v2` in this chat.
- Production signed `checkout.completed` sample `evt_2WX1Bdt55G8jllA0SSo6OU` reached the encrypted event inbox with HTTP200. It did not grant an entitlement.
- Starter/Growth/Scale paid and 72-hour trial products were created and independently retrieved in Creem production and test environments. Prices USD59/149/379 are tax-inclusive, recurring monthly. No live checkout purchase was made.
- A real Creem test hosted payment completed. The provider independently reports an active automatically charged subscription, USD5900 cents paid and a calendar-month period. It remains isolated from production application customers. Initial local fixture/provider-customer attribution mismatch was denied rather than credited to a different workspace.
- Fresh recovery backup of the current NEW Neon database: 306,351 bytes, SHA256 `0efb4e7b40975567e361f687c1cbd3bdc10fab28359588586c84521eb1e76542`. Snapshot-consistent restore reproduced every original table. Additive migration1005→1006 preserved all original customer rows; second apply0. One real customer was preserved. Old archive was never connected.
- Full isolated backend run: 1,221 passed, one deliberate real-outreach skip. Subsequent focused checkout retry/country/dispatch tests are recorded separately in restricted release evidence.
- Patched Next16.4.5 frontend: 197 unit tests passed and production build passed. No older dashboard/settings/Discover/graph/theme implementation was replaced.

## Implemented

Mandatory fifth setup step; four options; selected conversion plan and fresh recurring consent; server/API/worker entitlement checks; bounded prepayment setup-only AI budget; persistent checkout attempts and independent provider verification; exact72-hour trial claims; saved plan/usage periods; duplicate/out-of-order event handling; encrypted webhook inbox; current-period cancellation; billing portal; payment history; subscription status emails. Existing paid periods and historical seven-day trial snapshots remain intact. Existing PayU and Lead Engine source/data are preserved.

Billing country declarations remain unverified until supported by reviewed evidence. Editing a country never selects an approved provider. A single provider customer cannot be reassigned between workspaces. India does not fall back to Creem or an unapproved PayU mandate.

## Release state

Deployment and final production checks are in progress. Do not describe this source-only implementation as deployed until this section is replaced with actual deployment references.

## Remaining acceptance and external prerequisites

- Genuine card trial activation, exact first-charge disclosure, cancellation and conversion/renewal acceptance are not proven by the signed sample.
- Creem merchant verification/payout readiness needs account-specific evidence; test-mode success does not prove merchant readiness.
- PayU India requires approved INR amounts and actual recurring mandate/product permissions plus separate sandbox acceptance. USD PayU is not enabled.
- No approved yearly pricing; yearly checkout stays disabled.
- Global public registration remains closed pending the complete production customer journey. Existing controlled owner signup is preserved.
- No live charges/refunds/mandates, customer deletion, archive mutation or paid infrastructure changes were authorized by this release.

Restricted machine evidence is under `data/artifacts/verification/creem-20261117/`; it includes private provider responses and must not be published or committed.
