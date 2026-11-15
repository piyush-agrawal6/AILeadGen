# Lead Engine preservation and future reactivation

Lead Engine is hidden for the Intent Radar release, not discontinued. Its routes,
components, FastAPI services, discovery/enrichment, contacts, campaigns, outreach,
Gmail integration, schedules, safeguards, tests, configuration and migrations
remain in this repository. Historical data, contact history and suppression
records are not reset or deleted. Shared services remain in use.

Current customer access is denied through `LEAD_ENGINE_AVAILABLE=false` in the
backend/workers and Vercel. Direct legacy APIs, pages, developer scopes and worker
entry points retain their server-enforced gates. Stored workspace product grants
are preserved. Public registration and outbound automation remain separately off.

Future reactivation requires owner approval and normal regression/release checks:

1. Set the existing `LEAD_ENGINE_AVAILABLE` variable to `true` on the existing API,
   worker/acquisition jobs and Vercel project; deploy/promote matching versions.
2. Verify the intended workspace's existing `LEADGEN` product entitlement through
   the authoritative server administration flow. Availability alone never grants
   a workspace access. Do not bulk-enable unrelated customers.
3. Recheck Google sessions, tenant isolation, Gmail configuration and existing
   schedules. Re-enable only separately authorized sending/scheduling controls.
4. Run the preserved Lead Engine, Gmail and tenant regression suites and actual
   authorized-workspace acceptance before inviting customers.

No feature rebuild, deleted-source recovery or database restore is needed to
restore this preserved implementation. A data restore is a disaster-recovery
operation, not a product-toggle step. The existing three email/scanning flags and
global suppression protections must not be enabled or bypassed implicitly.
