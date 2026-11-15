# November 15 development recovery

This continues the `b11d753a0dcaa9f51f65bdb1070722d51304dc71` checkpoint. It is not a restart or a production-readiness certification.

## Changes found and preserved

Git history was unchanged at resume. The newer dashboard, unified settings, navigation, Intelligence Graph, Discover and dark-mode improvements were uncommitted working-tree changes. A recoverable patch, source archive and per-file hashes were saved to `data/backups/resume-20261115/` before implementation. Additional authentication-screen/style changes arrived during verification and were retained. The independent `planebyte-website/` directory remains untouched.

The new settings category/tab routes, compact dashboard, hidden Lead Engine navigation, graph styling, account menu, theme tokens and focused onboarding shell remain in place. Changes to existing product screens are limited to consuming the approved onboarding research defaults and showing saved active ICPs in the graph.

## Implemented continuation

- Website → reviewed company/offering → suggested ICPs → approved primary ICP → explicit completion. The previous Lead Engine setup remains available behind its existing reversible availability control.
- Existing company-profile jobs perform bounded website research and ICP/advice work. No new infrastructure, tables or authentication flow was introduced. Progress, review references and defaults use the existing versioned setup record.
- Approved company details and offerings use the canonical profile/services store. Accepted active ICPs use the existing ICP service, private proposal provenance, profile-version checks and idempotent request keys. Discovery keywords/exclusions and primary ICP are shared with Discover and new-monitor defaults; completion starts neither.
- Visible setup guidance reads saved facts without AI and uses the existing structured gateway for requested interpretation. Availability reflects actual configuration and role gates. Failures retain manual setup, saved state and explicit retry/cancellation.
- Owner-only automatic resume; completed users bypass the setup gate. Invited/read-only members cannot create or overwrite the company through this flow. Onboarding does not grant product enrollment.
- Website research enforces public destination validation, HTTPS on every hop, same registrable-domain redirects, bounded pages/bytes/time/concurrency, robots rules and publisher content-use restrictions before sending evidence to AI. Unsupported/unknown fields require manual review.
- Company-job dispatch now has a global two-job limit, an expiring dispatch claim and acknowledgement fencing. Failed attempts remain quota-bound; cancellation/role/lease checks prevent late results from applying.
- Overview hydration uses a bounded snapshot instead of repeated list hydration: three statements for the full overview service and two for its summary service, including fresh scope authorization. Middleware/authentication queries are additional. PostgreSQL and SQLite semantic-equivalence, retention and tenant tests cover this optimization.
- Scheduler database maintenance runs outside the HTTP event loop, closes database connections before asynchronous dispatch, and skips a revoked candidate without starving other authorized jobs.

## Verification and limits

The initial broad regression completed with 1,079 passes, one explicit live-mail skip and eight recorded warnings. Subsequent security/recovery changes are being checked in a final full run. Targeted setup/website/ICP checks passed 34; a separate PostgreSQL setup worker/replay/defaults check passed. The production-style frontend build and 165 frontend unit checks pass. The two real-app onboarding browser journeys passed with synthetic sources/providers, including manual failure fallback, reload/resume, shared graph/Discover context and light/dark responsive checks. Final unchanged-build product and onboarding browser evidence is recorded in the release checklist when complete.

Failures were retained rather than relabeled: incorrect initial test table/usage assertions; two outdated browser selectors; a product browser run invalidated by overlapping build output. Corrected assertions preserve the actual user-visible behavior. Synthetic signed local sessions and provider responses do not establish real Google OAuth or external-provider acceptance.

No production migration/reset, destructive cleanup, OAuth/secret replacement, payment activation, outreach or infrastructure move was performed. Current candidate deployment/latency and real bounded provider acceptance remain separate release gates. Independent human evaluation, additional source permissions and merchant recurring-payment approval remain external launch blockers. Public paid launch remains closed.
