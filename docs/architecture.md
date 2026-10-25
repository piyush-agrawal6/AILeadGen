# LeadEngine Architecture

## 1. Overview
LeadEngine is a local-first, zero-recurring-cost B2B lead discovery, technical auditing, and qualification engine. It combines open spatial data sources, lightweight static website analysis, local performance audits, and deterministic opportunity scoring to surface high-converting prospects for digital marketing and development agencies.

## 2. Core Architectural Principles
- **$0 Operating Cost**: Uses open geospatial data (Overture Maps Places, OpenStreetMap) and client-side analysis. No paid APIs, no proxies, no lead databases.
- **Explainable Scoring**: Deterministic rules-based scoring (0-100) across 4 pillars. No black-box AI hallucination in scoring.
- **Resource Conservative**: Cheap HTTP probing and HTML parsing run before headless browsers or Lighthouse. Lighthouse only executes for promising leads.
- **Fail-Safe & Resumable**: All discoveries, audit results, and findings are persisted in SQLite with WAL mode. Runs can be interrupted and resumed at any checkpoint.
- **Public & Compliant**: Discovers only publicly published business contact details (e.g. `info@`, `hello@`, contact forms). No private profile scraping, CAPTCHA bypassing, or invasive harvesting.

## 3. Data Flow Diagram

```text
[Human Market Query: e.g. "Austin, Texas, USA"]
                        ↓
             [Market Resolution (Cache/Nominatim)]
                        ↓ (Bounding Box)
    ┌───────────────────┴───────────────────┐
    ↓                                       ↓
[Overture Places GeoParquet (DuckDB)]    [OpenStreetMap (Overpass API)]
    └───────────────────┬───────────────────┘
                        ↓
            [Normalization (Name, Phone, Domain)]
                        ↓
         [Deduplication (Strong Domain/Phone + Fuzzy Nearby)]
                        ↓
            [Chain & Franchise Filtering]
                        ↓
            [Lightweight HTTP Probe (SSRF Check, Status, HTTPS)]
                        ↓
     ┌──────────────────┴──────────────────┐
     ↓                                     ↓
[Reachable Sites]                  [No-Website Leads]
     ↓                                     ↓
[Multi-Page Crawler (Max 8)]        [High Opportunity Score (+40)]
     ↓                                     ↓
[Public Contact & Social Extraction]       ↓
     ↓                                     ↓
[DNS MX Email Verification]                ↓
     ↓                                     ↓
[Static Technical & Vertical Audit]        ↓
     ↓                                     ↓
[Preliminary Opportunity Score]            ↓
     ↓                                     ↓
[Lighthouse CLI (Promising Sites Only)]    ↓
     └──────────────────┬──────────────────┘
                        ↓
         [Deterministic Scoring (0-100) & Tiers (A+, A, B, C, D)]
                        ↓
        [Service Classification & Sales Angle Generation]
                        ↓
             [Final Ranking & Target Filtering]
                        ↓
             [Excel (10 Tabs) & CSV Export]
```

## 4. Pipeline Stages & Persistence
1. `MARKET_RESOLVED`: Resolves geographic query to bounding box and country/state/city.
2. `DISCOVERED`: Ingests raw listings from Overture and OSM into `businesses` table.
3. `NORMALIZED`: Normalizes names, phone numbers (E.164), domains (apex domain), and websites.
4. `DEDUPED`: Flags exact duplicates (same domain/phone) and secondary duplicates (name similarity >= 85% within 300m).
5. `FILTERED`: Filters national chains and multi-location franchises (`config/chain_domains.yaml`).
6. `HTTP_PROBED`: Validates reachability, HTTPS encryption, redirect chains, and guards against SSRF.
7. `CRAWLED`: Discovers internal priority pages (`/contact`, `/about`, `/menu`, `/reservations`), extracting emails, phones, forms, and social accounts.
8. `QUICK_AUDITED`: Audits HTML title, meta description, viewport, headings, canonicals, analytics tags, JSON-LD schema.
9. `LIGHTHOUSE_AUDITED`: Local Lighthouse CLI audits performance, SEO, accessibility, and Core Web Vitals.
10. `SCORED`: Calculates normalized 0-100 score with breakdown and assigns tier (A+, A, B, C, D).
11. `QUALIFIED`: Verifies opportunity presence and public contactability.
12. `EXPORTED`: Generates 10-tab Excel workbook and CSV export.

## 5. Security & SSRF Protection
- All URLs pass through `is_safe_url` in `app/utils/urls.py`.
- Prohibits non-HTTP schemes (`file://`, `javascript:`, `data:`).
- Rejects loopback addresses (`127.0.0.1`, `localhost`, `::1`).
- Rejects cloud metadata endpoints (`169.254.169.254`).
- Rejects private IPv4 ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) and IPv6 private/link-local ranges.

## 6. Phase 2 Future Proposals (Documented)
1. **Next.js CRM Dashboard**: Local web interface to browse leads, filter by score, and mark outreach status (New, Contacted, Meeting Booked, Not Interested).
2. **Automated Proposal Generator**: Generate 1-page PDF proposal previews highlighting specific technical issues found during the audit.
3. **Visual Screenshot Comparison**: Automated before/after mockups using Playwright page screenshots.
