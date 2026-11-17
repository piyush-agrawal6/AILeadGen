# Approved test-customer reset — current result

**Verified 17 November 2026, 08:25 PM IST.** The owner explicitly approved the42-record preview for the account created at17:44IST. The exact reset committed and independent production checks passed. **Do not repeat this reset.** Read current production state before acting on any repeated reset message; accounts created afterward require a new scoped preview/confirmation.

- **42operational rows deleted** for`contact@planebyte.com` and workspace`fd8880da-c399-4796-8520-92a292a51fe8`.
- **Zero customer accounts and zero active customer workspaces** remain. The original identity unique keys, session, OTP/login links, workspace/profile/services/ICP proposal/AI jobs and setup quotas are absent. Actual signed account-session validation returns401.
- One archived minimal billing workspace and three non-login retired identity references remain to preserve historical consent/billing relationships. They have no customer accounts, authentication sessions, passwords, Google identities or workspace memberships.
- Earlier genuine Creem Live Starter subscription remains **`canceled`**, independently retrieved after this reset, with **next transaction null**. Its prior53-row reset/cancellation completed; no charge or refund was initiated by this agent.
- **33audit/security rows, five consent facts,12Creem products,12provider-event records, prior cancelled billing/cancellation history, schema1006and system configuration preserved.** This account's one consent foreign key was relinked to its non-login retired reference. Old retired references/archived ledger and unrelated system rows were unchanged.
- Fresh444,649-byte backup, exact restore of129tables/191rows and local reset rehearsal passed. SHA-256`84824cf35d13dac079ca16046d7c7cde4dd5a64574e896505425e01a2188ce6a`. Production matched the exact approved target hashes and preserved protected/unrelated fingerprints before committing. Old Neon archive was never connected. Restricted evidence:`data/artifacts/verification/test-customer-reset-20261117-round3/`.
- Fresh controlled signup for **contact@planebyte.com**: **https://app.planebyte.com/signup**. Signup/login/legal and API health checks passed; no new customer/OTP/payment was generated for verification. Real owner signup/OTP/card entry remains the owner's acceptance step.
- **Mandatory Step5 and Creem Live checkout remain enabled**, API`leadengine-api-00178-juv` and frontend`dpl_Bnw3PDBXntW1sAEyCbirdHbqK7NU`. This reset did not redeploy a service, change schema, modify products/webhook configuration or perform browser automation.

## Exact current deletion counts

| Table | Deleted rows |
|---|---:|
| `account_login_tickets` | 1 |
| `account_verifications` | 1 |
| `acquisition_ai_cache` | 2 |
| `ai_request_usage` | 3 |
| `customer_accounts` | 1 |
| `customer_sessions` | 1 |
| `customer_workspace_access` | 1 |
| `icp_ai_proposals` | 1 |
| `organization_ai_usage` | 2 |
| `organization_memberships` | 1 |
| `organization_onboarding` | 1 |
| `organization_products` | 3 |
| `organization_profile_job_events` | 4 |
| `organization_profile_jobs` | 3 |
| `organization_profile_sources` | 5 |
| `organization_profiles` | 1 |
| `organization_services` | 2 |
| `organization_setup` | 1 |
| `organizations` | 1 |
| `subscription_requirements` | 1 |
| `subscription_setup_reservations` | 1 |
| `subscription_setup_usage` | 1 |
| `transactional_notification_events` | 1 |
| `transactional_notifications` | 1 |
| `user_profiles` | 1 |
| `users` | 1 |
| **Total** | **42** |

## Historical earlier reset records

The following21-record report and earlier zero-account statements describe a prior account generation. A later53-row reset cancelled its genuine Live trial; the current42-row result above supersedes all pending-confirmation/account-presence statements.

Completed after the owner approved the exact scoped preview. This report supersedes older statements that the owner account or its seven-day trial remains present.

## Actual production result

- Deleted **21 approved rows** belonging to `contact@planebyte.com` and workspace `582a2cbb-36aa-4956-9bcc-dc1de8d1faae`.
- Zero customer accounts and zero customer workspaces remain. One retired non-login consent reference is retained; it has no customer account, password, Google identity, session, workspace or access.
- All four stored sessions, the old login ticket, OTP challenge, password-bearing account, original sign-in identity, workspace/profile/setup and trial/access records are absent. Signed production session validation returns **401**.
- Existing 11 audit/security rows and three consent facts are preserved. Only the approved three consent foreign keys were relinked to the retired reference so both original signup keys are available.
- All 12 Creem product mappings, six provider-event records, provider readiness, schema1006, migration history and other system configuration are preserved. No subscriptions/payments/ICPs/research profiles/AI jobs existed for deletion.
- The old archive was never connected. No database reset, schema change, service redeployment, real charge, refund, remote cancellation, email send or customer signup was performed for this reset.

| Table | Deleted rows |
|---|---:|
| `access_periods` | 1 |
| `account_login_tickets` | 1 |
| `account_verifications` | 1 |
| `customer_accounts` | 1 |
| `customer_sessions` | 4 |
| `customer_workspace_access` | 1 |
| `launch_trial_claims` | 1 |
| `organization_memberships` | 1 |
| `organization_onboarding` | 1 |
| `organization_products` | 3 |
| `organization_setup` | 1 |
| `organizations` | 1 |
| `transactional_notification_events` | 1 |
| `transactional_notifications` | 1 |
| `user_profiles` | 1 |
| `users` | 1 |
| **Total** | **21** |

## Recovery and exactness

Fresh restricted backup:383,392bytes. SHA-256 `ee46a87c5f3e150beb245160cf64e2f88d92b2082842e134b37eb8d74ebc13ff`. Exact isolated restore matched all129tables and119rows. The scoped deletion was rehearsed locally and rolled back before owner approval. Production execution rechecked the exact target-row hashes, deleted in dependency order in one transaction, preserved protected/system fingerprints, and was verified independently after commit. Recovery files and detailed restricted evidence are in `data/artifacts/verification/test-customer-reset-20261117/`; do not commit the database backup or private payloads. Do not repeat this reset.

## Deployed signup and billing

- API **`leadengine-api-00178-juv`**,100% customer traffic; source`a68ef91f613755ccd8a139a2068eebe8d942650b`, build`9594b7da-a702-41c4-b0f6-36c032c71075`.
- Frontend **`dpl_Bnw3PDBXntW1sAEyCbirdHbqK7NU`**,source`08b40ee554ea4eb0bbbc6cf091275acf93bce998`, promoted to https://app.planebyte.com .
- Creem Live checkout **enabled**, production secret bindings independently checked. Mandatory Step5 and72-hour provider-confirmed card trial configured. Global USD59/149/379 monthly; yearly disabled. Active PayU runtime bindings removed; stored protected credentials/history retained.
- Production webhook enabled for all required subscription events. Genuine signed event`evt_2WX1Bdt55G8jllA0SSo6OU` previously received; current unsigned/tampered callbacks return400. Guest billing APIs return401, protected product/billing pages redirect to real login. Signup/login/legal pages return200.
- Actual sandbox card trial and provider cancellation passed earlier. No Live monetary transaction has been performed or claimed.
- Fresh signup: **https://app.planebyte.com/signup** using **contact@planebyte.com**. Controlled registration permits that address; unrestricted public registration remains false.
- Owner performs actual fresh password/OTP→onboarding→Step5→hosted card/payment→dashboard acceptance. The newly reset customer journey is not represented as already passed.

## Remaining release context

SaaS checkout is deployed and handed over for the owner's personal Live test. Marketing candidate`6afc2807b516b4f7e18a2371` built separately and is not yet promoted; it did not block the SaaS release. Do not use browser automation. Preserve all newer UI, themes, database records, Lead Engine source and historical financial/audit records.
