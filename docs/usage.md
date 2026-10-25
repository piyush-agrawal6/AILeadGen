# LeadEngine CLI Usage Guide

## Quick Start

Activate your virtual environment:

```powershell
# Windows
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

Run system diagnostics:

```bash
python lead_engine.py doctor
```

---

## 1. Running a Discovery & Qualification Scan

### Basic Run
Discover and qualify up to 250 restaurant prospects in Austin, Texas:

```bash
python lead_engine.py run \
  --market "Austin, Texas, USA" \
  --vertical restaurant \
  --target 250
```

### Options & Flags
- `--market, -m`: Target geographic market name (e.g. `"Austin, Texas, USA"`, `"Miami, FL"`, `"London, UK"`).
- `--vertical, -v`: Business vertical (`restaurant`, `hospitality`, `real_estate`).
- `--target, -t`: Desired target count of **qualified prospects** (default: `250`).
- `--include-chains`: Include national franchise chains (disabled by default to focus on independent businesses).
- `--no-lighthouse`: Skip deep Lighthouse Web Vitals audits for ultra-fast scanning.
- `--verbose, -v`: Enable detailed debug logging to console and `logs/lead-engine.log`.

### Small Fast Test Scan
```bash
python lead_engine.py run \
  --market "Austin, Texas, USA" \
  --vertical restaurant \
  --target 10 \
  --no-lighthouse
```

---

## 2. Viewing Supported Markets & Verticals

### List Curated Offline Markets
```bash
python lead_engine.py markets
```

### List Configured Verticals & OSM Tags
```bash
python lead_engine.py verticals
```

---

## 3. Lead Inspection & Standalone Reports

### Inspect a Lead in Terminal
Print complete contact information, audit findings, and score breakdown for a single business:

```bash
python lead_engine.py inspect --business-id 42
```

### Generate Standalone HTML Lead Report
Generate an executive-ready HTML prospect report with responsive styling:

```bash
python lead_engine.py report --business-id 42
```

The report is saved to `output/reports/<id>_<business_name>.html`.

---

## 4. Pipeline Resumption & Database Metrics

### Resume an Interrupted Run
If a scan is stopped due to machine reboot or network interruption, resume it directly from stored checkpoints:

```bash
python lead_engine.py resume --run-id 3
```

### View Prospecting Statistics
```bash
python lead_engine.py stats
```

---

## 5. Configuration Files

- `config/settings.yaml`: Concurrency, timeouts, crawl depths, Lighthouse settings.
- `config/verticals.yaml`: Industry vertical definitions, OSM tags, and category keywords.
- `config/chain_domains.yaml`: Known chain domains and multi-location frequency thresholds.
- `config/scoring.yaml`: Scoring rules, weights, pillar caps, and tier thresholds.
