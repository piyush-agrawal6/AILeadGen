# HeySow release readiness

**NOT READY for public SaaS activation or production deployment.**

Local regression recovery is green and gated workspace foundations have real API,
UI, migration and browser evidence. These results do not certify a completed SaaS
product or authorize deployment. The current production system was not changed.

## Implemented locally

Verified membership scopes, tenant-safe identities/records/settings, internal-only
Gmail and platform controls, disabled legacy archive, owner-protected membership
roles, explicit workspace selection, company/personal profiles, one-use hashed
invitations, idempotent workspace creation, resumable validated setup, domain TXT
proof, bounded website-review proposals and optional reviewed AI ICP drafts are
implemented locally. New workspace
management stays disabled by default. Historical lead/contact/suppression data
has not been reset or removed.

## Blocking evidence and functionality

- Disposable PostgreSQL 16.15 now exercises real migrations, repository workflows,
  membership-backed ownership and concurrency. Pre-upgrade schema-22 dump/restore
  and upgrade through schema 26 passes independently. Full combined regression
  results are recorded in HEYSOW_TESTING.md when complete. A matching locked
  runtime and approved staging environment are still required before release.
- Public registration and coherent signed-identity admission are unfinished.
- Local onboarding/ICP/domain contracts have isolated evidence; live provider,
  owner DNS proof and a full customer journey have not been accepted in staging.
  New organizations cannot bypass onboarding into product APIs.
- Customer mailbox/CRM connections and tenant-isolated credential lifecycle are
  unfinished. Internal Gmail is not a customer-connected mailbox.
- Progressive global discovery, full company/contact intelligence, customer
  outreach, usage/entitlements, public API/webhooks/MCP and the AI Agent still
  require the phased implementation and acceptance described in the owner prompt.
- Public invitation delivery, new-account Google acceptance, notification
  presentation and full account security/data lifecycle controls are incomplete.

## Before any release proposal

Complete the next milestone, run a clean complete test/build/browser gate, preserve
an exact source checkpoint, restore a restricted database backup into isolated
PostgreSQL, validate the candidate there and document migration/rollback and
remaining risks. Obtain staging/release approval before production changes. Do
not activate registration, acquisition, outreach, infrastructure or real sends
as a side effect of development checks. OAuth/secret changes require the owner's
applicable approval; none has been made here.
