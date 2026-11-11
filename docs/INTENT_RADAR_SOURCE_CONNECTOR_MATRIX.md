# Intent Radar Phase 2 source connector matrix

## Independent product audit source follow-up — 2026-11-11

Historical source evidence below remains intact. Current additive evidence:
`data/artifacts/verification/intent-radar23-product-live-sources-final.log` and the
genuine real-routing source/Vertex browser log.

- Eight bounded source operations completed: Ask; Show; Stack Exchange; W3C RSS;
  combined HN/SE/RSS; New/Top/Best/comments; **opt-in jobs**; Discourse Meta RSS.
- HN job feed genuinely returned 20 scanned items/21 requests. Default discovery
  still excludes jobs. Job advertisements are now penalized by deterministic V3;
  transport coverage is not verified purchasing intent.
- Stack Exchange Python check reported quota remaining 297; combined check 296.
  Commercial approval is still pending and no customer source account connected.
- All four source families are returned by the repaired local preview catalog;
  source config/health endpoints return 200. Owner workspace remains HN Available,
  SE Requires approval, RSS/Discourse Not configured. A stale Phase 1 process
  caused the one-source view, not missing current connector definitions.
- Genuine Atom remains unverified. Category/tag Discourse access is public-feed
  configuration, not arbitrary/private forum search. Incremental cursor and
  cross-family duplicate policies are incomplete; completed-source job recovery
  now reuses fenced persisted checkpoints without refetching after hard-kill.
- Read-only evaluation permission is not commercial/publisher/staging approval.

### Preserved prior connector evidence

Current local evidence: 2026-11-11. All requests were read-only, bounded and made
against public endpoints from a disposable workspace/database. Configuration in
that runtime is evaluation approval, not production/commercial approval.

| Source | Supported access and actual live result | Bounds/safety | Remaining gate/coverage limitation |
|---|---|---|---|
| Hacker News | `hacker-news.firebaseio.com/v0/`; Ask and Show each 20 scanned, 21 requests; New/Top/Best with depth-one replies: 19 scanned, 22 requests | Public API only, fixed host, four-second request timeout, 22 requests, at most three feeds and two direct replies per story under the shared cap; no author profiling/external-link crawling | Recent snapshot only; no historical full-text search. Jobs code inspected but no live job-feed check. |
| Stack Exchange | `api.stackexchange.com/2.3/search/advanced`; Python question search: 20 scanned, one request, quota remaining 299; combined web query: 20 scanned, one request, remaining 298 | At most three configured sites, first page 20/site, safe five-second/500KB transport, IP/method/query cooldown, backoff and server-only optional key; original link/license/attribution | Commercial API terms/attribution review pending; not whole-network discovery or answers/comments search. |
| RSS/Atom | `https://www.w3.org/news/feed/`: 25 scanned, one request; combined repeat safely reused cache with zero requests | Operator-approved HTTPS hosts/public DNS, no auth parameters/redirects, 500KB XML ceiling, no DTD/entities, 40 entries/feed, four selected feed IDs, ≥60-minute polling, 1–30-day declared retention | Publisher-specific review required. Both RSS and Atom parser/ETag behavior tested; a separate W3C Atom endpoint probe (`/blog/feed/atom/`) returned 404. No distinct live Atom-format success claimed. |
| Approved Discourse | `https://meta.discourse.org/latest.rss`: 30 scanned, one request; genuine linked public discussions | Same approved-feed adapter; `.rss`/`.atom` endpoints only; no login, API key, posting, private categories or generic forum search | Meta robots permits latest.rss for the general agent; topic/category RSS patterns are disallowed and were not requested. General production instance/terms approval remains pending. |

Seven initial source checks completed, including a combined HN/Stack Exchange/RSS
check scanning 65 items. Initial distinct retained signals: HN 44, Stack Exchange
20, Discourse 20, RSS/Atom 10 (**94 total**). Scanned items and matched/retained
signals differ because filters and per-provider result limits are applied.

Native IDs, canonical public URLs, original publication timestamps and attribution
are preserved. Cache edits, source withdrawal, tombstones, per-feed errors,
conditional requests and revocation fences have isolated tests. No fixture
transport is counted as genuine-source evidence. Commercial terms review cannot
be inferred from a successful HTTP response or a robots permission.
