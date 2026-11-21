# PlaneByte Intent Radar

PlaneByte helps workspaces discover and review public buying signals. The product includes company setup, ICPs, Discovery, monitoring, research, reports and controlled integrations. Creem is the commercial subscription provider. Shared billing is explicit; membership in a workspace is not an entitlement to another account. See [cleanup scope and verification](docs/REPOSITORY_CLEANUP_REPORT.md).

## Safe local preview

From the repository root, use two terminals:

```sh
.venv/bin/python scripts/local_preview.py backend
.venv/bin/python scripts/local_preview.py frontend
```

Open http://localhost:3000. The launcher reads the existing root `.env`, preserves real Google authentication and uses the separate local preview database. It disables provider acquisition, AI inference, email sending, sync and automatic execution. It does not modify `.env` or production settings. The local preview requires the existing permitted Google account and workspace membership.

The modular backend uses PostgreSQL in production and isolated SQLite/PostgreSQL test databases. The frontend uses Next.js, React and the existing authenticated API gateway. Credentials stay server-side. Public signup remains blocked pending the broader SaaS isolation and release acceptance.

## Verification

Backend: `.venv/bin/python -m pytest tests`. Frontend: `npm test`, `npm run typecheck`, build and the isolated Playwright configurations in `dashboard/`. Provider tests and live email acceptance are opt-in; ordinary tests must not contact prospects. Exact commands, logs, limits and latest outcomes are recorded in the separation report.

## Build and deployment

Use Python 3.12 with `requirements.lock`. The ASGI entry point is `app.api.server:app`, and Cloud Run jobs use `python -m app.worker`. Production uses the `intent-radar-v1` PostgreSQL lineage; do not bootstrap production from the local preview. The dashboard build uses Node 24 and its checked-in npm lockfile. Follow the [guarded integration and packaging process](docs/PLANEBYTE_PRODUCTION_INTEGRATION.md), including the negative source control, tested backup restore and schema-compatible rollback. A feature branch test result alone is not release authorization.
