# Active source integration execution — 18 November 2026

Scope: Stack Exchange20 communities;10RSS/Discourse and10Atom candidates; complete supported HN; GitHub public/installations/webhooks; YouTube search/metadata/comments with unapproved analytics isolated; Bluesky Public API and Jetstreamv2. Owner directives are in the two18November attachments; this is implementation/deployment, not an audit-only task.

Preserve integration branch codex/production-integration-20261117 and onboarding/UI/backend fixes. Starting source230c54d; actual API183/worker sourcecf0e436, frontend0ad3295. Existing new Neon1006; root DATABASE_URL is the archive, use DATABASE_URL_NEW explicitly. Never reset, delete customers, alter billing/signup/access or expose secrets. No browser automation is needed. No agents were delegated.

Verified initial gaps:
- Connector registry exposes HN, Stack Exchange, RSS/Atom, Discourse only. GitHub/YouTube/Bluesky absent.
- Local Stack key and20-site comma configuration exist; code splits semicolons. Actual API/worker Stack flag false and no source secret bindings. Local env does not update production.
- Local GitHub App identity/private-key reference, installation ID, YouTube API key, Bluesky host/stream settings exist. Provider-named secrets not in current Cloud project inventory; verify actual private-key location/reference before asking for credentials. Do not generate replacement API keys.
- RSS/Atom parser loses nested author/category terms, XHTML markup, relative links and updated times; no endpoint-specific operator permission registry.
- HN supports six selected feeds (max3/check), shallow comments only; lacks supported updates/user/nested relationships.
- Shared discovery, signals, opportunities, growth, monitors, alerts, quotas, safe HTTP, jobs/leases, retention and integration vault already exist. Extend them, do not duplicate.
- Production schedules are false and scheduler jobs paused. Need genuinely verified bounded scheduling without changing customer entitlements.
- Current official YouTube docs confirm100search calls plus10,000other-method units by default; actual project allocation remains to inspect. Derived-metrics approval and30-day content refresh/deletion are separate gates.
- Current official Bluesky Jetstreamv2 docs confirm xrpc.v1.json envelopes, seq cursor and canonical subscribeEvents endpoint; do not accidentally implement legacy timestamp/v1 parameters.

Execution checklist (mark only after verification):
- [ ] Normalize existing source configuration; fix RSS/Atom parsing/security and tests.
- [ ] Implement unified provider policies/catalog, workspace configs, persistent health/quota/checkpoints.
- [ ] Finish Stack question/answer/comment/community/tag/update/pagination support.
- [ ] Finish HN feeds/items/nested comments/users/updates/checkpoints/deletions.
- [ ] GitHub JWT/install-token auth, public REST/GraphQL search, repo detail/comments/releases, quotas/cache.
- [ ] GitHub customer OAuth/install selection, encrypted ownership, webhook HMAC/dedup/revocation worker.
- [ ] YouTube public API/search/channel/video/comments/replies/pagination, shared fair quota/cache, retention and independent operation gates.
- [ ] Bluesky real search/profile/feed/thread; v2 stream filtering/cursor/reconnect/delete/supervision.
- [ ] Source-aware AI, signals/opportunities/growth/reports/MCP, no unapproved YouTube blended analytics.
- [ ] Existing UI source selection/configuration/health/filters and provider provenance.
- [ ] Backup/restore and additive migrations for both clean PostgreSQL and legacy test lineage.
- [ ] Real provider acceptance, actual worker/schedule execution, tenant/security/auth/billing/AI regression.
- [ ] Source-only secret/config bindings; verified API/worker/frontend deployment using guarded release process.
- [ ] Precise per-source production/permission/blocker report and actual owner actions.

Private evidence: data/artifacts/verification/sources-20261118/. Keep provider/customer payloads, environment copies, credentials and operator files out of Git.
