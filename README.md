# LeadEngine — Zero-Cost B2B Lead Discovery & Qualification Engine

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
Market Query ("Austin, Texas, USA")
        ↓
Market Resolution (Offline Curated Cache & Nominatim)
        ↓
Business Discovery (Overture Maps Places via DuckDB & OpenStreetMap via Overpass)
        ↓
Data Normalization & Deduplication (Strong domain/phone + fuzzy nearby dedupe)
        ↓
Franchise & National Chain Filtering
        ↓
Website Reachability & SSRF Safety Probing
        ↓
Multi-Page Crawler (Public contacts, social accounts, booking links, menus)
        ↓
Zero-Browser Technical & SEO Audit (HTTPS, viewport, title, meta desc, schema.org)
        ↓
Local Lighthouse Deep Audit (Performance, Core Web Vitals, SEO, Accessibility)
        ↓
Deterministic Lead Opportunity Scoring (0–100) & Tier Assignment (A+, A, B, C, D)
        ↓
Automated Service Classification & Sales Angle Generation
        ↓
Multi-Tab Excel (.xlsx) & CSV (.csv) Export
```

---

## Requirements

- **Python**: 3.12+ (64-bit)
- **Node.js**: v18+ (used for local Lighthouse CLI)
- **Chrome / Edge / Chromium**: Standard Google Chrome or Microsoft Edge installed on system
- **Operating System**: Windows 10/11, macOS, or Linux

---

## Installation & Setup

### Windows (Automated PowerShell Setup)

Run the included automated setup script in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
```

Or step-by-step:

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Install Playwright Chromium
python -m playwright install chromium

# 4. Install local Lighthouse CLI via npm
npm install lighthouse

# 5. Run system diagnostics
python lead_engine.py doctor
```

### macOS / Linux

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and install Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Install Playwright Chromium
python -m playwright install chromium

# 4. Install local Lighthouse CLI via npm
npm install lighthouse

# 5. Run system diagnostics
python lead_engine.py doctor
```

---

## Running LeadEngine

### 1. Run a Prospecting Scan

Discover and qualify the best 250 restaurant prospects in Austin, Texas:

```bash
python lead_engine.py run \
  --market "Austin, Texas, USA" \
  --vertical restaurant \
  --target 250
```

### Options & Flags:
- `--market, -m`: Target geographic market name (e.g. `"Austin, Texas, USA"`, `"Miami, Florida, USA"`, `"London, UK"`).
- `--vertical, -v`: Business vertical (`restaurant`, `hospitality`, `real_estate`).
- `--target, -t`: Target number of **qualified leads** to produce (default: `250`).
- `--include-chains`: Include national franchise chains (disabled by default to focus on independent businesses).
- `--no-lighthouse`: Skip deep Lighthouse Web Vitals audits for ultra-fast scanning.
- `--verbose, -v`: Enable detailed debug logging.

### 2. Fast Smoke Test (10 Leads)

```bash
python lead_engine.py run \
  --market "Austin, Texas, USA" \
  --vertical restaurant \
  --target 10 \
  --no-lighthouse
```

---

## All CLI Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `doctor` | Verify environment, database, browsers, and data connectivity | `python lead_engine.py doctor` |
| `run` | Execute discovery, audit, scoring, and exports | `python lead_engine.py run -m "Austin, TX" -v restaurant -t 50` |
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
