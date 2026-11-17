# Creem-only production release — 17 November 2026

The owner replaced the dual-provider decision with Creem-only billing globally, explicitly authorized customer-initiated Live checkout, stopped all browser automation, and confirmed Creem Live → Balance → Payout Account is **Approved — live payments allowed**. The account-review status is owner-confirmed, not inferred from an API key or product lookup.

## API and existing acceptance evidence

- Existing six production and six sandbox product variants are reused. USD59/149/379, recurring monthly, inclusive tax configuration, trial duration3days, zero trial charge.
- Real hosted sandbox immediate payment: provider-confirmed active subscription and independently retrieved paid USD59 transaction. No real money moved.
- Genuine sandbox card trial: provider-confirmed trialing state; exact259200seconds; workspace entitlement and one-use trial claim verified in disposable local PostgreSQL. Real provider cancellation returned canceled; no future charge remained scheduled. Existing trial access was preserved to its recorded end.
- Production raw-body signed test event `evt_2WX1Bdt55G8jllA0SSo6OU` was genuinely sent by Creem and durably accepted. It never created an entitlement.
- An authorized unsubmitted Live checkout was created and independently retrieved in mode prod, pending. No card, mandate or charge was submitted. That session alone was not represented as proof of merchant approval.
- Backend regression regressions are retained in restricted evidence; the previous full subscription suite passed1221 with one intentional outreach skip. Global-provider supplementation passed75 tests. Browser automation was stopped per owner instruction; no subsequent browser acceptance is claimed.
- The exact72-hour activation clock is provider-authoritative. An absolute pre-activation time is conditional on activation now; confirmed dates are displayed from Creem after activation. No fabricated fixed trial start is persisted.

## Retirement and preservation

No active PayU checkout, country routing or separate INR catalog remains. New API checkout/callback attempts to the retired provider return410. Historical orders, receipts, refund-review requests, financial rows, consent and access snapshots remain. Legacy provider source is retained only for archive/recovery and historical verification, including Lead Engine compatibility. Unused PayU runtime bindings are removed only after checking current financial dependencies; Secret Manager versions and operator credentials remain available for protected archives.

Creem verifies its customer's billing country and payment method; India is allowed through the same hosted checkout where Creem supports it. Country declarations do not grant entitlement. Product access still requires an independently verified current subscription or preserved legitimate existing access.

Policies are versioned as `planebyte-creem-global-2026-11-17-v3`, under the owner's final Creem-only publication directive. Prior v1/v2 documents and consent records are retained. No yearly checkout, handmade currency conversion or unverified GST is enabled.

## Rollout

Exact deployment revisions, configuration and activation checks are recorded in the restricted global release JSON. Do not claim a genuine paid production customer journey has passed: the owner will personally enter payment details and test it after handover.
