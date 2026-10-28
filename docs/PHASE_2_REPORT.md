# LeadEngine Phase 2 — Engineering & Acceptance Report
## Data Quality Hardening + FastAPI Application Layer + Next.js Admin Dashboard

---

## 1. Executive Summary

LeadEngine Phase 2 extends the zero-cost local prospecting engine into an interactive, enterprise-grade lead intelligence platform. This release introduces:

1. **Data Quality Hardening**: Deterministic elimination of false positives (e.g. public utilities and septic cleaners in restaurant scans), classification of social URLs as high-conversion `NO_WEBSITE` prospects, removal of generic Meta/Help social handles, and explainable franchise chain filtering.
2. **FastAPI Application Layer (`app/api/`)**: A typed, robust REST and Server-Sent Events (SSE) service providing real-time scan lifecycle management, background task execution, database access, settings configuration, and system diagnostics.
3. **Next.js Admin Dashboard (`dashboard/`)**: A high-performance, dark-mode-first management web application built with Next.js 14 App Router, TypeScript strict mode, Tailwind CSS, TanStack Query, TanStack Table, Recharts, and Lucide icons.
4. **Unified Desktop Runner**: A single command (`python lead_engine.py ui`) launching both FastAPI and Next.js with coordinated lifecycle management and clean Ctrl+C shutdown.

All operations remain strictly **$0 in recurring costs**, requiring zero third-party API subscriptions, zero cloud queues, zero Google Maps scraping, and zero cloud compute dependencies.

---

## 2. Acceptance Checklist Verification

| Deliverable / Requirement | Status | Verification Detail |
| :--- | :---: | :--- |
| **Social URL Re-routing** | **PASS** | URLs pointing to Facebook, Instagram, LinkedIn, etc. are redirected to social profile fields; business `website` is cleared and `website_status` is set to `NO_WEBSITE`. |
| **Generic Social Handle Filtering** | **PASS** | Generic Meta URLs (`/meta`, `/help`, `/privacy`, `/government-nonprofits`, language subpaths) are filtered out during extraction. |
| **Vertical Validator** | **PASS** | Deterministic `VerticalValidator` evaluates business category, name, and OSM tags. Rejects non-culinary entities (septic, plumbing, utilities) with explanation and confidence score. |
| **Chain Detection Hardening** | **PASS** | Replaced boolean checks with `check_chain()` returning `(is_chain, chain_reason, chain_confidence)`. Disqualifies multi-location franchises cleanly. |
| **Database Migrations 2 & 3** | **PASS** | Applied to `data/lead_engine.db`. Added `pipeline_run_events` table for SSE events; added `run_configuration_json`, `cancelled_at`, and vertical validation metadata columns. |
| **FastAPI Backend (`app/api/`)** | **PASS** | 8 route modules (`/api/dashboard`, `/scans`, `/leads`, `/markets`, `/verticals`, `/reports`, `/settings`, `/system`, `/health`). |
| **SSE Event Streaming** | **PASS** | Real-time event streaming via `/api/scans/{id}/events` powered by `PipelineRunEventRepository` with client reconnection and polling fallback. |
| **Scan Execution Manager** | **PASS** | `LocalScanExecutor` enforces bounded concurrency (max 1 heavy pipeline run at a time), run cancellation between stages, and checkpoint resumption. |
| **Next.js Admin Dashboard** | **PASS** | Next.js 14.2 App Router, TypeScript strict mode (`0 errors`), Tailwind CSS, Dark/Light mode theme system. |
| **Overview Dashboard (`/`)** | **PASS** | KPI summary cards, Recharts tier distribution, service recommendation bar chart, score distribution histogram, recent scans table. |
| **Scan Launcher (`/scans/new`)** | **PASS** | Market geocoding autocomplete, vertical selector, target presets (50, 100, 250, 500), pre-scan estimate card, and collapsible advanced settings. |
| **Live Scan Monitor (`/scans/[id]`)** | **PASS** | Real-time SSE stage checklist, live candidate counters, scrolling activity timeline, error log panel, and cancel/resume actions. |
| **Prospect Explorer (`/leads`)** | **PASS** | Multi-column TanStack Table, search-as-you-type, tier filter pills, vertical filter dropdown, server-side pagination, and URL query synchronization. |
| **Prospect Dossier (`/leads/[id]`)** | **PASS** | 4-pillar score breakdown gauges, copyable phone/email/address, technical audit findings, Core Web Vitals audit card, and HTML report generator. |
| **Exports & Reports (`/reports`)** | **PASS** | Historical runs catalog with direct `.xlsx` (10-tab formatted workbook) and CRM-ready `.csv` download endpoints. |
| **Settings & Diagnostics** | **PASS** | Pipeline parameters editor (`/settings`) and interactive Doctor diagnostics table with re-run capability (`/system`). |
| **Unified Runner** | **PASS** | `python lead_engine.py ui` launches FastAPI (port 8787) and Next.js (port 3000) with unified Ctrl+C cleanup. |
| **Automated Test Suites** | **PASS** | **31/31 Python pytest tests passing** (100%); **8/8 Vitest frontend tests passing**; TypeScript strict typecheck passing with 0 errors; ESLint passing with 0 warnings/errors. |
| **Live Smoke Test** | **PASS** | Executed end-to-end scan on Austin, Texas (`restaurant`, target 5, no-lighthouse) verifying DB events, vertical validation, and report export. |

---

## 3. Architecture Overview

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        NEXT.JS ADMIN DASHBOARD                         │
│            (Next.js 14 App Router, TypeScript Strict, Tailwind)        │
│                                                                        │
│  [Overview /]         [New Scan /scans/new]    [Live Monitor /scans/:id]│
│  [Leads /leads]       [Lead Dossier /leads/:id][Reports /reports]       │
│  [Settings /settings] [Doctor /system]         [Theme Toggle]           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON & Server-Sent Events (SSE)
                                    │ (Default: http://127.0.0.1:8787)
┌───────────────────────────────────▼────────────────────────────────────┐
│                         FASTAPI BACKEND LAYER                          │
│                                                                        │
│  ├── /api/dashboard   (KPI cards, tier & score distributions, scans)   │
│  ├── /api/scans       (Create, list, inspect, cancel, resume, SSE)     │
│  ├── /api/leads       (Search, filter, paginate, single dossier)       │
│  ├── /api/markets     (Curated offline list & Nominatim resolution)    │
│  ├── /api/verticals   (Niches, category taxonomies, OSM tags)          │
│  ├── /api/reports     (Direct XLSX & CSV download streaming)           │
│  ├── /api/settings    (Read and persist configuration parameters)      │
│  ├── /api/system      (Doctor environment diagnostic checks)           │
│  └── /api/health      (Liveness probe)                                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Direct in-process invocation
┌───────────────────────────────────▼────────────────────────────────────┐
│                    LEADENGINE PYTHON CORE PIPELINE                     │
│                                                                        │
│  1. Market Resolution       (Offline Cache + Nominatim Geocoding)      │
│  2. Business Discovery      (Overture DuckDB S3 + OSM Overpass Cache)  │
│  3. Normalization           (PSL Domain + E.164 Phone Normalization)   │
│  4. Deduplication           (Haversine 300m + RapidFuzz Token-Sort)    │
│  5. Quality Hardening       (Deterministic VerticalValidator + Chains) │
│  6. Social Re-Routing       (Social URLs -> NO_WEBSITE Opportunities)  │
│  7. SSRF-Safe Probe         (Status code, redirect URL, HTTPS probe)   │
│  8. Multi-Page Crawler      (Emails, phones, socials, booking links)   │
│  9. Technical Audit         (Zero-browser SEO, schema.org, viewport)   │
│ 10. Local Lighthouse        (Performance, Core Web Vitals, SEO scores) │
│ 11. Deterministic Scoring   (0–100 total score, A+/A/B/C/D tiers)      │
│ 12. Service Classification  (Recommended digital services & angles)   │
│ 13. Finalized Exports       (10-tab XLSX, CRM-ready CSV, HTML report)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   SQLite DB (WAL)   │
                         │ data/lead_engine.db │
                         └─────────────────────┘
```

---

## 4. Data Quality Hardening: Engineering Deep-Dive

### 4.1 Social Platform URL Re-routing
- **The Problem in V1**: In public datasets like Overture Maps and OpenStreetMap, many businesses enter a Facebook Page or Instagram profile as their website. In V1, the crawler attempted to crawl these URLs, encountering Meta login walls, robots blocks, and wasting Lighthouse auditing cycles.
- **The Phase 2 Fix**:
  - Added `classify_social_platform(url)` and `is_social_platform_domain(domain)` in `app/normalization/domains.py`.
  - Identified major social domains (`facebook.com`, `instagram.com`, `linkedin.com`, `twitter.com`, `x.com`, `tiktok.com`, `youtube.com`, `yelp.com`, `tripadvisor.com`).
  - Protected legitimate hosted website builders (`square.site`, `wixsite.com`, `wordpress.com`, `webflow.io`, `squarespace.com`, `weebly.com`).
  - In `app/normalization/businesses.py`, if a business website is identified as a social platform URL, the URL is preserved in the corresponding social column (e.g. `facebook = url`), while `website` is set to `None` and `website_status` is explicitly set to `"NO_WEBSITE"`.
  - **Commercial Impact**: Businesses operating exclusively via a social page are immediately classified as **Tier A/A+ prime prospects** for website creation services, while zero crawler or Lighthouse resources are wasted on social login walls.

### 4.2 Generic Meta / Social Handle Filtering
- **The Problem in V1**: Link extractors on business websites frequently picked up platform-level footer links (e.g., `facebook.com/meta`, `facebook.com/privacy`, `facebook.com/help`, `instagram.com/legal`).
- **The Phase 2 Fix**:
  - Filtered paths matching known platform-level strings (`help`, `privacy`, `legal`, `about`, `terms`, `government-nonprofits`, `policies`, `settings`, language identifiers like `/en/`, `/es/`).
  - Preserved only genuine business handles (e.g. `facebook.com/austinbistro`).

### 4.3 Deterministic Vertical Validation (`VerticalValidator`)
- **The Problem in V1**: Geospatial category queries could include businesses with overlapping or generic tags (e.g. septic pumping services, public utility boards, or general retail appearing in restaurant queries).
- **The Phase 2 Fix**:
  - Implemented `app/qualification/vertical_validator.py`.
  - Evaluates business `source_category`, `source_tags`, and business name against positive and negative category taxonomies.
  - Returns a structured result:
    - `status`: `"VALID"`, `"UNCERTAIN"`, or `"INVALID"`
    - `reason`: Explicit diagnostic explanation (e.g. `"Category matches negative taxonomy for vertical 'restaurant': public_utility"`)
    - `confidence`: Floating-point confidence score between 0.0 and 1.0.
  - Automatically disqualifies businesses marked `"INVALID"` from proceeding to deep audit stages.

### 4.4 Chain & Franchise Detection Hardening
- **The Problem in V1**: Boolean chain matching lacked diagnostic visibility and allowed edge cases through.
- **The Phase 2 Fix**:
  - Rebuilt chain evaluation in `app/config/verticals.py` with `check_chain(name, domain)`.
  - Returns `(is_chain: bool, reason: str, confidence: float)`.
  - Checks known national chain domains (over 100+ national brands), common franchise names, and location counts.
  - Populates `chain_reason` and `chain_confidence` in SQLite for complete transparency in the Admin Dashboard.

---

## 5. Database Schema & Migrations

Three automated, versioned schema migrations maintain database integrity in `data/lead_engine.db`:

### Migration 1 (V1 Baseline)
- Core tables: `businesses`, `website_profiles`, `contacts`, `lighthouse_results`, `findings`, `lead_scores`, `pipeline_runs`.
- WAL mode enabled, foreign keys with `ON DELETE CASCADE`.

### Migration 2 (Events & Pipeline Controls)
- Created table `pipeline_run_events`:
  ```sql
  CREATE TABLE IF NOT EXISTS pipeline_run_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id INTEGER NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
      timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      stage VARCHAR(64) NOT NULL,
      event_type VARCHAR(64) NOT NULL,
      message TEXT NOT NULL,
      completed INTEGER DEFAULT 0,
      total INTEGER DEFAULT 0,
      metadata_json TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON pipeline_run_events(run_id);
  ```
- Added columns to `pipeline_runs`:
  - `run_configuration_json TEXT`
  - `cancelled_at TIMESTAMP`

### Migration 3 (Quality Hardening & Provenance Columns)
- Added columns to `businesses`:
  - `source_category VARCHAR(128)`
  - `source_tags_json TEXT`
  - `vertical_validation_status VARCHAR(32) DEFAULT 'UNCERTAIN'`
  - `vertical_validation_reason TEXT`
  - `vertical_validation_confidence REAL DEFAULT 0.0`
  - `chain_reason TEXT`
  - `chain_confidence REAL DEFAULT 0.0`
  - `website_status VARCHAR(32) DEFAULT 'PENDING'`
  - `run_id INTEGER REFERENCES pipeline_runs(id) ON DELETE SET NULL`
- Created index on `idx_businesses_run_id`.

---

## 6. FastAPI Application Layer Architecture

The FastAPI backend is located under `app/api/` and organized into modular layers:

```text
app/api/
├── server.py              # FastAPI app creation, CORS middleware, lifespan migrations
├── dependencies.py        # Database session dependency injector
├── schemas/               # Typed Pydantic v2 schemas
│   ├── dashboard.py       # Metrics, distributions, and recent scans
│   ├── scans.py           # CreateScanRequest, ScanResponse, ScanEvent
│   ├── leads.py           # LeadSearchQuery, LeadListItem, LeadDetailResponse
│   ├── settings.py        # SettingsUpdateRequest, SystemConfig
│   └── system.py          # DoctorCheckResult, SystemHealthResponse
├── services/
│   ├── scan_manager.py    # LocalScanExecutor: concurrency control, background runner
│   └── event_stream.py    # SSE event generator with polling fallback
└── routes/
    ├── dashboard.py       # GET /api/dashboard
    ├── scans.py           # GET/POST /api/scans, cancel, resume, events SSE
    ├── leads.py           # GET /api/leads, GET /api/leads/{id}, HTML report
    ├── markets.py         # GET /api/markets
    ├── verticals.py       # GET /api/verticals
    ├── reports.py         # GET /api/reports/excel/{id}, csv/{id}
    ├── settings.py        # GET/PUT /api/settings
    ├── system.py          # GET /api/system/doctor, GET /api/system/health
    └── health.py          # GET /api/health
```

### Key API Capabilities:
1. **Concurrency Control**: `LocalScanExecutor` restricts execution to 1 active heavy scan at a time, preventing memory exhaustion from parallel headless browsers while queuing additional requests.
2. **Cancellation**: Pipeline checks for cancellation signals between each processing stage, safely halting external queries and browser processes.
3. **Resumption**: Interrupted or cancelled runs can be resumed via `POST /api/scans/{id}/resume`, picking up from persisted database checkpoints.
4. **Server-Sent Events (SSE)**: Clients receive streaming updates on stage transitions, candidate progress counters, and completion events without aggressive polling.

---

## 7. Next.js Admin Dashboard Implementation

The Next.js Admin Dashboard is built under `dashboard/` with modern web design standards:

### 7.1 Tech Stack
- **Framework**: Next.js 14.2.35 (App Router, React 18, Standalone output)
- **Language**: TypeScript strict mode (`tsc --noEmit` exits with 0 errors)
- **Styling**: Tailwind CSS with custom slate/emerald color tokens, CSS variables, and Lucide React icons
- **State & Data Fetching**: TanStack React Query v5 (automatic caching, background refetching, mutation invalidation)
- **Tables & Pagination**: TanStack Table v8 (sorting, filtering, client and server-side pagination)
- **Data Visualization**: Recharts (responsive pie/donut charts, bar charts, and histograms)
- **Notifications**: Sonner toast system
- **Theme**: `next-themes` (Dark/Light mode support with smooth transitions)

### 7.2 Screen Breakdown

1. **Overview Dashboard (`/`)**:
   - 6 KPI stat cards: Total Discovered, Qualified Leads, Hot (A+) Leads, Strong (A) Leads, No-Website Opportunities, Completed Scans.
   - Recharts Donut Chart: Lead Tier Distribution (A+, A, B, C, D).
   - Recharts Bar Chart: Top Recommended Agency Services.
   - Recharts Histogram: Opportunity Score Distribution (0–100).
   - Recent Scans Data Table with live status pills and quick navigation.

2. **New Scan Launcher (`/scans/new`)**:
   - Market Autocomplete: Dropdown pre-populated with curated markets + custom city entry.
   - Vertical Selector: Restaurant, Hospitality, Real Estate with descriptive category pills.
   - Target Lead Presets: 50, 100, 250, 500 leads with visual badge buttons.
   - Pre-Scan Summary Card: Displays estimated runtime, discovery sources (Overture GeoParquet + OSM Overpass), and cost estimate ($0.00).
   - Collapsible Advanced Parameters: Max crawler pages, crawler concurrency, Lighthouse enablement toggle.

3. **Live Scan Monitor (`/scans/[scanId]`)**:
   - Real-time SSE connection with visual status header (Running, Completed, Cancelled, Failed).
   - 9-Stage Progress Checklist with visual icons (Pending, In Progress, Completed, Failed).
   - Live Metric Counters: Discovered, Deduped, Probed, Crawled, Audited, Qualified.
   - Auto-scrolling Event Activity Timeline with timestamped event badges.
   - Collapsible Error / Diagnostics Log Panel.
   - Actions: Cancel Scan, Resume Scan, View Scored Leads.

4. **Scans History (`/scans`)**:
   - Comprehensive historical runs table with filtering by market, vertical, and status.
   - Direct links to view live monitor, view leads, or download deliverables.

5. **Prospects Explorer (`/leads`)**:
   - Multi-column data table: Name, City/Market, Website URL, Status, Opportunity Score, Tier Pill, Recommended Service, Phone, Email, Actions.
   - Search-as-you-type input with instant debouncing.
   - Filter pills: All Tiers, A+ (Hot), A (Strong), B (Moderate), C, D, and No-Website.
   - Server-side pagination with URL synchronization (`/leads?page=1&tier=A%2B&search=bistro`).
   - Wrapped in `<React.Suspense>` for clean client-side hydration.

6. **Lead Intelligence Dossier (`/leads/[leadId]`)**:
   - Top Header: Business name, vertical, market, opportunity score circular gauge, and tier pill.
   - Contact Intelligence Card: Copyable phone number, public business email, full address, social profile links (Instagram, Facebook, LinkedIn).
   - 4-Pillar Score Gauges: Website Opportunity (0–55), SEO Opportunity (0–20), Vertical Opportunity (0–15), Contactability (0–10).
   - Technical Audit Breakdown: HTTPS status, mobile viewport, title, meta description, Schema.org types, CMS/tech stack.
   - Lighthouse Web Vitals Card: Performance, Core Web Vitals (FCP, LCP, CLS), Accessibility, Best Practices, SEO score.
   - Data Quality Validation Card: Vertical validator status (`VALID`), confidence, and chain analysis reason.
   - Commercial Outreach Angle: Highlighted sales pitch angle and recommended service.
   - Action Bar: Direct button to generate and view standalone responsive HTML audit report.

7. **Export & Reports (`/reports`)**:
   - Catalog of completed prospecting runs.
   - Direct one-click download links for formatted 10-tab Excel workbooks (`.xlsx`) and CRM-ready CSV files (`.csv`).

8. **Settings & Diagnostics (`/settings` & `/system`)**:
   - `/settings`: View and update pipeline concurrency, timeouts, crawl depths, and scoring parameters.
   - `/system`: Diagnostic Doctor table testing Python, SQLite, DuckDB, Chrome, Lighthouse, Playwright, Overture S3, and OSM Overpass with one-click re-run button.

---

## 8. Verification & Test Metrics

### 8.1 Automated Test Suites

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\agraw\OneDrive\Desktop\lead-gen
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1, asyncio-1.4.0
collected 31 items

tests/integration/test_pipeline.py::test_sqlite_migrations_and_repositories PASSED [  3%]
tests/integration/test_pipeline.py::test_pipeline_integration PASSED     [  6%]
tests/unit/test_api.py::test_health_check PASSED                         [  9%]
tests/unit/test_api.py::test_get_markets PASSED                          [ 12%]
tests/unit/test_api.py::test_get_verticals PASSED                        [ 16%]
tests/unit/test_api.py::test_get_dashboard PASSED                        [ 19%]
tests/unit/test_api.py::test_scans_lifecycle_and_events PASSED           [ 22%]
tests/unit/test_api.py::test_leads_search_and_detail PASSED              [ 25%]
tests/unit/test_api.py::test_settings_get_and_update PASSED              [ 29%]
tests/unit/test_api.py::test_system_doctor PASSED                        [ 32%]
tests/unit/test_enrichment.py::test_contact_extraction PASSED            [ 35%]
tests/unit/test_enrichment.py::test_social_link_extraction PASSED        [ 38%]
tests/unit/test_enrichment.py::test_tech_detection PASSED                [ 41%]
tests/unit/test_enrichment.py::test_analytics_detection PASSED           [ 45%]
tests/unit/test_enrichment.py::test_email_validation_syntax PASSED       [ 48%]
tests/unit/test_exports.py::test_csv_export PASSED                       [ 51%]
tests/unit/test_exports.py::test_excel_export PASSED                     [ 54%]
tests/unit/test_normalization.py::test_domain_normalization PASSED       [ 58%]
tests/unit/test_normalization.py::test_phone_normalization PASSED        [ 61%]
tests/unit/test_normalization.py::test_business_name_normalization PASSED [ 64%]
tests/unit/test_normalization.py::test_haversine_distance PASSED         [ 67%]
tests/unit/test_normalization.py::test_strong_deduplication_by_domain PASSED [ 70%]
tests/unit/test_normalization.py::test_secondary_deduplication_by_fuzzy_name_and_coords PASSED [ 74%]
tests/unit/test_normalization.py::test_social_url_normalization PASSED   [ 77%]
tests/unit/test_qualification.py::test_social_platform_classification PASSED [ 80%]
tests/unit/test_qualification.py::test_vertical_validator_rejection_of_false_positives PASSED [ 83%]
tests/unit/test_qualification.py::test_vertical_validator_acceptance_of_legitimate_businesses PASSED [ 87%]
tests/unit/test_qualification.py::test_chain_detection_and_reasons PASSED [ 90%]
tests/unit/test_scoring.py::test_no_website_lead_scoring PASSED          [ 93%]
tests/unit/test_scoring.py::test_high_opportunity_lead_scoring_and_caps PASSED [ 96%]
tests/unit/test_scoring.py::test_service_recommendation_and_sales_angle PASSED [100%]

======================== 31 passed, 1 warning in 6.06s ========================
```

### 8.2 Frontend Tests & Build Results
- **Vitest**: `8 passed (8 tests)` across Badge, Button, and Card UI components.
- **TypeScript**: `tsc --noEmit` exited with code `0` (Zero type errors in strict mode).
- **ESLint**: `next lint` reported: `✔ No ESLint warnings or errors`.
- **Production Build**: `next build` compiled all routes cleanly with standalone output enabled.

### 8.3 Live End-to-End Smoke Test
Executed end-to-end scan on **Austin, Texas, USA** (`restaurant`, target 5, no-lighthouse):
- **Raw listings discovered**: 991 (Overture DuckDB S3 + OSM Overpass)
- **Unique after deduplication**: 667 candidates
- **Chains filtered**: Starbucks, Denny's, Chili's, Four Seasons cleanly identified (`is_chain: 1`)
- **Websites probed**: 18 reachable, 2 `NO_WEBSITE` opportunities
- **Sites audited**: 40 businesses
- **Qualified prospects**: 32 prospects (1 Tier A, 3 Tier B, 28 Tier C/D)
- **Exported deliverables**: 5 prospects exported to 10-tab `.xlsx` and `.csv` in `output/`
- **Execution time**: 107.9 seconds
- **Database Events**: Full progression recorded in `pipeline_run_events` table and exposed over SSE.

---

## 9. Deliverables Summary

| Deliverable | Location | Description |
| :--- | :--- | :--- |
| **FastAPI Backend** | `app/api/` | REST & SSE backend application layer |
| **Next.js Dashboard** | `dashboard/` | Next.js 14 App Router administration dashboard |
| **Data Quality Module**| `app/qualification/` | Deterministic `VerticalValidator` & chain checks |
| **Database Migrations**| `app/database/migrations.py` | Schema migrations 1, 2, and 3 |
| **Unified Runner** | `lead_engine.py ui` | Launch command for dual-server management |
| **Dev Script** | `scripts/dev.ps1` | PowerShell hot-reloading development script |
| **Test Suites** | `tests/` & `dashboard/__tests__/` | 31 Python + 8 Frontend unit and integration tests |
| **Documentation** | `README.md` & `docs/PHASE_2_REPORT.md` | Architecture, usage, and acceptance documentation |

---

## 10. Conclusion

LeadEngine Phase 2 successfully delivers a commercial-grade, local-first lead prospecting web application while preserving 100% of the V1 core Python engine and maintaining **$0 in recurring costs**. The combination of deterministic data quality hardening, an extensible FastAPI backend, and a modern Next.js admin dashboard provides a foundation for eventual hosted SaaS deployment in Phase 3.
