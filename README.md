# LeadEngine — shared lead intelligence

Phase 3 adds a Google-authenticated dashboard, shared PostgreSQL prospects and workflow, multi-city/vertical campaigns, separate website/SEO/passive security opportunities, private R2 artifacts and bounded Cloud Run workers. Desktop SQLite operation remains available. Public discovery sources require no paid lead-data API; cloud hosting and storage may incur charges.

Start with [deployment and local setup](docs/DEPLOYMENT.md), [architecture](docs/PHASE_3_ARCHITECTURE.md), [security](docs/SECURITY.md), [modernization audit](docs/PHASE_3_AUDIT.md), [quota evidence](docs/GCP_QUOTA_REPORT.md) and the [Phase 3 report](docs/PHASE_3_REPORT.md).

The sections below preserve the original engine reference. Their local-only architecture and zero recurring hosting cost description apply to the original desktop mode; production uses the shared cloud architecture above.

**LeadEngine** is an internal, local-first B2B prospecting and intelligence engine that discovers legitimate public businesses in target geographic markets, audits their technical infrastructure and SEO, scores their sales potential, and produces ranked prospect lists for digital agency outreach (web development, redesign, local SEO, technical SEO, and conversion optimization).

Operates with **$0 in recurring software or API costs**:
- ❌ No Google Maps scraping
- ❌ No Apollo, Hunter, ZoomInfo, Clay, or paid lead databases
- ❌ No Serper, SerpAPI, DataForSEO, or paid search APIs
- ❌ No OpenAI or Anthropic API keys
- ❌ No paid proxies or email verification APIs
- ✅ 100% open geospatial data (Overture Maps Foundation GeoParquet & OpenStreetMap)
- ✅ Local headless browser & Lighthouse performance auditing
- ✅ Deterministic, explainable opportunity scoring

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS ADMIN DASHBOARD                         │
│   (App Router, TypeScript Strict, Tailwind CSS, TanStack Query/Table)  │
│  • Overview KPIs & Charts        • Live Scan Monitor & SSE Logs        │
│  • Lead Explorer & Filters       • Lead Intelligence Dossier & Report  │
│  • Scan Launcher & Presets       • System Doctor Diagnostics & Settings│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON & SSE (Port 8787)
┌───────────────────────────────────▼────────────────────────────────────┐
│                         FASTAPI BACKEND LAYER                          │
│   (Uvicorn, REST Endpoints, Background Scan Manager, Event Streaming)  │
│  • /api/dashboard    • /api/scans       • /api/leads    • /api/markets │
│  • /api/verticals    • /api/reports     • /api/settings • /api/system  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ In-Process Pipeline Invocation
┌───────────────────────────────────▼────────────────────────────────────┐
│                    LEADENGINE PYTHON CORE PIPELINE                     │
│  1. Market Resolution (Offline Curated Cache & Nominatim Geocoding)    │
│  2. Business Discovery (Overture Maps GeoParquet & OpenStreetMap)      │
│  3. Normalization & Deduplication (Haversine 300m + RapidFuzz 85%)     │
│  4. Data Quality Hardening & Deterministic Vertical Validation         │
│  5. Social Re-routing (Social URLs -> NO_WEBSITE opportunities)        │
│  6. Multi-Page Crawler (Emails, Phones, Socials, Booking & Menus)      │
│  7. Zero-Browser Technical & SEO Audit (HTTPS, Mobile, Schema.org)     │
│  8. Local Headless Lighthouse Deep Audit (Core Web Vitals & Perf)      │
│  9. Opportunity Scoring (0-100), Tiering (A+, A, B, C, D) & Angles     │
│ 10. Multi-Tab Excel (.xlsx), CRM-Ready CSV & Responsive HTML Reports   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   SQLite DB (WAL)   │
                         │ data/lead_engine.db │
                         └─────────────────────┘
```

---

## Quick Start: Launching the Web UI

To launch both the **FastAPI backend** (port `8787`) and the **Next.js Admin Dashboard** (port `3000`) simultaneously with unified process lifecycle management:

```powershell
python lead_engine.py ui
```

Or for live frontend hot-reloading development:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

- **Dashboard UI**: [http://localhost:3000](http://localhost:3000)
- **Interactive API Documentation**: [http://127.0.0.1:8787/docs](http://127.0.0.1:8787/docs)
- **API Health Check**: [http://127.0.0.1:8787/api/health](http://127.0.0.1:8787/api/health)

Press `Ctrl+C` in the terminal to gracefully terminate both servers.

---

## All CLI Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `ui` | Launch FastAPI backend + Next.js Admin Dashboard with unified shutdown | `python lead_engine.py ui` |
| `api` | Run standalone FastAPI REST and SSE application server | `python lead_engine.py api --port 8787` |
| `doctor` | Verify environment, database, browsers, and data connectivity | `python lead_engine.py doctor` |
| `run` | Execute discovery, audit, scoring, and exports via CLI | `python lead_engine.py run -m "Austin, TX" -v restaurant -t 50` |
| `markets` | List offline curated markets and cached bounding boxes | `python lead_engine.py markets` |
| `verticals` | List configured business niches, categories, and OSM tags | `python lead_engine.py verticals` |
| `inspect` | Print terminal card with full findings and score breakdown for a lead | `python lead_engine.py inspect --business-id 42` |
| `report` | Generate a standalone responsive HTML audit report | `python lead_engine.py report --business-id 42` |
| `resume` | Resume an interrupted run from database checkpoints | `python lead_engine.py resume --run-id 3` |
| `stats` | Display overall database prospecting metrics | `python lead_engine.py stats` |

---

## Output Files

Every run creates two deliverables under `output/`:

1. **Excel Workbook (`.xlsx`)**:
   - `HOT LEADS`: Prospects scoring in Tier A+ (80–100)
   - `A LEADS`: Prospects scoring in Tier A (65–79)
   - `B LEADS`: Prospects scoring in Tier B (50–64)
   - `NO WEBSITE`: Active businesses lacking an official website
   - `WEBSITE REDESIGN`: Leads needing a redesign or performance overhaul
   - `SEO OPPORTUNITIES`: Leads with missing metadata, schema, or low SEO scores
   - `ALL QUALIFIED`: Complete list of qualified opportunities
   - `ALL DISCOVERED`: All raw unique candidate entities
   - `REJECTED`: Multi-location chains, franchises, or filtered listings
   - `RUN SUMMARY`: Executive audit overview and conversion rates
2. **CSV Export (`.csv`)**: Single-row-per-lead flattened format for immediate CRM import.

---

## Scoring Model (0–100)

LeadEngine evaluates four distinct opportunity pillars:

1. **Website Opportunity (0–55 pts)**:
   - No website found: `+40`
   - Unreachable domain: `+35`
   - Missing mobile viewport: `+20`
   - Missing HTTPS: `+15`
   - Performance < 40: `+20` | Performance 40-59: `+12`
   - No contact CTA or contact page: `+6`
   - No detectable analytics: `+3`
2. **SEO Opportunity (0–20 pts)**:
   - SEO score < 50: `+18` | SEO score 50-64: `+12`
   - Missing JSON-LD structured data: `+6`
   - Missing vertical-specific schema: `+5`
   - Missing title or meta description: `+5` / `+4`
   - Missing H1 heading or canonical: `+3` / `+2`
3. **Vertical-Specific Opportunity (0–15 pts)**:
   - *Restaurants*: PDF-only menu (`+8`), No online reservations (`+10`), No online ordering (`+5`)
   - *Hospitality*: No direct booking engine (`+12`), Missing room showcase (`+5`)
   - *Real Estate*: No property search filter (`+10`), Weak valuation lead funnel (`+8`)
4. **Contactability (0–10 pts)**:
   - DNS MX-verified public business email: `+5`
   - Telephone number: `+3`
   - Contact form: `+2`
   - Business social account: `+2`

### Prospect Tiers:
- **A+ (80–100)**: Hot leads — severe technical friction, high conversion opportunity.
- **A (65–79)**: Strong leads — major deficiencies in mobile or SEO.
- **B (50–64)**: Moderate leads — good base site with clear optimization gaps.
- **C (35–49)**: Low opportunity.
- **D (< 35)**: Not recommended.

---

## Configuration

All rules and constants are externalized in `config/`:
- `config/settings.yaml`: Concurrency, timeouts, crawl depths, Lighthouse parameters.
- `config/verticals.yaml`: Supported vertical niches, categories, keywords, and OSM tags.
- `config/chain_domains.yaml`: Known chain domains and multi-location thresholds.
- `config/scoring.yaml`: Weights, pillar caps, and tier thresholds.

---

## Compliance & Safety

- **Internal Prospecting Only**: LeadEngine is built for legitimate B2B research. It does not automate bulk email dispatch, form submission, or social DM spam.
- **Respectful Crawling**: Max 8 pages per site, bounded concurrency (default 4 concurrent sites), robots-aware headers, 3MB body limits, and per-domain throttling.
- **SSRF Protection**: Prohibits private networks (`10.0.0.0/8`, `192.168.0.0/16`, `127.0.0.1`, `169.254.169.254`) and non-HTTP protocols.
- **Public Contacts Only**: Collects only publicly published business contact details (`info@`, `hello@`, contact forms). Never manufactures or guesses employee emails.
# Phase 3.5 workspace and client reports

LeadEngine includes an editable lead workspace, accessible draft/apply filters, semantic opportunity/status colors, and versioned PlaneByte client PDFs. Open a lead or its Report column to generate a PDF from stored evidence; the reports library separates PDFs from campaign CSV/XLSX exports. See [Phase 3.5 report](docs/PHASE_3_5_REPORT.md) and [deployment instructions](docs/DEPLOYMENT.md). The accepted Phase 3 cloud architecture and Google account allowlist are retained.



## Phase 3.6 workspace and reports

Public social profiles, versioned mid-market targeting, commercial-fit filters, private scan-time website captures and PlaneByte client report V2 are described in [the delivery report](docs/PHASE_3_6_REPORT.md). Campaigns, scans and leads support scoped permanent deletion; see [deletion behavior](docs/PERMANENT_DELETION.md).
