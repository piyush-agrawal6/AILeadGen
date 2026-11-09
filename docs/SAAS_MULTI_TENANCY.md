# HeySow multi-tenancy stabilization

Status: **partial implementation; public SaaS release blocked**. This document is
an evidence-based inventory, not a claim that every query has been certified.

## Trusted context

`app/platform/context.py` binds an immutable request-local organization and actor.
There is no default tenant. `workspace_scope` validates active membership and an
active organization, rejects nested tenant switching and resets on exit. Request
middleware resolves membership before permission checks and before cache access.
The previous test-only automatic organization provisioning and global-owner fast
path were removed. A revoked primary allowlisted account does not retain access.

`job_scope` validates a persisted acquisition/workflow/scan/report owner against
active membership. Acquisition and scan workers enter this scope before claiming
or executing work. Report workers do the same. Scheduler dispatch groups work by
explicit organization, filters runs/schedules by that organization and rechecks
creator membership. Unknown ownership remains blocked, not reassigned.

The anonymous tracking surface uses a separate, stored opaque-token capability.
Its tenant is taken from the validated token/message, never posted by the browser.
This authority cannot connect to or send through a mailbox.

## Implemented repairs

- Acquisition jobs, campaigns and pipeline runs retain organization ownership.
- Canonical observation verifies the persisted business/run/campaign relationship.
- New identity aliases include a workspace namespace. Historical unscoped aliases
  remain readable only through a prospect ownership join; they are not deleted.
- Shared contact-evidence reuse joins the owning prospect before reading evidence.
- Workflow lookup/creation, report creation, sales services, notes, dossier access
  and deletion entry points require workspace context and resource ownership.
- Reconciliation scopes prospect, contact, history, queue and activity operations;
  newly created Master Lead states and qualification activities receive an owner.
- Permanent contact history rejects another-tenant overrides. Accepted-message
  recording, engagement flags and usage counts are scoped.
- The existing Gmail/Hostinger mailbox remains **internal only**. Customer account
  status accurately returns NOT_CONFIGURED. Customer mailbox health, sync, preview
  and send are rejected before calling the provider. Background inbox sync binds
  the existing account's persisted, active owner.
- Reply matching and bounce processing restrict messages to the internal account
  and its organization. Bounce contact invalidation no longer affects every
  workspace containing the same address.

## Verified tests

The full isolated backend suite passes 499 tests with zero failures or errors. It covers
missing context, mismatched resources, revoked owner, role denial, cross-tenant
API mutation denial, job ownership, independent identity alias stability, registry
separation, customer mailbox unavailability, historical migration preservation,
mocked sends, replies, DSNs and tracking. See the stabilization report for the full
suite; the focused pass does not certify unrelated paths.

## Remaining blockers

Migration 17 adds organization-keyed settings while retaining the historical
`shared_settings` singleton; settings consumers now use the shared scoped service.
The address-keyed suppression schema is still not a completed general
multi-customer connection model. Remaining ancillary creation paths still need a complete ownership audit; all
currently collected backend fixture and regression failures have been resolved. Remaining
read models, artifact/cleanup paths, job retries and integration configuration
require individual audit and regression repair. PostgreSQL integration has not
been validated on a dedicated local server in this environment.

Public registration stays disabled. Do not expose a customer's connection as the
internal runtime mailbox, migrate production, or deploy this recovery checkout.
