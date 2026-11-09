# PlaneByte Lead Engine

A workspace-based B2B prospecting application for discovering companies, reviewing public business information, managing campaigns and preparing customer-owned outreach.

Current flow:

```text
Discovery providers / reviewed CSV, XLSX or Sheets import
→ normalization and canonical-company deduplication
→ bounded public company crawling and contact extraction
→ company / ICP qualification
→ campaign and Master Leads
→ workspace email template → exact preview → guarded outreach
```

Website crawling supports company context and contacts. It does not run SEO/AEO/GEO assessments, Lighthouse, performance scoring, vulnerability testing or VAPT. Opportunity thresholds and audit PDFs are not qualification or outreach requirements. Contact availability and email send eligibility remain separate from company qualification.

See [prospecting separation and verification](docs/PLANEBYTE_PROSPECTING_SEPARATION.md), [engineering standards](docs/ENGINEERING_STANDARDS_AUDIT.md), [multi-tenancy](docs/MULTI_TENANCY.md) and [module architecture](docs/MODULE_ARCHITECTURE.md). The [legacy engine reference](docs/LEGACY_ENGINE_REFERENCE.md) is historical documentation, not a list of enabled features.

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

No production deployment, infrastructure changes, data reset or real outreach is part of this cleanup.
