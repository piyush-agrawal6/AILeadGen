# Multi-tenancy

Worker resource contract: `app/platform/workspace.py.business_workspace` validates
the persisted company, run and optional campaign against the expected organization.
Acquisition evidence reuse joins prospect ownership before reading contact data.
The caller must obtain expected ownership from verified membership or an owned job
record. Neither provider data nor an arbitrary request field establishes membership.

`app/database/organization_schema.py` adds organizations, memberships, profiles and tenant columns. `app/api/organization.py` resolves membership, and middleware stores the verified organization on request state. Read cache keys include actor and organization. Browser-supplied IDs do not establish tenant access.

Template CRUD now prevents cross-workspace upsert takeover. Workspace copy rendering joins the company run and template through the same organization. Existing company observation requires an organization; tests and legacy callers that omit it must be repaired rather than weakening that boundary.

Still required before public SaaS release: all legacy mail/account/registry paths, background tasks, exports and source admission must carry verified tenant context; no global credential may serve another workspace; migration/backfill and cross-tenant integration tests must pass. Existing internal data remains retained. This document does not certify complete isolation.
