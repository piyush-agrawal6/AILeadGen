# Caching strategy

Existing `app/api/read_cache.py` uses an explicit read allowlist, short TTLs, per-key locks and an Upstash generation key. Identity includes user, organization, path, ordered filters and generation. Successful writes invalidate cached reads; cache failures fall back to the database.

Do not cache authentication decisions, send eligibility, previews, sending, tracking, unsubscribe, inbox content or private exports. Never omit workspace or permission context from a tenant-specific cache key. Do not move credentials to client caches.

New cache use requires evidence of repeat cost, a freshness policy, invalidation tests and hit/miss/latency measurement. No new cache product was introduced. Compiler-cache removal is local housekeeping and is unrelated to production application caching.
