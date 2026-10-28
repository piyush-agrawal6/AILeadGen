# Phase 3 architecture

The existing Python pipeline and dashboard remain one product. Next.js 16 serves the dashboard on Vercel. Google OAuth sessions terminate there; the browser calls only same-origin Next.js routes. Those routes authorize the current email and sign each upstream request to FastAPI on Cloud Run. FastAPI independently checks the actor, signature, timestamp and persisted replay nonce.

PostgreSQL is the production source of truth for campaigns, child runs, events, canonical prospects, observations, workflow, notes, scores, settings and artifact references. SQLite remains the desktop development backend. `database/postgres.py` adapts the repository interface rather than maintaining a second pipeline. Migrations are explicit in production and serialized with a PostgreSQL advisory lock.

Transaction-local schema, UTC and statement timeouts are reapplied after each commit, so transaction pooling cannot leak a previous session's schema. The worker's session advisory lock uses the direct Neon endpoint, because transaction pooling cannot retain that lock across commits. Real PostgreSQL tests cover both behavior boundaries. See [Neon connection pooling](https://neon.com/docs/connect/connection-pooling).

A campaign expands a city × vertical selection into bounded child runs. The database reserves dispatch slots before Cloud Run Jobs are invoked. Each worker takes a per-run advisory lock, persists a lease and heartbeat, checks cancellation between units, and schedules queued work on completion. Closing the dashboard does not own or stop execution. Two active scans are permitted; each job has one task, one vCPU and 2 GiB memory. API instances are capped at two.

Discovery uses public Overture GeoParquet and OpenStreetMap tags. Market presets are data in `config/market_presets.json`; custom geocoding remains available. Vertical rules and taxonomy are in `config/verticals.yaml`. The original restaurant vertical remains available alongside the seven recommended families.

Canonical prospects retain collaboration state across observations. Strong source IDs, location-scoped domains, phone/name pairs and name/address pairs create identity keys. Shared corporate domains include street addresses to keep separate venues apart. Ambiguous persisted identity conflicts stop for review; historical backfill may unite groups created within its own transaction when later observations bridge their strong evidence. It never automatically merges persisted workflow.

One bounded crawl supplies website, SEO and passive security analyzers. Scores range from 0 to 100 with higher scores indicating more service opportunity. Unassessed SEO/security remain null. Scoring version and evidence are persisted. Scale, opportunity selection, quality thresholds and rediscovery preferences determine qualification independently of the legacy scores.

R2 stores generated reports, exports and audit objects under validated keys. PostgreSQL stores references. Downloads stream through authenticated routes, with private cache policy and sandboxed HTML. Workers use ephemeral local scratch only; their durable state lives in PostgreSQL and R2.

Local deterministic tests use explicit `APP_ENV=test`, isolated SQLite databases and local artifact directories. Test fixtures and authentication bypasses are rejected in production. Real PostgreSQL integration tests use a temporary schema and remove that schema afterward.
